"""Security Engineer Agent - Implements security measures."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class SecurityAgent(BaseAgent):
    """Implements security measures and threat modeling."""

    agent_type = AgentType.SECURITY
    name = "Security Engineer"
    description = "Implements security controls, threat modeling, and vulnerability management"

    default_config = AgentConfig(
        system_prompt="""You are a security engineer. Implement comprehensive security:
1. Threat modeling (STRIDE, PASTA)
2. Authentication and authorization (OAuth2, OIDC, RBAC, ABAC)
3. Input validation and sanitization
4. Secure coding practices
5. Cryptography (encryption, hashing, signing)
6. API security (rate limiting, CORS, CSP)
7. Infrastructure security (network, secrets, scanning)
8. Compliance (OWASP, SOC2, GDPR)
9. Security testing (SAST, DAST, penetration)

Output structured JSON with:
- threat_model: assets, threats, mitigations
- auth_system: authentication, authorization flow
- security_headers: CSP, HSTS, etc.
- encryption: at rest, in transit
- secrets_management: vault, rotation
- vulnerability_scan: findings, remediation
- compliance: controls, evidence
- incident_response: runbooks""",
        temperature=0.1,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        arch = context.get("project_memory", {}).get("architecture", {})
        backend = context.get("project_memory", {}).get("backend", {})
        return f"""Secure the system based on:
Architecture: {arch}
Backend: {backend}

Requirements:
- Zero trust architecture
- JWT with short expiry, refresh tokens
- Argon2id password hashing
- Rate limiting per endpoint
- Security headers (CSP, HSTS, X-Frame-Options)
- Input validation on all boundaries
- Audit logging for sensitive operations
- Dependency scanning (pip-audit, npm audit)"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                sec = json.loads(response.content)
                return AgentResult(
                    success=True, output=sec, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=sec,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"Security implementation failed: {e}")