"""Sound Engineer Agent - Designs audio/sonic experience."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class SoundEngineerAgent(BaseAgent):
    """Designs sonic UX, UI sounds, and audio architecture."""

    agent_type = AgentType.SOUND_ENGINEER
    name = "Sound Engineer / Audio Director"
    description = "Designs UI sounds, interaction audio, sonic branding, and audio accessibility"

    default_config = AgentConfig(
        system_prompt="""You are a sound engineer and audio director. Design comprehensive sonic experiences:
1. UI interaction sounds (click, hover, success, error, notification)
2. Sonic branding (logo sound, startup, completion chimes)
3. Audio hierarchy and priority system
4. Ambient and atmospheric audio
5. Music direction and adaptive audio
6. Audio accessibility (reduced audio, captions, visual alternatives)
7. Technical implementation (Web Audio API, HTML Audio, audio sprites)
8. Performance optimization (lazy loading, compression, formats)
9. Cross-browser and mobile audio behavior

Output structured JSON with:
- audio_events: event -> sound mapping with specs
- sonic_branding: logo sound, brand audio identity
- audio_hierarchy: priority, volume, ducking rules
- ambient_audio: loops, crossfades, contexts
- accessibility: reduced audio prefs, visual alternatives
- technical: formats, compression, preload strategy
- implementation: Web Audio API code, fallback
- testing: loudness, latency, device testing""",
        temperature=0.3,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        design = context.get("project_memory", {}).get("ui_ux", {})
        motion = context.get("project_memory", {}).get("motion_designer", {})
        creative = context.get("project_memory", {}).get("creative_director", {})
        return f"""Design sonic UX based on:
UI/UX: {design}
Motion: {motion}
Creative: {creative}

Requirements:
- WCAG 2.1 audio compliance
- Web Audio API + HTML Audio fallback
- Audio sprites for performance
- Lazy loading, preload strategy
- Reduced audio preference support
- Mobile autoplay policies
- Loudness normalization (-24 LUFS)
- Cross-browser testing"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                audio = json.loads(response.content)
                return AgentResult(
                    success=True, output=audio, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=audio,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Sound design failed: {e}")