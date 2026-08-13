"""Testing Engineer Agent - Implements testing strategies."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class TestingAgent(BaseAgent):
    """Implements comprehensive testing strategies."""

    agent_type = AgentType.TESTING
    name = "Testing Engineer"
    description = "Creates test plans, implements tests, and ensures quality"

    default_config = AgentConfig(
        system_prompt="""You are a testing engineer. Implement comprehensive testing:
1. Test strategy and planning
2. Unit tests (pytest, Vitest, Jest)
3. Integration tests (API, database, services)
4. End-to-end tests (Playwright, Cypress)
5. Contract testing (Pact)
6. Performance/load tests (k6, Locust)
7. Accessibility tests (axe-core)
8. Visual regression tests
9. Test data management
10. CI/CD integration

Output structured JSON with:
- test_plan: strategy, scope, priorities
- unit_tests: test files, coverage targets
- integration_tests: scenarios, fixtures
- e2e_tests: critical paths, selectors
- contract_tests: provider/consumer
- performance_tests: scenarios, thresholds
- accessibility_tests: WCAG criteria
- test_data: factories, fixtures
- ci_config: pipeline stages""",
        temperature=0.2,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        backend = context.get("project_memory", {}).get("backend", {})
        frontend = context.get("project_memory", {}).get("frontend", {})
        arch = context.get("project_memory", {}).get("architecture", {})
        return f"""Create tests for:
Backend: {backend}
Frontend: {frontend}
Architecture: {arch}

Requirements:
- Unit: >80% coverage, fast, isolated
- Integration: real DB, test containers
- E2E: critical user journeys only
- Contract: API schema validation
- Accessibility: axe-core in CI
- Visual: Chromatic or similar
- Flaky test detection"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                tests = json.loads(response.content)
                return AgentResult(
                    success=True, output=tests, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=tests,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Test implementation failed: {e}")