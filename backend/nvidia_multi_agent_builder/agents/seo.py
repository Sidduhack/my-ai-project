"""SEO Specialist Agent - Implements SEO strategy."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.agents.base import AgentConfig, AgentResult, BaseAgent
from nvidia_multi_agent_builder.db.models import AgentType, Task


class SEOAgent(BaseAgent):
    """Implements SEO strategy and technical optimization."""

    agent_type = AgentType.SEO
    name = "SEO Specialist"
    description = "Optimizes for search engines, implements technical SEO, and content strategy"

    default_config = AgentConfig(
        system_prompt="""You are an SEO specialist. Implement comprehensive SEO:
1. Technical SEO (crawlability, indexability, site speed)
2. On-page SEO (titles, headings, structured data)
3. Content strategy (keywords, topics, clusters)
4. Schema.org markup (JSON-LD)
5. Sitemaps and robots.txt
6. Core Web Vitals optimization
7. International SEO (hreflang)
8. Link building strategy
9. Analytics and Search Console setup
10. SEO monitoring and reporting

Output structured JSON with:
- technical: crawl budget, indexation, redirects
- on_page: title tags, meta, headings, content
- schema: JSON-LD for key pages
- content: keyword clusters, content briefs
- performance: Core Web Vitals targets
- sitemap: XML sitemap structure
- robots: robots.txt rules
- analytics: GA4, GSC, events
- monitoring: rank tracking, alerts""",
        temperature=0.3,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    def get_instructions(self, task: Task, context: dict[str, Any]) -> str:
        frontend = context.get("project_memory", {}).get("frontend", {})
        arch = context.get("project_memory", {}).get("architecture", {})
        return f"""Implement SEO for:
Frontend: {frontend}
Architecture: {arch}

Requirements:
- SSR/SSG for crawlability
- Semantic HTML with proper headings
- JSON-LD schema (WebSite, Organization, Product)
- Dynamic meta tags per route
- Sitemap.xml auto-generation
- robots.txt with crawl directives
- Core Web Vitals < 2.5s LCP
- Open Graph + Twitter cards
- Canonical URLs"""

    async def execute(self, task: Task, context: dict[str, Any]) -> AgentResult:
        messages = self.build_prompt(task, context)
        try:
            response = await self.call_model(messages)
            if response.content:
                import json
                seo = json.loads(response.content)
                return AgentResult(
                    success=True, output=seo, model_used=response.model,
                    latency_ms=response.latency_ms,
                    tokens_used=response.usage.get("total_tokens") if response.usage else None,
                    structured_output=seo,
                )
            return AgentResult(success=False, error="Empty response")
        except Exception as e:
            return AgentResult(success=False, error=f"SEO implementation failed: {e}")