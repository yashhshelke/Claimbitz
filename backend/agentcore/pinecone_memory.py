"""Pinecone-backed semantic memory for agents.

This is the real implementation of the ``AgentMemory`` interface defined in
``agentcore.memory`` — per the product requirement to use Pinecone as the
vector database backing agent memory (fraud-pattern matching, medical/policy
knowledge retrieval, judge precedent lookup). It is a drop-in replacement
for ``InMemoryAgentMemory``; nothing in ``agentcore.base.Agent`` needs to
change to use it.

Two deployment modes, selected by ``AgentCoreSettings.pinecone_use_local``:

- **Local (dev/test)**: talks to the Pinecone Local docker emulator
  (``ghcr.io/pinecone-io/pinecone-local``), which requires no real API key
  (``pclocal`` is accepted as a placeholder) and needs its ``https://`` host
  rewritten to ``http://`` because it only serves plaintext HTTP — this
  quirk is documented by Pinecone and was confirmed against a live
  container while building this module (SSL handshake fails otherwise).
- **Serverless (staging/prod)**: talks to real Pinecone with
  ``PINECONE_API_KEY``, creating a serverless index in
  ``pinecone_cloud``/``pinecone_region`` if it doesn't already exist.

Embeddings: Pinecone Local does not support Pinecone's own hosted Inference
API (confirmed in Pinecone's own docs: "Pinecone Local does not currently
support ... Pinecone Inference"), so this module embeds text itself via the
Gemini embedding endpoint (``AsyncLLMClient.embed_batch``), reusing the same
LLM provider/key every agent already has. Each ``PineconeAgentMemory``
instance is scoped to one Pinecone *namespace* — typically one per agent
role, per the design goal that each agent's memory is private unless it
chooses to share it (see ``agentcore.base.Agent.answer_question``).
"""

from __future__ import annotations

from typing import Any

from pinecone import AsyncPinecone, ServerlessSpec

from .llm import AsyncLLMClient
from .memory import AgentMemory, MemoryRecord
from .protocol import new_id, now_utc
from .settings import AgentCoreSettings, get_settings


class PineconeAgentMemory(AgentMemory):
    """Semantic memory backed by a Pinecone index, scoped to one namespace.

    Construction is cheap (no network I/O); call :meth:`ensure_ready` once
    before first use (or rely on ``remember``/``recall`` to call it
    lazily) to create the underlying index/connection.
    """

    def __init__(
        self,
        *,
        namespace: str,
        llm: AsyncLLMClient,
        settings: AgentCoreSettings | None = None,
    ) -> None:
        self._namespace = namespace
        self._llm = llm
        self._settings = settings or get_settings()
        self._pc: AsyncPinecone | None = None
        self._index: Any = None  # pinecone.AsyncIndex, once resolved
        self._ready = False

    async def ensure_ready(self) -> None:
        """Create the Pinecone client/index connection if not already done.

        Idempotent — safe to call before every operation (``remember`` and
        ``recall`` both do this) without re-creating the index each time.
        """
        if self._ready:
            return

        settings = self._settings
        if settings.pinecone_use_local:
            pc = AsyncPinecone(api_key="pclocal", host=settings.pinecone_local_host)
        else:
            if not settings.pinecone_api_key:
                raise RuntimeError(
                    "PINECONE_API_KEY is not set and pinecone_use_local is False. "
                    "Either provide a real Pinecone API key, or set PINECONE_USE_LOCAL=true "
                    "and run the Pinecone Local docker emulator for dev/test."
                )
            pc = AsyncPinecone(api_key=settings.pinecone_api_key)

        self._pc = pc

        name = settings.pinecone_index_name
        if not await pc.has_index(name):
            await pc.create_index(
                name=name,
                dimension=settings.embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
                deletion_protection="disabled",
            )

        desc = await pc.describe_index(name)
        # Pinecone Local advertises an https:// host but only serves
        # plaintext HTTP; forcing http:// avoids a TLS handshake failure
        # (SSL: WRONG_VERSION_NUMBER), confirmed against a live container.
        # Real Pinecone serverless hosts are HTTPS-only, so this rewrite is
        # only applied in local mode.
        host = desc.host.replace("https://", "http://") if settings.pinecone_use_local else desc.host
        self._index = await pc.index(name=name, host=host)
        self._ready = True

    async def aclose(self) -> None:
        """Release the underlying HTTP connections."""
        if self._index is not None:
            await self._index.close()
        if self._pc is not None:
            await self._pc.close()
        self._ready = False

    async def remember(
        self,
        *,
        text: str,
        metadata: dict[str, Any] | None = None,
        record_id: str | None = None,
    ) -> str:
        await self.ensure_ready()

        rid = record_id or new_id()
        [vector] = await self._llm.embed_batch([text])

        meta = dict(metadata or {})
        meta["text"] = text
        meta.setdefault("stored_at", now_utc().isoformat())

        await self._index.upsert(
            vectors=[{"id": rid, "values": vector, "metadata": meta}],
            namespace=self._namespace,
        )
        return rid

    async def recall(
        self,
        *,
        query: str,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,  # noqa: A002 - matches Pinecone's own kwarg name
    ) -> list[MemoryRecord]:
        await self.ensure_ready()

        [query_vector] = await self._llm.embed_batch([query])

        response = await self._index.query(
            vector=query_vector,
            top_k=top_k,
            namespace=self._namespace,
            filter=filter,
            include_metadata=True,
            include_values=False,
        )

        records: list[MemoryRecord] = []
        for match in response.matches:
            metadata = dict(match.metadata or {})
            text = metadata.pop("text", "")
            records.append(MemoryRecord(id=match.id, text=text, metadata=metadata, score=match.score))
        return records

    async def forget_namespace(self) -> None:
        """Delete every record in this memory's namespace.

        Mainly useful for tests / re-running a demo scenario from a clean
        slate. Not exposed via the base ``AgentMemory`` interface since it's
        a destructive operation most callers should not need.
        """
        await self.ensure_ready()
        await self._index.delete(delete_all=True, namespace=self._namespace)


__all__ = ["PineconeAgentMemory"]
