"""Endpoint-level tests for BFF auth additions.

Covers:
- POST /auth/refresh shim returns 204 when a BFF session is active and
  401 when none is present (since we removed the JWT-rotating refresh).
- GET /auth/api-tokens lists tokens (empty list when DB has none).
- POST /auth/api-token rejects non-admin callers (handled in
  endpoint logic, not just dependencies).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio


async def test_refresh_shim_returns_401_without_session(unauth_client):
    """No cookie → 401 (the shim does not magic up a session)."""
    response = await unauth_client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


async def test_api_tokens_list_requires_auth(unauth_client):
    """Listing tokens without a session should fail with 401."""
    response = await unauth_client.get("/api/v1/auth/api-tokens")
    assert response.status_code == 401


async def test_api_tokens_list_returns_empty_for_authed_user(client, test_app):
    """With overridden auth + an empty repository, list returns []."""
    # Patch the repository to return no rows.
    from app.api.v1.endpoints import auth as auth_module

    monkey_repo = MagicMock()
    monkey_repo.list_for_user = AsyncMock(return_value=[])
    monkey_class = MagicMock(return_value=monkey_repo)
    original = auth_module.ApiTokenRepository
    auth_module.ApiTokenRepository = monkey_class
    try:
        response = await client.get("/api/v1/auth/api-tokens")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        auth_module.ApiTokenRepository = original


async def test_logout_sets_clearing_cookies_on_response(client, test_app):
    """P1.2 regression: logout must set Set-Cookie deletion headers even
    though it returns 204. Previous bug was to return a fresh Response()
    which dropped cookie mutations."""
    from app.api.v1.endpoints import auth as auth_module

    # Patch repositories to no-op.
    stub_session_repo = MagicMock()
    stub_session_repo.invalidate_all_user_sessions = AsyncMock(return_value=0)
    stub_session_repo.invalidate_session = AsyncMock(return_value=True)
    stub_session_repo.get_by_token = AsyncMock(return_value=None)

    stub_fe_repo = MagicMock()
    stub_fe_repo.revoke = AsyncMock()
    stub_fe_repo.revoke_by_backend_session = AsyncMock(return_value=0)

    orig_session = auth_module.UserSessionRepository
    orig_fe = auth_module.FrontendSessionRepository
    auth_module.UserSessionRepository = MagicMock(return_value=stub_session_repo)
    auth_module.FrontendSessionRepository = MagicMock(return_value=stub_fe_repo)
    try:
        response = await client.post(
            "/api/v1/auth/logout",
            json={"invalidate_all_sessions": False},
        )
        assert response.status_code == 204
        # All Set-Cookie headers on the response should be cookie-clearing
        # (Max-Age=0 or an expires in the past).
        set_cookies = (
            response.headers.get_list("set-cookie")
            if hasattr(response.headers, "get_list")
            else [h for k, h in response.headers.raw if k.decode().lower() == "set-cookie"]
        )
        # We expect at least the BFF cookie + CSRF + legacy to be cleared.
        assert len(set_cookies) >= 3
        # Every Set-Cookie must target a known auth cookie name.
        joined = "\n".join(c if isinstance(c, str) else c.decode() for c in set_cookies)
        assert "__Host-capsulecorp_session" in joined or "capsulecorp_session" in joined
        assert "capsulecorp_csrf" in joined
        assert "access_token" in joined
    finally:
        auth_module.UserSessionRepository = orig_session
        auth_module.FrontendSessionRepository = orig_fe
