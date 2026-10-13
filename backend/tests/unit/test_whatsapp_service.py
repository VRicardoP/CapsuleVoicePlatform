"""
Unit tests for WhatsApp Service.

Tests verify HMAC signature verification and URL construction.
No database or external API calls required.
"""

import hashlib
import hmac

import pytest

from app.services.whatsapp_service import WhatsAppService


@pytest.fixture
def service():
    return WhatsAppService()


class TestVerifyWebhookSignature:
    """Test HMAC-SHA256 signature verification for Meta webhooks."""

    APP_SECRET = "test_app_secret_abc123"

    def _sign(self, payload: bytes) -> str:
        """Generate a valid X-Hub-Signature-256 header value."""
        sig = hmac.new(
            self.APP_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={sig}"

    def test_valid_signature(self):
        payload = b'{"entry": [{"changes": []}]}'
        signature = self._sign(payload)
        assert WhatsAppService.verify_webhook_signature(payload, signature, self.APP_SECRET)

    def test_invalid_signature(self):
        payload = b'{"entry": []}'
        assert not WhatsAppService.verify_webhook_signature(
            payload,
            "sha256=0000000000000000000000000000000000000000000000000000000000000000",
            self.APP_SECRET,
        )

    def test_tampered_payload(self):
        payload = b'{"entry": [{"id": "123"}]}'
        signature = self._sign(payload)
        tampered = b'{"entry": [{"id": "456"}]}'
        assert not WhatsAppService.verify_webhook_signature(tampered, signature, self.APP_SECRET)

    def test_empty_signature_header(self):
        assert not WhatsAppService.verify_webhook_signature(b"test", "", self.APP_SECRET)

    def test_missing_sha256_prefix(self):
        payload = b"test"
        sig = hmac.new(self.APP_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        # No "sha256=" prefix
        assert not WhatsAppService.verify_webhook_signature(payload, sig, self.APP_SECRET)

    def test_empty_payload(self):
        payload = b""
        signature = self._sign(payload)
        assert WhatsAppService.verify_webhook_signature(payload, signature, self.APP_SECRET)

    def test_unicode_payload(self):
        payload = '{"text": "Hola 👋"}'.encode()
        signature = self._sign(payload)
        assert WhatsAppService.verify_webhook_signature(payload, signature, self.APP_SECRET)


class TestSendTemplatePayload:
    """Test template message payload construction."""

    @pytest.mark.asyncio
    async def test_send_template_builds_correct_payload(
        self, service: WhatsAppService, monkeypatch
    ):
        """Verify the payload structure for send_template_message."""
        captured_payload = {}

        class MockResponse:
            status_code = 200
            is_success = True
            text = ""

            def raise_for_status(self):
                pass

            def json(self):
                return {"messages": [{"id": "wamid.test123"}]}

        async def mock_post(*args, **kwargs):
            captured_payload.update(kwargs.get("json", {}))
            return MockResponse()

        from app.core import http_clients

        monkeypatch.setattr(
            http_clients,
            "whatsapp_client",
            type("MockClient", (), {"post": staticmethod(mock_post)})(),
        )

        result = await service.send_template_message(
            phone_number_id="12345",
            to="+34612345678",
            template_name="promo_enero",
            language="es",
            token="test_token",
        )

        assert captured_payload["messaging_product"] == "whatsapp"
        assert captured_payload["type"] == "template"
        assert captured_payload["to"] == "+34612345678"
        assert captured_payload["template"]["name"] == "promo_enero"
        assert captured_payload["template"]["language"]["code"] == "es"
        assert "components" not in captured_payload["template"]
        assert result["messages"][0]["id"] == "wamid.test123"

    @pytest.mark.asyncio
    async def test_send_template_with_components(self, service: WhatsAppService, monkeypatch):
        captured_payload = {}

        class MockResponse:
            status_code = 200
            is_success = True
            text = ""

            def raise_for_status(self):
                pass

            def json(self):
                return {"messages": [{"id": "wamid.test456"}]}

        async def mock_post(*args, **kwargs):
            captured_payload.update(kwargs.get("json", {}))
            return MockResponse()

        from app.core import http_clients

        monkeypatch.setattr(
            http_clients,
            "whatsapp_client",
            type("MockClient", (), {"post": staticmethod(mock_post)})(),
        )

        components = [{"type": "body", "parameters": [{"type": "text", "text": "John"}]}]
        await service.send_template_message(
            phone_number_id="12345",
            to="+34600000001",
            template_name="welcome",
            language="en",
            token="tok",
            components=components,
        )

        assert captured_payload["template"]["components"] == components


class TestURLConstruction:
    """Test Meta Graph API URL building."""

    def test_messages_url(self, service: WhatsAppService):
        url = service._url("123456789", "messages")
        assert "123456789" in url
        assert "/messages" in url
        assert "graph.facebook.com" in url

    def test_default_path_is_messages(self, service: WhatsAppService):
        url = service._url("123456789")
        assert url.endswith("/messages")

    def test_api_version_in_url(self, service: WhatsAppService):
        url = service._url("123456789")
        assert "/v21.0/" in url

    def test_headers(self, service: WhatsAppService):
        headers = service._headers("test_token_abc")
        assert headers["Authorization"] == "Bearer test_token_abc"
        assert headers["Content-Type"] == "application/json"
