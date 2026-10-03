"""OCR Agent — structured field extraction from documents.

Takes raw text (from a PDF parser or actual OCR) and uses LLM reasoning to
extract the structured claim fields the rest of the system needs: patient
info, provider, diagnosis, procedure codes, amounts, dates, etc.

Exposes ``extract()`` for the Supervisor to call directly for the full
structured extraction result.
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, AgentRole, Evidence, EvidenceSource, Verdict


_EXTRACTION_SCHEMA = """\
Extract the following fields from the document text. Return strict JSON:
{
  "patient_name": "string or null",
  "patient_dob": "YYYY-MM-DD or null",
  "provider_name": "string or null",
  "provider_npi": "string or null",
  "diagnosis": "string or null",
  "diagnosis_codes": ["ICD-10 codes"],
  "procedure_codes": ["CPT/HCPCS codes"],
  "service_date": "YYYY-MM-DD or null",
  "billed_amount": number or null,
  "currency": "USD" (default),
  "confidence": 0.0-1.0,
  "missing_fields": ["list of fields that could not be extracted"],
  "notes": "any extraction caveats"
}
"""


class OCRAgent(Agent):
    """Structured field extraction from raw document text."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the OCR/Extraction Agent in a medical insurance claim processing system. "
            "You receive raw text extracted from a claim document (PDF) and your job is to "
            "identify and extract all structured data fields needed for claim processing. "
            "Be precise about amounts, dates, and medical codes. If a field cannot be found, "
            "report it as null and include it in missing_fields.\n\n"
            + _EXTRACTION_SCHEMA
        )

    async def extract(self, *, claim_id: str, raw_text: str) -> dict[str, Any]:
        """Rich extraction result for the Supervisor."""
        instructions = (
            f"Extract structured claim fields from the following document text:\n\n"
            f"---BEGIN DOCUMENT---\n{raw_text[:8000]}\n---END DOCUMENT---\n\n"
            f"Apply the extraction schema above. Be thorough."
        )
        result = await self.ask_llm_json(instructions, max_tokens=2000)
        parsed = result.parsed

        await self.memory.remember(
            text=f"Extracted claim {claim_id}: diagnosis={parsed.get('diagnosis')}, amount={parsed.get('billed_amount')}",
            metadata={"claim_id": claim_id, "has_codes": bool(parsed.get("diagnosis_codes"))},
        )

        parsed["_provider"] = result.provider
        parsed["_model"] = result.model
        return parsed

    async def analyze(self, *, claim_id: str, claim: dict[str, Any], context: dict[str, Any] | None = None) -> AgentFinding:
        raw_text = claim.get("raw_text", "")
        if not raw_text:
            return AgentFinding(
                agent=self.role,
                claim_id=claim_id,
                verdict=Verdict.REJECT,
                confidence=self.make_confidence(0.95, "No text provided for extraction"),
                reasoning="Cannot extract fields: no document text was provided.",
                tags=["no_text"],
            )

        extracted = await self.extract(claim_id=claim_id, raw_text=raw_text)
        missing = extracted.get("missing_fields", [])
        conf_value = extracted.get("confidence", 0.7)

        if len(missing) > 3:
            verdict = Verdict.FLAG
        elif missing:
            verdict = Verdict.APPROVE
        else:
            verdict = Verdict.APPROVE

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, f"Extracted with {len(missing)} missing fields"),
            reasoning=f"Extracted {len(extracted) - 2} fields; missing: {missing or 'none'}",
            evidence=[Evidence(source=EvidenceSource.DOCUMENT, field="raw_text", snippet=raw_text[:200])],
            referenced_fields=list(extracted.keys()),
            tags=["extraction_complete"] if not missing else ["partial_extraction"],
        )
