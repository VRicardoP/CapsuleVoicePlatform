"""Tests for authentication endpoints.

Tests negative cases (missing/invalid credentials) which don't need
a real database. Positive login flow requires DB integration tests.
"""



async def test_login_missing_body(unauth_client):
    """POST /api/v1/auth/login without body returns 422."""
    response = await unauth_client.post("/api/v1/auth/login")
    assert response.status_code == 422


async def test_login_missing_password(unauth_client):
    """POST /api/v1/auth/login with email but no password returns 422."""
    response = await unauth_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com"},
    )
    assert response.status_code == 422


async def test_logout_without_token(unauth_client):
    """POST /api/v1/auth/logout without token returns 401."""
    response = await unauth_client.post("/api/v1/auth/logout")
    assert response.status_code == 401


async def test_refresh_without_token(unauth_client):
    """POST /api/v1/auth/refresh without token returns 401 or 422."""
    response = await unauth_client.post("/api/v1/auth/refresh")
    assert response.status_code in (401, 422)


async def test_sessions_without_token(unauth_client):
    """GET /api/v1/auth/sessions without token returns 401."""
    response = await unauth_client.get("/api/v1/auth/sessions")
    assert response.status_code == 401


async def test_validate_without_token(unauth_client):
    """POST /api/v1/auth/validate without token returns 401."""
    response = await unauth_client.post("/api/v1/auth/validate")
    assert response.status_code == 401
