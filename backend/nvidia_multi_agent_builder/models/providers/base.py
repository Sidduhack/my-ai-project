"""Abstract model provider interface."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator
from uuid import uuid4

from nvidia_multi_agent_builder.config.logging import get_logger

logger = get_logger(__name__)


class ProviderErrorType(str, Enum):
    """Classification of provider errors for retry logic."""

    TRANSIENT = "transient"           # Network blip, temporary unavailable
    RATE_LIMIT = "rate_limit"         # Too many requests
    TIMEOUT = "timeout"               # Request timed out
    AUTHENTICATION = "authentication" # Invalid/missing API key
    PERMISSION = "permission"         # Access denied
    MODEL_NOT_FOUND = "model_not_found"  # Model doesn't exist
    CONTEXT_LENGTH = "context_length"    # Input too long
    MALFORMED_REQUEST = "malformed_request"  # Bad request format
    PROVIDER_ERROR = "provider_error"      # 5xx from provider
    UNKNOWN = "unknown"               # Unclassified error


@dataclass
class ProviderError(Exception):
    """Structured provider error."""

    message: str
    error_type: ProviderErrorType
    provider: str
    model: str | None = None
    status_code: int | None = None
    response_body: str | None = None
    retry_after: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.provider}] {self.error_type.value}: {self.message}"

    def is_retryable(self) -> bool:
        """Check if error is retryable."""
        return self.error_type in (
            ProviderErrorType.TRANSIENT,
            ProviderErrorType.RATE_LIMIT,
            ProviderErrorType.TIMEOUT,
            ProviderErrorType.PROVIDER_ERROR,
        )


@dataclass
class Message:
    """Chat message."""

    role: str  # system, user, assistant, tool
    content: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass
class CompletionRequest:
    """Completion request parameters."""

    model: str
    messages: list[Message]
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: list[str] | None = None
    stream: bool = False
    response_format: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    seed: int | None = None
    user: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletionResponse:
    """Completion response."""

    id: str = field(default_factory=lambda: f"cmpl-{uuid4().hex[:12]}")
    model: str = ""
    content: str | None = None
    reasoning: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str | None = None
    usage: dict[str, int] | None = None
    latency_ms: float = 0.0
    created_at: float = field(default_factory=time.time)


@dataclass
class ModelInfo:
    """Model metadata."""

    id: str
    provider: str
    display_name: str
    capabilities: list[str] = field(default_factory=list)
    context_window: int = 4096
    max_output_tokens: int = 4096
    supports_streaming: bool = True
    supports_structured: bool = False
    supports_vision: bool = False
    supports_functions: bool = False
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0


class ModelProvider(ABC):
    """Abstract model provider interface."""

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        self.name = name
        self.config = config or {}
        self._available_models: dict[str, ModelInfo] = {}

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate a completion."""
        pass

    @abstractmethod
    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[CompletionResponse]:
        """Stream a completion."""
        pass

    @abstractmethod
    async def get_models(self) -> list[ModelInfo]:
        """List available models."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider health."""
        pass

    def classify_error(self, error: Exception, status_code: int | None = None) -> ProviderError:
        """Classify an error for retry logic."""
        error_msg = str(error).lower()

        if status_code == 429 or "rate limit" in error_msg:
            return ProviderError(
                message=str(error),
                error_type=ProviderErrorType.RATE_LIMIT,
                provider=self.name,
                status_code=status_code,
            )
        elif status_code == 401 or "unauthorized" in error_msg or "api key" in error_msg:
            return ProviderError(
                message=str(error),
                error_type=ProviderErrorType.AUTHENTICATION,
                provider=self.name,
                status_code=status_code,
            )
        elif status_code == 403 or "forbidden" in error_msg or "permission" in error_msg:
            return ProviderError(
                message=str(error),
                error_type=ProviderErrorType.PERMISSION,
                provider=self.name,
                status_code=status_code,
            )
        elif status_code == 404 or "not found" in error_msg or "model" in error_msg:
            return ProviderError(
                message=str(error),
                error_type=ProviderErrorType.MODEL_NOT_FOUND,
                provider=self.name,
                status_code=status_code,
            )
        elif status_code == 400 and ("context" in error_msg or "token" in error_msg):
            return ProviderError(
                message=str(error),
                error_type=ProviderErrorType.CONTEXT_LENGTH,
                provider=self.name,
                status_code=status_code,
            )
        elif status_code and 500 <= status_code < 600:
            return ProviderError(
                message=str(error),
                error_type=ProviderErrorType.PROVIDER_ERROR,
                provider=self.name,
                status_code=status_code,
            )
        elif "timeout" in error_msg:
            return ProviderError(
                message=str(error),
                error_type=ProviderErrorType.TIMEOUT,
                provider=self.name,
            )
        elif "connection" in error_msg or "network" in error_msg:
            return ProviderError(
                message=str(error),
                error_type=ProviderErrorType.TRANSIENT,
                provider=self.name,
            )
        else:
            return ProviderError(
                message=str(error),
                error_type=ProviderErrorType.UNKNOWN,
                provider=self.name,
                status_code=status_code,
            )

    async def _measure_latency(self, coro):
        """Measure execution latency of a coroutine."""
        start = time.perf_counter()
        try:
            result = await coro
            return result, (time.perf_counter() - start) * 1000
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            raise e from None  # Re-raise without the timing context

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"