"""Tests for call management endpoints."""

from uuid import uuid4


async def test_list_calls_requires_auth(unauth_client):
    """GET /api/v1/calls without token returns 401."""
    response = await unauth_client.get("/api/v1/calls")
    assert response.status_code == 401


async def test_call_detail_requires_auth(unauth_client):
    """GET /api/v1/calls/{id} without token returns 401."""
    fake_id = str(uuid4())
    response = await unauth_client.get(f"/api/v1/calls/{fake_id}")
    assert response.status_code == 401


async def test_active_calls_requires_auth(unauth_client):
    """GET /api/v1/calls/active without token returns 401."""
    response = await unauth_client.get("/api/v1/calls/active")
    assert response.status_code == 401


async def test_create_call_requires_auth(unauth_client):
    """POST /api/v1/calls without token returns 401."""
    response = await unauth_client.post(
        "/api/v1/calls",
        json={"direction": "inbound", "call_type": "ai_agent"},
    )
    assert response.status_code == 401


async def test_requiring_review_requires_auth(unauth_client):
    """GET /api/v1/calls/requiring-review without token returns 401."""
    response = await unauth_client.get("/api/v1/calls/requiring-review")
    assert response.status_code == 401


async def test_transcript_requires_auth(unauth_client):
    """GET /api/v1/calls/{id}/transcript without token returns 401."""
    fake_id = str(uuid4())
    response = await unauth_client.get(f"/api/v1/calls/{fake_id}/transcript")
    assert response.status_code == 401
