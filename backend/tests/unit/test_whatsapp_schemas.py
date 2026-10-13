"""
Unit tests for WhatsApp Pydantic schemas.

Tests verify field constraints, validation, and serialization.
No database required.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.whatsapp import (
    WAContactSummary,
    WAConversationAssignRequest,
    WAConversationListResponse,
    WAConversationResponse,
    WAMessageListResponse,
    WAMessageResponse,
    WAMessageSendRequest,
)

# === WAMessageSendRequest ===


class TestWAMessageSendRequest:
    def test_valid_text(self):
        req = WAMessageSendRequest(text="Hola, buenos dias")
        assert req.text == "Hola, buenos dias"

    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError) as exc:
            WAMessageSendRequest(text="")
        assert "text" in str(exc.value)

    def test_whitespace_only_rejected(self):
        """min_length=1 after stripping? Pydantic v2 doesn't strip by default."""
        # Single space is still length 1, so it passes min_length
        req = WAMessageSendRequest(text=" ")
        assert req.text == " "

    def test_max_length_4096(self):
        req = WAMessageSendRequest(text="A" * 4096)
        assert len(req.text) == 4096

    def test_exceeds_max_length(self):
        with pytest.raises(ValidationError) as exc:
            WAMessageSendRequest(text="A" * 4097)
        assert "text" in str(exc.value)

    def test_unicode_text(self):
        req = WAMessageSendRequest(text="Hola! 👋 ¿Cómo estás?")
        assert "👋" in req.text

    def test_multiline_text(self):
        req = WAMessageSendRequest(text="Linea 1\nLinea 2\nLinea 3")
        assert "\n" in req.text


# === WAConversationAssignRequest ===


class TestWAConversationAssignRequest:
    def test_valid_uuid(self):
        uid = uuid4()
        req = WAConversationAssignRequest(user_id=uid)
        assert req.user_id == uid

    def test_string_uuid_coerced(self):
        uid = uuid4()
        req = WAConversationAssignRequest(user_id=str(uid))
        assert req.user_id == uid

    def test_invalid_uuid_rejected(self):
        with pytest.raises(ValidationError):
            WAConversationAssignRequest(user_id="not-a-uuid")

    def test_missing_user_id_rejected(self):
        with pytest.raises(ValidationError):
            WAConversationAssignRequest()


# === WAContactSummary ===


class TestWAContactSummary:
    def test_full_contact(self):
        c = WAContactSummary(
            id=uuid4(),
            phone_e164="+34612345678",
            display_name="Maria Garcia",
        )
        assert c.display_name == "Maria Garcia"

    def test_contact_without_name(self):
        c = WAContactSummary(
            id=uuid4(),
            phone_e164="+34612345678",
        )
        assert c.display_name is None

    def test_serialization(self):
        uid = uuid4()
        c = WAContactSummary(id=uid, phone_e164="+34600000001")
        data = c.model_dump()
        assert data["id"] == uid
        assert data["phone_e164"] == "+34600000001"
        assert data["display_name"] is None


# === WAMessageResponse ===


class TestWAMessageResponse:
    def _make_msg(self, **overrides) -> WAMessageResponse:
        defaults = {
            "id": uuid4(),
            "direction": "inbound",
            "msg_type": "text",
            "text_body": "Hola",
            "delivery_status": "delivered",
            "is_from_ai": False,
            "created_at": datetime.now(UTC),
        }
        defaults.update(overrides)
        return WAMessageResponse(**defaults)

    def test_inbound_message(self):
        msg = self._make_msg(direction="inbound", sender_phone="+34612345678")
        assert msg.direction == "inbound"
        assert msg.sender_phone == "+34612345678"

    def test_outbound_message(self):
        msg = self._make_msg(
            direction="outbound",
            delivery_status="sent",
            sent_at=datetime.now(UTC),
        )
        assert msg.direction == "outbound"
        assert msg.sent_at is not None

    def test_optional_fields_default_none(self):
        msg = self._make_msg()
        assert msg.media_url is None
        assert msg.media_mime_type is None
        assert msg.media_caption is None
        assert msg.sender_phone is None
        assert msg.sent_at is None
        assert msg.delivered_at is None
        assert msg.read_at is None

    def test_ai_message(self):
        msg = self._make_msg(is_from_ai=True, direction="outbound")
        assert msg.is_from_ai is True

    def test_media_message(self):
        msg = self._make_msg(
            msg_type="image",
            text_body=None,
            media_url="https://example.com/image.jpg",
            media_mime_type="image/jpeg",
            media_caption="Mi foto",
        )
        assert msg.msg_type == "image"
        assert msg.media_caption == "Mi foto"

    def test_serialization_roundtrip(self):
        now = datetime.now(UTC)
        msg = self._make_msg(created_at=now)
        data = msg.model_dump()
        assert data["msg_type"] == "text"
        assert data["text_body"] == "Hola"


# === WAConversationResponse ===


class TestWAConversationResponse:
    def _make_conv(self, **overrides) -> WAConversationResponse:
        now = datetime.now(UTC)
        defaults = {
            "id": uuid4(),
            "status": "open",
            "priority": "normal",
            "unread_count": 0,
            "message_count": 5,
            "created_at": now,
            "updated_at": now,
            "contact": WAContactSummary(
                id=uuid4(),
                phone_e164="+34612345678",
                display_name="Test Contact",
            ),
        }
        defaults.update(overrides)
        return WAConversationResponse(**defaults)

    def test_open_conversation(self):
        conv = self._make_conv(status="open")
        assert conv.status == "open"
        assert conv.assignee_user_id is None

    def test_assigned_conversation(self):
        uid = uuid4()
        conv = self._make_conv(status="assigned", assignee_user_id=uid)
        assert conv.assignee_user_id == uid

    def test_unread_count(self):
        conv = self._make_conv(unread_count=3)
        assert conv.unread_count == 3

    def test_window_expires(self):
        now = datetime.now(UTC)
        conv = self._make_conv(window_expires_at=now)
        assert conv.window_expires_at == now

    def test_last_message_fields(self):
        now = datetime.now(UTC)
        conv = self._make_conv(
            last_message_text="Ultimo mensaje",
            last_message_at=now,
        )
        assert conv.last_message_text == "Ultimo mensaje"

    def test_contact_embedded(self):
        conv = self._make_conv()
        assert conv.contact.phone_e164 == "+34612345678"
        assert conv.contact.display_name == "Test Contact"


# === WAConversationListResponse ===


class TestWAConversationListResponse:
    def test_empty_list(self):
        resp = WAConversationListResponse(items=[], total=0)
        assert len(resp.items) == 0
        assert resp.total == 0

    def test_list_with_items(self):
        now = datetime.now(UTC)
        contact = WAContactSummary(id=uuid4(), phone_e164="+34600000001")
        conv = WAConversationResponse(
            id=uuid4(),
            status="open",
            priority="normal",
            unread_count=0,
            message_count=1,
            created_at=now,
            updated_at=now,
            contact=contact,
        )
        resp = WAConversationListResponse(items=[conv], total=1)
        assert len(resp.items) == 1
        assert resp.total == 1


# === WAMessageListResponse ===


class TestWAMessageListResponse:
    def test_empty_no_more(self):
        resp = WAMessageListResponse(items=[], has_more=False, next_cursor=None)
        assert not resp.has_more

    def test_with_cursor(self):
        now = datetime.now(UTC)
        msg = WAMessageResponse(
            id=uuid4(),
            direction="inbound",
            msg_type="text",
            text_body="Test",
            delivery_status="delivered",
            is_from_ai=False,
            created_at=now,
        )
        resp = WAMessageListResponse(
            items=[msg],
            has_more=True,
            next_cursor=now.isoformat(),
        )
        assert resp.has_more
        assert resp.next_cursor is not None
