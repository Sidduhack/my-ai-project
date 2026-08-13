"""Model routing with primary/fallback selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.core.exceptions import ModelNotFoundError
from nvidia_multi_agent_builder.models.providers.base import ModelProvider, ModelInfo

logger = get_logger(__name__)


@dataclass
class ModelRoute:
    """Model route configuration for an agent."""

    agent_type: str
    primary_model: str  # format: "provider/model-id"
    fallback_models: list[str] = field(default_factory=list)  # ordered list
    priority: int = 0
    enabled: bool = True

    def get_all_models(self) -> list[str]:
        """Get all models in priority order."""
        return [self.primary_model] + self.fallback_models

    def parse_model_spec(self, spec: str) -> tuple[str, str]:
        """Parse 'provider/model-id' into (provider, model_id)."""
        parts = spec.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid model spec: {spec}. Expected 'provider/model-id'")
        return parts[0], parts[1]


class ModelRouter:
    """Routes model requests with primary/fallback logic."""

    def __init__(self, provider_registry):
        self.provider_registry = provider_registry
        self._routes: dict[str, ModelRoute] = {}

    def register_route(self, route: ModelRoute) -> None:
        """Register a model route for an agent type."""
        self._routes[route.agent_type] = route
        logger.info("model_route_registered", agent_type=route.agent_type, primary=route.primary_model)

    def get_route(self, agent_type: str) -> ModelRoute | None:
        """Get route for agent type."""
        return self._routes.get(agent_type)

    def get_candidate_models(self, agent_type: str) -> list[tuple[str, str]]:
        """Get all candidate models for agent as (provider, model_id) tuples."""
        route = self._routes.get(agent_type)
        if not route or not route.enabled:
            return []

        candidates = []
        for spec in route.get_all_models():
            try:
                provider_name, model_id = route.parse_model_spec(spec)
                candidates.append((provider_name, model_id))
            except ValueError as e:
                logger.warning("invalid_model_spec", spec=spec, error=str(e))
        return candidates

    def get_best_model(
        self,
        agent_type: str,
        health_check: dict[str, bool] | None = None,
        scoring: dict[str, float] | None = None,
    ) -> tuple[str, str] | None:
        """Select best available model for agent considering health and scoring."""
        candidates = self.get_candidate_models(agent_type)
        if not candidates:
            return None

        health_check = health_check or {}
        scoring = scoring or {}

        for provider_name, model_id in candidates:
            # Check provider exists
            provider = self.provider_registry.get_provider(provider_name)
            if not provider:
                logger.debug("provider_not_found", provider=provider_name)
                continue

            # Check provider health
            provider_healthy = health_check.get(provider_name, True)
            if not provider_healthy:
                logger.debug("provider_unhealthy", provider=provider_name)
                continue

            # Check model exists in provider
            model = self._find_model_in_provider(provider, model_id)
            if not model:
                logger.debug("model_not_in_provider", provider=provider_name, model=model_id)
                continue

            # Check model-specific health/scoring if available
            model_key = f"{provider_name}/{model_id}"
            model_score = scoring.get(model_key, 1.0)
            if model_score <= 0:
                logger.debug("model_score_too_low", model=model_key, score=model_score)
                continue

            return provider_name, model_id

        return None

    def _find_model_in_provider(self, provider: ModelProvider, model_id: str) -> ModelInfo | None:
        """Find model in provider's available models."""
        for model in provider._available_models.values():
            if model.id == model_id:
                return model
        return None

    async def execute_with_fallback(
        self,
        agent_type: str,
        request,
        health_check: dict[str, bool] | None = None,
        scoring: dict[str, float] | None = None,
    ) -> tuple[Any, str, str]:
        """Execute request with automatic fallback."""
        candidates = self.get_candidate_models(agent_type)
        if not candidates:
            raise ModelNotFoundError(f"No models configured for agent: {agent_type}")

        health_check = health_check or {}
        scoring = scoring or {}

        last_error = None
        for i, (provider_name, model_id) in enumerate(candidates):
            provider = self.provider_registry.get_provider(provider_name)
            if not provider:
                last_error = f"Provider not found: {provider_name}"
                continue

            if not health_check.get(provider_name, True):
                last_error = f"Provider unhealthy: {provider_name}"
                continue

            # Create request with selected model
            request.model = model_id

            try:
                logger.info("model_attempt", agent_type=agent_type, provider=provider_name, model=model_id, attempt=i+1)
                response = await provider.complete(request)
                logger.info("model_success", agent_type=agent_type, provider=provider_name, model=model_id)
                return response, provider_name, model_id
            except Exception as e:
                last_error = e
                logger.warning("model_failed", agent_type=agent_type, provider=provider_name, model=model_id, error=str(e))
                continue

        raise ModelNotFoundError(
            f"All models failed for agent {agent_type}. Last error: {last_error}"
        )

    def list_routes(self) -> dict[str, ModelRoute]:
        """List all registered routes."""
        return self._routes.copy()