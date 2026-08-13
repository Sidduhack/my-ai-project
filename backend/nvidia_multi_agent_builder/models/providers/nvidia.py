"""NVIDIA API provider implementation."""

from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncIterator

import httpx

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.models.providers.base import (
    CompletionRequest,
    CompletionResponse,
    ModelInfo,
    ModelProvider,
    ProviderError,
    ProviderErrorType,
    Message,
)

logger = get_logger(__name__)


class NVIDIAProvider(ModelProvider):
    """NVIDIA API provider."""

    BASE_URL = "https://integrate.api.nvidia.com/v1"
    DEFAULT_TIMEOUT = 60.0

    # Known NVIDIA models with capabilities
    KNOWN_MODELS = {
        "nvidia/nemotron-3-ultra": ModelInfo(
            id="nvidia/nemotron-3-ultra",
            provider="nvidia",
            display_name="Nemotron 3 Ultra",
            capabilities=["reasoning", "coding", "analysis"],
            context_window=8192,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=False,
        ),
        "nvidia/nemotron-4-340b": ModelInfo(
            id="nvidia/nemotron-4-340b",
            provider="nvidia",
            display_name="Nemotron 4 340B",
            capabilities=["reasoning", "coding", "analysis", "multilingual"],
            context_window=16384,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=False,
        ),
        "nvidia/llama-3.1-405b-instruct": ModelInfo(
            id="nvidia/llama-3.1-405b-instruct",
            provider="nvidia",
            display_name="Llama 3.1 405B Instruct",
            capabilities=["general", "coding", "reasoning"],
            context_window=131072,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=True,
        ),
        "nvidia/llama-3.1-70b-instruct": ModelInfo(
            id="nvidia/llama-3.1-70b-instruct",
            provider="nvidia",
            display_name="Llama 3.1 70B Instruct",
            capabilities=["general", "coding", "reasoning"],
            context_window=131072,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=True,
        ),
        "nvidia/llama-3.1-8b-instruct": ModelInfo(
            id="nvidia/llama-3.1-8b-instruct",
            provider="nvidia",
            display_name="Llama 3.1 8B Instruct",
            capabilities=["general", "fast"],
            context_window=131072,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=True,
        ),
        "nvidia/mistral-7b-instruct": ModelInfo(
            id="nvidia/mistral-7b-instruct",
            provider="nvidia",
            display_name="Mistral 7B Instruct",
            capabilities=["general", "fast"],
            context_window=32768,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=False,
        ),
        "nvidia/gemma-2-27b-it": ModelInfo(
            id="nvidia/gemma-2-27b-it",
            provider="nvidia",
            display_name="Gemma 2 27B IT",
            capabilities=["general", "coding"],
            context_window=8192,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=False,
        ),
    }

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        **kwargs,
    ):
        super().__init__("nvidia", kwargs)
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.base_url = (base_url or os.getenv("NVIDIA_BASE_URL") or self.BASE_URL).rstrip("/")
        self.timeout = httpx.Timeout(timeout)
        self._client: httpx.AsyncClient | None = None

        # Register known models
        for model in self.KNOWN_MODELS.values():
            self._available_models[model.id] = model

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate a completion."""
        start = time.perf_counter()

        # Convert messages to OpenAI format
        messages = self._convert_messages(request.messages)

        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": False,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        if request.response_format:
            payload["response_format"] = request.response_format
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.user:
            payload["user"] = request.user

        # Add extra parameters
        payload.update(request.extra)

        try:
            response = await self.client.post("/chat/completions", json=payload)
            latency_ms = (time.perf_counter() - start) * 1000

            if response.status_code != 200:
                await self._handle_error_response(response)

            data = response.json()
            return self._parse_response(data, request.model, latency_ms)

        except httpx.TimeoutException as e:
            raise ProviderError(
                message="Request timed out",
                error_type=ProviderErrorType.TIMEOUT,
                provider=self.name,
            ) from e
        except httpx.NetworkError as e:
            raise ProviderError(
                message=f"Network error: {e}",
                error_type=ProviderErrorType.TRANSIENT,
                provider=self.name,
            ) from e
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("nvidia_complete_error", model=request.model, error=str(e))
            raise self.classify_error(e) from e

    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[CompletionResponse]:
        """Stream a completion."""
        messages = self._convert_messages(request.messages)

        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": True,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.seed is not None:
            payload["seed"] = request.seed

        try:
            async with self.client.stream("POST", "/chat/completions", json=payload) as response:
                if response.status_code != 200:
                    await self._handle_error_response(response)

                async for line in response.aiter_lines():
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        try:
                            chunk = json.loads(line[6:])
                            yield self._parse_stream_chunk(chunk, request.model)
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException as e:
            raise ProviderError(
                message="Stream request timed out",
                error_type=ProviderErrorType.TIMEOUT,
                provider=self.name,
            ) from e
        except httpx.NetworkError as e:
            raise ProviderError(
                message=f"Network error: {e}",
                error_type=ProviderErrorType.TRANSIENT,
                provider=self.name,
            ) from e
        except Exception as e:
            logger.error("nvidia_stream_error", model=request.model, error=str(e))
            raise self.classify_error(e) from e

    async def get_models(self) -> list[ModelInfo]:
        """List available models."""
        try:
            response = await self.client.get("/models")
            if response.status_code == 200:
                data = response.json()
                models = []
                for m in data.get("data", []):
                    model_id = m.get("id", "")
                    if model_id in self.KNOWN_MODELS:
                        models.append(self.KNOWN_MODELS[model_id])
                    else:
                        # Unknown model - create basic info
                        models.append(ModelInfo(
                            id=model_id,
                            provider="nvidia",
                            display_name=m.get("id", model_id),
                            context_window=m.get("context_window", 4096),
                        ))
                return models
        except Exception as e:
            logger.warning("nvidia_get_models_failed", error=str(e))

        # Return known models as fallback
        return list(self.KNOWN_MODELS.values())

    async def health_check(self) -> bool:
        """Check provider health with a minimal request."""
        try:
            # Try to list models as health check
            response = await self.client.get("/models", timeout=10.0)
            return response.status_code == 200
        except Exception:
            return False

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert internal messages to API format."""
        result = []
        for msg in messages:
            api_msg = {"role": msg.role}
            if msg.content is not None:
                api_msg["content"] = msg.content
            if msg.name:
                api_msg["name"] = msg.name
            if msg.tool_calls:
                api_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                api_msg["tool_call_id"] = msg.tool_call_id
            result.append(api_msg)
        return result

    def _parse_response(self, data: dict[str, Any], model: str, latency_ms: float) -> CompletionResponse:
        """Parse API response."""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        content = message.get("content")
        reasoning = message.get("reasoning")
        tool_calls = message.get("tool_calls")
        finish_reason = choice.get("finish_reason")

        usage = data.get("usage")
        if usage:
            usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }

        return CompletionResponse(
            id=data.get("id", ""),
            model=model,
            content=content,
            reasoning=reasoning,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
            latency_ms=latency_ms,
        )

    def _parse_stream_chunk(self, chunk: dict[str, Any], model: str) -> CompletionResponse:
        """Parse streaming chunk."""
        choice = chunk.get("choices", [{}])[0]
        delta = choice.get("delta", {})

        content = delta.get("content")
        reasoning = delta.get("reasoning")
        tool_calls = delta.get("tool_calls")
        finish_reason = choice.get("finish_reason")

        return CompletionResponse(
            id=chunk.get("id", ""),
            model=model,
            content=content,
            reasoning=reasoning,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    async def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error response and raise appropriate exception."""
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_msg = response.text

        raise ProviderError(
            message=error_msg,
            error_type=self._classify_http_error(response.status_code, error_msg),
            provider=self.name,
            status_code=response.status_code,
            response_body=response.text,
        )

    def _classify_http_error(self, status_code: int, message: str) -> ProviderErrorType:
        """Classify HTTP error."""
        msg_lower = message.lower()

        if status_code == 429:
            return ProviderErrorType.RATE_LIMIT
        elif status_code == 401:
            return ProviderErrorType.AUTHENTICATION
        elif status_code == 403:
            return ProviderErrorType.PERMISSION
        elif status_code == 404:
            return ProviderErrorType.MODEL_NOT_FOUND
        elif status_code == 400 and ("context" in msg_lower or "token" in msg_lower):
            return ProviderErrorType.CONTEXT_LENGTH
        elif 500 <= status_code < 600:
            return ProviderErrorType.PROVIDER_ERROR
        else:
            return ProviderErrorType.UNKNOWN