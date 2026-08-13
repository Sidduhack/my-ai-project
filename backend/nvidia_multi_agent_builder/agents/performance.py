"""Performance Engineer Agent - Optimizes system performance."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class PerformanceAgent(BaseAgent):
    """Optimizes system performance and scalability."""

    agent_type = AgentType.PERFORMANCE
    name = "Performance Engineer"
    description = "Optimizes performance, implements caching, and ensures scalability"

    default_config = AgentConfig(
        system_prompt="""You are a performance engineer. Optimize system performance:
1. Performance profiling and bottleneck identification
2. Caching strategies (Redis, CDN, in-memory)
3. Database query optimization
4. Frontend performance (bundle size, lazy loading, SSR)
5. API response time optimization
6. Load testing and capacity planning
7. Resource utilization monitoring
7. Auto-scaling configuration

Output structured JSON with:
- benchmarks: baseline metrics
- bottlenecks: identified issues
- caching: strategy, TTL, invalidation
- database: query optimizations, indexes
- frontend: bundle analysis, code splitting
- api: response time targets, pagination
- load_test: scenarios, thresholds
- scaling: HPA config, resource limits""",
        temperature=0.2,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        backend = context.get("project_memory", {}).get("backend", {})
        frontend = context.get("project_memory", {}).get("frontend", {})
        db = context.get("project_memory", {}).get("database", {})
        return f"""Optimize based on:
Backend: {backend}
Frontend: {frontend}
Database: {db}

Targets:
- API p95 < 200ms
- Frontend FCP < 1.5s, TTI < 3s
- Bundle size < 200KB gzipped
- Database queries < 50ms p95
- Cache hit rate > 80%
- Horizontal scaling ready"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                perf = json.loads(response.content)
                return AgentResult(
                    success=True, output=perf, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=perf,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Performance optimization failed: {e}")