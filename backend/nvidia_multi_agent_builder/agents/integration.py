"""Integration Engineer Agent - Handles system integration."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class IntegrationAgent(BaseAgent):
    """Handles system integration and third-party services."""

    agent_type = AgentType.INTEGRATION
    name = "Integration Engineer"
    description = "Integrates systems, third-party APIs, and implements event-driven architecture"

    default_config = AgentConfig(
        system_prompt="""You are an integration engineer. Build robust integrations:
1. Third-party API integration (REST, GraphQL, SOAP)
2. Event-driven architecture (Kafka, RabbitMQ, Redis Streams)
3. Message queues and workers (Celery, Bull, RQ)
4. Webhook handling and retry logic
5. API gateway and service mesh
6. Data synchronization patterns
7. Circuit breakers and resilience
8. Observability (distributed tracing)

Output structured JSON with:
- integrations: list of external systems
- event_schema: message formats
- queue_topics: topics, partitions
- webhook_handlers: endpoints, verification
- api_gateway: routes, policies
- resilience: circuit breaker, retry, timeout
- monitoring: tracing, metrics, alerts
- deployment: infrastructure as code""",
        temperature=0.2,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        arch = context.get("project_memory", {}).get("architecture", {})
        backend = context.get("project_memory", {}).get("backend", {})
        return f"""Integrate systems based on:
Architecture: {arch}
Backend: {backend}

Requirements:
- Event-driven with Redis Streams
- Celery for background jobs
- Webhook signature verification
- Idempotency keys for mutations
- OpenTelemetry distributed tracing
- Dead letter queues
- Integration test contracts"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                integ = json.loads(response.content)
                return AgentResult(
                    success=True, output=integ, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=integ,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Integration failed: {e}")