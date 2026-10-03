"""Supervisor orchestration engine.

The Supervisor is NOT "just another agent" — it is the workflow controller
that drives claims through the multi-agent pipeline. It owns the
``ClaimWorkflowState`` for each in-flight claim and decides what happens
next based on:
- The current ``ClaimStage``
- The results returned by agents it dispatches work to
- Disagreement detection (do analysts' verdicts conflict?)
- Confidence thresholds (does any finding require escalation?)

Workflow state machine:
  INGESTED -> SCANNING -> OCR_EXTRACTION -> VALIDATION
  -> PARALLEL_ANALYSIS (fan-out to 4 analysts concurrently)
  -> (if consensus) COMMUNICATION -> COMPLETED
  -> (if disagreement) DEBATE (up to MAX_DEBATE_ROUNDS)
  -> (if still unresolved) JUDGMENT (Judge agent rules)
  -> (if confidence < 0.80) HUMAN_ESCALATION
  -> (otherwise) COMMUNICATION -> COMPLETED | REJECTED

The Supervisor talks to agents by awaiting their ``analyze()`` directly
(in-process mode) rather than going through the message bus — this is
simpler, avoids circular bus subscriptions, and the bus exists for
*agent-to-agent* communication (peer questions, objections), not for the
orchestrator-to-agent dispatch pattern.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .agents.communication import CommunicationAgent
from .agents.fraud_detection import FraudDetectionAgent
from .agents.judge import JudgeAgent
from .agents.medical_expert import MedicalExpertAgent
from .agents.ocr import OCRAgent
from .agents.policy_expert import PolicyExpertAgent
from .agents.risk_assessment import RiskAssessmentAgent
from .agents.scanner import ScannerAgent
from .agents.validator import ValidatorAgent
from .protocol import (
    AgentFinding,
    AgentRole,
    ClaimStage,
    ClaimWorkflowState,
    DebateRound,
    DecisionPath,
    DecisionStep,
    EscalationReason,
    HumanEscalation,
    HUMAN_ESCALATION_CONFIDENCE_THRESHOLD,
    JudgeRuling,
    PARALLEL_ANALYST_ROLES,
    Verdict,
    now_utc,
)

logger = logging.getLogger(__name__)

MAX_DEBATE_ROUNDS = 2


class Supervisor:
    """Workflow orchestrator for the multi-agent claim pipeline."""

    def __init__(
        self,
        *,
        scanner: ScannerAgent,
        ocr: OCRAgent,
        validator: ValidatorAgent,
        medical_expert: MedicalExpertAgent,
        policy_expert: PolicyExpertAgent,
        fraud_detection: FraudDetectionAgent,
        risk_assessment: RiskAssessmentAgent,
        communication: CommunicationAgent,
        judge: JudgeAgent,
    ) -> None:
        self.scanner = scanner
        self.ocr = ocr
        self.validator = validator
        self.medical_expert = medical_expert
        self.policy_expert = policy_expert
        self.fraud_detection = fraud_detection
        self.risk_assessment = risk_assessment
        self.communication = communication
        self.judge = judge

        self._analysts: dict[AgentRole, Any] = {
            AgentRole.MEDICAL_EXPERT: self.medical_expert,
            AgentRole.POLICY_EXPERT: self.policy_expert,
            AgentRole.FRAUD_DETECTION: self.fraud_detection,
            AgentRole.RISK_ASSESSMENT: self.risk_assessment,
        }

    async def process_claim(
        self,
        *,
        claim_id: str,
        raw_text: str,
        file_meta: dict[str, Any] | None = None,
    ) -> ClaimWorkflowState:
        """Drive a claim through the entire pipeline end-to-end.

        Returns the final ``ClaimWorkflowState`` snapshot.
        """
        dp = DecisionPath(claim_id=claim_id)
        state = ClaimWorkflowState(
            claim_id=claim_id,
            stage=ClaimStage.INGESTED,
            decision_path=dp,
        )

        try:
            state = await self._run_scanning(state, file_meta or {})
            if state.stage in (ClaimStage.REJECTED, ClaimStage.FAILED):
                return state

            await asyncio.sleep(1.5)  # Rate limit delay

            state = await self._run_ocr(state, raw_text)
            if state.stage in (ClaimStage.REJECTED, ClaimStage.FAILED):
                return state

            await asyncio.sleep(1.5)  # Rate limit delay

            state = await self._run_validation(state)
            # Validation issues are noted but DON'T stop the pipeline.
            # Only Scanner rejection (unprocessable file) stops early.
            # The parallel analysts will factor in validation issues.
            if state.stage == ClaimStage.REJECTED:
                state.stage = ClaimStage.VALIDATION  # downgrade to continue

            state = await self._run_parallel_analysis(state)
            state = await self._resolve_disagreement(state)
            state = await self._run_communication(state)

        except Exception as exc:
            logger.exception("Supervisor pipeline failed for %s", claim_id)
            state.stage = ClaimStage.FAILED
            state.decision_path = state.decision_path.append(
                DecisionStep(
                    agent=AgentRole.SUPERVISOR,
                    action="pipeline_failed",
                    summary=str(exc),
                )
            )

        state.updated_at = now_utc()
        return state

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    async def _run_scanning(
        self, state: ClaimWorkflowState, file_meta: dict[str, Any]
    ) -> ClaimWorkflowState:
        state.stage = ClaimStage.SCANNING
        finding = await self.scanner.analyze(
            claim_id=state.claim_id, claim={"file_meta": file_meta}
        )
        state.findings.append(finding)
        state.decision_path = state.decision_path.append(
            DecisionStep(
                agent=AgentRole.SCANNER,
                action="scanned_document",
                summary=finding.reasoning,
                confidence=finding.confidence,
            )
        )
        if finding.verdict == Verdict.REJECT:
            state.stage = ClaimStage.REJECTED
        return state

    async def _run_ocr(
        self, state: ClaimWorkflowState, raw_text: str
    ) -> ClaimWorkflowState:
        state.stage = ClaimStage.OCR_EXTRACTION
        finding = await self.ocr.analyze(
            claim_id=state.claim_id, claim={"raw_text": raw_text}
        )
        state.findings.append(finding)
        state.decision_path = state.decision_path.append(
            DecisionStep(
                agent=AgentRole.OCR,
                action="extracted_fields",
                summary=finding.reasoning,
                confidence=finding.confidence,
            )
        )
        # Store extracted data on the state for downstream agents
        # OCR agent puts extracted fields in its finding's referenced_fields
        # but the real data lives in the extract() return — we call it here
        extracted = await self.ocr.extract(
            claim_id=state.claim_id, raw_text=raw_text
        )
        # Attach extracted claim data for downstream use
        state._extracted_claim = extracted  # type: ignore[attr-defined]
        return state

    async def _run_validation(
        self, state: ClaimWorkflowState
    ) -> ClaimWorkflowState:
        state.stage = ClaimStage.VALIDATION
        claim_data = getattr(state, "_extracted_claim", {})
        finding = await self.validator.analyze(
            claim_id=state.claim_id, claim=claim_data
        )
        state.findings.append(finding)
        state.decision_path = state.decision_path.append(
            DecisionStep(
                agent=AgentRole.VALIDATOR,
                action="validated_fields",
                summary=finding.reasoning,
                confidence=finding.confidence,
            )
        )
        if finding.verdict == Verdict.REJECT:
            state.stage = ClaimStage.REJECTED
        return state

    async def _run_parallel_analysis(
        self, state: ClaimWorkflowState
    ) -> ClaimWorkflowState:
        """Run analyst agents sequentially with delays to avoid rate limits."""
        state.stage = ClaimStage.PARALLEL_ANALYSIS
        claim_data = getattr(state, "_extracted_claim", {})

        # Run sequentially with delay to respect Groq free-tier rate limits
        for role in PARALLEL_ANALYST_ROLES:
            try:
                finding = await self._analysts[role].analyze(
                    claim_id=state.claim_id, claim=claim_data
                )
                state.findings.append(finding)
                state.decision_path = state.decision_path.append(
                    DecisionStep(
                        agent=role,
                        action="analyzed_claim",
                        summary=finding.reasoning[:100],
                        confidence=finding.confidence,
                    )
                )
            except Exception as exc:
                logger.error("Analyst %s failed: %s", role.value, exc)
            # Small delay between calls to avoid rate limiting
            await asyncio.sleep(1.5)
        return state

    # ------------------------------------------------------------------
    # Disagreement resolution
    # ------------------------------------------------------------------

    def _detect_disagreement(
        self, state: ClaimWorkflowState
    ) -> bool:
        """True if analyst findings disagree on verdict."""
        analyst_findings = [
            f for f in state.findings
            if f.agent in PARALLEL_ANALYST_ROLES
        ]
        if len(analyst_findings) < 2:
            return False

        verdicts = {f.verdict for f in analyst_findings}
        # Disagreement: mixed approve/reject, or any flag + approve
        if Verdict.REJECT in verdicts and Verdict.APPROVE in verdicts:
            return True
        if Verdict.FLAG in verdicts and Verdict.APPROVE in verdicts:
            return True
        # Any finding below escalation threshold
        if any(
            f.confidence.requires_escalation for f in analyst_findings
        ):
            return True
        return False

    async def _resolve_disagreement(
        self, state: ClaimWorkflowState
    ) -> ClaimWorkflowState:
        """Handle disagreement: debate rounds then judge ruling."""
        if not self._detect_disagreement(state):
            # Consensus — take majority verdict
            analyst_findings = [
                f for f in state.findings
                if f.agent in PARALLEL_ANALYST_ROLES
            ]
            if analyst_findings:
                # Simple majority
                verdicts = [f.verdict for f in analyst_findings]
                if verdicts.count(Verdict.APPROVE) > len(verdicts) // 2:
                    state._consensus_verdict = Verdict.APPROVE  # type: ignore[attr-defined]
                elif verdicts.count(Verdict.REJECT) > len(verdicts) // 2:
                    state._consensus_verdict = Verdict.REJECT  # type: ignore[attr-defined]
                else:
                    state._consensus_verdict = Verdict.FLAG  # type: ignore[attr-defined]
            return state

        # --- Debate Mode ---
        state.stage = ClaimStage.DEBATE
        claim_data = getattr(state, "_extracted_claim", {})
        analyst_findings = [
            f for f in state.findings if f.agent in PARALLEL_ANALYST_ROLES
        ]

        for round_num in range(1, MAX_DEBATE_ROUNDS + 1):
            debate_round = DebateRound(
                round_number=round_num, claim_id=state.claim_id
            )
            # Each analyst votes
            votes = await asyncio.gather(*[
                self._analysts[role].cast_vote(
                    claim_id=state.claim_id,
                    claim=claim_data,
                    context={"findings": [
                        f.model_dump(mode="json") for f in analyst_findings
                    ]},
                )
                for role in PARALLEL_ANALYST_ROLES
                if role in self._analysts
            ], return_exceptions=True)

            for v in votes:
                if not isinstance(v, Exception):
                    debate_round.votes.append(v)

            debate_round.closed_at = now_utc()
            state.debate_rounds.append(debate_round)

            # Check for super-majority after voting
            choices = [v.choice.value for v in debate_round.votes]
            for choice in ("approve", "reject", "escalate"):
                if choices.count(choice) >= 3:
                    state._consensus_verdict = Verdict(choice) if choice != "escalate" else Verdict.FLAG  # type: ignore[attr-defined]
                    return state

        # --- No consensus after debate -> Judge rules ---
        state.stage = ClaimStage.JUDGMENT
        ruling = await self.judge.rule(
            claim_id=state.claim_id,
            findings=analyst_findings,
            debate_history=[
                dr.model_dump(mode="json") for dr in state.debate_rounds
            ],
            decision_path=state.decision_path,
        )
        state.ruling = ruling
        state.decision_path = state.decision_path.append(
            DecisionStep(
                agent=AgentRole.JUDGE,
                action="issued_ruling",
                summary=ruling.rationale[:100],
                confidence=ruling.confidence,
            )
        )

        # Escalation check
        if ruling.requires_human_review or ruling.confidence.requires_escalation:
            state.stage = ClaimStage.HUMAN_ESCALATION
            state.escalation = HumanEscalation(
                claim_id=state.claim_id,
                reason=EscalationReason.UNRESOLVED_DEBATE
                if not ruling.confidence.requires_escalation
                else EscalationReason.LOW_CONFIDENCE,
                triggered_by=AgentRole.JUDGE,
                confidence_at_escalation=ruling.confidence,
                decision_path=state.decision_path,
            )
            return state

        state._consensus_verdict = ruling.verdict  # type: ignore[attr-defined]
        return state

    async def _run_communication(
        self, state: ClaimWorkflowState
    ) -> ClaimWorkflowState:
        """Draft outbound communications and mark complete."""
        if state.stage in (
            ClaimStage.HUMAN_ESCALATION,
            ClaimStage.REJECTED,
            ClaimStage.FAILED,
        ):
            return state

        state.stage = ClaimStage.COMMUNICATION
        verdict = getattr(state, "_consensus_verdict", Verdict.FLAG)
        claim_data = getattr(state, "_extracted_claim", {})

        reasoning_parts = [
            f.reasoning for f in state.findings
            if f.agent in PARALLEL_ANALYST_ROLES
        ]
        combined_reasoning = " | ".join(reasoning_parts[:4])

        drafts = await self.communication.draft(
            claim_id=state.claim_id,
            decision=verdict.value,
            reasoning=combined_reasoning[:500],
            claim=claim_data,
        )
        state.decision_path = state.decision_path.append(
            DecisionStep(
                agent=AgentRole.COMMUNICATION,
                action="drafted_communications",
                summary=f"Decision: {verdict.value}",
            )
        )

        # Final state
        if verdict == Verdict.REJECT:
            state.stage = ClaimStage.REJECTED
        else:
            state.stage = ClaimStage.COMPLETED

        state.updated_at = now_utc()
        return state


__all__ = ["Supervisor", "MAX_DEBATE_ROUNDS"]
