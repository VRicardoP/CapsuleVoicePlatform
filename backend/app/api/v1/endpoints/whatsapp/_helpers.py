"""Shared helpers for WhatsApp endpoint sub-routers."""

import asyncio
import logging
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_active_tenant_id, verify_tenant_ownership
from app.repositories.whatsapp_repository import (
    WAConversationRepository,
    WATenantSettingsRepository,
)
from app.schemas.whatsapp import (
    WAContactSummary,
    WAConversationResponse,
)
from app.schemas.whatsapp.core import WASegmentSummary, WATagSummary
from app.services.whatsapp_campaign_service import CampaignSendingService
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)

# Rate limiter for direct Meta API sends (10 concurrent)
_send_rate_semaphore = asyncio.Semaphore(10)

# Lazy-initialized campaign sender
_campaign_sender: CampaignSendingService | None = None


def _get_campaign_sender() -> CampaignSendingService:
    global _campaign_sender
    if _campaign_sender is None:
        from app.config.database import async_session_maker

        _campaign_sender = CampaignSendingService(async_session_maker)
    return _campaign_sender


async def _get_tenant_id(db: AsyncSession, user_id: str | None = None) -> UUID:
    """Get the active organization's ID, preferring the user's org."""
    return await get_active_tenant_id(
        db, user_id=user_id, status_code=500, detail="No active organization"
    )


async def _get_tenant_settings(db: AsyncSession, tenant_id: UUID):
    """Get WhatsApp tenant settings or raise 404."""
    repo = WATenantSettingsRepository(db)
    ts = await repo.get_by_tenant(tenant_id)
    if not ts:
        raise HTTPException(status_code=404, detail="WhatsApp not configured for this tenant")
    return ts


def _get_wa_token(ts) -> str:
    """Extract the WhatsApp API token from tenant settings."""
    return whatsapp_service.get_token(ts)


async def _get_conversation_or_404(
    db: AsyncSession, conversation_id: UUID, tenant_id: UUID | None = None
):
    """Get a conversation by ID or raise 404. Optionally verify tenant ownership."""
    repo = WAConversationRepository(db)
    conv = await repo.get_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if tenant_id is not None:
        verify_tenant_ownership(conv, tenant_id, "Conversation")
    return conv


def _build_conversation_response(
    conv,
    contact_tags: list | None = None,
    contact_segments: list | None = None,
) -> WAConversationResponse:
    """Build WAConversationResponse from a conversation with contact loaded."""
    return WAConversationResponse(
        id=conv.id,
        status=conv.status,
        priority=conv.priority,
        assignee_user_id=conv.assignee_user_id,
        last_message_text=conv.last_message_text,
        last_message_at=conv.last_message_at,
        last_inbound_at=conv.last_inbound_at,
        last_outbound_at=conv.last_outbound_at,
        window_expires_at=conv.window_expires_at,
        unread_count=conv.unread_count,
        message_count=conv.message_count,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        contact=WAContactSummary(
            id=conv.contact.id,
            phone_e164=conv.contact.phone_e164,
            display_name=conv.contact.display_name,
        ),
        contact_tags=[WATagSummary.model_validate(t) for t in (contact_tags or [])],
        contact_segments=[WASegmentSummary.model_validate(s) for s in (contact_segments or [])],
    )


def _build_template_components(template) -> list[dict] | None:
    """Build Meta API components array from template DB fields (for media headers).

    Returns components only when header_content contains a valid public URL
    (not a temporary Meta CDN link which would cause 131053 errors).
    """
    if not template.header_type or not template.header_content:
        return None

    ht = template.header_type.upper()
    if ht not in ("IMAGE", "VIDEO", "DOCUMENT"):
        return None

    url = template.header_content
    if "scontent.whatsapp.net" in url:
        return None

    media_type = ht.lower()
    return [
        {
            "type": "header",
            "parameters": [
                {
                    "type": media_type,
                    media_type: {"link": url},
                }
            ],
        }
    ]


async def _trigger_survey_on_close(
    tenant_id_str: str,
    conversation_id_str: str,
    contact_id_str: str,
) -> None:
    """Background task: send auto-survey when a conversation is closed."""
    from app.config.database import async_session_maker

    try:
        async with async_session_maker() as db:
            result = await db.execute(
                text("""
                SELECT id, name, questions FROM wa_surveys
                WHERE tenant_id = CAST(:tid AS UUID)
                  AND is_active = true
                  AND trigger = 'conversation_closed'
                LIMIT 1
            """),
                {"tid": tenant_id_str},
            )
            survey = result.fetchone()
            if not survey:
                return

            contact_result = await db.execute(
                text("""
                SELECT phone_e164, opt_in_status FROM wa_contacts
                WHERE id = CAST(:cid AS UUID)
            """),
                {"cid": contact_id_str},
            )
            contact = contact_result.fetchone()
            if not contact or contact.opt_in_status in ("opted_out", "blocked"):
                return

            ts_result = await db.execute(
                text("""
                SELECT phone_number_id, api_token_enc FROM wa_tenant_settings
                WHERE tenant_id = CAST(:tid AS UUID)
            """),
                {"tid": tenant_id_str},
            )
            ts = ts_result.fetchone()
            if not ts:
                return

            survey_text = f"Hola! Nos gustaria conocer tu opinion. En una escala del 1 al 5, como valorarias la atencion recibida? (Encuesta: {survey.name})"
            await whatsapp_service.send_text_message(
                phone_number_id=ts.phone_number_id,
                to=contact.phone_e164,
                text=survey_text,
                token=ts.api_token_enc,
            )

            logger.info(
                "Survey auto-sent on conversation close",
                survey_id=str(survey.id),
                conversation_id=conversation_id_str,
            )
    except (SQLAlchemyError, httpx.HTTPError):
        logger.error("Failed to auto-send survey", exc_info=True)


async def _get_next_assignee(db: AsyncSession, user_id: str | None = None) -> UUID | None:
    """Get next agent using stateless round-robin (DB conversation count as index)."""
    tenant_id = await _get_tenant_id(db, user_id=user_id)
    result = await db.execute(
        text("""
        SELECT s.auto_assign_config,
               (SELECT COUNT(*) FROM wa_conversations WHERE tenant_id = s.tenant_id) AS conv_count
        FROM wa_tenant_settings s
        WHERE s.tenant_id = CAST(:tid AS UUID)
    """),
        {"tid": str(tenant_id)},
    )
    row = result.fetchone()
    if not row or not row.auto_assign_config:
        return None
    config = row.auto_assign_config
    if not config.get("enabled") or not config.get("agent_ids"):
        return None
    agents = config["agent_ids"]
    agent = agents[(row.conv_count or 0) % len(agents)]
    return UUID(agent)
