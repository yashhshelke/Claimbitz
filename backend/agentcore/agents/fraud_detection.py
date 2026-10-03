"""Fraud Detection Agent — duplicate/pattern-based fraud analysis.

Looks for fraud indicators: duplicate submissions, upcoding, unbundling,
impossible day surgery combinations, phantom billing, identity mismatches.
Relies heavily on vector memory recall to find similar past fraud patterns.
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, Evidence, EvidenceSource, Verdict


class FraudDetectionAgent(Agent):
    """Fraud analysis: duplicates, upcoding, patterns, anomalies."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Fraud Detection Agent in a medical insurance claim processing system. "
            "You are naturally suspicious and look for fraud indicators. Your job is to identify "
            "potential fraud, waste, or abuse in medical claims.\n\n"
            "Look for:\n"
            "- Duplicate or near-duplicate submissions\n"
            "- Upcoding (billing for more expensive service than provided)\n"
            "- Unbundling (splitting bundled procedures to bill separately)\n"
            "- Impossible combinations (multiple full-day procedures same day)\n"
            "- Unusually high amounts for the service type\n"
            "- Pattern matches with known fraud schemes\n"
            "- Identity or provider inconsistencies\n\n"
            "Respond with strict JSON:\n"
            '{"verdict": "approve"|"reject"|"flag", "confidence": 0.0-1.0, '
            '"reasoning": "fraud assessment", "fraud_score": 0.0-1.0, '
            '"indicators": [{"type": "...", "severity": "high"|"medium"|"low", "detail": "..."}], '
            '"similar_fraud_patterns": []}'
        )

    async def analyze(self, *, claim_id: str, claim: dict[str, Any], context: dict[str, Any] | None = None) -> AgentFinding:
        # Search memory for similar patterns (key fraud detection capability)
        search_text = (
            f"fraud pattern: provider={claim.get('provider_name', '')} "
            f"amount={claim.get('billed_amount', '')} "
            f"procedure={claim.get('procedure_codes', [])} "
            f"diagnosis={claim.get('diagnosis', '')}"
        )
        similar = await self.memory.recall(query=search_text, top_k=5)
        memory_context = ""
        if similar:
            memory_context = "\n\nSimilar past cases from fraud memory:\n" + "\n".join(
                f"- {r.text} (similarity={r.score:.2f})" for r in similar
            )

        objection_note = ""
        if context and context.get("objection"):
            objection_note = f"\n\nReconsider after challenge: {context['objection'].get('reason', '')}"

        instructions = (
            f"Analyze this claim for fraud indicators:\n\n"
            f"{json.dumps(claim, indent=2, default=str)}"
            f"{memory_context}{objection_note}\n\n"
            f"Apply fraud detection expertise. Be thorough but fair."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        verdict = Verdict(parsed.get("verdict", "flag"))
        conf_value = parsed.get("confidence", 0.7)
        reasoning = parsed.get("reasoning", "No reasoning provided")
        indicators = parsed.get("indicators", [])
        fraud_score = parsed.get("fraud_score", 0.0)

        # Remember this analysis for future pattern matching
        await self.memory.remember(
            text=f"Claim {claim_id} fraud analysis: score={fraud_score}, verdict={verdict.value}, indicators={[i.get('type') for i in indicators]}",
            metadata={"claim_id": claim_id, "fraud_score": fraud_score, "verdict": verdict.value},
        )

        evidence = [
            Evidence(
                source=EvidenceSource.RULE_ENGINE,
                field=indicator.get("type", "unknown"),
                snippet=indicator.get("detail", ""),
                weight=1.0 if indicator.get("severity") == "high" else 0.6,
            )
            for indicator in indicators[:5]
        ]
        if similar:
            evidence.append(Evidence(
                source=EvidenceSource.VECTOR_MEMORY,
                snippet=f"Matched {len(similar)} similar historical patterns",
                weight=0.7,
            ))

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, reasoning),
            reasoning=reasoning,
            evidence=evidence,
            referenced_fields=["provider_name", "billed_amount", "procedure_codes", "service_date"],
            tags=[i.get("type", "") for i in indicators[:5]] + ([f"fraud_score_{fraud_score:.1f}"] if fraud_score > 0.3 else []),
        )
