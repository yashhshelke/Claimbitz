"""Medical Expert Agent — clinical plausibility assessment.

Assesses whether the diagnosis, procedures, and billing are clinically
plausible: Does the ICD code match the stated diagnosis? Is the procedure
appropriate for the condition? Are the charges within reasonable bounds for
the service? Can recall similar past cases from its Pinecone memory.
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, AgentRole, Evidence, EvidenceSource, Verdict


class MedicalExpertAgent(Agent):
    """Clinical plausibility: ICD/CPT consistency, treatment appropriateness."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Medical Expert Agent in a medical insurance claim processing system. "
            "You have deep knowledge of ICD-10 diagnosis codes, CPT procedure codes, and "
            "clinical treatment protocols. Your job is to assess whether a claim is "
            "clinically plausible.\n\n"
            "Assess:\n"
            "- Does the ICD-10 code match the stated diagnosis text?\n"
            "- Is the procedure (CPT code) appropriate for this diagnosis?\n"
            "- Is the billed amount reasonable for this type of service?\n"
            "- Are there any clinical red flags (e.g. incompatible codes, impossible combinations)?\n\n"
            "Respond with strict JSON:\n"
            '{"verdict": "approve"|"reject"|"flag", "confidence": 0.0-1.0, '
            '"reasoning": "clinical assessment", '
            '"icd_consistent": true/false, "procedure_appropriate": true/false, '
            '"amount_reasonable": true/false, "red_flags": ["list of concerns"]}'
        )

    async def answer_question(self, *, claim_id: str, question: str, context: dict[str, Any] | None = None) -> str:
        """Answer peer questions about clinical plausibility."""
        instructions = (
            f"A peer agent asks about claim {claim_id}: {question}\n\n"
            f"Context: {json.dumps(context or {}, default=str)}\n\n"
            f"Answer from your clinical expertise. Be specific and cite medical reasoning."
        )
        result = await self.ask_llm_json(instructions)
        return result.parsed.get("answer", result.raw_text)

    async def analyze(self, *, claim_id: str, claim: dict[str, Any], context: dict[str, Any] | None = None) -> AgentFinding:
        # Check memory for similar past cases
        similar = await self.memory.recall(
            query=f"diagnosis: {claim.get('diagnosis', '')} codes: {claim.get('diagnosis_codes', [])}",
            top_k=3,
        )
        memory_context = ""
        if similar:
            memory_context = "\n\nSimilar past cases from memory:\n" + "\n".join(
                f"- {r.text} (score={r.score:.2f})" for r in similar
            )

        objection_note = ""
        if context and context.get("objection"):
            objection_note = f"\n\nYou previously assessed this claim and were challenged: {context['objection'].get('reason', '')}. Reconsider carefully."

        instructions = (
            f"Assess clinical plausibility of this claim:\n\n"
            f"{json.dumps(claim, indent=2, default=str)}"
            f"{memory_context}{objection_note}\n\n"
            f"Apply your medical expertise to determine verdict."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        verdict = Verdict(parsed.get("verdict", "flag"))
        conf_value = parsed.get("confidence", 0.7)
        reasoning = parsed.get("reasoning", "No reasoning provided")
        red_flags = parsed.get("red_flags", [])

        # Remember this assessment
        await self.memory.remember(
            text=f"Claim {claim_id}: {verdict.value} - {reasoning}",
            metadata={"claim_id": claim_id, "verdict": verdict.value, "red_flags": len(red_flags)},
        )

        evidence = []
        if not parsed.get("icd_consistent", True):
            evidence.append(Evidence(source=EvidenceSource.RULE_ENGINE, field="diagnosis_codes", snippet="ICD code inconsistent with diagnosis text"))
        if not parsed.get("procedure_appropriate", True):
            evidence.append(Evidence(source=EvidenceSource.RULE_ENGINE, field="procedure_codes", snippet="Procedure not appropriate for diagnosis"))
        if not parsed.get("amount_reasonable", True):
            evidence.append(Evidence(source=EvidenceSource.RULE_ENGINE, field="billed_amount", snippet="Amount outside reasonable range"))
        if similar:
            evidence.append(Evidence(source=EvidenceSource.VECTOR_MEMORY, snippet=f"Found {len(similar)} similar past cases", weight=0.5))

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, reasoning),
            reasoning=reasoning,
            evidence=evidence,
            referenced_fields=["diagnosis", "diagnosis_codes", "procedure_codes", "billed_amount"],
            tags=red_flags[:5],
        )
