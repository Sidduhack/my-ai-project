"""Local model provider (llama.cpp, Ollama, vLLM, etc.)."""

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


class LocalProvider(ModelProvider):
    """Local model provider supporting llama.cpp server, Ollama, vLLM."""

    SUPPORTED_ENDPOINTS = {
        "llamacpp": "/v1/chat/completions",
        "ollama": "/api/chat",
        "vllm": "/v1/chat/completions",
    }

    DEFAULT_MODELS = {
        "llama-3.1-70b-instruct": ModelInfo(
            id="llama-3.1-70b-instruct",
            provider="local",
            display_name="Llama 3.1 70B Instruct (Local)",
            capabilities=["reasoning", "coding", "multilingual"],
            context_window=131072,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_functions=False,
        ),
        "llama-3.1-8b-instruct": ModelInfo(
            id="llama-3.1-8b-instruct",
            provider="local",
            display_name="Llama 3.1 8B Instruct (Local)",
            capabilities=["general", "fast"],
            context_window=131072,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_functions=False,
        ),
        "codellama-34b-instruct": ModelInfo(
            id="codellama-34b-instruct",
            provider="local",
            display_name="CodeLlama 34B Instruct (Local)",
            capabilities=["coding", "reasoning"],
            context_window=16384,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_functions=False,
        ),
        "mistral-7b-instruct": ModelInfo(
            id="mistral-7b-instruct",
            provider="local",
            display_name="Mistral 7B Instruct (Local)",
            capabilities=["general", "fast"],
            context_window=32768,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_functions=False,
        ),
        "gemma-2-27b-it": ModelInfo(
            id="gemma-2-27b-it",
            provider="local",
            display_name="Gemma 2 27B IT (Local)",
            capabilities=["general", "coding"],
            context_window=8192,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_functions=False,
        ),
        "phi-3-medium": ModelInfo(
            id="phi-3-medium",
            provider="local",
            display_name="Phi-3 Medium (Local)",
            capabilities=["reasoning", "coding", "compact"],
            context_window=128000,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_functions=False,
        ),
    }

    def __init__(
        self,
        base_url: str | None = None,
        endpoint_type: str = "llamacpp",
        timeout: float = 120.0,
        model_path: str | None = None,
        **kwargs,
    ):
        super().__init__("local", kwargs)
        self.base_url = (base_url or os.getenv("LOCAL_MODEL_URL") or "http://localhost:8080").rstrip("/")
        self.endpoint_type = endpoint_type
        self.timeout = httpx.Timeout(timeout)
        self.model_path = model_path or os.getenv("LOCAL_MODEL_PATH", "./models")
        self._client: httpx.AsyncClient | None = None
        self._endpoint = self.SUPPORTED_ENDPOINTS.get(endpoint_type, "/v1/chat/completions")

        for model in self.DEFAULT_MODELS.values():
            self._available_models[model.id] = model

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
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

        if self.endpoint_type == "ollama":
            payload = self._build_ollama_payload(request, messages)
        else:
            payload = self._build_openai_payload(request, messages)

        try:
            response = await self.client.post(self._endpoint, json=payload)
            latency_ms = (time.perf_counter() - start) * 1000

            if response.status_code != 200:
                await self._handle_error_response(response)

            if self.endpoint_type == "ollama":
                return self._parse_ollama_response(response.json(), request.model, latency_ms)
            else:
                return self._parse_openai_response(response.json(), request.model, latency_ms)

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
            logger.error("local_complete_error", model=request.model, error=str(e))
            raise self.classify_error(e) from e

    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[CompletionResponse]:
        messages = self._convert_messages(request.messages)

        if self.endpoint_type == "ollama":
            payload = self._build_ollama_payload(request, messages)
            payload["stream"] = True
        else:
            payload = self._build_openai_payload(request, messages)
            payload["stream"] = True

        try:
            async with self.client.stream("POST", self._endpoint, json=payload) as response:
                if response.status_code != 200:
                    await self._handle_error_response(response)

                if self.endpoint_type == "ollama":
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            yield self._parse_ollama_stream_chunk(chunk, request.model)
                        except json.JSONDecodeError:
                            continue
                else:
                    async for line in response.aiter_lines():
                        if not line or line == "data: [DONE]":
                            continue
                        if line.startswith("data: "):
                            try:
                                chunk = json.loads(line[6:])
                                yield self._parse_openai_stream_chunk(chunk, request.model)
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
            logger.error("local_stream_error", model=request.model, error=str(e))
            raise self.classify_error(e) from e

    async def get_models(self) -> list[ModelInfo]:
        # For local providers, we don't have a standard /models endpoint
        # Return configured models
        return list(self._available_models.values())

    async def health_check(self) -> bool:
        try:
            # Try a simple completion to check if model is loaded
            response = await self.client.post(
                self._endpoint,
                json=self._build_health_check_payload(),
                timeout=10.0,
            )
            return response.status_code == 200
        except Exception:
            return False

    def _build_openai_payload(self, request: CompletionRequest, messages: list[dict]) -> dict[str, Any]:
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
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
        payload.update(request.extra)
        return payload

    def _build_ollama_payload(self, request: CompletionRequest, messages: list[dict]) -> dict[str, Any]:
        return {
            "model": request.model,
            "messages": messages,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "num_predict": request.max_tokens or -1,
            },
        }

    def _build_health_check_payload(self) -> dict[str, Any]:
        if self.endpoint_type == "ollama":
            return {
                "model": list(self._available_models.keys())[0] if self._available_models else "llama3",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
            }
        return {
            "model": list(self._available_models.keys())[0] if self._available_models else "default",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        result = []
        for msg in messages:
            api_msg = {"role": msg.role}
            if msg.content is not None:
                api_msg["content"] = msg.content
            result.append(api_msg)
        return result

    def _parse_openai_response(self, data: dict[str, Any], model: str, latency_ms: float) -> CompletionResponse:
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

    def _parse_ollama_response(self, data: dict[str, Any], model: str, latency_ms: float) -> CompletionResponse:
        message = data.get("message", {})

        return CompletionResponse(
            id="",
            model=model,
            content=message.get("content"),
            finish_reason=data.get("done_reason"),
            latency_ms=latency_ms,
        )

    def _parse_openai_stream_chunk(self, chunk: dict[str, Any], model: str) -> CompletionResponse:
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

    def _parse_ollama_stream_chunk(self, chunk: dict[str, Any], model: str) -> CompletionResponse:
        message = chunk.get("message", {})

        return CompletionResponse(
            id="",
            model=model,
            content=message.get("content"),
            finish_reason=chunk.get("done_reason"),
        )

    async def _handle_error_response(self, response: httpx.Response) -> None:
        try:
            error_data = response.json()
            if self.endpoint_type == "ollama":
                error_msg = error_data.get("error", response.text)
            else:
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
        elif status_code == 404:
            return ProviderErrorType.MODEL_NOT_FOUND
        elif status_code == 400 and ("context" in msg_lower or "token" in msg_lower):
            return ProviderErrorType.CONTEXT_LENGTH
        elif 500 <= status_code < 600:
            return ProviderErrorType.PROVIDER_ERROR
        else:
            return ProviderErrorType.UNKNOWN