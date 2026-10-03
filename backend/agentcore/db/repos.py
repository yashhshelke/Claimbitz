"""MongoDB repository classes — async CRUD over document collections.

Collections:
- claims          — one document per submitted claim
- findings        — one document per AgentFinding
- workflows       — one document per claim workflow state
- escalations     — human-in-the-loop records
- audit_log       — append-only decision trail

Each repo gets the database via ``get_database()`` and operates on its
own collection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..protocol import AgentFinding, ClaimWorkflowState, DecisionStep, HumanEscalation
from .engine import get_database


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ClaimRepository:
    """CRUD for the claims collection."""

    def __init__(self) -> None:
        self._col = get_database()["claims"]

    async def create(self, **kwargs: Any) -> dict[str, Any]:
        doc = {**kwargs, "created_at": _utcnow(), "updated_at": _utcnow()}
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get(self, claim_id: str) -> dict[str, Any] | None:
        return await self._col.find_one({"_id": claim_id})

    async def update_stage(self, claim_id: str, stage: str, **extras: Any) -> None:
        await self._col.update_one(
            {"_id": claim_id},
            {"$set": {"stage": stage, "updated_at": _utcnow(), **extras}},
        )

    async def list_by_stage(self, stage: str, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self._col.find({"stage": stage}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)


class FindingRepository:
    """CRUD for the findings collection."""

    def __init__(self) -> None:
        self._col = get_database()["findings"]

    async def save(self, finding: AgentFinding) -> dict[str, Any]:
        doc = {
            "_id": finding.id,
            "claim_id": finding.claim_id,
            "agent_role": finding.agent.value,
            "verdict": finding.verdict.value,
            "confidence": finding.confidence.value,
            "reasoning": finding.reasoning,
            "evidence": [e.model_dump(mode="json") for e in finding.evidence],
            "referenced_fields": finding.referenced_fields,
            "tags": finding.tags,
            "created_at": finding.created_at,
        }
        await self._col.insert_one(doc)
        return doc

    async def list_for_claim(self, claim_id: str) -> list[dict[str, Any]]:
        cursor = self._col.find({"claim_id": claim_id}).sort("created_at", 1)
        return await cursor.to_list(length=100)


class WorkflowRepository:
    """CRUD for the workflows collection."""

    def __init__(self) -> None:
        self._col = get_database()["workflows"]

    async def upsert(self, state: ClaimWorkflowState) -> None:
        doc = {
            "_id": state.claim_id,
            "stage": state.stage.value,
            "is_paused": state.is_paused,
            "retry_count": state.retry_count,
            "decision_path": state.decision_path.model_dump(mode="json"),
            "debate_rounds": [dr.model_dump(mode="json") for dr in state.debate_rounds],
            "ruling": state.ruling.model_dump(mode="json") if state.ruling else None,
            "updated_at": _utcnow(),
        }
        await self._col.replace_one({"_id": state.claim_id}, doc, upsert=True)

    async def get(self, claim_id: str) -> dict[str, Any] | None:
        return await self._col.find_one({"_id": claim_id})


class EscalationRepository:
    """CRUD for the escalations collection."""

    def __init__(self) -> None:
        self._col = get_database()["escalations"]

    async def create(self, escalation: HumanEscalation) -> dict[str, Any]:
        doc = {
            "_id": escalation.id,
            "claim_id": escalation.claim_id,
            "reason": escalation.reason.value,
            "triggered_by": escalation.triggered_by.value,
            "confidence_value": escalation.confidence_at_escalation.value if escalation.confidence_at_escalation else None,
            "status": escalation.status.value,
            "created_at": escalation.created_at,
        }
        await self._col.insert_one(doc)
        return doc

    async def list_pending(self, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self._col.find({"status": "pending"}).sort("created_at", 1).limit(limit)
        return await cursor.to_list(length=limit)


class AuditRepository:
    """Append-only audit log."""

    def __init__(self) -> None:
        self._col = get_database()["audit_log"]

    async def log_step(self, step: DecisionStep, claim_id: str) -> None:
        doc = {
            "claim_id": claim_id,
            "agent_role": step.agent.value,
            "action": step.action,
            "summary": step.summary,
            "confidence": step.confidence.value if step.confidence else None,
            "created_at": step.timestamp,
        }
        await self._col.insert_one(doc)

    async def get_trail(self, claim_id: str) -> list[dict[str, Any]]:
        cursor = self._col.find({"claim_id": claim_id}).sort("created_at", 1)
        return await cursor.to_list(length=500)
