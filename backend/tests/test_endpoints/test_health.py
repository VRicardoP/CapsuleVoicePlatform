"""Tests for health check endpoints (no auth required)."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def health_client():
    """Client for health endpoints — no dependency overrides needed."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_root_returns_api_info(health_client):
    """GET / returns API name, version, and status."""
    response = await health_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["status"] == "operational"


async def test_health_check(health_client):
    """GET /health returns healthy status."""
    response = await health_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
