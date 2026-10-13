"""Tests for GDPR rights endpoints."""



async def test_export_requires_auth(unauth_client):
    """GET /api/v1/gdpr/export without token returns 401."""
    response = await unauth_client.get("/api/v1/gdpr/export")
    assert response.status_code == 401


async def test_requests_requires_auth(unauth_client):
    """GET /api/v1/gdpr/requests without token returns 401."""
    response = await unauth_client.get("/api/v1/gdpr/requests")
    assert response.status_code == 401


async def test_create_request_requires_auth(unauth_client):
    """POST /api/v1/gdpr/requests without token returns 401."""
    response = await unauth_client.post(
        "/api/v1/gdpr/requests",
        json={
            "request_type": "access",
            "requester_type": "user",
            "request_details": "Test request",
        },
    )
    assert response.status_code == 401


async def test_rectify_requires_auth(unauth_client):
    """POST /api/v1/gdpr/rectify without token returns 401."""
    response = await unauth_client.post(
        "/api/v1/gdpr/rectify",
        json={"field": "name", "new_value": "Test"},
    )
    assert response.status_code == 401


async def test_erase_requires_auth(unauth_client):
    """POST /api/v1/gdpr/erase without token returns 401."""
    response = await unauth_client.post(
        "/api/v1/gdpr/erase",
        json={"reason": "Test erasure"},
    )
    assert response.status_code == 401


async def test_restrict_requires_auth(unauth_client):
    """POST /api/v1/gdpr/restrict without token returns 401."""
    response = await unauth_client.post(
        "/api/v1/gdpr/restrict",
        json={"reason": "Test restriction"},
    )
    assert response.status_code == 401
