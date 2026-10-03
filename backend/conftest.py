"""Shared test fixtures for the ClaimBlitz backend."""

import pytest
from fastapi.testclient import TestClient

from agentcore.api.app import create_app


@pytest.fixture
def test_client():
    """Provides a TestClient against the new multi-agent API."""
    app = create_app()
    return TestClient(app)
