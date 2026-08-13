"""Code Reviewer Agent - Reviews code quality and standards."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class CodeReviewerAgent(BaseAgent):
    """Reviews code for quality, security, and standards compliance."""

    agent_type = AgentType.CODE_REVIEWER
    name = "Code Reviewer"
    description = "Reviews code for quality, security, performance, and maintainability"

    default_config = AgentConfig(
        system_prompt="""You are a principal code reviewer. Review code comprehensively:
1. Code correctness and logic
2. Security vulnerabilities (OWASP, CWE)
3. Performance implications
4. Maintainability and readability
5. Test coverage and quality
6. Architecture alignment
7. Dependency risks
8. Coding standards compliance
9. Documentation completeness
10. Breaking changes detection

Output structured JSON with:
- summary: overall assessment, risk level
- findings: list of issues with severity (critical/high/medium/low)
- suggestions: improvements, refactoring
- security: vulnerabilities, mitigations
- performance: bottlenecks, optimizations
- tests: missing coverage, flaky tests
- dependencies: outdated, vulnerable, unused
- approval: approved/changes_requested/rejected
- follow_up: items for next review""",
        temperature=0.1,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        code = task.input_data.get("code", {})
        changed_files = task.input_data.get("changed_files", [])
        return f"""Review this code:
Files: {changed_files}
Code: {code}

Checklist:
- [ ] No hardcoded secrets
- [ ] Input validation everywhere
- [ ] Proper error handling
- [ ] No SQL injection risks
- [ ] No XSS vulnerabilities
- [ ] Efficient algorithms
- [ ] Proper async/await
- [ ] Type hints complete
- [ ] Tests cover new code
- [ ] Documentation updated
- [ ] No breaking changes without version bump"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                review = json.loads(response.content)
                return AgentResult(
                    success=True, output=review, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=review,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Code review failed: {e}")