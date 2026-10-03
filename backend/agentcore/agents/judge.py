"""Judge Agent — consensus ruling over analyst findings.

The Judge is invoked when the four parallel analysts disagree on verdict,
or when debate rounds fail to reach consensus. It receives all findings,
any debate history, and produces a binding ``JudgeRuling`` that becomes
the final decision (subject to human escalation if confidence is low).
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import (
    AgentFinding,
    AgentRole,
    DecisionPath,
    Evidence,
    EvidenceSource,
    JudgeRuling,
    Verdict,
)


class JudgeAgent(Agent):
    """Consensus agent: weighs analyst findings and issues a ruling."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Judge Agent in a medical insurance claim "
            "processing system. You are the final arbiter when "
            "specialist agents disagree. You must weigh all findings, "
            "consider each agent's confidence and evidence, and "
            "produce a fair, well-reasoned ruling.\n\n"
            "Principles:\n"
            "- Higher-confidence findings carry more weight\n"
            "- Fraud signals are serious — even one credible flag "
            "should prevent approval\n"
            "- Medical plausibility outweighs policy technicalities\n"
            "- When in doubt, flag for human review rather than "
            "reject outright\n\n"
            "Respond with strict JSON:\n"
            '{"verdict": "approve"|"reject"|"flag", '
            '"confidence": 0.0-1.0, '
            '"reasoning": "detailed ruling rationale", '
            '"dissenting_agents": ["role names that disagreed"], '
            '"requires_human_review": true/false}'
        )

    async def rule(
        self,
        *,
        claim_id: str,
        findings: list[AgentFinding],
        debate_history: list[dict[str, Any]] | None = None,
        decision_path: DecisionPath | None = None,
    ) -> JudgeRuling:
        """Produce a binding ruling from analyst findings + debate."""
        findings_summary = [
            {
                "agent": f.agent.value,
                "verdict": f.verdict.value,
                "confidence": f.confidence.value,
                "reasoning": f.reasoning[:200],
                "tags": f.tags[:5],
            }
            for f in findings
        ]

        instructions = (
            f"Issue a ruling for claim {claim_id}.\n\n"
            f"Analyst findings:\n"
            f"{json.dumps(findings_summary, indent=2)}\n\n"
        )
        if debate_history:
            instructions += (
                f"Debate history:\n"
                f"{json.dumps(debate_history, indent=2, default=str)}\n\n"
            )
        instructions += "Weigh all evidence and issue your ruling."

        result = await self.ask_llm_json(instructions, max_tokens=1500)
        parsed = result.parsed

        verdict = Verdict(parsed.get("verdict", "flag"))
        conf_value = parsed.get("confidence", 0.6)
        reasoning = parsed.get("reasoning", "No rationale")
        dissenting = parsed.get("dissenting_agents", [])
        human_review = parsed.get("requires_human_review", False)

        # Recall relevant precedents
        similar = await self.memory.recall(
            query=f"ruling: {verdict.value} {reasoning[:100]}",
            top_k=3,
        )

        await self.memory.remember(
            text=(
                f"Ruling claim {claim_id}: {verdict.value} "
                f"(conf={conf_value:.2f}) - {reasoning[:150]}"
            ),
            metadata={
                "claim_id": claim_id,
                "verdict": verdict.value,
                "confidence": conf_value,
            },
        )

        dp = decision_path or DecisionPath(claim_id=claim_id)

        dissenting_roles = []
        for name in dissenting:
            try:
                dissenting_roles.append(AgentRole(name))
            except ValueError:
                pass

        return JudgeRuling(
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, reasoning),
            dissenting_agents=dissenting_roles,
            rationale=reasoning,
            decision_path=dp,
            requires_human_review=human_review or conf_value < 0.8,
        )

    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        """Standard analyze() — wraps rule() for bus compatibility."""
        findings_data = (context or {}).get("findings", [])
        findings = [
            AgentFinding.model_validate(f) for f in findings_data
        ] if findings_data else []

        if not findings:
            return AgentFinding(
                agent=self.role,
                claim_id=claim_id,
                verdict=Verdict.ABSTAIN,
                confidence=self.make_confidence(
                    0.3, "No findings to judge"
                ),
                reasoning="No analyst findings provided.",
                tags=["no_input"],
            )

        ruling = await self.rule(
            claim_id=claim_id,
            findings=findings,
            debate_history=(context or {}).get("debate_history"),
        )

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=ruling.verdict,
            confidence=ruling.confidence,
            reasoning=ruling.rationale,
            evidence=[
                Evidence(
                    source=EvidenceSource.PEER_AGENT,
                    snippet=(
                        f"Ruling over {len(findings)} findings, "
                        f"dissent: {[r.value for r in ruling.dissenting_agents]}"
                    ),
                )
            ],
            tags=["judge_ruling"],
        )
