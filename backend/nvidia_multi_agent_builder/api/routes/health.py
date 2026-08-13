"""Health and system API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from nvidia_multi_agent_builder.config import settings
from nvidia_multi_agent_builder.db import get_session, engine
from nvidia_multi_agent_builder.models import provider_registry, health_tracker, scoring_engine
from nvidia_multi_agent_builder.orchestration import orchestrator

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check - verifies database and critical services."""
    checks = {}

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Provider check
    try:
        provider_health = await provider_registry.health_check_all()
        checks["providers"] = provider_health
    except Exception as e:
        checks["providers"] = f"error: {e}"

    # Model health summary
    try:
        checks["model_health"] = health_tracker.get_health_summary()
    except Exception as e:
        checks["model_health"] = f"error: {e}"

    # Overall status
    all_healthy = all(
        v == "healthy" or (isinstance(v, dict) and all(vv for vv in v.values()))
        for v in checks.values()
    )

    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Liveness check for Kubernetes."""
    return {"status": "alive"}


@router.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Prometheus-style metrics."""
    return {
        "orchestrator": {
            "queue": orchestrator.task_queue.get_queue_status(),
        },
        "models": {
            "health": health_tracker.get_health_summary(),
            "providers": list(provider_registry.get_all_providers().keys()),
        },
        "scoring": {
            "total_scored_pairs": sum(
                len(scoring_engine.get_all_scores(at.value)) for at in __import__("nvidia_multi_agent_builder.db.models", fromlist=["AgentType"]).AgentType
            ),
        },
    }