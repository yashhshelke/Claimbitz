"""FastAPI API layer for the agentcore multi-agent system.

This is the NEW API that exposes the multi-agent pipeline to external
callers (and eventually the frontend). It replaces the legacy
``backend/main.py`` endpoints, but the old app is left on disk.

Routes:
- POST /v2/claims           — submit a new claim for processing
- GET  /v2/claims/{id}      — get claim status + extracted data
- GET  /v2/claims/{id}/workflow — full workflow state (findings, debate, ruling)
- POST /v2/claims/{id}/pause   — pause processing
- POST /v2/claims/{id}/resume  — resume processing
- POST /v2/claims/{id}/retry   — retry a failed claim
- GET  /v2/escalations      — list pending human escalations
- POST /v2/escalations/{id}/resolve — resolve an escalation
- GET  /v2/health           — health check
- GET  /v2/health/agents    — agent system status
"""
