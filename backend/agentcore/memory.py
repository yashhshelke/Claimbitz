"""Agent memory interface.

Every agent gets its own semantic memory: a place to store observations
("this claim's ICD code combination looked fraudulent") and later recall
similar past cases ("have I seen this pattern before?").

``AgentMemory`` is the abstract contract. The real implementation — backed
by Pinecone, per the user's requirement to use a vector database — is built
in task #3 (``agentcore.pinecone_memory`` or similar). Defining the
interface here, in the framework task, lets the base ``Agent`` class (and
its unit tests) depend on an abstraction rather than a concrete vector DB,
so agents can be built and tested before Pinecone is wired up.

``InMemoryAgentMemory`` is a naive, no-external-dependency fallback: it does
*not* do real semantic search (no embeddings), just substring/keyword
overlap scoring. It exists so the framework has a working default and so
unit tests don't need network access — it is not intended for production
semantic recall.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .protocol import new_id, now_utc


class MemoryRecord(BaseModel):
    """A single remembered item, as returned from a memory search."""

    model_config = ConfigDict(extra="ignore")

    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = Field(default=None, description="Similarity score, higher is more relevant")


class AgentMemory(ABC):
    """Abstract semantic memory an agent can write to and query."""

    @abstractmethod
    async def remember(
        self,
        *,
        text: str,
        metadata: dict[str, Any] | None = None,
        record_id: str | None = None,
    ) -> str:
        """Persist ``text`` (plus metadata) and return its record id."""

    @abstractmethod
    async def recall(
        self,
        *,
        query: str,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,  # noqa: A002 - matches Pinecone's own kwarg name
    ) -> list[MemoryRecord]:
        """Return up to ``top_k`` records most relevant to ``query``."""


_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


class InMemoryAgentMemory(AgentMemory):
    """Process-local, dependency-free stand-in for a real vector memory.

    Scoring is plain keyword-overlap (Jaccard similarity over tokenized
    words) — good enough to make the framework and its tests deterministic
    without Pinecone, but not a substitute for real semantic search. Task #3
    replaces this with a Pinecone-backed implementation behind the same
    ``AgentMemory`` interface; agents built against that interface don't
    need to change.
    """

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    async def remember(
        self,
        *,
        text: str,
        metadata: dict[str, Any] | None = None,
        record_id: str | None = None,
    ) -> str:
        rid = record_id or new_id()
        meta = dict(metadata or {})
        meta.setdefault("stored_at", now_utc().isoformat())
        self._records[rid] = MemoryRecord(id=rid, text=text, metadata=meta)
        return rid

    async def recall(
        self,
        *,
        query: str,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,  # noqa: A002
    ) -> list[MemoryRecord]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored: list[MemoryRecord] = []
        for record in self._records.values():
            if filter and not all(record.metadata.get(k) == v for k, v in filter.items()):
                continue
            record_tokens = _tokenize(record.text)
            if not record_tokens:
                continue
            overlap = len(query_tokens & record_tokens)
            if overlap == 0:
                continue
            union = len(query_tokens | record_tokens)
            score = overlap / union if union else 0.0
            scored.append(record.model_copy(update={"score": score}))

        scored.sort(key=lambda r: r.score or 0.0, reverse=True)
        return scored[:top_k]

    def __len__(self) -> int:
        return len(self._records)


__all__ = ["MemoryRecord", "AgentMemory", "InMemoryAgentMemory"]
