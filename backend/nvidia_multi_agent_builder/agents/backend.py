"""Backend Engineer Agent - Implements backend services."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class BackendAgent(BaseAgent):
    """Implements backend services and APIs."""

    agent_type = AgentType.BACKEND
    name = "Backend Engineer"
    description = "Builds backend services, APIs, business logic, and integrations"

    default_config = AgentConfig(
        system_prompt="""You are a senior backend engineer. Write production-ready backend code:
1. API implementation (FastAPI, Express, Go)
2. Database models and repositories
3. Authentication and authorization
4. Business logic and domain services
5. Event-driven architecture
6. Caching strategies
7. Background jobs and workers
8. API documentation (OpenAPI)
9. Testing (unit, integration, contract)

Output structured JSON with:
- files: map of filepath -> content
- dependencies: requirements.txt / package.json
- API routes: endpoint definitions
- database models: ORM models
- services: business logic
- middleware: auth, logging, errors
- background tasks: job definitions
- tests: test files
- docker: Dockerfile, docker-compose""",
        temperature=0.2,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        arch = context.get("project_memory", {}).get("architecture", {})
        db = context.get("project_memory", {}).get("database", {})
        return f"""Implement backend based on:
Architecture: {arch}
Database: {db}

Requirements:
- Python 3.11+, FastAPI, SQLAlchemy 2.0
- PostgreSQL (prod) / SQLite (dev)
- JWT authentication, RBAC
- Alembic migrations
- Redis for caching/queue
- Pydantic v2 for validation
- Structured logging (structlog)
- OpenTelemetry instrumentation
- Comprehensive test coverage"""

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
            return AgentResult(success=False, error=f"Backend implementation failed: {e}")