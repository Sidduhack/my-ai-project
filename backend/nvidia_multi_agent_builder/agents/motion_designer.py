"""Motion Designer Agent - Designs animations and transitions."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class MotionDesignerAgent(BaseAgent):
    """Designs motion, animations, and transitions."""

    agent_type = AgentType.MOTION_DESIGNER
    name = "Motion Designer"
    description = "Creates animation specs, transitions, micro-interactions, and motion principles"

    default_config = AgentConfig(
        system_prompt="""You are a motion designer. Create comprehensive motion specifications:
1. Motion principles and easing curves
2. Transition animations (page, modal, drawer)
3. Micro-interactions (button, hover, focus, loading)
4. State animations (success, error, empty, loading)
5. Choreography (stagger, sequencing)
6. Performance budgets (60fps, GPU acceleration)
7. Reduced motion accessibility

Output structured JSON with:
- motion_principles: easing, duration, choreography
- transitions: page, component, overlay
- micro_interactions: button, input, card, navigation
- state_animations: success, error, loading, empty
- performance: fps targets, GPU layers, will-change
- reduced_motion: alternatives, disable criteria
- implementation: CSS/JS specs, libraries""",
        temperature=0.3,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        design = context.get("project_memory", {}).get("ui_ux", {})
        creative = context.get("project_memory", {}).get("creative_director", {})
        return f"""Design motion system based on:
UI/UX: {design}
Creative: {creative}

Requirements:
- 60fps target, GPU accelerated
- Respect prefers-reduced-motion
- Consistent easing curves
- Meaningful, not decorative"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                motion = json.loads(response.content)
                return AgentResult(
                    success=True, output=motion, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=motion,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Motion design failed: {e}")