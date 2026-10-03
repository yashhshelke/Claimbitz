"""Redis-backed shared working memory ("blackboard") for in-flight claims.

The Blackboard provides a fast, shared scratchpad for an in-flight claim's
transient state — extracted data, intermediate agent results, real-time
progress — that doesn't belong in Postgres (too slow for the tight
orchestration loop) or in Pinecone (not semantic, just key-value lookups).

It also exposes pub-sub channels so the FastAPI layer (task #8) can push
real-time progress events to connected WebSocket/SSE clients.

Design:
- One Redis hash per claim: ``claim:{claim_id}`` with fields for extracted
  data, current stage, agent progress, etc.
- Automatic TTL (24h default) so completed claims are garbage-collected.
- Pub-sub channel per claim: ``claim:{claim_id}:events`` for real-time
  streaming.
- A ``InMemoryBlackboard`` fallback for tests/dev without Redis.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from .settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 86400  # 24 hours


class Blackboard(ABC):
    """Abstract shared working memory for a claim pipeline run."""

    @abstractmethod
    async def set_field(
        self, claim_id: str, field: str, value: Any
    ) -> None:
        """Set a single field on the claim's blackboard."""

    @abstractmethod
    async def get_field(
        self, claim_id: str, field: str
    ) -> Any | None:
        """Get a single field (None if not set)."""

    @abstractmethod
    async def set_many(
        self, claim_id: str, data: dict[str, Any]
    ) -> None:
        """Set multiple fields at once."""

    @abstractmethod
    async def get_all(self, claim_id: str) -> dict[str, Any]:
        """Get all fields for a claim."""

    @abstractmethod
    async def publish_event(
        self, claim_id: str, event: dict[str, Any]
    ) -> None:
        """Publish a real-time event on the claim's pub-sub channel."""

    @abstractmethod
    async def delete(self, claim_id: str) -> None:
        """Remove a claim's blackboard entirely."""


class RedisBlackboard(Blackboard):
    """Redis-backed implementation using hashes + pub-sub."""

    def __init__(self, redis_url: str | None = None, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        self._url = redis_url or get_settings().redis_url
        self._ttl = ttl
        self._redis: Any = None

    async def _get_redis(self) -> Any:
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self._url, decode_responses=True
            )
        return self._redis

    def _key(self, claim_id: str) -> str:
        return f"claim:{claim_id}"

    def _channel(self, claim_id: str) -> str:
        return f"claim:{claim_id}:events"

    async def set_field(
        self, claim_id: str, field: str, value: Any
    ) -> None:
        r = await self._get_redis()
        key = self._key(claim_id)
        serialized = json.dumps(value, default=str)
        await r.hset(key, field, serialized)
        await r.expire(key, self._ttl)

    async def get_field(
        self, claim_id: str, field: str
    ) -> Any | None:
        r = await self._get_redis()
        raw = await r.hget(self._key(claim_id), field)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set_many(
        self, claim_id: str, data: dict[str, Any]
    ) -> None:
        r = await self._get_redis()
        key = self._key(claim_id)
        mapping = {
            k: json.dumps(v, default=str) for k, v in data.items()
        }
        await r.hset(key, mapping=mapping)
        await r.expire(key, self._ttl)

    async def get_all(self, claim_id: str) -> dict[str, Any]:
        r = await self._get_redis()
        raw = await r.hgetall(self._key(claim_id))
        result: dict[str, Any] = {}
        for k, v in raw.items():
            try:
                result[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                result[k] = v
        return result

    async def publish_event(
        self, claim_id: str, event: dict[str, Any]
    ) -> None:
        r = await self._get_redis()
        channel = self._channel(claim_id)
        payload = json.dumps(event, default=str)
        await r.publish(channel, payload)

    async def delete(self, claim_id: str) -> None:
        r = await self._get_redis()
        await r.delete(self._key(claim_id))

    async def aclose(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


class InMemoryBlackboard(Blackboard):
    """Process-local fallback for tests/dev without Redis."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._events: dict[str, list[dict[str, Any]]] = {}

    async def set_field(
        self, claim_id: str, field: str, value: Any
    ) -> None:
        self._store.setdefault(claim_id, {})[field] = value

    async def get_field(
        self, claim_id: str, field: str
    ) -> Any | None:
        return self._store.get(claim_id, {}).get(field)

    async def set_many(
        self, claim_id: str, data: dict[str, Any]
    ) -> None:
        self._store.setdefault(claim_id, {}).update(data)

    async def get_all(self, claim_id: str) -> dict[str, Any]:
        return dict(self._store.get(claim_id, {}))

    async def publish_event(
        self, claim_id: str, event: dict[str, Any]
    ) -> None:
        self._events.setdefault(claim_id, []).append(event)

    async def delete(self, claim_id: str) -> None:
        self._store.pop(claim_id, None)
        self._events.pop(claim_id, None)

    def get_events(self, claim_id: str) -> list[dict[str, Any]]:
        """Test helper: retrieve published events."""
        return list(self._events.get(claim_id, []))


__all__ = [
    "Blackboard",
    "RedisBlackboard",
    "InMemoryBlackboard",
    "DEFAULT_TTL_SECONDS",
]
