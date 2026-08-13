"""OpenAI-compatible provider implementation."""

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


class OpenAICompatibleProvider(ModelProvider):
    """OpenAI-compatible API provider (OpenAI, Together, Groq, etc.)."""

    DEFAULT_TIMEOUT = 60.0

    # Common models across providers
    COMMON_MODELS = {
        "gpt-4o": ModelInfo(
            id="gpt-4o",
            provider="openai_compatible",
            display_name="GPT-4o",
            capabilities=["reasoning", "coding", "vision", "functions"],
            context_window=128000,
            max_output_tokens=16384,
            supports_streaming=True,
            supports_structured=True,
            supports_vision=True,
            supports_functions=True,
        ),
        "gpt-4o-mini": ModelInfo(
            id="gpt-4o-mini",
            provider="openai_compatible",
            display_name="GPT-4o Mini",
            capabilities=["reasoning", "coding", "vision", "functions"],
            context_window=128000,
            max_output_tokens=16384,
            supports_streaming=True,
            supports_structured=True,
            supports_vision=True,
            supports_functions=True,
        ),
        "gpt-4-turbo": ModelInfo(
            id="gpt-4-turbo",
            provider="openai_compatible",
            display_name="GPT-4 Turbo",
            capabilities=["reasoning", "coding", "vision", "functions"],
            context_window=128000,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_structured=True,
            supports_vision=True,
            supports_functions=True,
        ),
        "gpt-3.5-turbo": ModelInfo(
            id="gpt-3.5-turbo",
            provider="openai_compatible",
            display_name="GPT-3.5 Turbo",
            capabilities=["general", "fast", "functions"],
            context_window=16384,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=True,
        ),
        "llama-3.1-405b-instruct": ModelInfo(
            id="llama-3.1-405b-instruct",
            provider="openai_compatible",
            display_name="Llama 3.1 405B Instruct",
            capabilities=["reasoning", "coding", "multilingual", "functions"],
            context_window=131072,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=True,
        ),
        "llama-3.1-70b-instruct": ModelInfo(
            id="llama-3.1-70b-instruct",
            provider="openai_compatible",
            display_name="Llama 3.1 70B Instruct",
            capabilities=["reasoning", "coding", "multilingual", "functions"],
            context_window=131072,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=True,
        ),
        "llama-3.1-8b-instruct": ModelInfo(
            id="llama-3.1-8b-instruct",
            provider="openai_compatible",
            display_name="Llama 3.1 8B Instruct",
            capabilities=["general", "fast", "functions"],
            context_window=131072,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=True,
        ),
        "mixtral-8x7b-instruct": ModelInfo(
            id="mixtral-8x7b-instruct",
            provider="openai_compatible",
            display_name="Mixtral 8x7B Instruct",
            capabilities=["reasoning", "coding", "multilingual"],
            context_window=32768,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_structured=False,
            supports_functions=False,
        ),
        "codellama-34b-instruct": ModelInfo(
            id="codellama-34b-instruct",
            provider="openai_compatible",
            display_name="CodeLlama 34B Instruct",
            capabilities=["coding", "reasoning"],
            context_window=16384,
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
        super().__init__("openai_compatible", kwargs)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.timeout = httpx.Timeout(timeout)
        self._client: httpx.AsyncClient | None = None

        for model in self.COMMON_MODELS.values():
            self._available_models[model.id] = model

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.perf_counter()

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
            logger.error("openai_compatible_complete_error", model=request.model, error=str(e))
            raise self.classify_error(e) from e

    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[CompletionResponse]:
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
            logger.error("openai_compatible_stream_error", model=request.model, error=str(e))
            raise self.classify_error(e) from e

    async def get_models(self) -> list[ModelInfo]:
        try:
            response = await self.client.get("/models")
            if response.status_code == 200:
                data = response.json()
                models = []
                for m in data.get("data", []):
                    model_id = m.get("id", "")
                    if model_id in self.COMMON_MODELS:
                        models.append(self.COMMON_MODELS[model_id])
                    else:
                        models.append(ModelInfo(
                            id=model_id,
                            provider="openai_compatible",
                            display_name=model_id,
                            context_window=m.get("context_window", 4096),
                        ))
                return models
        except Exception as e:
            logger.warning("openai_compatible_get_models_failed", error=str(e))

        return list(self.COMMON_MODELS.values())

    async def health_check(self) -> bool:
        try:
            response = await self.client.get("/models", timeout=10.0)
            return response.status_code == 200
        except Exception:
            return False

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
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
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        return CompletionResponse(
            id=data.get("id", ""),
            model=model,
            content=message.get("content"),
            reasoning=message.get("reasoning"),
            tool_calls=message.get("tool_calls"),
            finish_reason=choice.get("finish_reason"),
            usage={
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0),
            } if data.get("usage") else None,
            latency_ms=latency_ms,
        )

    def _parse_stream_chunk(self, chunk: dict[str, Any], model: str) -> CompletionResponse:
        choice = chunk.get("choices", [{}])[0]
        delta = choice.get("delta", {})

        return CompletionResponse(
            id=chunk.get("id", ""),
            model=model,
            content=delta.get("content"),
            reasoning=delta.get("reasoning"),
            tool_calls=delta.get("tool_calls"),
            finish_reason=choice.get("finish_reason"),
        )

    async def _handle_error_response(self, response: httpx.Response) -> None:
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