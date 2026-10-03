"""Async LLM client for the agentcore multi-agent system.

Behavior:
- Primary provider: OpenAI ChatGPT (via official openai SDK, async).
- Fallback provider: local Ollama (``format: json``), for offline dev.
- Each provider call is retried with exponential backoff (via ``tenacity``)
  on transient failures (timeouts, connection errors, 429/5xx).
- Every call returns an ``LLMResult`` carrying which provider/model actually
  served the request and how long it took.

For embeddings (used by Pinecone memory), OpenAI's text-embedding-3-small
is used (1536 dimensions by default).
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

_BACKEND_ROOT = str(Path(__file__).resolve().parent.parent)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from utils.json_cleaner import parse_json_response  # noqa: E402

from .settings import AgentCoreSettings, get_settings  # noqa: E402


class LLMProviderError(RuntimeError):
    """A single provider failed to produce a usable response."""


class LLMAllProvidersFailedError(RuntimeError):
    """Every configured provider failed."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        summary = " | ".join(f"{name}: {msg}" for name, msg in errors.items())
        super().__init__(summary or "No LLM provider configured")


@dataclass(frozen=True)
class LLMResult:
    parsed: dict[str, Any]
    raw_text: str
    provider: str
    model: str
    latency_ms: float


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    if isinstance(exc, Exception) and "rate_limit" in str(exc).lower():
        return True
    return False


class OpenAIProvider:
    """Async ChatGPT provider via the official openai SDK."""

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, prompt: str, *, temperature: float, max_tokens: int, timeout: float) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url, timeout=timeout)
        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content or ""
            if not text.strip():
                raise LLMProviderError("OpenAI returned an empty response")
            return text.strip()
        finally:
            await client.close()

    async def embed_batch(self, texts: list[str], *, embedding_model: str, timeout: float) -> list[list[float]]:
        """Embed texts via OpenAI embeddings endpoint."""
        from openai import AsyncOpenAI

        if not texts:
            return []

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url, timeout=timeout)
        try:
            response = await client.embeddings.create(
                model=embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        finally:
            await client.close()


class OllamaProvider:
    """Thin async wrapper around a local Ollama endpoint."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, model: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, prompt: str, *, temperature: float, max_tokens: int, timeout: float) -> str:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        response = await self._client.post(
            f"{self._base_url}/api/generate",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        text = str(data.get("response", "")).strip()
        if not text:
            raise LLMProviderError("Ollama returned an empty response")
        return text

    async def is_reachable(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/api/tags", timeout=2.0)
            return response.is_success
        except Exception:
            return False


class AsyncLLMClient:
    """OpenAI-primary, Ollama-fallback async client with per-provider retry."""

    def __init__(self, settings: AgentCoreSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._http = httpx.AsyncClient()

        self._openai: OpenAIProvider | None = None
        if self._settings.openai_api_key and not self._settings.use_ollama_only:
            self._openai = OpenAIProvider(
                api_key=self._settings.openai_api_key,
                model=self._settings.openai_model,
                base_url=self._settings.openai_base_url,
            )

        self._ollama = OllamaProvider(
            self._http,
            base_url=self._settings.ollama_base_url,
            model=self._settings.ollama_model,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncLLMClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def call_json(self, prompt: str, *, max_tokens: int = 1200) -> LLMResult:
        """Get a structured JSON response, trying OpenAI before Ollama."""
        errors: dict[str, str] = {}

        if self._openai is not None:
            try:
                return await self._call_provider("openai", self._openai, prompt, max_tokens)
            except Exception as exc:
                errors["openai"] = str(exc)

        try:
            return await self._call_provider("ollama", self._ollama, prompt, max_tokens)
        except Exception as exc:
            errors["ollama"] = str(exc)

        raise LLMAllProvidersFailedError(errors)

    async def _call_provider(
        self, name: str, provider: OpenAIProvider | OllamaProvider, prompt: str, max_tokens: int
    ) -> LLMResult:
        settings = self._settings

        @retry(
            reraise=True,
            stop=stop_after_attempt(settings.llm_max_retries + 1),
            wait=wait_exponential(multiplier=1, max=15),
            retry=retry_if_exception(_is_retryable),
        )
        async def _attempt() -> str:
            return await provider.generate(
                prompt,
                temperature=settings.llm_temperature,
                max_tokens=max_tokens,
                timeout=settings.llm_timeout_seconds,
            )

        start = time.perf_counter()
        raw_text = await _attempt()
        latency_ms = (time.perf_counter() - start) * 1000

        try:
            parsed = parse_json_response(raw_text)
        except Exception as exc:
            raise LLMProviderError(f"{name} returned unparsable JSON: {exc}") from exc

        return LLMResult(
            parsed=parsed,
            raw_text=raw_text,
            provider=name,
            model=provider.model,
            latency_ms=latency_ms,
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed texts via OpenAI embeddings API."""
        if self._openai is None:
            raise LLMProviderError("OpenAI is not configured; embeddings require OPENAI_API_KEY")

        settings = self._settings

        @retry(
            reraise=True,
            stop=stop_after_attempt(settings.llm_max_retries + 1),
            wait=wait_exponential(multiplier=1, max=15),
            retry=retry_if_exception(_is_retryable),
        )
        async def _attempt() -> list[list[float]]:
            return await self._openai.embed_batch(  # type: ignore[union-attr]
                texts,
                embedding_model=settings.embedding_model,
                timeout=settings.llm_timeout_seconds,
            )

        return await _attempt()

    async def provider_status(self) -> dict[str, Any]:
        return {
            "mode": "ollama_only" if self._settings.use_ollama_only else "openai_with_ollama_fallback",
            "openai_configured": self._openai is not None,
            "openai_model": self._settings.openai_model,
            "ollama_base_url": self._settings.ollama_base_url,
            "ollama_model": self._settings.ollama_model,
            "ollama_reachable": await self._ollama.is_reachable(),
        }


__all__ = [
    "AsyncLLMClient",
    "LLMResult",
    "LLMProviderError",
    "LLMAllProvidersFailedError",
]
