"""
Fixtures for endpoint (HTTP-level) tests.

Uses httpx.AsyncClient + ASGITransport against the real FastAPI app,
with dependency overrides for authentication and database.
"""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config.database import get_session
from app.core.authorization import Principal
from app.core.dependencies import (
    AuthContext,
    get_auth_context,
    get_current_principal,
    get_current_user_id,
    get_db,
    get_db_with_rls,
    require_admin,
    require_dpo,
)

# Fixed test user ID used across all endpoint tests
TEST_USER_ID = "00000000-1111-2222-3333-444444444444"
TEST_USER_UUID = UUID(TEST_USER_ID)


@pytest_asyncio.fixture
async def test_app():
    """Create a FastAPI app with dependency overrides for testing.

    Overrides:
    - get_db → mock async session
    - get_current_user_id → fixed UUID string
    - get_auth_context → fixed AuthContext
    - require_admin → "admin"
    - require_dpo → "admin"
    """
    from app.main import app

    # Create a mock DB session
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    async def override_get_db():
        yield mock_session

    async def override_get_current_user_id():
        return TEST_USER_ID

    async def override_get_auth_context():
        return AuthContext(user_id=TEST_USER_UUID, session_token="test-session-token")

    async def override_require_admin():
        return "admin"

    async def override_require_dpo():
        return "admin"

    async def override_get_db_with_rls():
        return mock_session

    async def override_get_current_principal():
        return Principal(
            user_id=TEST_USER_UUID,
            role="superadmin",
            organization_id=None,
            permissions=frozenset({"*"}),
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_with_rls] = override_get_db_with_rls
    app.dependency_overrides[get_session] = override_get_db  # Newsletter endpoints use get_session
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    app.dependency_overrides[get_auth_context] = override_get_auth_context
    app.dependency_overrides[require_admin] = override_require_admin
    app.dependency_overrides[require_dpo] = override_require_dpo
    app.dependency_overrides[get_current_principal] = override_get_current_principal

    yield app

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_app_no_auth():
    """FastAPI app WITHOUT auth overrides — for testing 401 responses."""
    from app.main import app

    # Only override DB to avoid real connections
    mock_session = AsyncMock()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    yield app

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(test_app):
    """Authenticated HTTP client (dependency overrides bypass auth)."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def unauth_client(test_app_no_auth):
    """Unauthenticated HTTP client (no auth overrides)."""
    transport = ASGITransport(app=test_app_no_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
