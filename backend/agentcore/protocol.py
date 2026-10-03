"""Shared communication protocol for the ClaimBlitz multi-agent system.

Every agent, the event bus, the Supervisor, and the API layer speak this
protocol exclusively. Nothing in here talks to RabbitMQ, Redis, Postgres, or
Pinecone directly — this module is pure data (Pydantic models + enums) so it
can be imported anywhere without pulling in infrastructure dependencies.

Design goals:
- JSON-only structured communication between agents (no free-text chat).
- Every opinion an agent contributes is a typed ``AgentFinding`` carrying a
  verdict, a calibrated confidence score, reasoning, and evidence — this is
  what makes the system's decisions explainable and auditable.
- Disagreement is a first-class concept (``Objection``, ``Vote``,
  ``DebateRound``) rather than something bolted on.
- Every message carries a ``trace_id`` (propagated end-to-end) and a
  ``causation_id`` (the message that caused it), so any claim's full journey
  through the system can be replayed or audited after the fact.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def new_id() -> str:
    """Generate a new opaque identifier (message/finding/trace ids, etc.)."""
    return uuid4().hex


def now_utc() -> datetime:
    """Current UTC timestamp, timezone-aware (never use naive datetimes)."""
    return datetime.now(timezone.utc)


# Confidence below this line always triggers human-in-the-loop escalation,
# per the product requirement: "escalate to a human below 80% confidence."
HUMAN_ESCALATION_CONFIDENCE_THRESHOLD = 0.80

# Below this line a confidence score is considered "low" for reporting
# purposes (distinct from the escalation threshold above, which is the one
# behavioral gate — this one is just for dashboards/labels).
LOW_CONFIDENCE_THRESHOLD = 0.50


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentRole(str, Enum):
    """The fixed roster of specialized agents in the system.

    Exactly the ten roles called for by the architecture: one orchestrator
    (Supervisor), a document intake pair (Scanner, OCR), a structural check
    (Validator), four parallel domain analysts (Medical Expert, Policy
    Expert, Fraud Detection, Risk Assessment), an outbound agent
    (Communication), and a consensus agent (Judge).
    """

    SUPERVISOR = "supervisor"
    SCANNER = "scanner"
    OCR = "ocr"
    VALIDATOR = "validator"
    MEDICAL_EXPERT = "medical_expert"
    POLICY_EXPERT = "policy_expert"
    FRAUD_DETECTION = "fraud_detection"
    RISK_ASSESSMENT = "risk_assessment"
    COMMUNICATION = "communication"
    JUDGE = "judge"


# Agents whose findings run concurrently once OCR + validation succeed, and
# whose disagreements are what Debate Mode / the Judge exist to resolve.
PARALLEL_ANALYST_ROLES: tuple[AgentRole, ...] = (
    AgentRole.MEDICAL_EXPERT,
    AgentRole.POLICY_EXPERT,
    AgentRole.FRAUD_DETECTION,
    AgentRole.RISK_ASSESSMENT,
)


class ClaimStage(str, Enum):
    """States of the claim workflow state machine, owned by the Supervisor."""

    INGESTED = "ingested"
    SCANNING = "scanning"
    OCR_EXTRACTION = "ocr_extraction"
    VALIDATION = "validation"
    PARALLEL_ANALYSIS = "parallel_analysis"
    DEBATE = "debate"
    JUDGMENT = "judgment"
    HUMAN_ESCALATION = "human_escalation"
    COMMUNICATION = "communication"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageType(str, Enum):
    """The kind of speech-act an ``AgentMessage`` represents on the bus."""

    REQUEST = "request"        # ask an agent to do work
    RESPONSE = "response"      # result of a REQUEST
    QUESTION = "question"      # ask a peer agent for information it holds
    ANSWER = "answer"          # reply to a QUESTION
    ASSERTION = "assertion"    # publish an AgentFinding / opinion
    OBJECTION = "objection"    # challenge another agent's assertion
    VOTE = "vote"              # cast a vote in a debate round
    ESCALATION = "escalation"  # hand off to a human reviewer
    ERROR = "error"            # an agent failed to complete its work
    EVENT = "event"            # lifecycle/broadcast notification (fan-out)
    HEARTBEAT = "heartbeat"    # liveness signal for health/monitoring


class EvidenceSource(str, Enum):
    DOCUMENT = "document"
    POLICY_DB = "policy_db"
    VECTOR_MEMORY = "vector_memory"
    EXTERNAL_API = "external_api"
    PEER_AGENT = "peer_agent"
    RULE_ENGINE = "rule_engine"


class ConfidenceBand(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Verdict(str, Enum):
    """An agent's (or the Judge's) conclusion about a claim."""

    APPROVE = "approve"
    REJECT = "reject"
    FLAG = "flag"        # suspicious / needs more info, not an outright reject
    ABSTAIN = "abstain"  # out of this agent's domain, or insufficient evidence


class VoteChoice(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    UNRESOLVED_DEBATE = "unresolved_debate"
    FRAUD_SUSPECTED = "fraud_suspected"
    POLICY_AMBIGUITY = "policy_ambiguity"
    SYSTEM_ERROR = "system_error"


class EscalationStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"


# ---------------------------------------------------------------------------
# Confidence, evidence, decision path — the explainability primitives
# ---------------------------------------------------------------------------


class ConfidenceScore(BaseModel):
    """A calibrated, self-reported confidence value with a stated reason.

    Every agent must attach one of these to every finding, vote, and ruling
    it produces. Confidence is never inferred after the fact — the agent
    that produced the opinion is responsible for scoring it.
    """

    model_config = ConfigDict(extra="ignore")

    value: float = Field(ge=0.0, le=1.0, description="Calibrated confidence, 0.0-1.0")
    rationale: str = Field(default="", description="Why this confidence value was assigned")

    @property
    def band(self) -> ConfidenceBand:
        if self.value >= HUMAN_ESCALATION_CONFIDENCE_THRESHOLD:
            return ConfidenceBand.HIGH
        if self.value >= LOW_CONFIDENCE_THRESHOLD:
            return ConfidenceBand.MODERATE
        return ConfidenceBand.LOW

    @property
    def requires_escalation(self) -> bool:
        """True when this score alone is grounds for human-in-the-loop review."""
        return self.value < HUMAN_ESCALATION_CONFIDENCE_THRESHOLD


class Evidence(BaseModel):
    """One piece of support for a finding — what an agent is pointing at."""

    model_config = ConfigDict(extra="ignore")

    source: EvidenceSource
    field: str | None = Field(default=None, description="Referenced claim field, e.g. 'diagnosis'")
    snippet: str = Field(default="", description="Quoted/extracted text supporting the finding")
    citation: str | None = Field(default=None, description="e.g. 'Policy §4.2', page number, vector id")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Relative contribution to the finding")


class DecisionStep(BaseModel):
    """One entry in a claim's audit trail — what an agent did and why."""

    model_config = ConfigDict(extra="ignore")

    agent: AgentRole
    action: str = Field(description="e.g. 'extracted_fields', 'flagged_mismatch', 'voted_approve'")
    summary: str = ""
    confidence: ConfidenceScore | None = None
    timestamp: datetime = Field(default_factory=now_utc)


class DecisionPath(BaseModel):
    """The full ordered audit trail for a single claim, across all agents."""

    model_config = ConfigDict(extra="ignore")

    claim_id: str
    steps: list[DecisionStep] = Field(default_factory=list)

    def append(self, step: DecisionStep) -> DecisionPath:
        """Return a new DecisionPath with ``step`` appended (immutable style)."""
        return DecisionPath(claim_id=self.claim_id, steps=[*self.steps, step])


# ---------------------------------------------------------------------------
# Agent findings — the JSON-only structured opinion every analyst produces
# ---------------------------------------------------------------------------


class AgentFinding(BaseModel):
    """A structured, JSON-only opinion an agent contributes about a claim.

    This is the atomic unit of collaboration: agents never send each other
    free-text chat, they publish (and can later be challenged on) findings
    like this one.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=new_id)
    agent: AgentRole
    claim_id: str
    verdict: Verdict
    confidence: ConfidenceScore
    reasoning: str = Field(description="Human-readable explanation of the verdict")
    evidence: list[Evidence] = Field(default_factory=list)
    referenced_fields: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list, description="e.g. ['duplicate_claim', 'icd_mismatch']")
    created_at: datetime = Field(default_factory=now_utc)


# ---------------------------------------------------------------------------
# Debate mode — objections, votes, and rounds
# ---------------------------------------------------------------------------


class Objection(BaseModel):
    """A challenge raised by one agent against another agent's finding."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=new_id)
    objector: AgentRole
    target_agent: AgentRole
    target_finding_id: str | None = None
    reason: str
    counter_evidence: list[Evidence] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)


class Vote(BaseModel):
    """A single agent's vote in a debate round."""

    model_config = ConfigDict(extra="ignore")

    voter: AgentRole
    choice: VoteChoice
    confidence: ConfidenceScore
    justification: str = ""
    cast_at: datetime = Field(default_factory=now_utc)


class DebateRound(BaseModel):
    """One round of structured disagreement over a claim.

    Debate Mode is entered automatically whenever two or more analyst
    findings disagree on verdict (or a lone finding falls below the
    escalation confidence threshold). Rounds continue until a quorum is
    reached or a round limit is hit, at which point the Judge rules.
    """

    model_config = ConfigDict(extra="ignore")

    round_number: int = Field(ge=1)
    claim_id: str
    objections: list[Objection] = Field(default_factory=list)
    votes: list[Vote] = Field(default_factory=list)
    opened_at: datetime = Field(default_factory=now_utc)
    closed_at: datetime | None = None

    @property
    def is_closed(self) -> bool:
        return self.closed_at is not None


class JudgeRuling(BaseModel):
    """The Judge agent's binding consensus decision for a claim."""

    model_config = ConfigDict(extra="ignore")

    claim_id: str
    verdict: Verdict
    confidence: ConfidenceScore
    dissenting_agents: list[AgentRole] = Field(default_factory=list)
    rationale: str
    decision_path: DecisionPath
    requires_human_review: bool = False
    ruled_at: datetime = Field(default_factory=now_utc)


# ---------------------------------------------------------------------------
# Human-in-the-loop escalation
# ---------------------------------------------------------------------------


class HumanEscalation(BaseModel):
    """A claim handed off for human review, and its resolution lifecycle."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=new_id)
    claim_id: str
    reason: EscalationReason
    triggered_by: AgentRole
    confidence_at_escalation: ConfidenceScore | None = None
    decision_path: DecisionPath | None = None
    status: EscalationStatus = EscalationStatus.PENDING
    assigned_to: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    resolved_at: datetime | None = None
    resolution_notes: str | None = None


# ---------------------------------------------------------------------------
# The wire envelope — what actually travels over the event bus
# ---------------------------------------------------------------------------


class AgentMessage(BaseModel):
    """The envelope every agent-to-agent (or agent-to-Supervisor) message uses.

    ``payload`` carries the type-specific body (e.g. a serialized
    ``AgentFinding``, ``Objection``, or ``Vote``) as a plain dict, so the
    envelope itself never needs to change shape as new payload kinds are
    added. Consumers dispatch on ``type`` to know how to parse ``payload``.
    """

    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(default_factory=new_id)
    type: MessageType
    sender: AgentRole
    recipient: AgentRole | None = Field(default=None, description="None means broadcast")
    claim_id: str
    correlation_id: str = Field(default_factory=new_id, description="Ties a request to its response(s)")
    causation_id: str | None = Field(default=None, description="message_id that caused this message")
    trace_id: str = Field(default_factory=new_id, description="Propagated end-to-end for tracing/replay")
    priority: Priority = Priority.NORMAL
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)

    def reply(
        self,
        *,
        type: MessageType,  # noqa: A002 - mirrors the field name intentionally
        sender: AgentRole,
        payload: dict[str, Any] | None = None,
        priority: Priority = Priority.NORMAL,
    ) -> AgentMessage:
        """Build a reply correctly correlated/caused-by this message.

        Keeps ``correlation_id`` and ``trace_id`` stable across the whole
        conversation, and sets ``causation_id`` to this message's id so the
        full chain can be reconstructed for audit/replay.
        """
        return AgentMessage(
            type=type,
            sender=sender,
            recipient=self.sender,
            claim_id=self.claim_id,
            correlation_id=self.correlation_id,
            causation_id=self.message_id,
            trace_id=self.trace_id,
            priority=priority,
            payload=payload or {},
        )


# ---------------------------------------------------------------------------
# Aggregate workflow state — what the Supervisor tracks per claim
# ---------------------------------------------------------------------------


class ClaimWorkflowState(BaseModel):
    """A point-in-time snapshot of a claim's progress through the system.

    This is the shape returned by the workflow inspection APIs (task #8) and
    persisted by the Supervisor (task #5) — it is the single source of truth
    for "what has happened to this claim so far and why."
    """

    model_config = ConfigDict(extra="ignore")

    claim_id: str
    stage: ClaimStage
    is_paused: bool = False
    retry_count: int = 0
    findings: list[AgentFinding] = Field(default_factory=list)
    debate_rounds: list[DebateRound] = Field(default_factory=list)
    ruling: JudgeRuling | None = None
    escalation: HumanEscalation | None = None
    decision_path: DecisionPath
    started_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


# ---------------------------------------------------------------------------
# Bus topology conventions (actual queue/exchange declarations live in bus.py)
# ---------------------------------------------------------------------------

EXCHANGE_EVENTS = "claimblitz.events"      # topic exchange: lifecycle + broadcast
EXCHANGE_COMMANDS = "claimblitz.commands"  # direct exchange: supervisor -> one agent
EXCHANGE_DLX = "claimblitz.dlx"            # dead-letter exchange for poison messages


def routing_key(role: AgentRole, claim_id: str | None = None) -> str:
    """Canonical topic routing key: ``agent.<role>`` or ``agent.<role>.<claim_id>``."""
    return f"agent.{role.value}.{claim_id}" if claim_id else f"agent.{role.value}"


__all__ = [
    "AgentRole",
    "PARALLEL_ANALYST_ROLES",
    "ClaimStage",
    "Priority",
    "MessageType",
    "EvidenceSource",
    "ConfidenceBand",
    "Verdict",
    "VoteChoice",
    "EscalationReason",
    "EscalationStatus",
    "ConfidenceScore",
    "Evidence",
    "DecisionStep",
    "DecisionPath",
    "AgentFinding",
    "Objection",
    "Vote",
    "DebateRound",
    "JudgeRuling",
    "HumanEscalation",
    "AgentMessage",
    "ClaimWorkflowState",
    "HUMAN_ESCALATION_CONFIDENCE_THRESHOLD",
    "LOW_CONFIDENCE_THRESHOLD",
    "EXCHANGE_EVENTS",
    "EXCHANGE_COMMANDS",
    "EXCHANGE_DLX",
    "routing_key",
    "new_id",
    "now_utc",
]
