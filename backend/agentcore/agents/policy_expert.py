"""Policy Expert Agent — coverage rules and policy compliance.

Determines whether a claim is covered under the patient's policy: checks
pre-authorization requirements, coverage exclusions, benefit limits, network
status, and waiting periods. Can answer peer questions about specific
policy rules.
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, Evidence, EvidenceSource, Verdict


class PolicyExpertAgent(Agent):
    """Policy coverage assessment: exclusions, limits, pre-auth, network."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Policy Expert Agent in a medical insurance claim processing system. "
            "You have deep knowledge of insurance policy rules, coverage terms, exclusions, "
            "and regulatory requirements. Your job is to determine whether a claim is covered "
            "under typical insurance policy terms.\n\n"
            "Assess:\n"
            "- Is the procedure/diagnosis typically covered?\n"
            "- Would pre-authorization be required?\n"
            "- Are there common exclusions that apply?\n"
            "- Is the provider likely in-network?\n"
            "- Are there benefit limits that might be exceeded?\n"
            "- Any waiting period concerns?\n\n"
            "Respond with strict JSON:\n"
            '{"verdict": "approve"|"reject"|"flag", "confidence": 0.0-1.0, '
            '"reasoning": "policy assessment", "covered": true/false, '
            '"pre_auth_required": true/false, "exclusions_apply": false/true, '
            '"in_network": true/false/null, "policy_concerns": ["list"]}'
        )

    async def answer_question(self, *, claim_id: str, question: str, context: dict[str, Any] | None = None) -> str:
        """Answer peer questions about policy coverage rules."""
        instructions = (
            f"A peer agent asks about policy rules for claim {claim_id}: {question}\n\n"
            f"Context: {json.dumps(context or {}, default=str)}\n\n"
            f"Answer from your policy expertise. Cite relevant policy sections or rules."
        )
        result = await self.ask_llm_json(instructions)
        return result.parsed.get("answer", result.raw_text)

    async def analyze(self, *, claim_id: str, claim: dict[str, Any], context: dict[str, Any] | None = None) -> AgentFinding:
        similar = await self.memory.recall(
            query=f"policy coverage: {claim.get('diagnosis', '')} procedure: {claim.get('procedure_codes', [])}",
            top_k=3,
        )
        memory_context = ""
        if similar:
            memory_context = "\n\nRelevant policy precedents from memory:\n" + "\n".join(
                f"- {r.text} (score={r.score:.2f})" for r in similar
            )

        objection_note = ""
        if context and context.get("objection"):
            objection_note = f"\n\nReconsider after challenge: {context['objection'].get('reason', '')}"

        instructions = (
            f"Assess policy coverage for this claim:\n\n"
            f"{json.dumps(claim, indent=2, default=str)}"
            f"{memory_context}{objection_note}\n\n"
            f"Determine coverage status and any policy concerns."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        verdict = Verdict(parsed.get("verdict", "flag"))
        conf_value = parsed.get("confidence", 0.7)
        reasoning = parsed.get("reasoning", "No reasoning provided")
        concerns = parsed.get("policy_concerns", [])

        await self.memory.remember(
            text=f"Claim {claim_id} policy: {verdict.value} - {reasoning}",
            metadata={"claim_id": claim_id, "verdict": verdict.value, "covered": parsed.get("covered")},
        )

        evidence = []
        if parsed.get("exclusions_apply"):
            evidence.append(Evidence(source=EvidenceSource.POLICY_DB, field="exclusions", snippet="Policy exclusion applies"))
        if parsed.get("pre_auth_required"):
            evidence.append(Evidence(source=EvidenceSource.POLICY_DB, field="pre_authorization", snippet="Pre-authorization required"))
        if parsed.get("in_network") is False:
            evidence.append(Evidence(source=EvidenceSource.POLICY_DB, field="provider_network", snippet="Provider out-of-network"))

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, reasoning),
            reasoning=reasoning,
            evidence=evidence,
            referenced_fields=["diagnosis", "procedure_codes", "provider_name", "billed_amount"],
            tags=concerns[:5],
        )
