"""Creative Director Agent - Oversees creative direction."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class CreativeDirectorAgent(BaseAgent):
    """Oversees creative direction and brand consistency."""

    agent_type = AgentType.CREATIVE_DIRECTOR
    name = "Creative Director"
    description = "Defines creative vision, brand identity, and ensures consistency"

    default_config = AgentConfig(
        system_prompt="""You are a creative director. Define and maintain creative vision:
1. Brand identity (logo, colors, typography, voice)
2. Creative strategy and direction
3. Visual language and design principles
4. Brand guidelines and usage rules
5. Marketing and promotional concepts
6. Creative review and approval

Output structured JSON with:
- brand_identity: logo, colors, typography, imagery
- brand_voice: tone, messaging pillars
- creative_strategy: vision, differentiation
- guidelines: do's and don'ts
- assets: required creative assets
- review_criteria: approval standards""",
        temperature=0.5,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        design = context.get("project_memory", {}).get("ui_ux", {})
        return f"""Define creative direction based on UI/UX design:
{design}

Ensure:
- Cohesive brand identity
- Consistent visual language
- Scalable design system
- Clear usage guidelines"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                creative = json.loads(response.content)
                return AgentResult(
                    success=True, output=creative, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=creative,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Creative direction failed: {e}")