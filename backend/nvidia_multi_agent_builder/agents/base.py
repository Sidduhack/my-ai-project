"""Base agent class and agent registry."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.core import Event, EventType, publish_event
from nvidia_multi_agent_builder.core.exceptions import AgentError, AgentExecutionError
from nvidia_multi_agent_builder.db.models import AgentType, Task, TaskStatus
from nvidia_multi_agent_builder.models import (
    CompletionRequest,
    CompletionResponse,
    Message,
    ModelProvider,
    provider_registry,
    ModelRouter,
    health_tracker,
    scoring_engine,
)

logger = get_logger(__name__)


@dataclass
class AgentConfig:
    """Agent configuration."""

    system_prompt: str = ""
    temperature: float = 0.3
    max_tokens: int = 8192
    response_format: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result of agent execution."""

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    model_used: str | None = None
    provider_used: str | None = None
    latency_ms: float = 0.0
    tokens_used: int | None = None
    structured_output: Any = None


class BaseAgent(ABC):
    """Base class for all specialist agents."""

    # Override in subclasses
    agent_type: AgentType
    name: str
    description: str
    default_config: AgentConfig = AgentConfig()

    def __init__(
        self,
        agent_id: str | None = None,
        config: AgentConfig | None = None,
        model_router: ModelRouter | None = None,
    ):
        self.agent_id = agent_id or f"{self.agent_type.value}-{uuid4().hex[:8]}"
        self.config = config or self.default_config
        self.model_router = model_router
        self._memory: dict[str, Any] = {}

    @abstractmethod
    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        """Execute the agent's work on a task."""
        pass

    def build_prompt(self, task: Task, context: dict[str, Any]) -> list[Message]:
        """Build the prompt messages for the model."""
        messages = []

        # System prompt
        if self.config.system_prompt:
            messages.append(Message(role="system", content=self.config.system_prompt))

        # Context from project/agent memory
        if context.get("project_memory"):
            mem_content = self._format_memory(context["project_memory"])
            messages.append(Message(role="system", content=f"Project Context:\n{mem_content}"))

        if context.get("agent_memory"):
            mem_content = self._format_memory(context["agent_memory"])
            messages.append(Message(role="system", content=f"Your Memory:\n{mem_content}"))

        # Task description
        task_content = f"Task: {task.description}\n\n"
        if task.input_data:
            task_content += f"Input Data:\n{self._format_input(task.input_data)}\n\n"

        # Add any specific instructions
        instructions = self.get_instructions(task, context)
        if instructions:
            task_content += f"Instructions:\n{instructions}\n\n"

        messages.append(Message(role="user", content=task_content))

        return messages

    def _format_memory(self, memory: dict[str, Any]) -> str:
        """Format memory for prompt inclusion."""
        lines = []
        for key, value in memory.items():
            if isinstance(value, dict):
                lines.append(f"{key}: {value}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _format_input(self, input_data: dict[str, Any]) -> str:
        """Format input data for prompt."""
        import json
        return json.dumps(input_data, indent=2)

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        """Get agent-specific instructions. Override in subclasses."""
        return ""

    async def call_model(
        self,
        messages: list[Message],
        model_spec: str | None = None,
    ) -> CompletionResponse:
        """Call the model with fallback support."""
        if not self.model_router:
            raise AgentExecutionError(
                "No model router configured",
                agent_id=self.agent_id,
            )

        # Get provider registry
        providers = provider_registry.get_all_providers()
        if not providers:
            raise AgentExecutionError(
                "No model providers available",
                agent_id=self.agent_id,
            )

        # Build request
        request = CompletionRequest(
            model=model_spec or "",
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format=self.config.response_format,
            tools=self.config.tools,
        )

        # Get health and scoring
        health_check = {}
        for name, provider in providers.items():
            health_check[name] = await provider.health_check()

        # Get scoring for this agent
        scoring = {}
        for score in scoring_engine.get_all_scores(self.agent_type.value):
            scoring[score.model_id] = score.total_score

        # Execute with fallback
        try:
            response, provider_name, model_id = await self.model_router.execute_with_fallback(
                agent_type=self.agent_type.value,
                request=request,
                health_check=health_check,
                scoring=scoring,
            )

            # Record outcome for scoring
            health = health_tracker.get_health(model_id, provider_name)
            scoring_engine.update_from_health(
                self.agent_type.value,
                f"{provider_name}/{model_id}",
                health,
            )
            scoring_engine.record_outcome(
                self.agent_type.value,
                f"{provider_name}/{model_id}",
                True,
                response.latency_ms,
            )

            response.model = model_id
            return response

        except Exception as e:
            # Record failure
            logger.error("agent_model_call_failed", agent_id=self.agent_id, error=str(e))
            raise AgentExecutionError(
                f"Model call failed: {e}",
                agent_id=self.agent_id,
            ) from e

    def remember(self, key: str, value: Any) -> None:
        """Store in agent memory."""
        self._memory[key] = value

    def recall(self, key: str, default: Any = None) -> Any:
        """Retrieve from agent memory."""
        return self._memory.get(key, default)

    def get_memory(self) -> dict[str, Any]:
        """Get all agent memory."""
        return self._memory.copy()

    def clear_memory(self) -> None:
        """Clear agent memory."""
        self._memory.clear()

    async def on_task_start(self, task: Task) -> None:
        """Called when task starts."""
        await publish_event(
            EventType.AGENT_STARTED,
            {"agent_id": self.agent_id, "agent_type": self.agent_type.value, "task_id": task.id},
            source=self.agent_id,
        )

    async def on_task_complete(self, task: Task, result: AgentResult) -> None:
        """Called when task completes."""
        await publish_event(
            EventType.AGENT_COMPLETED,
            {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "task_id": task.id,
                "success": result.success,
            },
            source=self.agent_id,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.agent_id}, type={self.agent_type.value})>"


class AgentRegistry:
    """Registry for agent classes and instances."""

    def __init__(self):
        self._agent_classes: dict[AgentType, type[BaseAgent]] = {}
        self._agent_instances: dict[str, BaseAgent] = {}
        self._model_router: ModelRouter | None = None

    def register_agent_class(self, agent_class: type[BaseAgent]) -> None:
        """Register an agent class."""
        self._agent_classes[agent_class.agent_type] = agent_class
        logger.info("agent_class_registered", agent_type=agent_class.agent_type.value)

    def create_agent(
        self,
        agent_type: AgentType,
        agent_id: str | None = None,
        config: AgentConfig | None = None,
    ) -> BaseAgent:
        """Create an agent instance."""
        agent_class = self._agent_classes.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")

        agent = agent_class(
            agent_id=agent_id,
            config=config,
            model_router=self._model_router,
        )
        self._agent_instances[agent.agent_id] = agent
        logger.info("agent_created", agent_id=agent.agent_id, agent_type=agent_type.value)
        return agent

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        """Get agent instance by ID."""
        return self._agent_instances.get(agent_id)

    def get_agents_by_type(self, agent_type: AgentType) -> list[BaseAgent]:
        """Get all instances of an agent type."""
        return [
            a for a in self._agent_instances.values()
            if a.agent_type == agent_type
        ]

    def list_agent_types(self) -> list[AgentType]:
        """List registered agent types."""
        return list(self._agent_classes.keys())

    def set_model_router(self, router: ModelRouter) -> None:
        """Set model router for all agents."""
        self._model_router = router
        for agent in self._agent_instances.values():
            agent.model_router = router

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent instance."""
        if agent_id in self._agent_instances:
            del self._agent_instances[agent_id]
            return True
        return False


# Global agent registry
agent_registry = AgentRegistry()