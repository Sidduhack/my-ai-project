"""UI/UX Designer Agent - Designs user interfaces and experiences."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class UIUXAgent(BaseAgent):
    """Designs user interfaces and user experiences."""

    agent_type = AgentType.UI_UX
    name = "UI/UX Designer"
    description = "Creates user interface designs, user flows, wireframes, and design systems"

    default_config = AgentConfig(
        system_prompt="""You are a senior UI/UX designer. Create comprehensive designs including:
1. User research and personas
2. User journey maps and flows
3. Wireframes (low and high fidelity)
4. Visual design system (colors, typography, spacing, components)
5. Interactive prototypes
6. Responsive breakpoints
7. Accessibility annotations
8. Design tokens and component library specs

Output structured JSON with:
- personas: target users
- user_flows: key journeys
- wireframes: screen layouts
- design_system: colors, typography, components
- components: reusable UI components
- responsiveness: breakpoint specs
- accessibility: WCAG compliance notes
- prototypes: interaction specs""",
        temperature=0.4,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        arch = context.get("project_memory", {}).get("architecture", {})
        return f"""Design the UI/UX based on architecture:
{arch}

Requirements:
- Modern, clean aesthetic (glassmorphism, subtle depth)
- Dark/light theme support
- Mobile-first responsive
- WCAG 2.1 AA compliance
- Design system for consistency"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                design = json.loads(response.content)
                return AgentResult(
                    success=True, output=design, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=design,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"UI/UX design failed: {e}")