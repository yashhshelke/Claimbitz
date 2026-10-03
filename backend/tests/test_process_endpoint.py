"""Tests for the new multi-agent ClaimBlitz API."""

import pytest
from fastapi.testclient import TestClient

from agentcore.api.app import create_app

app = create_app()
client = TestClient(app)


class TestHealthEndpoint:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_agents(self):
        r = client.get("/health/agents")
        assert r.status_code == 200
        assert len(r.json()["agents"]) == 10


class TestClaimsAPI:
    def test_submit_claim(self):
        r = client.post("/v2/claims", json={
            "raw_text": "Patient: Test\nDiagnosis: Flu",
            "source_filename": "test.pdf",
        })
        assert r.status_code == 202
        assert "claim_id" in r.json()

    def test_get_unknown_claim(self):
        r = client.get("/v2/claims/nonexistent")
        assert r.status_code == 404

    def test_escalations_empty(self):
        r = client.get("/v2/escalations")
        assert r.status_code == 200
        assert r.json() == []
