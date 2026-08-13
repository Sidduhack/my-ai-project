"""Documentation Engineer Agent - Creates comprehensive documentation."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class DocumentationAgent(BaseAgent):
    """Creates comprehensive project documentation."""

    agent_type = AgentType.DOCUMENTATION
    name = "Documentation Engineer"
    description = "Creates technical documentation, API docs, user guides, and developer resources"

    default_config = AgentConfig(
        system_prompt="""You are a documentation engineer. Create comprehensive documentation:
1. Architecture decision records (ADRs)
2. API documentation (OpenAPI/Swagger)
3. Developer guides (setup, contribution, deployment)
4. User guides and tutorials
5. Component documentation (Storybook)
6. Runbooks and operational procedures
7. Changelog and release notes
8. Diagrams (Mermaid, PlantUML)
9. README and quickstart
10. Documentation site (MkDocs, Docusaurus)

Output structured JSON with:
- adrs: architectural decisions
- api_docs: OpenAPI spec, examples
- dev_guides: setup, workflows, standards
- user_guides: tutorials, FAQs
- components: props, examples, playground
- runbooks: incidents, deployments, rollbacks
- diagrams: architecture, data flow, sequence
- changelog: version history
- site_config: MkDocs/Docusaurus config
- maintenance: update procedures""",
        temperature=0.3,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        arch = context.get("project_memory", {}).get("architecture", {})
        backend = context.get("project_memory", {}).get("backend", {})
        frontend = context.get("project_memory", {}).get("frontend", {})
        return f"""Document the project:
Architecture: {arch}
Backend: {backend}
Frontend: {frontend}

Requirements:
- ADR for each major decision
- OpenAPI spec from FastAPI
- MkDocs Material site
- Mermaid diagrams in docs
- Code examples for all APIs
- Contribution guidelines
- Deployment guide
- Troubleshooting guide"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                docs = json.loads(response.content)
                return AgentResult(
                    success=True, output=docs, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=docs,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Documentation failed: {e}")