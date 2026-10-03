"""The abstract base class every specialized agent inherits from.

This is the load-bearing piece of the framework: it gives every agent its
own memory, its own tools, its own system prompt, and a uniform way to
produce a calibrated ``AgentFinding`` — while also handling the mechanics
of peer-to-peer communication (asking a question, raising an objection,
casting a vote) over a ``MessageBus``.

Design intent, per the product requirement that this must be a *true*
multi-agent system and not one LLM calling another:
- Every agent has its own persona (``system_prompt``), independent from any
  other agent's.
- Every agent owns its own ``AgentMemory`` instance (not shared global
  state) — what one agent has "learned" is private to it unless it chooses
  to answer a peer's question.
- Agents talk to each other exclusively through typed ``AgentMessage``
  envelopes (never raw text), and can challenge (``object_to``) or be
  challenged (``respond_to_objection``) on their conclusions.
- ``analyze`` is the one method every concrete agent must implement — it is
  the agent's actual domain reasoning, and everything else in this class is
  plumbing around it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .bus import MessageBus
from .llm import AsyncLLMClient, LLMResult
from .memory import AgentMemory, InMemoryAgentMemory
from .protocol import (
    AgentFinding,
    AgentMessage,
    AgentRole,
    ConfidenceScore,
    MessageType,
    Objection,
    Vote,
    VoteChoice,
)
from .tools import ToolRegistry

_VERDICT_TO_VOTE_CHOICE = {
    "approve": VoteChoice.APPROVE,
    "reject": VoteChoice.REJECT,
    "flag": VoteChoice.ESCALATE,
    "abstain": VoteChoice.ESCALATE,
}


class AgentError(RuntimeError):
    """Raised when a peer agent (contacted over the bus) reports a failure."""


class Agent(ABC):
    """Base class for every specialized agent in the system.

    Subclasses must implement :meth:`analyze` and the :attr:`system_prompt`
    property. Everything else has a working default that subclasses may
    override (``answer_question``, ``respond_to_objection``, ``cast_vote``).
    """

    def __init__(
        self,
        *,
        role: AgentRole,
        llm: AsyncLLMClient,
        memory: AgentMemory | None = None,
        tools: ToolRegistry | None = None,
        bus: MessageBus | None = None,
    ) -> None:
        self.role = role
        self.llm = llm
        self.memory: AgentMemory = memory if memory is not None else InMemoryAgentMemory()
        self.tools = tools if tools is not None else ToolRegistry()
        self.bus = bus
        if bus is not None:
            bus.subscribe(role, self.handle_message)

    # -- What makes this agent *this* agent -------------------------------

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """This agent's persona and standing instructions.

        Prepended to every LLM call this agent makes (see
        :meth:`ask_llm_json`), so two agents given the exact same claim will
        reason about it differently — this is what makes them independent
        specialists rather than one model called from different call sites.
        """

    @abstractmethod
    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        """Produce this agent's structured opinion about ``claim``.

        ``context`` carries situational extras (e.g. an objection being
        responded to, peer findings already available, prior debate
        rounds). Implementations decide what, if anything, to do with it.
        """

    # -- Optional capabilities with sane defaults -------------------------

    async def answer_question(
        self,
        *,
        claim_id: str,
        question: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Answer a peer agent's question about domain knowledge this agent holds.

        Default: not supported. Agents that are useful information sources
        for peers (e.g. Policy Expert answering "what does the policy say
        about pre-authorization?") should override this.
        """
        raise NotImplementedError(f"{self.role.value} does not answer peer questions")

    async def respond_to_objection(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        objection: Objection,
        original: AgentFinding,
    ) -> AgentFinding:
        """React to a peer's challenge of ``original``: defend or revise it.

        Default behavior: re-run :meth:`analyze` with the objection folded
        into ``context`` so subclasses get a chance to change their mind
        (or double down) using their normal reasoning path. Override for
        more deliberate defend-vs-concede logic.
        """
        context = dict(objection=objection.model_dump(mode="json"), prior_finding=original.model_dump(mode="json"))
        return await self.analyze(claim_id=claim_id, claim=claim, context=context)

    async def cast_vote(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Vote:
        """Cast this agent's vote in a debate round.

        Default: derive the vote from a fresh :meth:`analyze` call. Override
        if voting should reason differently than an initial analysis (e.g.
        weighing other agents' published findings more heavily).
        """
        finding = await self.analyze(claim_id=claim_id, claim=claim, context=context)
        choice = _VERDICT_TO_VOTE_CHOICE[finding.verdict.value]
        return Vote(
            voter=self.role,
            choice=choice,
            confidence=finding.confidence,
            justification=finding.reasoning,
        )

    # -- LLM + confidence helpers ------------------------------------------

    async def ask_llm_json(self, instructions: str, *, max_tokens: int = 1200) -> LLMResult:
        """Call this agent's LLM with its persona prepended, returning parsed JSON."""
        prompt = f"{self.system_prompt}\n\n{instructions}"
        return await self.llm.call_json(prompt, max_tokens=max_tokens)

    @staticmethod
    def make_confidence(value: float, rationale: str) -> ConfidenceScore:
        """Build a ``ConfidenceScore``, clamping ``value`` into [0, 1].

        LLM-reported confidence values are untrusted input and occasionally
        arrive out of range (e.g. ``1.2``, or a stray percentage like
        ``95``); clamping here means a slightly-malformed LLM response can't
        crash validation deep inside an agent's ``analyze`` implementation.
        """
        clamped = max(0.0, min(1.0, value))
        return ConfidenceScore(value=clamped, rationale=rationale)

    # -- Peer-to-peer communication -----------------------------------------

    async def ask_peer(
        self,
        *,
        recipient: AgentRole,
        claim_id: str,
        question: str,
        context: dict[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> str:
        """Ask another agent a question and return its answer.

        This is what makes agents "capable of requesting info from others"
        per the product spec, rather than each agent working in isolation.
        """
        if self.bus is None:
            raise RuntimeError(f"{self.role.value} has no message bus attached")

        message = AgentMessage(
            type=MessageType.QUESTION,
            sender=self.role,
            recipient=recipient,
            claim_id=claim_id,
            payload={"question": question, "context": context or {}},
        )
        reply = await self.bus.request(message, timeout=timeout)
        if reply.type == MessageType.ERROR:
            raise AgentError(f"{recipient.value} failed to answer: {reply.payload.get('error')}")
        return str(reply.payload.get("answer", ""))

    async def object_to(
        self,
        *,
        target_finding: AgentFinding,
        reason: str,
        counter_evidence: list[dict[str, Any]] | None = None,
        claim: dict[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> AgentFinding:
        """Challenge a peer's finding and get back their defended/revised finding.

        This is the "capable of ... rejecting outputs" / debate-triggering
        primitive. The full Debate Mode round-tracking (objections tallied
        across multiple agents, quorum, escalation on deadlock) is owned by
        the Supervisor (task #5); this method is the point-to-point
        challenge that debate rounds are built out of.
        """
        if self.bus is None:
            raise RuntimeError(f"{self.role.value} has no message bus attached")

        objection = Objection(
            objector=self.role,
            target_agent=target_finding.agent,
            target_finding_id=target_finding.id,
            reason=reason,
        )
        message = AgentMessage(
            type=MessageType.OBJECTION,
            sender=self.role,
            recipient=target_finding.agent,
            claim_id=target_finding.claim_id,
            payload={
                "objection": objection.model_dump(mode="json"),
                "original_finding": target_finding.model_dump(mode="json"),
                "claim": claim or {},
                "counter_evidence": counter_evidence or [],
            },
        )
        reply = await self.bus.request(message, timeout=timeout)
        if reply.type == MessageType.ERROR:
            raise AgentError(f"{target_finding.agent.value} failed to respond: {reply.payload.get('error')}")
        return AgentFinding.model_validate(reply.payload["finding"])

    # -- Wire dispatch -------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> AgentMessage | None:
        """Dispatch an incoming ``AgentMessage`` to the right handler.

        This is the single entry point the message bus calls. It never
        raises: any exception from ``analyze``/``answer_question``/etc is
        caught and turned into an ``ERROR`` reply, so one agent's failure
        (an LLM outage, a bad tool call) can't take down the bus's dispatch
        loop or silently hang a peer waiting on ``request()``.
        """
        try:
            return await self._dispatch(message)
        except Exception as exc:  # noqa: BLE001 - deliberately broad: last-resort safety net
            return message.reply(
                type=MessageType.ERROR,
                sender=self.role,
                payload={"error": str(exc), "error_type": type(exc).__name__},
            )

    async def _dispatch(self, message: AgentMessage) -> AgentMessage | None:
        if message.type == MessageType.REQUEST:
            action = message.payload.get("action", "analyze")
            claim = message.payload.get("claim", {})
            context = message.payload.get("context")

            if action == "vote":
                vote = await self.cast_vote(claim_id=message.claim_id, claim=claim, context=context)
                return message.reply(type=MessageType.VOTE, sender=self.role, payload={"vote": vote.model_dump(mode="json")})

            finding = await self.analyze(claim_id=message.claim_id, claim=claim, context=context)
            return message.reply(type=MessageType.RESPONSE, sender=self.role, payload={"finding": finding.model_dump(mode="json")})

        if message.type == MessageType.QUESTION:
            answer = await self.answer_question(
                claim_id=message.claim_id,
                question=str(message.payload.get("question", "")),
                context=message.payload.get("context"),
            )
            return message.reply(type=MessageType.ANSWER, sender=self.role, payload={"answer": answer})

        if message.type == MessageType.OBJECTION:
            objection = Objection.model_validate(message.payload["objection"])
            original = AgentFinding.model_validate(message.payload["original_finding"])
            revised = await self.respond_to_objection(
                claim_id=message.claim_id,
                claim=message.payload.get("claim", {}),
                objection=objection,
                original=original,
            )
            return message.reply(type=MessageType.ASSERTION, sender=self.role, payload={"finding": revised.model_dump(mode="json")})

        # EVENT/HEARTBEAT/ESCALATION/etc: no reply expected from a plain agent.
        return None


__all__ = ["Agent", "AgentError"]
