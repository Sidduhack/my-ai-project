"""Debugging Engineer Agent - Diagnoses and fixes issues."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class DebuggingAgent(BaseAgent):
    """Diagnoses issues and implements fixes."""

    agent_type = AgentType.DEBUGGING
    name = "Debugging Engineer"
    description = "Diagnoses bugs, analyzes failures, and implements fixes"

    default_config = AgentConfig(
        system_prompt="""You are a debugging engineer. Diagnose and fix issues:
1. Root cause analysis (5 Whys, fishbone)
2. Log analysis and correlation
3. Distributed tracing analysis
3. Memory/CPU profiling
4. Database query analysis
5. Network debugging
6. Test failure analysis
7. Regression identification
8. Fix implementation and verification

Output structured JSON with:
- issue: description, severity, impact
- root_cause: analysis, evidence
- hypothesis: testable theories
- fix: code changes, config changes
- verification: test cases, monitoring
- prevention: process improvements
- rollback_plan: if fix fails""",
        temperature=0.1,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        error = task.input_data.get("error", "Unknown error")
        logs = task.input_data.get("logs", [])
        traces = task.input_data.get("traces", [])
        return f"""Debug this issue:
Error: {error}
Logs: {logs}
Traces: {traces}

Approach:
1. Reproduce locally if possible
2. Analyze stack traces and logs
3. Check recent deployments
4. Identify root cause
5. Implement minimal fix
6. Add regression test
7. Verify in staging"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                debug = json.loads(response.content)
                return AgentResult(
                    success=True, output=debug, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=debug,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Debugging failed: {e}")