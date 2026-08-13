"""Model providers package."""

from nvidia_multi_agent_builder.models.providers.base import (
    CompletionRequest,
    CompletionResponse,
    Message,
    ModelInfo,
    ModelProvider,
    ProviderError,
    ProviderErrorType,
)
from nvidia_multi_agent_builder.models.providers.local import LocalProvider
from nvidia_multi_agent_builder.models.providers.nvidia import NVIDIAProvider
from nvidia_multi_agent_builder.models.providers.openai_compatible import OpenAICompatibleProvider
from nvidia_multi_agent_builder.models.providers.registry import ProviderRegistry, create_default_registry, provider_registry

__all__ = [
    # Base
    "CompletionRequest",
    "CompletionResponse",
    "Message",
    "ModelInfo",
    "ModelProvider",
    "ProviderError",
    "ProviderErrorType",
    # Providers
    "NVIDIAProvider",
    "OpenAICompatibleProvider",
    "LocalProvider",
    # Registry
    "ProviderRegistry",
    "create_default_registry",
    "provider_registry",
]