"""Provider registry for managing model providers."""

from __future__ import annotations

from typing import Any

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.models.providers.base import ModelProvider, ModelInfo
from nvidia_multi_agent_builder.models.providers.local import LocalProvider
from nvidia_multi_agent_builder.models.providers.nvidia import NVIDIAProvider
from nvidia_multi_agent_builder.models.providers.openai_compatible import OpenAICompatibleProvider

logger = get_logger(__name__)


class ProviderRegistry:
    """Registry for model providers."""

    def __init__(self):
        self._providers: dict[str, ModelProvider] = {}
        self._provider_configs: dict[str, dict[str, Any]] = {}

    def register_provider(
        self,
        name: str,
        provider_class: type[ModelProvider],
        config: dict[str, Any] | None = None,
    ) -> ModelProvider:
        """Register a provider instance."""
        config = config or {}
        provider = provider_class(**config)
        self._providers[name] = provider
        self._provider_configs[name] = config
        logger.info("provider_registered", name=name, provider_class=provider_class.__name__)
        return provider

    def get_provider(self, name: str) -> ModelProvider | None:
        """Get provider by name."""
        return self._providers.get(name)

    def get_all_providers(self) -> dict[str, ModelProvider]:
        """Get all registered providers."""
        return self._providers.copy()

    def list_provider_names(self) -> list[str]:
        """List registered provider names."""
        return list(self._providers.keys())

    def unregister_provider(self, name: str) -> bool:
        """Unregister a provider."""
        if name in self._providers:
            provider = self._providers[name]
            import asyncio
            asyncio.create_task(provider.close())
            del self._providers[name]
            del self._provider_configs[name]
            logger.info("provider_unregistered", name=name)
            return True
        return False

    async def get_all_models(self) -> dict[str, list[ModelInfo]]:
        """Get models from all providers."""
        result = {}
        for name, provider in self._providers.items():
            try:
                models = await provider.get_models()
                result[name] = models
            except Exception as e:
                logger.warning("provider_get_models_failed", provider=name, error=str(e))
                result[name] = []
        return result

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all providers."""
        result = {}
        for name, provider in self._providers.items():
            try:
                result[name] = await provider.health_check()
            except Exception as e:
                logger.warning("provider_health_check_failed", provider=name, error=str(e))
                result[name] = False
        return result

    async def close_all(self) -> None:
        """Close all providers."""
        for name, provider in self._providers.items():
            try:
                await provider.close()
            except Exception as e:
                logger.warning("provider_close_failed", provider=name, error=str(e))
        self._providers.clear()
        self._provider_configs.clear()


# Global registry instance
provider_registry = ProviderRegistry()


def create_default_registry(
    nvidia_api_key: str | None = None,
    nvidia_base_url: str | None = None,
    openai_api_key: str | None = None,
    openai_base_url: str | None = None,
    local_base_url: str | None = None,
    local_endpoint_type: str = "llamacpp",
) -> ProviderRegistry:
    """Create a registry with default providers."""
    registry = ProviderRegistry()

    # Register NVIDIA provider
    if nvidia_api_key:
        registry.register_provider(
            "nvidia",
            NVIDIAProvider,
            {"api_key": nvidia_api_key, "base_url": nvidia_base_url},
        )

    # Register OpenAI-compatible provider
    if openai_api_key:
        registry.register_provider(
            "openai_compatible",
            OpenAICompatibleProvider,
            {"api_key": openai_api_key, "base_url": openai_base_url},
        )

    # Register local provider
    registry.register_provider(
        "local",
        LocalProvider,
        {"base_url": local_base_url, "endpoint_type": local_endpoint_type},
    )

    return registry