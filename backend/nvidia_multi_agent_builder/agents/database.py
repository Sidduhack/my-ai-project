"""Database Architect Agent - Designs and implements database layer."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class DatabaseAgent(BaseAgent):
    """Designs database schema and implements data layer."""

    agent_type = AgentType.DATABASE
    name = "Database Architect"
    description = "Designs database schemas, migrations, queries, and data architecture"

    default_config = AgentConfig(
        system_prompt="""You are a database architect. Design and implement data layers:
1. Logical and physical schema design
2. Normalization and denormalization strategies
3. Index optimization
4. Migration scripts (Alembic, Flyway)
5. Query optimization and analysis
6. Data modeling patterns (event sourcing, CQRS)
7. Replication and backup strategies
8. Performance tuning

Output structured JSON with:
- schema: tables, columns, constraints, indexes
- relationships: ER diagram description
- migrations: migration files
- queries: optimized queries for key access patterns
- indexes: indexing strategy
- partitioning: if applicable
- backup: backup/recovery plan
- monitoring: slow query detection""",
        temperature=0.2,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        arch = context.get("project_memory", {}).get("architecture", {})
        backend = context.get("project_memory", {}).get("backend", {})
        return f"""Design database based on:
Architecture: {arch}
Backend: {backend}

Requirements:
- PostgreSQL primary, SQLite dev
- SQLAlchemy 2.0 async models
- Alembic migrations
- Proper indexing for query patterns
- Soft deletes, timestamps
- UUID primary keys
- Row-level security where needed"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                db = json.loads(response.content)
                return AgentResult(
                    success=True, output=db, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=db,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Database design failed: {e}")