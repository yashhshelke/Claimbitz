"""Scanner Agent — document intake and triage.

First agent in the pipeline. Receives a raw document (PDF bytes or
pre-extracted text), determines document type, quality, and whether it's
processable. Produces a finding with verdict APPROVE (proceed to OCR) or
REJECT (unprocessable document).

Also exposes ``scan()`` for the Supervisor to call directly for the richer
scan-result payload (file metadata, page count, quality assessment).
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, AgentRole, Evidence, EvidenceSource, Verdict


class ScannerAgent(Agent):
    """Document intake: validates file format, estimates quality, triages."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Scanner Agent in a medical insurance claim processing system. "
            "Your sole job is document intake triage. Given metadata about a submitted "
            "document (filename, page count, file size, any OCR-ability indicators), "
            "determine whether it is a valid, processable medical claim document.\n\n"
            "Respond with strict JSON:\n"
            '{"processable": true/false, "document_type": "claim_form"|"invoice"|"prescription"|"unknown", '
            '"quality": "high"|"medium"|"low", "confidence": 0.0-1.0, '
            '"reason": "short explanation"}'
        )

    async def scan(self, *, claim_id: str, file_meta: dict[str, Any]) -> dict[str, Any]:
        """Rich scan result for the Supervisor (beyond the generic Finding)."""
        instructions = (
            f"Assess the following document metadata for processability:\n"
            f"{json.dumps(file_meta, indent=2)}\n\n"
            f"Determine document_type, quality, and whether it can proceed to OCR extraction."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        # Remember this scan for future pattern matching
        await self.memory.remember(
            text=f"Scanned document {file_meta.get('filename', 'unknown')}: {parsed.get('reason', '')}",
            metadata={"claim_id": claim_id, "document_type": parsed.get("document_type", "unknown")},
        )

        return {
            "processable": parsed.get("processable", False),
            "document_type": parsed.get("document_type", "unknown"),
            "quality": parsed.get("quality", "low"),
            "confidence": parsed.get("confidence", 0.5),
            "reason": parsed.get("reason", ""),
            "provider": result.provider,
            "model": result.model,
        }

    async def analyze(self, *, claim_id: str, claim: dict[str, Any], context: dict[str, Any] | None = None) -> AgentFinding:
        file_meta = claim.get("file_meta", claim)
        scan_result = await self.scan(claim_id=claim_id, file_meta=file_meta)

        verdict = Verdict.APPROVE if scan_result["processable"] else Verdict.REJECT
        confidence = self.make_confidence(scan_result["confidence"], scan_result["reason"])

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=confidence,
            reasoning=scan_result["reason"],
            evidence=[Evidence(source=EvidenceSource.DOCUMENT, field="file_meta", snippet=str(file_meta.get("filename", "")))],
            referenced_fields=["filename", "page_count", "file_size"],
            tags=[scan_result["document_type"], scan_result["quality"]],
        )
