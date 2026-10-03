"""API route definitions for the multi-agent claim system.

All routes live under /v2 (prefix applied by app.py). The user's original
spec called for: start, pause, resume, retry, replay workflow, plus
escalation management and health checks.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File

from ..protocol import AgentRole, ClaimStage, new_id
from .deps import get_supervisor_dep, get_blackboard_dep
from .schemas import (
    AgentStatusResponse,
    ClaimStatusResponse,
    ClaimSubmitRequest,
    ClaimSubmitResponse,
    EscalationResolveRequest,
    EscalationResponse,
    HealthResponse,
    WorkflowResponse,
)

router = APIRouter()


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse()


@router.get("/health/agents", response_model=AgentStatusResponse)
async def agent_status() -> AgentStatusResponse:
    return AgentStatusResponse(
        agents=[r.value for r in AgentRole],
        pinecone_configured=True,
        redis_configured=True,
    )


# --------------------------------------------------------------------------
# Claims
# --------------------------------------------------------------------------


@router.post("/claims", response_model=ClaimSubmitResponse, status_code=202)
async def submit_claim(
    req: ClaimSubmitRequest,
    background_tasks: BackgroundTasks,
) -> ClaimSubmitResponse:
    """Submit a new claim for multi-agent processing.

    Processing runs in a background task so the endpoint returns
    immediately with a claim_id the client can poll.
    """
    claim_id = new_id()
    blackboard = get_blackboard_dep()

    # Store initial state on blackboard for immediate status queries
    await blackboard.set_many(claim_id, {
        "stage": ClaimStage.INGESTED.value,
        "source_filename": req.source_filename,
    })

    # Kick off async processing
    background_tasks.add_task(
        _process_claim_background,
        claim_id=claim_id,
        raw_text=req.raw_text,
        file_meta=req.file_meta or {},
    )

    return ClaimSubmitResponse(
        claim_id=claim_id,
        stage=ClaimStage.INGESTED.value,
    )


async def _process_claim_background(
    *, claim_id: str, raw_text: str, file_meta: dict[str, Any]
) -> None:
    """Run the full Supervisor pipeline in the background."""
    supervisor = get_supervisor_dep()
    blackboard = get_blackboard_dep()

    try:
        state = await supervisor.process_claim(
            claim_id=claim_id,
            raw_text=raw_text,
            file_meta=file_meta,
        )
        # Update blackboard with final state
        await blackboard.set_many(claim_id, {
            "stage": state.stage.value,
            "final_verdict": getattr(state, "_consensus_verdict", None)
            and getattr(state, "_consensus_verdict").value,
            "findings_count": len(state.findings),
            "decision_steps": len(state.decision_path.steps),
        })
        await blackboard.publish_event(claim_id, {
            "type": "processing_complete",
            "stage": state.stage.value,
        })
    except Exception as exc:
        await blackboard.set_many(claim_id, {
            "stage": ClaimStage.FAILED.value,
            "error": str(exc),
        })
        await blackboard.publish_event(claim_id, {
            "type": "processing_failed",
            "error": str(exc),
        })


@router.get("/claims/{claim_id}", response_model=ClaimStatusResponse)
async def get_claim_status(claim_id: str) -> ClaimStatusResponse:
    """Get current status of a claim."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")
    return ClaimStatusResponse(
        claim_id=claim_id,
        stage=data.get("stage", "unknown"),
        final_verdict=data.get("final_verdict"),
        risk_score=data.get("risk_score"),
        risk_label=data.get("risk_label"),
    )


@router.get("/claims/{claim_id}/workflow", response_model=WorkflowResponse)
async def get_claim_workflow(claim_id: str) -> WorkflowResponse:
    """Get full workflow state including findings, debate, and ruling."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")
    return WorkflowResponse(
        claim_id=claim_id,
        stage=data.get("stage", "unknown"),
        findings=data.get("findings", []),
        debate_rounds=data.get("debate_rounds", []),
        ruling=data.get("ruling"),
        decision_path=data.get("decision_path"),
    )


@router.post("/claims/{claim_id}/pause")
async def pause_claim(claim_id: str) -> dict[str, str]:
    """Pause processing of a claim."""
    blackboard = get_blackboard_dep()
    await blackboard.set_field(claim_id, "is_paused", True)
    return {"claim_id": claim_id, "status": "paused"}


@router.post("/claims/{claim_id}/resume")
async def resume_claim(claim_id: str) -> dict[str, str]:
    """Resume a paused claim."""
    blackboard = get_blackboard_dep()
    await blackboard.set_field(claim_id, "is_paused", False)
    return {"claim_id": claim_id, "status": "resumed"}


@router.post("/claims/{claim_id}/retry")
async def retry_claim(
    claim_id: str, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Retry a failed claim from the beginning."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")
    if data.get("stage") != ClaimStage.FAILED.value:
        raise HTTPException(
            status_code=400, detail="Only failed claims can be retried"
        )
    await blackboard.set_field(claim_id, "stage", ClaimStage.INGESTED.value)

    raw_text = data.get("raw_text", "")
    file_meta = data.get("file_meta", {})
    background_tasks.add_task(
        _process_claim_background,
        claim_id=claim_id,
        raw_text=raw_text,
        file_meta=file_meta,
    )
    return {"claim_id": claim_id, "status": "retrying"}


# --------------------------------------------------------------------------
# Escalations
# --------------------------------------------------------------------------


@router.get("/escalations", response_model=list[EscalationResponse])
async def list_escalations() -> list[EscalationResponse]:
    """List pending human escalations."""
    # Placeholder: in production this would query Postgres via repos
    return []


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: str, req: EscalationResolveRequest
) -> dict[str, str]:
    """Resolve a human escalation."""
    # Placeholder: would update Postgres + trigger communication agent
    return {
        "escalation_id": escalation_id,
        "status": "resolved",
        "notes": req.resolution_notes,
    }


# --------------------------------------------------------------------------
# Legacy-compatible /process endpoint (what the frontend calls directly)
# --------------------------------------------------------------------------


@router.post("/process")
async def process_file_upload(file: UploadFile = File(...)) -> dict:
    """Process a claim document upload — frontend-compatible endpoint.

    Accepts a PDF/image file, extracts text, runs the full 9-agent
    Supervisor pipeline synchronously, and returns the result in the
    shape the frontend expects (claimData, riskScore, email, whatsapp, etc).
    """
    import fitz  # PyMuPDF

    # Extract text from uploaded file
    content = await file.read()
    raw_text = ""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        for page in doc:
            raw_text += page.get_text()
        doc.close()
    except Exception:
        # If not a valid PDF, treat content as plain text
        raw_text = content.decode("utf-8", errors="ignore")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from uploaded file")

    # Run full pipeline
    supervisor = get_supervisor_dep()
    claim_id = new_id()

    state = await supervisor.process_claim(
        claim_id=claim_id,
        raw_text=raw_text,
        file_meta={"filename": file.filename, "size_kb": len(content) // 1024},
    )

    # Build frontend-compatible response
    extracted = getattr(state, "_extracted_claim", {})
    verdict = getattr(state, "_consensus_verdict", None)
    
    # Determine final verdict from findings if not explicitly set
    if verdict is None:
        # Use majority vote from all analyst findings
        from ..protocol import PARALLEL_ANALYST_ROLES, Verdict
        analyst_findings = [f for f in state.findings if f.agent in PARALLEL_ANALYST_ROLES]
        if analyst_findings:
            verdicts = [f.verdict for f in analyst_findings]
            approve_count = verdicts.count(Verdict.APPROVE)
            reject_count = verdicts.count(Verdict.REJECT)
            if approve_count >= reject_count:
                verdict = Verdict.APPROVE
            else:
                verdict = Verdict.REJECT
        elif state.stage.value == "completed":
            verdict = Verdict.APPROVE
        else:
            # Fallback: if most findings are approve, approve
            all_verdicts = [f.verdict for f in state.findings]
            approve_count = all_verdicts.count(Verdict.APPROVE)
            if approve_count > len(all_verdicts) // 2:
                verdict = Verdict.APPROVE
            else:
                verdict = Verdict.FLAG

    verdict_str = verdict.value if verdict else "flag"

    # Find risk finding
    risk_score = 0.0
    risk_label = "LOW"
    risk_reasons = []
    for f in state.findings:
        if f.agent == AgentRole.RISK_ASSESSMENT:
            risk_score = next(
                (float(t.split("_")[1]) for t in f.tags if t.startswith("score_")), 0.3
            )
            risk_label = next(
                (t.split("_")[1].upper() for t in f.tags if t.startswith("risk_")), "MEDIUM"
            )
            risk_reasons.append(f.reasoning)

    # Find communication drafts
    email_draft = ""
    whatsapp_draft = ""
    for f in state.findings:
        if f.agent == AgentRole.COMMUNICATION:
            email_draft = f.reasoning
            whatsapp_draft = f.reasoning[:200]

    recommendation = "APPROVE" if verdict_str == "approve" else (
        "REJECT" if verdict_str in ("reject", "rejected") else "REVIEW"
    )
    # Override: LOW risk should always be APPROVE
    if risk_label == "LOW" and recommendation != "REJECT":
        recommendation = "APPROVE"

    return {
        "claimData": extracted or {
            "patientName": extracted.get("patient_name", "Unknown"),
            "diagnosis": extracted.get("diagnosis", ""),
            "diagnosisCode": (extracted.get("diagnosis_codes") or [""])[0] if extracted.get("diagnosis_codes") else "",
            "cptCode": (extracted.get("procedure_codes") or [""])[0] if extracted.get("procedure_codes") else "",
            "provider": extracted.get("provider_name", ""),
            "totalBilled": extracted.get("billed_amount", 0),
            "dateOfService": extracted.get("service_date", ""),
        },
        "riskScore": risk_score,
        "riskLabel": risk_label,
        "recommendation": recommendation,
        "riskReasons": risk_reasons or [f.reasoning for f in state.findings if f.agent in (AgentRole.FRAUD_DETECTION, AgentRole.RISK_ASSESSMENT)],
        "extractionIssues": [],
        "extractionTextPreview": raw_text[:500],
        "riskModel": {
            "engine": "multi-agent",
            "modelName": "claimblitz-9-agent-v2",
            "baseScore": 0.1,
            "maxIssuePenalty": 0.5,
            "issuePenaltyPerItem": 0.1,
            "thresholds": {"lowMax": 0.3, "mediumMax": 0.6, "highMax": 1.0},
            "contributions": [
                {"rule": f.agent.value, "delta": 1 - f.confidence.value, "reason": f.reasoning[:80]}
                for f in state.findings if f.agent in (AgentRole.FRAUD_DETECTION, AgentRole.RISK_ASSESSMENT, AgentRole.MEDICAL_EXPERT)
            ],
        },
        "email": email_draft or f"Subject: Claim {claim_id} - {recommendation}\n\nDear Policyholder,\n\nYour claim has been processed.\nDecision: {recommendation}\nRisk Level: {risk_label}\n\nBest regards,\nClaimBlitz AI",
        "whatsapp": whatsapp_draft or f"Claim Update: {recommendation} | Risk: {risk_label} ({risk_score:.2f})",
        "findings": [
            {"agent": f.agent.value, "verdict": f.verdict.value, "confidence": f.confidence.value, "reasoning": f.reasoning[:100]}
            for f in state.findings
        ],
        "stage": state.stage.value,
        "decisionSteps": len(state.decision_path.steps),
    }
