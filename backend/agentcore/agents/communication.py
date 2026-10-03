"""Communication Agent — drafts outbound messages.

Once a claim decision is reached, this agent drafts policyholder-facing
communications (approval letter, rejection explanation, request-for-info)
as well as internal notes. Exposes ``draft()`` for the Supervisor.
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, Evidence, EvidenceSource, Verdict


class CommunicationAgent(Agent):
    """Draft outbound messages: approval, rejection, or info-request."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Communication Agent in a medical insurance "
            "claim processing system. You draft clear, empathetic, "
            "professional communications to policyholders about their "
            "claims.\n\n"
            "You can draft:\n"
            "- Approval letters\n"
            "- Rejection explanations (with specific reasons)\n"
            "- Requests for additional information\n"
            "- Internal processing notes\n\n"
            "Respond with strict JSON:\n"
            '{"email_draft": "...", "sms_draft": "...", '
            '"internal_note": "...", "tone": "...", '
            '"confidence": 0.0-1.0}'
        )

    async def draft(
        self,
        *,
        claim_id: str,
        decision: str,
        reasoning: str,
        claim: dict[str, Any],
    ) -> dict[str, str]:
        """Generate outbound communication drafts."""
        instructions = (
            f"Draft communications for claim {claim_id}.\n"
            f"Decision: {decision}\n"
            f"Reasoning: {reasoning}\n"
            f"Claim details: {json.dumps(claim, default=str)}\n\n"
            f"Create an email draft, SMS draft, and internal note."
        )
        result = await self.ask_llm_json(instructions, max_tokens=2000)
        return result.parsed

    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        decision = claim.get("decision", "pending")
        reasoning = claim.get("reasoning", "")
        drafts = await self.draft(
            claim_id=claim_id,
            decision=decision,
            reasoning=reasoning,
            claim=claim,
        )

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=Verdict.APPROVE,
            confidence=self.make_confidence(
                drafts.get("confidence", 0.85),
                "Communication drafts generated",
            ),
            reasoning="Drafts generated for policyholder communication",
            evidence=[
                Evidence(
                    source=EvidenceSource.PEER_AGENT,
                    snippet=f"Decision: {decision}",
                )
            ],
            tags=["drafts_ready"],
        )
