"""Tests for the permission system endpoints and authorization logic."""

from uuid import UUID

import pytest

from app.core.authorization import Principal

# === Unit tests for Principal.has_permission ===


class TestPrincipalHasPermission:
    def _make(self, perms: set[str]) -> Principal:
        return Principal(
            user_id=UUID("00000000-1111-2222-3333-444444444444"),
            role="user",
            organization_id=UUID("00000000-0000-0000-0000-aaaaaaaaaaaa"),
            permissions=frozenset(perms),
        )

    def test_wildcard_grants_everything(self):
        p = self._make({"*"})
        assert p.has_permission("anything.at.all")
        assert p.has_permission("whatsapp.inbox.view")

    def test_exact_match(self):
        p = self._make({"outbound.campaigns.view"})
        assert p.has_permission("outbound.campaigns.view")

    def test_parent_grants_child(self):
        p = self._make({"outbound"})
        assert p.has_permission("outbound.campaigns.view")
        assert p.has_permission("outbound.settings.manage")
        assert p.has_permission("outbound.analytics.view")

    def test_mid_level_grants_children(self):
        p = self._make({"outbound.campaigns"})
        assert p.has_permission("outbound.campaigns.view")
        assert p.has_permission("outbound.campaigns.manage")

    def test_child_does_not_grant_parent(self):
        p = self._make({"outbound.campaigns.view"})
        assert not p.has_permission("outbound")
        assert not p.has_permission("outbound.campaigns.manage")

    def test_unrelated_permission_denied(self):
        p = self._make({"outbound.campaigns.view"})
        assert not p.has_permission("newsletter.campaigns.view")
        assert not p.has_permission("whatsapp.inbox.view")

    def test_empty_permissions(self):
        p = self._make(set())
        assert not p.has_permission("dashboard")

    def test_superadmin_principal(self):
        p = Principal(
            user_id=UUID("00000000-1111-2222-3333-444444444444"),
            role="superadmin",
            organization_id=None,
            permissions=frozenset({"*"}),
        )
        assert p.has_permission("users.permissions.manage")
        assert p.has_permission("whatsapp.settings.manage")


# === Endpoint tests ===


class TestPermissionsMeEndpoint:
    async def test_requires_auth(self, unauth_client):
        response = await unauth_client.get("/api/v1/permissions/me")
        assert response.status_code == 401

    async def test_returns_authorization_context(self, client):
        response = await client.get("/api/v1/permissions/me")
        # With superadmin mock, should return 200
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "permissions" in data
        assert data["user"]["role"] == "superadmin"


class TestPermissionsCatalogEndpoint:
    async def test_requires_auth(self, unauth_client):
        response = await unauth_client.get("/api/v1/permissions/catalog")
        assert response.status_code == 401


class TestUserPermissionsEndpoint:
    async def test_get_requires_auth(self, unauth_client):
        response = await unauth_client.get(
            "/api/v1/users/00000000-1111-2222-3333-444444444444/permissions"
        )
        assert response.status_code == 401

    async def test_put_requires_auth(self, unauth_client):
        response = await unauth_client.put(
            "/api/v1/users/00000000-1111-2222-3333-444444444444/permissions",
            json={"permissions": ["dashboard"]},
        )
        assert response.status_code == 401


class TestPermissionEnforcementOnModules:
    """Verify that module endpoints return 403 without proper permissions."""

    @pytest.fixture
    def _no_perms_app(self, test_app):
        """Override principal to have NO permissions (regular user, empty)."""
        from app.core.dependencies import get_current_principal

        async def _override():
            return Principal(
                user_id=UUID("00000000-1111-2222-3333-444444444444"),
                role="user",
                organization_id=UUID("00000000-0000-0000-0000-aaaaaaaaaaaa"),
                permissions=frozenset(),
            )

        test_app.dependency_overrides[get_current_principal] = _override
        return test_app

    async def test_dashboard_denied(self, _no_perms_app, client):
        response = await client.get("/api/v1/dashboard")
        assert response.status_code == 403
