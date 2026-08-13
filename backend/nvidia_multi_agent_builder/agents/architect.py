"""Architect Agent - Designs system architecture."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class ArchitectAgent(BaseAgent):
    """Designs system architecture and technical specifications."""

    agent_type = AgentType.ARCHITECT
    name = "Architect"
    description = "Designs system architecture, APIs, data models, and infrastructure"

    default_config = AgentConfig(
        system_prompt="""You are a principal software architect. Design comprehensive system architectures including:
1. High-level architecture diagrams (component, deployment, data flow)
2. API specifications (REST, GraphQL, gRPC)
3. Database schema design
3. Technology stack selection
4. Infrastructure requirements
5. Security architecture
7. Scalability and performance considerations
8. Integration patterns

Output structured JSON with:
- architecture_overview
- components: list of services/modules with responsibilities
- api_specs: endpoint definitions
- data_models: entity relationships
- tech_stack: languages, frameworks, tools
- infrastructure: deployment, scaling, monitoring
- security: auth, encryption, compliance
- adrs: architectural decision records""",
        temperature=0.2,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        plan = context.get("project_memory", {}).get("plan", {})
        return f"""Design the system architecture based on the project plan:
{plan}

Consider:
- Microservices vs monolith
- Database selection (SQL/NoSQL)
- API design principles
- Cloud vs on-premise
- Observability requirements"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)

        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                arch = json.loads(response.content)
                return AgentResult(
                    success=True,
                    output=arch,
                    model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=arch,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Architecture design failed: {e}")