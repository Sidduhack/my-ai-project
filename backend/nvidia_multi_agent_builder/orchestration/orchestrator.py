"""Main orchestrator - coordinates agents and tasks."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.core import Event, EventType, publish_event
from nvidia_multi_agent_builder.core.exceptions import OrchestrationError
from nvidia_multi_agent_builder.db import session_context, init_db
from nvidia_multi_agent_builder.db.models import (
    Agent,
    AgentType,
    Project,
    ProjectStatus,
    Task,
    TaskPriority,
    TaskStatus,
)
from nvidia_multi_agent_builder.models import (
    ModelRouter,
    provider_registry,
    health_tracker,
    scoring_engine,
)
from nvidia_multi_agent_builder.orchestration.scheduler import Scheduler, SchedulerConfig
from nvidia_multi_agent_builder.orchestration.state_machine import StateMachine
from nvidia_multi_agent_builder.orchestration.task_queue import TaskQueue

logger = get_logger(__name__)


class Orchestrator:
    """Central orchestration engine."""

    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        max_concurrent_per_agent: int = 3,
    ):
        self.task_queue = TaskQueue(max_concurrent=max_concurrent_tasks)
        self.model_router = ModelRouter(provider_registry)
        self.scheduler = Scheduler(
            task_queue=self.task_queue,
            executor=self._execute_task,
            config=SchedulerConfig(
                max_concurrent_tasks=max_concurrent_tasks,
                max_concurrent_per_agent=max_concurrent_per_agent,
            ),
        )
        self._running = False
        self._scheduler_task: asyncio.Task | None = None

        # Register default model routes
        self._register_default_routes()

    def _register_default_routes(self) -> None:
        """Register default model routes from config."""
        # This would load from model_registry.yaml
        # For now, register basic routes for all agent types
        routes = {
            AgentType.PLANNER: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/llama-3.1-70b-instruct"]),
            AgentType.ARCHITECT: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
            AgentType.UI_UX: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/llama-3.1-70b-instruct"]),
            AgentType.CREATIVE_DIRECTOR: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/llama-3.1-70b-instruct"]),
            AgentType.MOTION_DESIGNER: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/llama-3.1-70b-instruct"]),
            AgentType.FRONTEND: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
            AgentType.BACKEND: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
            AgentType.DATABASE: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
            AgentType.SECURITY: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
            AgentType.PERFORMANCE: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
            AgentType.TESTING: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
            AgentType.INTEGRATION: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
            AgentType.DEBUGGING: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
            AgentType.SOUND_ENGINEER: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/llama-3.1-70b-instruct"]),
            AgentType.ACCESSIBILITY: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/llama-3.1-70b-instruct"]),
            AgentType.SEO: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/llama-3.1-70b-instruct"]),
            AgentType.DOCUMENTATION: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/llama-3.1-70b-instruct"]),
            AgentType.CODE_REVIEWER: ("nvidia/nemotron-3-ultra", ["openai_compatible/gpt-4o", "local/codellama-34b-instruct"]),
        }

        for agent_type, (primary, fallbacks) in routes.items():
            from nvidia_multi_agent_builder.models.routing import ModelRoute
            route = ModelRoute(
                agent_type=agent_type,
                primary_model=primary,
                fallback_models=fallbacks,
            )
            self.model_router.register_route(route)

    async def start(self) -> None:
        """Start the orchestrator."""
        if self._running:
            return
        self._running = True
        await init_db()
        self._scheduler_task = asyncio.create_task(self.scheduler.start())
        logger.info("orchestrator_started")

    async def stop(self) -> None:
        """Stop the orchestrator."""
        if not self._running:
            return
        self._running = False
        await self.scheduler.stop()
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("orchestrator_stopped")

    async def create_project(
        self,
        name: str,
        description: str | None = None,
        requirements: dict[str, Any] | None = None,
    ) -> Project:
        """Create a new project."""
        async with session_context() as session:
            project = Project(
                name=name,
                description=description,
                status=ProjectStatus.CREATED,
                requirements=requirements or {},
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)

            await publish_event(
                EventType.PROJECT_CREATED,
                {"project_id": project.id, "name": name},
                source="orchestrator",
            )
            return project

    async def start_project(self, project_id: str) -> None:
        """Start project execution."""
        async with session_context() as session:
            project = await session.get(Project, project_id)
            if not project:
                raise OrchestrationError(f"Project not found: {project_id}")

            if not StateMachine.can_transition_project(project.status, ProjectStatus.PLANNING):
                raise OrchestrationError(f"Cannot start project in status: {project.status}")

            project.status = ProjectStatus.PLANNING
            project.started_at = datetime.now(UTC)
            await session.commit()

            # Create initial planning task
            await self._create_initial_tasks(project)

            await publish_event(
                EventType.PROJECT_STARTED,
                {"project_id": project_id},
                source="orchestrator",
            )

    async def _create_initial_tasks(self, project: Project) -> None:
        """Create initial planning tasks."""
        # First task: Planner creates the plan
        plan_task = Task(
            project_id=project.id,
            agent_id="planner",
            description="Create comprehensive project plan and task breakdown",
            priority=TaskPriority.CRITICAL,
            input_data={
                "requirements": project.requirements,
                "project_name": project.name,
            },
        )

        async with session_context() as session:
            session.add(plan_task)
            await session.commit()
            await session.refresh(plan_task)

        await self.task_queue.add_task(plan_task)

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task with the appropriate agent."""
        from nvidia_multi_agent_builder.agents import agent_registry, register_all_agents

        # Ensure agents are registered
        register_all_agents()

        # Get agent
        agent = agent_registry.get_agent(task.agent_id)
        if not agent:
            # Try to find by type
            agents = agent_registry.get_agents_by_type(AgentType(task.agent_id))
            if agents:
                agent = agents[0]
            else:
                raise OrchestrationError(f"No agent found for: {task.agent_id}")

        # Set model router
        agent.model_router = self.model_router

        # Build context from project memory
        context = await self._build_context(task)

        # Notify task start
        await agent.on_task_start(task)

        try:
            # Execute agent
            result = await agent.execute(task, context)

            # Update task with result
            async with session_context() as session:
                db_task = await session.get(Task, task.id)
                if db_task:
                    db_task.output_data = result.output
                    db_task.assigned_model = result.model_used
                    if result.success:
                        db_task.status = TaskStatus.COMPLETED
                        db_task.completed_at = datetime.now(UTC)
                    else:
                        db_task.status = TaskStatus.FAILED
                        db_task.error = result.error
                        db_task.completed_at = datetime.now(UTC)
                    await session.commit()

            # Store result in project memory
            await self._store_result(task, result)

            # Notify completion
            await agent.on_task_complete(task, result)

            # Create follow-up tasks based on result
            await self._create_followup_tasks(task, result)

            # Complete in queue
            await self.task_queue.complete_task(task.id, result.success)

        except Exception as e:
            logger.error("task_execution_failed", task_id=task.id, error=str(e), exc_info=True)
            async with session_context() as session:
                db_task = await session.get(Task, task.id)
                if db_task:
                    db_task.status = TaskStatus.FAILED
                    db_task.error = str(e)
                    db_task.completed_at = datetime.now(UTC)
                    await session.commit()
            await self.task_queue.fail_task(task.id, str(e))

    async def _build_context(self, task: Task) -> dict[str, Any]:
        """Build context for agent execution."""
        from nvidia_multi_agent_builder.db.models import ProjectMemory, AgentMemory

        async with session_context() as session:
            # Get project memory
            project_memories = await session.execute(
                "SELECT key, value FROM project_memory WHERE project_id = ?",
                (task.project_id,)
            )
            project_memory = {row.key: row.value for row in project_memories}

            # Get agent memory
            agent_memories = await session.execute(
                "SELECT key, value FROM agent_memory WHERE agent_id = ?",
                (task.agent_id,)
            )
            agent_memory = {row.key: row.value for row in agent_memories}

        return {
            "project_memory": project_memory,
            "agent_memory": agent_memory,
            "task_input": task.input_data,
        }

    async def _store_result(self, task: Task, result) -> None:
        """Store agent result in project memory."""
        from nvidia_multi_agent_builder.db.models import ProjectMemory

        async with session_context() as session:
            memory = ProjectMemory(
                project_id=task.project_id,
                key=f"{task.agent_id}_result",
                value=result.output,
                category="agent_output",
                importance=5,
            )
            session.add(memory)
            await session.commit()

    async def _create_followup_tasks(self, task: Task, result) -> None:
        """Create follow-up tasks based on agent output."""
        # This would be customized per agent type
        # For now, simple example: if planner creates tasks, queue them
        if task.agent_id == "planner" and result.success:
            plan = result.structured_output
            if plan and "tasks" in plan:
                for task_data in plan["tasks"]:
                    new_task = Task(
                        project_id=task.project_id,
                        agent_id=task_data.get("agent_type", "planner"),
                        description=task_data.get("description", ""),
                        priority=TaskPriority(task_data.get("priority", "normal")),
                        dependencies=task_data.get("dependencies", []),
                        input_data=task_data.get("input_data", {}),
                    )
                    async with session_context() as session:
                        session.add(new_task)
                        await session.commit()
                        await session.refresh(new_task)
                    await self.task_queue.add_task(new_task)

    async def get_project_status(self, project_id: str) -> dict[str, Any]:
        """Get project status with task details."""
        async with session_context() as session:
            project = await session.get(Project, project_id)
            if not project:
                return {"error": "Project not found"}

            # Get tasks
            tasks = await session.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at",
                (project_id,)
            )

            task_list = []
            for t in tasks:
                task_list.append({
                    "id": t.id,
                    "agent_id": t.agent_id,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "created_at": t.created_at,
                    "started_at": t.started_at,
                    "completed_at": t.completed_at,
                    "error": t.error,
                })

            return {
                "project_id": project.id,
                "name": project.name,
                "status": project.status,
                "created_at": project.created_at,
                "started_at": project.started_at,
                "completed_at": project.completed_at,
                "tasks": task_list,
                "queue_status": self.task_queue.get_queue_status(),
            }