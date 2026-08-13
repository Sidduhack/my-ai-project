"""Planner Agent - Creates project plans and task breakdowns."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task
from nvidia_multi_agent_builder.models import Message


class PlannerAgent(BaseAgent):
    """Plans project structure and breaks down into tasks."""

    agent_type = AgentType.PLANNER
    name = "Planner"
    description = "Creates project plans, task breakdowns, and timelines"

    default_config = AgentConfig(
        system_prompt="""You are an expert software project planner. Your job is to:
1. Analyze requirements and create comprehensive project plans
2. Break down projects into atomic, executable tasks
3. Identify dependencies between tasks
4. Estimate effort and prioritize tasks
5. Define clear acceptance criteria for each task

Output structured JSON with:
- project_overview: high-level summary
- tasks: list of tasks with id, description, agent_type, priority, dependencies, acceptance_criteria
- timeline: estimated phases
- risks: identified risks and mitigations""",
        temperature=0.3,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        return """Create a detailed project plan. Consider:
- All 18 specialist agents available
- Task dependencies (some tasks must complete before others)
- Priority: critical path tasks first
- Each task should be assignable to a single agent type
- Output valid JSON only"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)

        try:
            response = await self.call_model(messages)

            if response.content:
                import json
                plan = json.loads(response.content)

                return AgentResult(
                    success=True,
                    output=plan,
                    model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=plan,
                )
            else:
                return AgentResult(
                    success=False,
                    error="Empty response from model",
                )

        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Planning failed: {e}",
            )