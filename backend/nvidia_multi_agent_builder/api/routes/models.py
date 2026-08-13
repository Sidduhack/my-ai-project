"""Model API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nvidia_multi_agent_builder.db import get_session
from nvidia_multi_agent_builder.db.models import Model, ModelHealth, ModelScore, AgentType
from nvidia_multi_agent_builder.models import provider_registry, health_tracker, scoring_engine, ModelRouter

router = APIRouter(prefix="/models", tags=["models"])


class ModelResponse(BaseModel):
    id: str
    provider: str
    model_id: str
    display_name: str
    capabilities: list[str]
    context_window: int
    max_output_tokens: int
    supports_streaming: bool
    supports_structured: bool
    supports_vision: bool
    supports_functions: bool
    enabled: bool

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    model_id: str
    provider: str
    state: str
    success_count: int
    failure_count: int
    consecutive_failures: int
    avg_latency_ms: float
    recent_avg_latency_ms: float
    timeout_count: int
    error_count: int
    last_success_at: str | None
    last_failure_at: str | None
    cooldown_until: str | None
    is_available: bool


class ScoreResponse(BaseModel):
    model_id: str
    agent_type: str
    reliability_score: float
    latency_score: float
    confidence_score: float
    recency_score: float
    specialization_score: float
    priority_score: float
    total_score: float
    sample_count: int


@router.get("", response_model=list[ModelResponse])
async def list_models(
    provider: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[Model]:
    """List all registered models."""
    query = select(Model)
    if provider:
        query = query.where(Model.provider == provider)
    query = query.where(Model.enabled == True).order_by(Model.provider, Model.model_id)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/health", response_model=list[HealthResponse])
async def get_models_health() -> list[dict[str, Any]]:
    """Get health status for all models."""
    health_data = health_tracker.get_all_health()
    return [h.to_dict() for h in health_data.values()]


@router.get("/health/{provider}/{model_id}", response_model=HealthResponse)
async def get_model_health(
    provider: str,
    model_id: str,
) -> dict[str, Any]:
    """Get health for a specific model."""
    health = health_tracker.get_health(model_id, provider)
    return health.to_dict()


@router.get("/scores", response_model=list[ScoreResponse])
async def get_model_scores(
    agent_type: AgentType | None = Query(None),
) -> list[dict[str, Any]]:
    """Get adaptive scores for models."""
    if agent_type:
        scores = scoring_engine.get_all_scores(agent_type.value)
    else:
        scores = []
        for at in AgentType:
            scores.extend(scoring_engine.get_all_scores(at.value))

    return [s.to_dict() for s in scores]


@router.get("/scores/{agent_type}", response_model=list[ScoreResponse])
async def get_agent_model_scores(
    agent_type: AgentType,
) -> list[dict[str, Any]]:
    """Get ranked models for an agent type."""
    scores = scoring_engine.get_all_scores(agent_type.value)
    return [s.to_dict() for s in scores]


@router.get("/routes")
async def get_model_routes() -> dict[str, Any]:
    """Get all model routes."""
    routes = ModelRouter(provider_registry).list_routes()
    return {
        agent_type: {
            "primary_model": route.primary_model,
            "fallback_models": route.fallback_models,
            "priority": route.priority,
            "enabled": route.enabled,
        }
        for agent_type, route in routes.items()
    }


@router.post("/health/check")
async def trigger_health_check() -> dict[str, bool]:
    """Trigger health check for all providers."""
    return await provider_registry.health_check_all()


@router.get("/providers")
async def list_providers() -> dict[str, list[str]]:
    """List available providers and their models."""
    return await provider_registry.get_all_models()