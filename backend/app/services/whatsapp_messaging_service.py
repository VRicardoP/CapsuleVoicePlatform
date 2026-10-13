"""WhatsApp messaging service for sending text and template messages.

Handles validation, Meta API calls, DB persistence, conversation updates,
and SSE broadcasting for outbound messages.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx

from app.models.whatsapp import WAMessage
from app.repositories.whatsapp_repository import (
    WAConversationRepository,
    WAMessageRepository,
    WATemplateRepository,
    WATenantSettingsRepository,
)
from app.services.whatsapp_service import WhatsAppAPIError, whatsapp_service
from app.services.whatsapp_sse import sse_broadcaster

# Rate limiter for outbound messages (shared across all conversations)
_send_rate_semaphore = asyncio.Semaphore(10)


def _get_wa_token(ts) -> str:
    """Extract the WhatsApp API token from tenant settings."""
    return whatsapp_service.get_token(ts)


def _build_template_components(template) -> list[dict] | None:
    """Build Meta API components array from template DB fields (for media headers)."""
    if not template.header_type or not template.header_content:
        return None
    ht = template.header_type.upper()
    if ht not in ("IMAGE", "VIDEO", "DOCUMENT"):
        return None
    url = template.header_content
    if "scontent.whatsapp.net" in url:
        return None
    media_type = ht.lower()
    return [{"type": "header", "parameters": [{"type": media_type, media_type: {"link": url}}]}]


logger = logging.getLogger(__name__)


class MessageValidationError(Exception):
    """Raised when message sending preconditions are not met."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class MessageSendError(Exception):
    """Raised when Meta API call fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def send_text_message(
    db,
    tenant_id: UUID,
    conversation_id: UUID,
    text: str,
    sender_user_id: str,
) -> WAMessage:
    """Send a text message in an existing conversation.

    Validates contact opt-in and 24h window, calls Meta API,
    creates DB record, updates conversation, publishes SSE.

    Returns the created WAMessage.

    Raises:
        MessageValidationError: if contact opted out or window expired.
        MessageSendError: if Meta API call fails.
    """
    ts_repo = WATenantSettingsRepository(db)
    ts = await ts_repo.get_by_tenant(tenant_id)
    if not ts:
        raise MessageValidationError("WhatsApp not configured for this tenant", 404)

    conv_repo = WAConversationRepository(db)
    conv = await conv_repo.get_with_contact(conversation_id)
    if not conv:
        raise MessageValidationError("Conversation not found", 404)

    if conv.contact.opt_in_status in ("opted_out", "blocked"):
        raise MessageValidationError(
            "Contact has opted out or is blocked. Cannot send messages.", 403
        )

    now = datetime.now(UTC)
    if conv.window_expires_at and now > conv.window_expires_at:
        raise MessageValidationError("24-hour messaging window expired. Use a template message.")

    try:
        async with _send_rate_semaphore:
            result = await whatsapp_service.send_text_message(
                phone_number_id=ts.phone_number_id,
                to=conv.contact.phone_e164,
                text=text,
                token=_get_wa_token(ts),
            )
    except WhatsAppAPIError as e:
        raise MessageSendError(e.message) from e
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.error("Failed to send WhatsApp message", exc_info=True)
        raise MessageSendError("Error de conexion con WhatsApp") from e

    wamid = None
    meta_messages = result.get("messages", [])
    if meta_messages:
        wamid = meta_messages[0].get("id")

    msg_repo = WAMessageRepository(db)
    wa_message = await msg_repo.create(
        {
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "direction": "outbound",
            "msg_type": "text",
            "provider_message_id": wamid,
            "text_body": text,
            "delivery_status": "sent",
            "sent_at": now,
        }
    )

    conv.last_message_text = text[:255]
    conv.last_message_at = now
    conv.last_outbound_at = now
    conv.message_count += 1
    await db.flush()
    await db.commit()

    await sse_broadcaster.publish(
        str(tenant_id),
        "message.new",
        {
            "conversationId": str(conversation_id),
            "message": {
                "id": str(wa_message.id),
                "direction": "outbound",
                "msg_type": "text",
                "text_body": text,
                "delivery_status": "sent",
                "created_at": wa_message.created_at.isoformat(),
            },
        },
    )

    return wa_message


async def send_template_message(
    db,
    tenant_id: UUID,
    conversation_id: UUID,
    template_id: UUID,
    sender_user_id: str,
) -> WAMessage:
    """Send a template message in an existing conversation.

    Validates contact opt-in, template approval status, calls Meta API,
    creates DB record, re-opens 24h window, publishes SSE.

    Returns the created WAMessage.

    Raises:
        MessageValidationError: if contact opted out, template not found/approved.
        MessageSendError: if Meta API call fails.
    """
    ts_repo = WATenantSettingsRepository(db)
    ts = await ts_repo.get_by_tenant(tenant_id)
    if not ts:
        raise MessageValidationError("WhatsApp not configured for this tenant", 404)

    conv_repo = WAConversationRepository(db)
    conv = await conv_repo.get_with_contact(conversation_id)
    if not conv:
        raise MessageValidationError("Conversation not found", 404)

    if conv.contact.opt_in_status in ("opted_out", "blocked"):
        raise MessageValidationError(
            "Contact has opted out or is blocked. Cannot send messages.", 403
        )

    template_repo = WATemplateRepository(db)
    template = await template_repo.get_by_id(template_id)
    if not template:
        raise MessageValidationError("Template not found", 404)
    if template.status != "approved":
        raise MessageValidationError("Only approved templates can be sent")

    now = datetime.now(UTC)

    try:
        async with _send_rate_semaphore:
            result = await whatsapp_service.send_template_message(
                phone_number_id=ts.phone_number_id,
                to=conv.contact.phone_e164,
                template_name=template.name,
                language=template.language,
                token=_get_wa_token(ts),
                components=_build_template_components(template),
            )
    except WhatsAppAPIError as e:
        raise MessageSendError(e.message) from e
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.error("Failed to send template message", exc_info=True)
        raise MessageSendError("Error de conexion con WhatsApp") from e

    wamid = None
    meta_messages = result.get("messages", [])
    if meta_messages:
        wamid = meta_messages[0].get("id")

    msg_repo = WAMessageRepository(db)
    wa_message = await msg_repo.create(
        {
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "direction": "outbound",
            "msg_type": "template",
            "provider_message_id": wamid,
            "text_body": template.body_text,
            "delivery_status": "sent",
            "sent_at": now,
        }
    )

    conv.window_expires_at = now + timedelta(hours=24)
    conv.last_message_text = f"[Plantilla: {template.name}]"
    conv.last_message_at = now
    conv.last_outbound_at = now
    conv.message_count += 1
    if conv.status == "closed":
        # Reabrir: "open" es el estado valido del CHECK de wa_conversations
        # (open/assigned/snoozed/closed/expired). "active" no existe y rompia
        # el commit con IntegrityError al responder con plantilla a una cerrada.
        conv.status = "open"
    await db.flush()
    await db.commit()

    await sse_broadcaster.publish(
        str(tenant_id),
        "message.new",
        {
            "conversationId": str(conversation_id),
            "message": {
                "id": str(wa_message.id),
                "direction": "outbound",
                "msg_type": "template",
                "text_body": template.body_text,
                "delivery_status": "sent",
                "created_at": wa_message.created_at.isoformat(),
            },
        },
    )

    return wa_message
