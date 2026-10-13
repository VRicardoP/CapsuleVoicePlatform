"""WhatsApp conversations, messages, internal notes, and SSE endpoints.

Thin HTTP handlers — business logic lives in services and repositories.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.dependencies import (
    get_current_user_id,
    get_db,
    require_feature,
    require_permission,
    require_wa_manager,
)
from app.core.tenant import verify_tenant_ownership
from app.repositories.user_repository import UserRepository
from app.repositories.whatsapp_repository import (
    WAConversationRepository,
    WAInternalNoteRepository,
    WAMessageRepository,
    WASegmentRepository,
    WASlaBreachRepository,
    WATagRepository,
)
from app.schemas.whatsapp import (
    WAConversationAssignRequest,
    WAConversationListResponse,
    WAConversationResponse,
    WAInternalNoteCreateRequest,
    WAInternalNoteListResponse,
    WAInternalNoteResponse,
    WAInternalNoteUpdateRequest,
    WAMessageListResponse,
    WAMessageResponse,
    WAMessageSendRequest,
    WATemplateSendRequest,
)
from app.services.whatsapp_messaging_service import (
    MessageSendError,
    MessageValidationError,
)
from app.services.whatsapp_messaging_service import (
    send_template_message as svc_send_template,
)
from app.services.whatsapp_messaging_service import (
    send_text_message as svc_send_text,
)
from app.services.whatsapp_service import whatsapp_service
from app.services.whatsapp_sse import sse_broadcaster
from app.services.whatsapp_webhook_service import process_webhook

from ._helpers import (
    _build_conversation_response,
    _get_conversation_or_404,
    _get_tenant_id,
    _trigger_survey_on_close,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_wa_inbox_view = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.inbox.view")),
]


# ── Webhook endpoints (public, HMAC verified) ────────────────────────────────


@router.get("/webhooks/meta", include_in_schema=False)
async def webhook_verify(request: Request) -> Response:
    """Meta webhook verification challenge."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_webhook_verify_token:
        logger.info("Webhook verification successful")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Webhook verification failed", extra={"mode": mode})
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhooks/meta", status_code=200)
async def webhook_receive(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Receive Meta webhook events."""
    body = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    app_secret = settings.whatsapp_app_secret
    if not app_secret:
        logger.error("whatsapp_app_secret is not configured — rejecting webhook")
        raise HTTPException(status_code=403, detail="Webhook secret not configured")
    if not whatsapp_service.verify_webhook_signature(body, signature, app_secret):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(body)
    background_tasks.add_task(process_webhook, payload)

    return {"status": "ok"}


# ── SSE endpoint ──────────────────────────────────────────────────────────────


@router.get("/events", dependencies=_wa_inbox_view)
async def sse_stream(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """SSE stream for real-time WhatsApp updates."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)

    async def event_generator():
        queue = sse_broadcaster.subscribe(str(tenant_id))
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30)
                    event_type = payload["event"]
                    data = json.dumps(payload["data"])
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_broadcaster.unsubscribe(str(tenant_id), queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Conversations REST ────────────────────────────────────────────────────────


@router.get(
    "/conversations", response_model=WAConversationListResponse, dependencies=_wa_inbox_view
)
async def list_conversations(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    assignee: UUID | None = Query(None),
    segment: UUID | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=100),
    unanswered: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=2000),
) -> WAConversationListResponse:
    """List WhatsApp conversations for the tenant.

    Unanswered conversations (the customer wrote last and we have not replied yet)
    are always returned first. Pass `unanswered=true` to restrict the result to
    only those conversations.
    """
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAConversationRepository(db)

    items, total = await repo.list_by_tenant(
        tenant_id=tenant_id,
        status=status_filter,
        assignee_user_id=assignee,
        segment_id=segment,
        search=search,
        unanswered=unanswered,
        skip=skip,
        limit=limit,
    )

    # Batch-load tags and segments for all contacts in the results
    contact_ids = [c.contact.id for c in items]
    tag_repo = WATagRepository(db)
    seg_repo = WASegmentRepository(db)
    tags_map = await tag_repo.get_tags_for_contacts(contact_ids)
    segs_map = await seg_repo.get_segments_for_contacts(contact_ids)

    return WAConversationListResponse(
        items=[
            _build_conversation_response(
                c, tags_map.get(c.contact.id, []), segs_map.get(c.contact.id, [])
            )
            for c in items
        ],
        total=total,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=WAConversationResponse,
    dependencies=_wa_inbox_view,
)
async def get_conversation(
    conversation_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAConversationResponse:
    """Get a single conversation with contact details."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAConversationRepository(db)
    conv = await repo.get_with_contact(conversation_id)
    verify_tenant_ownership(conv, tenant_id, "Conversation")

    return _build_conversation_response(conv)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=WAMessageListResponse,
    dependencies=_wa_inbox_view,
)
async def list_messages(
    conversation_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    before: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
) -> WAMessageListResponse:
    """List messages in a conversation with cursor-based pagination."""
    repo = WAMessageRepository(db)
    messages, has_more = await repo.list_by_conversation(
        conversation_id=conversation_id,
        before=before,
        limit=limit,
    )

    items = [
        WAMessageResponse(
            id=m.id,
            direction=m.direction,
            msg_type=m.msg_type,
            text_body=m.text_body,
            media_url=m.media_url,
            media_mime_type=m.media_mime_type,
            media_caption=m.media_caption,
            delivery_status=m.delivery_status,
            is_from_ai=m.is_from_ai,
            sender_phone=m.sender_phone,
            sent_at=m.sent_at,
            delivered_at=m.delivered_at,
            read_at=m.read_at,
            created_at=m.created_at,
        )
        for m in messages
    ]

    next_cursor = None
    if has_more and messages:
        next_cursor = messages[0].created_at.isoformat()

    return WAMessageListResponse(items=items, has_more=has_more, next_cursor=next_cursor)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=WAMessageResponse,
    dependencies=_wa_inbox_view,
)
async def send_message(
    conversation_id: UUID,
    body: WAMessageSendRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAMessageResponse:
    """Send a text message in a conversation."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)

    try:
        wa_message = await svc_send_text(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            text=body.text,
            sender_user_id=current_user_id,
        )
    except MessageValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except MessageSendError as e:
        raise HTTPException(status_code=502, detail=e.message)

    return WAMessageResponse(
        id=wa_message.id,
        direction="outbound",
        msg_type="text",
        text_body=body.text,
        delivery_status="sent",
        is_from_ai=False,
        sent_at=wa_message.sent_at,
        created_at=wa_message.created_at,
    )


@router.post(
    "/conversations/{conversation_id}/template",
    response_model=WAMessageResponse,
    dependencies=_wa_inbox_view,
)
async def send_template_in_conversation(
    conversation_id: UUID,
    body: WATemplateSendRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAMessageResponse:
    """Send a template message to re-open the 24h window."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)

    try:
        wa_message = await svc_send_template(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            template_id=body.template_id,
            sender_user_id=current_user_id,
        )
    except MessageValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except MessageSendError as e:
        raise HTTPException(status_code=502, detail=e.message)

    return WAMessageResponse(
        id=wa_message.id,
        direction="outbound",
        msg_type="template",
        text_body=wa_message.text_body,
        delivery_status="sent",
        is_from_ai=False,
        sent_at=wa_message.sent_at,
        created_at=wa_message.created_at,
    )


# ── Conversation actions ──────────────────────────────────────────────────────


@router.post("/conversations/{conversation_id}/close", status_code=204, dependencies=_wa_inbox_view)
async def close_conversation(
    conversation_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> None:
    """Close a conversation."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    conv = await _get_conversation_or_404(db, conversation_id, tenant_id=tenant_id)
    conv.status = "closed"

    breach_repo = WASlaBreachRepository(db)
    await breach_repo.resolve_by_conversation(conversation_id)

    await db.commit()

    await sse_broadcaster.publish(
        str(conv.tenant_id),
        "conversation.updated",
        {"conversationId": str(conversation_id), "changes": {"status": "closed"}},
    )

    background_tasks.add_task(
        _trigger_survey_on_close,
        str(conv.tenant_id),
        str(conversation_id),
        str(conv.contact_id),
    )


@router.post(
    "/conversations/{conversation_id}/assign", status_code=204, dependencies=_wa_inbox_view
)
async def assign_conversation(
    conversation_id: UUID,
    body: WAConversationAssignRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Assign a conversation to an agent."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    conv = await _get_conversation_or_404(db, conversation_id, tenant_id=tenant_id)

    conv.assignee_user_id = body.user_id
    conv.status = "assigned"
    await db.commit()

    await sse_broadcaster.publish(
        str(conv.tenant_id),
        "conversation.updated",
        {
            "conversationId": str(conversation_id),
            "changes": {"status": "assigned", "assignee_user_id": str(body.user_id)},
        },
    )


@router.post("/conversations/{conversation_id}/read", status_code=204, dependencies=_wa_inbox_view)
async def mark_as_read(
    conversation_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Mark all messages in a conversation as read."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    conv = await _get_conversation_or_404(db, conversation_id, tenant_id=tenant_id)
    conv.unread_count = 0
    await db.commit()


# ── Internal Notes ────────────────────────────────────────────────────────────


@router.get(
    "/conversations/{conversation_id}/notes",
    response_model=WAInternalNoteListResponse,
    dependencies=_wa_inbox_view,
)
async def list_notes(
    conversation_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAInternalNoteListResponse:
    """List internal notes for a conversation."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    await _get_conversation_or_404(db, conversation_id, tenant_id=tenant_id)
    repo = WAInternalNoteRepository(db)
    notes = await repo.list_by_conversation(conversation_id)
    return WAInternalNoteListResponse(
        items=[WAInternalNoteResponse.model_validate(n) for n in notes]
    )


@router.post(
    "/conversations/{conversation_id}/notes",
    response_model=WAInternalNoteResponse,
    status_code=201,
    dependencies=_wa_inbox_view,
)
async def create_note(
    conversation_id: UUID,
    body: WAInternalNoteCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAInternalNoteResponse:
    """Create an internal note on a conversation."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    conv = await _get_conversation_or_404(db, conversation_id, tenant_id=tenant_id)

    user_repo = UserRepository(db)
    author_name = await user_repo.get_display_name(UUID(current_user_id))

    repo = WAInternalNoteRepository(db)
    note = await repo.create(
        {
            "tenant_id": conv.tenant_id,
            "conversation_id": conversation_id,
            "author_user_id": UUID(current_user_id),
            "author_name": author_name,
            "content": body.content,
        }
    )
    await db.commit()

    await sse_broadcaster.publish(
        str(conv.tenant_id),
        "note.new",
        {
            "conversationId": str(conversation_id),
            "note": {
                "id": str(note.id),
                "authorUserId": current_user_id,
                "authorName": author_name,
                "content": body.content,
                "createdAt": note.created_at.isoformat(),
            },
        },
    )

    return WAInternalNoteResponse.model_validate(note)


@router.patch(
    "/conversations/{conversation_id}/notes/{note_id}",
    response_model=WAInternalNoteResponse,
    dependencies=_wa_inbox_view,
)
async def update_note(
    conversation_id: UUID,
    note_id: UUID,
    body: WAInternalNoteUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAInternalNoteResponse:
    """Update an internal note's content."""
    repo = WAInternalNoteRepository(db)
    note = await repo.get_by_id(note_id)
    if not note or note.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Note not found")

    if str(note.author_user_id) != str(current_user_id):
        raise HTTPException(status_code=403, detail="Only the note author can edit this note")

    updated = await repo.update(note_id, {"content": body.content})
    await db.commit()

    return WAInternalNoteResponse.model_validate(updated)


@router.delete(
    "/conversations/{conversation_id}/notes/{note_id}",
    status_code=204,
    dependencies=_wa_inbox_view,
)
async def delete_note(
    conversation_id: UUID,
    note_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete an internal note."""
    repo = WAInternalNoteRepository(db)
    note = await repo.get_by_id(note_id)
    if not note or note.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Note not found")

    if str(note.author_user_id) != str(current_user_id):
        raise HTTPException(status_code=403, detail="Only the note author can delete this note")

    await repo.delete(note_id)
    await db.commit()
