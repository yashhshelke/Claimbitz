"""Validator Agent — structural and consistency checks.

Validates extracted claim fields for completeness, format correctness, and
internal consistency (e.g. service date not in the future, billed amount
positive, ICD/CPT codes syntactically valid). Does NOT assess clinical
plausibility — that's the Medical Expert's domain.
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, Evidence, EvidenceSource, Verdict


class ValidatorAgent(Agent):
    """Structural/consistency validation of extracted claim data."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Validator Agent in a medical insurance claim processing system. "
            "Your job is to check extracted claim data for structural correctness and "
            "internal consistency. You do NOT assess medical plausibility or policy coverage "
            "— those are other agents' domains.\n\n"
            "Check for:\n"
            "- Required fields present (patient_name, diagnosis, service_date, billed_amount)\n"
            "- Date formats valid and logical (service_date not in future)\n"
            "- ICD-10 codes match regex pattern ([A-Z][0-9]{2}(\\.[0-9]{1,4})?)\n"
            "- CPT codes are 5-digit numeric\n"
            "- Billed amount is positive\n"
            "- No obvious internal contradictions\n\n"
            "Respond with strict JSON:\n"
            '{"valid": true/false, "issues": [{"field": "...", "severity": "error"|"warning", '
            '"message": "..."}], "confidence": 0.0-1.0, "summary": "short overall assessment"}'
        )

    async def analyze(self, *, claim_id: str, claim: dict[str, Any], context: dict[str, Any] | None = None) -> AgentFinding:
        instructions = (
            f"Validate the following extracted claim data:\n\n"
            f"{json.dumps(claim, indent=2, default=str)}\n\n"
            f"Check all structural rules. Report any issues found."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        issues = parsed.get("issues", [])
        errors = [i for i in issues if i.get("severity") == "error"]
        warnings = [i for i in issues if i.get("severity") == "warning"]

        if errors:
            verdict = Verdict.REJECT
        elif warnings:
            verdict = Verdict.FLAG
        else:
            verdict = Verdict.APPROVE

        conf_value = parsed.get("confidence", 0.85)
        summary = parsed.get("summary", f"{len(errors)} errors, {len(warnings)} warnings")

        evidence = [
            Evidence(
                source=EvidenceSource.RULE_ENGINE,
                field=issue.get("field", ""),
                snippet=issue.get("message", ""),
                weight=1.0 if issue.get("severity") == "error" else 0.5,
            )
            for issue in issues[:5]
        ]

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, summary),
            reasoning=summary,
            evidence=evidence,
            referenced_fields=[i.get("field", "") for i in issues],
            tags=[f"{len(errors)}_errors", f"{len(warnings)}_warnings"],
        )
