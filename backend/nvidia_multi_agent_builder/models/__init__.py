"""Models package - provider abstraction, routing, health, scoring."""

from nvidia_multi_agent_builder.models.providers import (
    CompletionRequest,
    CompletionResponse,
    Message,
    ModelInfo,
    ModelProvider,
    ProviderError,
    ProviderErrorType,
    NVIDIAProvider,
    OpenAICompatibleProvider,
    LocalProvider,
    ProviderRegistry,
    create_default_registry,
    provider_registry,
)
from nvidia_multi_agent_builder.models.routing import ModelRoute, ModelRouter
from nvidia_multi_agent_builder.models.health import ModelHealth, ModelHealthState, HealthTracker, health_tracker
from nvidia_multi_agent_builder.models.scoring import ModelScore, ScoringEngine, scoring_engine

__all__ = [
    # Providers
    "CompletionRequest",
    "CompletionResponse",
    "Message",
    "ModelInfo",
    "ModelProvider",
    "ProviderError",
    "ProviderErrorType",
    "NVIDIAProvider",
    "OpenAICompatibleProvider",
    "LocalProvider",
    "ProviderRegistry",
    "create_default_registry",
    "provider_registry",
    # Routing
    "ModelRoute",
    "ModelRouter",
    # Health
    "ModelHealth",
    "ModelHealthState",
    "HealthTracker",
    "health_tracker",
    # Scoring
    "ModelScore",
    "ScoringEngine",
    "scoring_engine",
]