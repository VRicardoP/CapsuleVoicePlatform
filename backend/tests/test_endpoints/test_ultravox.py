"""Tests for Ultravox webhook endpoints."""



class TestUltravoxWebhook:
    """Ultravox webhook requires HMAC signature."""

    async def test_webhook_missing_signature(self, unauth_client):
        """POST without signature header should be rejected."""
        response = await unauth_client.post(
            "/api/v1/ultravox/webhook",
            json={"event": "call.ended"},
        )
        assert response.status_code in (401, 403, 400)

    async def test_webhook_invalid_signature(self, unauth_client):
        """POST with invalid signature should be rejected."""
        response = await unauth_client.post(
            "/api/v1/ultravox/webhook",
            json={"event": "call.ended"},
            headers={"X-Ultravox-Signature": "invalid-signature"},
        )
        assert response.status_code in (401, 403, 400)


class TestZadarmaWebhook:
    """Zadarma webhook verification endpoint."""

    async def test_zadarma_webhook_get(self, unauth_client):
        """GET zadarma webhook should respond (public endpoint)."""
        response = await unauth_client.get("/api/v1/ultravox/zadarma/webhook")
        # Public endpoint — should not return 401
        assert response.status_code != 401
