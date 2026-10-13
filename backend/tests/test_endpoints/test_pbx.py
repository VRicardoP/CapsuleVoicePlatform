"""Tests for PBX endpoints (API key auth).

PBX endpoints use custom API key authentication, not JWT.
"""



class TestPbxAuth:
    """PBX endpoints require API key authentication."""

    async def test_create_call_without_auth(self, unauth_client):
        """POST /pbx/calls without API key should fail."""
        response = await unauth_client.post("/api/v1/pbx/calls", json={})
        assert response.status_code in (401, 403, 422)

    async def test_get_call_without_auth(self, unauth_client):
        """GET /pbx/calls/{id} without API key should fail."""
        response = await unauth_client.get("/api/v1/pbx/calls/00000000-0000-0000-0000-000000000001")
        assert response.status_code in (401, 403, 404)
