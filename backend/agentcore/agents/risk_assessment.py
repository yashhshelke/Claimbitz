"""Risk Assessment Agent — numeric risk scoring and categorization.

Synthesizes signals from other fields (amount, procedure complexity,
provider history, patient age) into a single numeric risk score plus
a risk category label. Operates on the extracted claim data, not raw text.
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, Evidence, EvidenceSource, Verdict


class RiskAssessmentAgent(Agent):
    """Numeric risk scoring: low/medium/high/critical."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Risk Assessment Agent in a medical insurance "
            "claim processing system. You produce a numeric risk score "
            "and category for each claim based on multiple factors.\n\n"
            "Factors to weigh:\n"
            "- Billed amount relative to service type\n"
            "- Procedure complexity\n"
            "- Provider history signals\n"
            "- Patient demographics\n"
            "- Geographic and temporal patterns\n\n"
            "Respond with strict JSON:\n"
            '{"verdict": "approve"|"reject"|"flag", '
            '"confidence": 0.0-1.0, '
            '"reasoning": "risk assessment summary", '
            '"risk_score": 0.0-1.0, '
            '"risk_label": "low"|"medium"|"high"|"critical", '
            '"risk_factors": [{"factor":"...","weight":0.0-1.0,'
            '"detail":"..."}]}'
        )

    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        objection_note = ""
        if context and context.get("objection"):
            objection_note = (
                "\n\nReconsider after challenge: "
                f"{context['objection'].get('reason', '')}"
            )

        instructions = (
            f"Score the risk for this claim:\n\n"
            f"{json.dumps(claim, indent=2, default=str)}"
            f"{objection_note}\n\n"
            f"Produce risk_score, risk_label, and risk_factors."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        verdict = Verdict(parsed.get("verdict", "flag"))
        conf_value = parsed.get("confidence", 0.7)
        reasoning = parsed.get("reasoning", "No reasoning")
        risk_score = parsed.get("risk_score", 0.5)
        risk_label = parsed.get("risk_label", "medium")
        factors = parsed.get("risk_factors", [])

        await self.memory.remember(
            text=(
                f"Claim {claim_id} risk: "
                f"score={risk_score}, label={risk_label}"
            ),
            metadata={
                "claim_id": claim_id,
                "risk_score": risk_score,
                "risk_label": risk_label,
            },
        )

        evidence = [
            Evidence(
                source=EvidenceSource.RULE_ENGINE,
                field=f.get("factor", ""),
                snippet=f.get("detail", ""),
                weight=f.get("weight", 0.5),
            )
            for f in factors[:5]
        ]

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, reasoning),
            reasoning=reasoning,
            evidence=evidence,
            referenced_fields=["billed_amount", "procedure_codes"],
            tags=[f"risk_{risk_label}", f"score_{risk_score:.2f}"],
        )
