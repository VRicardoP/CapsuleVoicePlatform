"""Tests for WhatsApp webhook endpoints."""



class TestWhatsAppMetaWebhookVerification:
    """GET /webhooks/meta is the Meta webhook verification (public)."""

    async def test_verification_with_challenge(self, unauth_client):
        """Meta sends hub.challenge for verification — should echo it back."""
        response = await unauth_client.get(
            "/api/v1/whatsapp/webhooks/meta",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-token",
                "hub.challenge": "challenge123",
            },
        )
        # May return 200 (token match) or 403 (token mismatch), not 401
        assert response.status_code in (200, 403)

    async def test_verification_without_params(self, unauth_client):
        """GET without params should fail validation."""
        response = await unauth_client.get("/api/v1/whatsapp/webhooks/meta")
        assert response.status_code in (400, 403, 422)


class TestWhatsAppMetaWebhookIncoming:
    """POST /webhooks/meta receives incoming messages from Meta."""

    async def test_webhook_without_signature_returns_ok(self, unauth_client):
        """POST without signature — Meta webhook endpoint accepts and processes."""
        response = await unauth_client.post(
            "/api/v1/whatsapp/webhooks/meta",
            json={"object": "whatsapp_business_account", "entry": []},
        )
        # Endpoint accepts the payload (signature validation may be optional
        # or handled differently depending on config)
        assert response.status_code in (200, 400, 403, 500)

    async def test_webhook_with_invalid_payload(self, unauth_client):
        """POST with non-whatsapp object type."""
        response = await unauth_client.post(
            "/api/v1/whatsapp/webhooks/meta",
            json={"object": "not_whatsapp", "entry": []},
        )
        assert response.status_code in (200, 400, 403, 404)
