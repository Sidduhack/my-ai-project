"""Accessibility Specialist Agent - Ensures accessibility compliance."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class AccessibilityAgent(BaseAgent):
    """Ensures accessibility compliance and inclusive design."""

    agent_type = AgentType.ACCESSIBILITY
    name = "Accessibility Specialist"
    description = "Audits and implements WCAG compliance, inclusive design, and assistive technology support"

    default_config = AgentConfig(
        system_prompt="""You are an accessibility specialist. Ensure inclusive design:
1. WCAG 2.1/2.2 compliance (A, AA, AAA)
2. Semantic HTML and ARIA patterns
3. Keyboard navigation and focus management
4. Screen reader compatibility (NVDA, JAWS, VoiceOver)
5. Color contrast and visual accessibility
6. Reduced motion and reduced audio support
7. Cognitive accessibility (plain language, consistent nav)
8. Mobile accessibility (touch targets, zoom)
9. Accessibility testing (axe, Lighthouse, manual)
10. VPAT and conformance statements

Output structured JSON with:
- audit: WCAG criteria, pass/fail, severity
- fixes: code changes for each violation
- patterns: recommended ARIA patterns
- keyboard: focus order, skip links, traps
- screen_reader: labels, announcements, live regions
- color: contrast ratios, alternatives
- motion: prefers-reduced-motion handling
- audio: captions, transcripts, alternatives
- testing: automated + manual checklist
- documentation: accessibility statement""",
        temperature=0.2,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        frontend = context.get("project_memory", {}).get("frontend", {})
        design = context.get("project_memory", {}).get("ui_ux", {})
        motion = context.get("project_memory", {}).get("motion_designer", {})
        audio = context.get("project_memory", {}).get("sound_engineer", {})
        return f"""Audit and fix accessibility for:
Frontend: {frontend}
Design: {design}
Motion: {motion}
Audio: {audio}

Target: WCAG 2.1 AA minimum
- Semantic HTML5 elements
- Focus visible, logical order
- ARIA labels, roles, states
- Contrast 4.5:1 (3:1 large text)
- Skip links, landmarks
- prefers-reduced-motion
- prefers-reduced-audio
- Screen reader tested"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                a11y = json.loads(response.content)
                return AgentResult(
                    success=True, output=a11y, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=a11y,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Accessibility audit failed: {e}")