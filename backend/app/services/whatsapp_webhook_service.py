"""Webhook processing logic for Meta WhatsApp webhooks.

Handles inbound messages, delivery status updates, and campaign delivery tracking.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whatsapp import (
    WACampaign,
    WACampaignRecipient,
    WAConversation,
    WAMessage,
)
from app.repositories.whatsapp_repository import (
    WAContactRepository,
    WAConversationRepository,
    WAEventRepository,
    WAMessageRepository,
    WATenantSettingsRepository,
)
from app.services.whatsapp_sse import sse_broadcaster

logger = logging.getLogger(__name__)


async def process_webhook(payload: dict) -> None:
    """Background task: process Meta webhook payload.

    Opens its own DB session since it runs outside the request lifecycle.
    """
    from app.config.database import async_session_maker

    async with async_session_maker() as db:
        try:
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    meta_phone_id = value.get("metadata", {}).get("phone_number_id")

                    if not meta_phone_id:
                        continue

                    ts_repo = WATenantSettingsRepository(db)
                    ts = await ts_repo.get_by_phone_number_id(meta_phone_id)
                    if not ts:
                        logger.warning(
                            "Unknown phone_number_id", extra={"phone_number_id": meta_phone_id}
                        )
                        continue

                    for msg in value.get("messages", []):
                        await process_inbound_message(db, ts, value, msg)

                    for status_update in value.get("statuses", []):
                        await process_status_update(db, ts, status_update)

            await db.commit()
        except (SQLAlchemyError, Exception):
            logger.exception("Webhook processing error")
            await db.rollback()


async def process_inbound_message(db: AsyncSession, ts, value: dict, msg: dict) -> None:
    """Process a single inbound message from Meta webhook.

    Creates the event, contact, conversation (if needed), message record,
    updates conversation state, publishes SSE, and triggers flows.
    """
    from app.api.v1.endpoints.whatsapp._helpers import _get_next_assignee

    wamid = msg.get("id", "")
    provider_event_id = f"msg:{wamid}"

    event_repo = WAEventRepository(db)
    event = await event_repo.create_event(
        provider_event_id=provider_event_id,
        event_type="message_inbound",
        payload_raw=msg,
        tenant_id=ts.tenant_id,
        meta_phone_number_id=ts.phone_number_id,
    )
    if not event:
        return

    sender_phone = msg.get("from", "")
    contact_name = None
    contacts = value.get("contacts", [])
    if contacts:
        profile = contacts[0].get("profile", {})
        contact_name = profile.get("name")

    contact_repo = WAContactRepository(db)
    contact, _ = await contact_repo.get_or_create_by_phone(
        tenant_id=ts.tenant_id,
        phone_e164=sender_phone,
        display_name=contact_name,
    )

    conv_repo = WAConversationRepository(db)
    conv = await conv_repo.get_open_for_contact(ts.tenant_id, contact.id)
    now = datetime.now(UTC)
    is_new_conversation = conv is None

    if not conv:
        assignee = await _get_next_assignee(db)
        conv = await conv_repo.create(
            {
                "tenant_id": ts.tenant_id,
                "contact_id": contact.id,
                "status": "assigned" if assignee else "open",
                "assignee_user_id": assignee,
                "last_inbound_at": now,
                "last_message_at": now,
            }
        )

    msg_type = msg.get("type", "text")
    text_body, media_url, media_mime_type, media_sha256, media_caption = _extract_message_content(
        msg, msg_type
    )

    msg_repo = WAMessageRepository(db)
    wa_message = await msg_repo.create(
        {
            "tenant_id": ts.tenant_id,
            "conversation_id": conv.id,
            "direction": "inbound",
            "msg_type": msg_type,
            "provider_message_id": wamid,
            "sender_phone": sender_phone,
            "text_body": text_body,
            "media_url": media_url,
            "media_mime_type": media_mime_type,
            "media_sha256": media_sha256,
            "media_caption": media_caption,
            "delivery_status": "delivered",
        }
    )

    preview = (text_body or f"[{msg_type}]")[:255]
    conv.last_message_text = preview
    conv.last_message_at = now
    conv.last_inbound_at = now
    conv.window_expires_at = now + timedelta(hours=24)
    await conv_repo.increment_unread(conv.id)

    await db.flush()

    event.processing_status = "processed"
    event.processed_at = now

    await sse_broadcaster.publish(
        str(ts.tenant_id),
        "message.new",
        {
            "conversationId": str(conv.id),
            "message": {
                "id": str(wa_message.id),
                "direction": "inbound",
                "msg_type": msg_type,
                "text_body": text_body,
                "media_url": media_url,
                "media_mime_type": media_mime_type,
                "media_caption": media_caption,
                "sender_phone": sender_phone,
                "delivery_status": "delivered",
                "created_at": wa_message.created_at.isoformat(),
            },
        },
    )

    try:
        from app.config.database import async_session_maker
        from app.services.whatsapp_flow_engine import FlowEngine

        engine = FlowEngine(async_session_maker)
        await engine.check_triggers(
            tenant_id=ts.tenant_id,
            trigger_type="message_received",
            conversation_id=conv.id,
            message_text=text_body,
            is_new_conversation=is_new_conversation,
        )
    except (SQLAlchemyError, ValueError):
        logger.error("Flow trigger check failed", exc_info=True)


def _extract_message_content(
    msg: dict, msg_type: str
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """Extract text, media fields from a raw Meta message object."""
    text_body = None
    media_url = None
    media_mime_type = None
    media_sha256 = None
    media_caption = None

    if msg_type == "text":
        text_body = msg.get("text", {}).get("body", "")
    elif msg_type in ("image", "video", "audio", "document", "sticker"):
        media_data = msg.get(msg_type, {})
        media_url = media_data.get("id")
        media_mime_type = media_data.get("mime_type")
        media_sha256 = media_data.get("sha256")
        media_caption = media_data.get("caption")
        if media_caption:
            text_body = media_caption
    elif msg_type == "location":
        loc = msg.get("location", {})
        text_body = f"Ubicaci\u00f3n: {loc.get('latitude', '')}, {loc.get('longitude', '')}"
    elif msg_type == "contacts":
        text_body = "[Contacto compartido]"
    elif msg_type == "reaction":
        text_body = msg.get("reaction", {}).get("emoji", "")

    return text_body, media_url, media_mime_type, media_sha256, media_caption


async def process_status_update(db: AsyncSession, ts, status_update: dict) -> None:
    """Process a delivery status update (sent/delivered/read/failed).

    Updates the message record, propagates to campaign counters if applicable,
    and publishes SSE events.
    """
    wamid = status_update.get("id", "")
    new_status = status_update.get("status", "")
    provider_event_id = f"sts:{wamid}:{new_status}"

    event_repo = WAEventRepository(db)
    event = await event_repo.create_event(
        provider_event_id=provider_event_id,
        event_type="message_status",
        payload_raw=status_update,
        tenant_id=ts.tenant_id,
        meta_phone_number_id=ts.phone_number_id,
    )
    if not event:
        return

    msg_repo = WAMessageRepository(db)
    message = await msg_repo.get_by_provider_id(wamid)
    if not message:
        event.processing_status = "processed"
        return

    now = datetime.now(UTC)
    message.delivery_status = new_status

    if new_status == "sent":
        message.sent_at = message.sent_at or now
    elif new_status == "delivered":
        message.delivered_at = message.delivered_at or now
    elif new_status == "read":
        message.read_at = message.read_at or now
    elif new_status == "failed":
        message.failed_at = now
        errors = status_update.get("errors", [])
        if errors:
            message.error_code = str(errors[0].get("code", ""))
            message.error_detail = errors[0].get("title", "")

    event.processing_status = "processed"
    event.processed_at = now

    if new_status in ("delivered", "read", "failed") and message.msg_type == "template":
        await update_campaign_delivery(db, message, new_status, now)

    await sse_broadcaster.publish(
        str(ts.tenant_id),
        "message.status",
        {
            "conversationId": str(message.conversation_id),
            "messageId": str(message.id),
            "status": new_status,
            "timestamp": now.isoformat(),
        },
    )


async def update_campaign_delivery(
    db: AsyncSession, message: WAMessage, new_status: str, now: datetime
) -> None:
    """Propagate delivered/read/failed status to campaign recipient and counters."""
    conv = await db.get(WAConversation, message.conversation_id)
    if not conv:
        return

    allowed = ["sent", "delivered"] if new_status != "failed" else ["sent"]
    result = await db.execute(
        select(WACampaignRecipient)
        .where(
            WACampaignRecipient.contact_id == conv.contact_id,
            WACampaignRecipient.status.in_(allowed),
        )
        .order_by(WACampaignRecipient.sent_at.desc())
        .limit(1)
    )
    recipient = result.scalar_one_or_none()
    if not recipient:
        return

    campaign = await db.get(WACampaign, recipient.campaign_id)
    if not campaign:
        return

    if new_status == "delivered" and recipient.status == "sent":
        recipient.status = "delivered"
        recipient.delivered_at = now
        campaign.delivered_count += 1
    elif new_status == "read" and recipient.status in ("sent", "delivered"):
        if recipient.status == "sent":
            recipient.delivered_at = recipient.delivered_at or now
            campaign.delivered_count += 1
        recipient.status = "read"
        recipient.read_at = now
        campaign.read_count += 1
    elif new_status == "failed" and recipient.status == "sent":
        recipient.status = "failed"
        recipient.failed_at = now
        campaign.failed_count += 1

    await sse_broadcaster.publish(
        str(campaign.tenant_id),
        "campaign.delivery",
        {
            "campaignId": str(campaign.id),
            "delivered": campaign.delivered_count,
            "read": campaign.read_count,
        },
    )
