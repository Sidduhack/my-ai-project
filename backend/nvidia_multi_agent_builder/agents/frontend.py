"""Frontend Engineer Agent - Implements frontend code."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class FrontendAgent(BaseAgent):
    """Implements frontend code and components."""

    agent_type = AgentType.FRONTEND
    name = "Frontend Engineer"
    description = "Builds frontend applications, components, and user interfaces"

    default_config = AgentConfig(
        system_prompt="""You are a senior frontend engineer. Write production-ready frontend code:
1. Component implementation (React, Vue, Svelte)
2. State management (Redux, Zustand, Pinia, signals)
3. Routing and navigation
4. API integration (TanStack Query, SWR, RTK Query)
5. Form handling and validation
6. Styling (CSS Modules, Tailwind, Styled Components)
6. Build configuration (Vite, Webpack, Next.js)
7. Testing (Vitest, Playwright, Testing Library)
8. Performance optimization

Output structured JSON with:
- files: map of filepath -> content
- dependencies: package.json additions
- scripts: build, dev, test commands
- components: component inventory
- API integration layer
- state management setup
- routing configuration""",
        temperature=0.2,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        design = context.get("project_memory", {}).get("ui_ux", {})
        motion = context.get("project_memory", {}).get("motion_designer", {})
        arch = context.get("project_memory", {}).get("architecture", {})
        return f"""Implement frontend based on:
Design: {design}
Motion: {motion}
Architecture: {arch}

Requirements:
- TypeScript, React 18+, Vite
- Tailwind CSS for styling
- React Router for navigation
- TanStack Query for data fetching
- Framer Motion for animations
- ESLint + Prettier + TypeScript strict
- Component-driven development
- Accessible by default (ARIA)"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                code = json.loads(response.content)
                return AgentResult(
                    success=True, output=code, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=code,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Frontend implementation failed: {e}")