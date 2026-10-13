"""WhatsApp contacts, segments, tags, and agents endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user_id,
    get_db,
    require_feature,
    require_permission,
    require_wa_manager,
)
from app.core.tenant import verify_tenant_ownership
from app.models.whatsapp import WAConversation, WAMessage
from app.repositories.whatsapp_repository import (
    WAContactRepository,
    WAConversationRepository,
    WASegmentRepository,
    WATagRepository,
)
from app.schemas.whatsapp import (
    WAAgentResponse,
    WABulkSegmentAssignRequest,
    WAContactCreateRequest,
    WAContactDetailResponse,
    WAContactListResponse,
    WAContactSegmentsRequest,
    WAContactUpdateRequest,
    WAConversationResponse,
    WASegmentCreateRequest,
    WASegmentListResponse,
    WASegmentResponse,
    WASegmentUpdateRequest,
    WATagCreateRequest,
    WATagListResponse,
    WATagResponse,
)

from ._helpers import _build_conversation_response, _get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()

_wa_ct_view = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.contacts.view")),
]
_wa_ct_manage = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.contacts.manage")),
]


# =============================================================================
# Phase A: Segments
# =============================================================================


@router.get("/segments", response_model=WASegmentListResponse, dependencies=_wa_ct_view)
async def list_segments(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WASegmentListResponse:
    """List all segments for the tenant."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WASegmentRepository(db)
    segments = await repo.list_by_tenant(tenant_id)

    # Seed system segments only if none exist (first access)
    if not segments:
        await repo.seed_system_segments(tenant_id)
        await db.commit()
        segments = await repo.list_by_tenant(tenant_id)

    return WASegmentListResponse(items=[WASegmentResponse.model_validate(s) for s in segments])


@router.post(
    "/segments", response_model=WASegmentResponse, status_code=201, dependencies=_wa_ct_manage
)
async def create_segment(
    body: WASegmentCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WASegmentResponse:
    """Create a custom segment."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WASegmentRepository(db)

    # Generate slug from name
    slug = body.name.lower().replace(" ", "-")
    existing = await repo.get_by_slug(tenant_id, slug)
    if existing:
        raise HTTPException(status_code=409, detail="Segment with this name already exists")

    segment = await repo.create(
        {
            "tenant_id": tenant_id,
            "name": body.name,
            "slug": slug,
            "color": body.color,
            "icon": body.icon,
            "description": body.description,
            "is_system": False,
        }
    )
    await db.commit()
    return WASegmentResponse.model_validate(segment)


@router.patch(
    "/segments/{segment_id}", response_model=WASegmentResponse, dependencies=_wa_ct_manage
)
async def update_segment(
    segment_id: UUID,
    body: WASegmentUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WASegmentResponse:
    """Update a segment."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WASegmentRepository(db)
    segment = await repo.get_by_id(segment_id)
    verify_tenant_ownership(segment, tenant_id, "Segment")

    updates = body.model_dump(exclude_unset=True)

    if updates:
        segment = await repo.update(segment_id, updates)
    await db.commit()
    return WASegmentResponse.model_validate(segment)


@router.delete("/segments/{segment_id}", status_code=204, dependencies=_wa_ct_manage)
async def delete_segment(
    segment_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a segment."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WASegmentRepository(db)
    segment = await repo.get_by_id(segment_id)
    verify_tenant_ownership(segment, tenant_id, "Segment")

    await repo.delete(segment_id)
    await db.commit()


@router.post("/contacts/bulk/segments", status_code=204, dependencies=_wa_ct_manage)
async def bulk_assign_segments(
    body: WABulkSegmentAssignRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Bulk assign segments to multiple contacts."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    seg_repo = WASegmentRepository(db)

    for contact_id in body.contact_ids:
        await seg_repo.assign_contact(
            tenant_id=tenant_id,
            contact_id=contact_id,
            segment_ids=body.segment_ids,
            assigned_by=UUID(current_user_id),
        )

    # Refresh counts
    for seg_id in body.segment_ids:
        await seg_repo.refresh_contact_count(seg_id)

    await db.commit()


@router.post("/contacts/{contact_id}/segments", status_code=204, dependencies=_wa_ct_manage)
async def assign_contact_segments(
    contact_id: UUID,
    body: WAContactSegmentsRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Assign segments to a contact (replaces all current assignments)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    contact_repo = WAContactRepository(db)
    contact = await contact_repo.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    seg_repo = WASegmentRepository(db)
    await seg_repo.assign_contact(
        tenant_id=tenant_id,
        contact_id=contact_id,
        segment_ids=body.segment_ids,
        assigned_by=UUID(current_user_id),
    )

    # Refresh counts for affected segments
    for seg_id in body.segment_ids:
        await seg_repo.refresh_contact_count(seg_id)

    await db.commit()


# =============================================================================
# Phase A: Tags
# =============================================================================


@router.get("/tags", response_model=WATagListResponse, dependencies=_wa_ct_view)
async def list_tags(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WATagListResponse:
    """List all tags for the tenant."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WATagRepository(db)
    tags = await repo.list_by_tenant(tenant_id)
    return WATagListResponse(items=[WATagResponse.model_validate(t) for t in tags])


@router.post("/tags", response_model=WATagResponse, status_code=201, dependencies=_wa_ct_manage)
async def create_tag(
    body: WATagCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WATagResponse:
    """Create a tag."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WATagRepository(db)
    tag = await repo.create(
        {
            "tenant_id": tenant_id,
            "name": body.name,
            "color": body.color,
        }
    )
    await db.commit()
    return WATagResponse.model_validate(tag)


@router.patch("/tags/{tag_id}", response_model=WATagResponse, dependencies=_wa_ct_manage)
async def update_tag(
    tag_id: UUID,
    body: WATagCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WATagResponse:
    """Update a tag."""
    repo = WATagRepository(db)
    tag = await repo.update(tag_id, {"name": body.name, "color": body.color})
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    await db.commit()
    return WATagResponse.model_validate(tag)


@router.delete("/tags/{tag_id}", status_code=204, dependencies=_wa_ct_manage)
async def delete_tag(
    tag_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a tag."""
    repo = WATagRepository(db)
    deleted = await repo.delete(tag_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tag not found")
    await db.commit()


# =============================================================================
# Contact Export / Import (literal paths before {contact_id} routes)
# =============================================================================


@router.get("/contacts/export", dependencies=_wa_ct_view)
async def export_contacts_csv(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Export all contacts as CSV."""
    from app.services.whatsapp_contact_csv_service import generate_contacts_csv

    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    csv_content = await generate_contacts_csv(db, tenant_id)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contactos_whatsapp.csv"},
    )


@router.post("/contacts/import", dependencies=_wa_ct_manage)
async def import_contacts_csv(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> dict:
    """Import contacts from a CSV file."""
    from app.services.whatsapp_contact_import_service import import_contacts_from_csv

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    MAX_IMPORT_SIZE = 10 * 1024 * 1024  # 10 MB
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    content = await file.read()
    if len(content) > MAX_IMPORT_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    try:
        return await import_contacts_from_csv(db, tenant_id, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Phase A: Contact Detail
# =============================================================================


@router.get(
    "/contacts/{contact_id}", response_model=WAContactDetailResponse, dependencies=_wa_ct_view
)
async def get_contact_detail(
    contact_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAContactDetailResponse:
    """Get full contact detail with segments and tags."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    contact_repo = WAContactRepository(db)
    contact = await contact_repo.get_by_id(contact_id)
    verify_tenant_ownership(contact, tenant_id, "Contact")

    seg_repo = WASegmentRepository(db)
    tag_repo = WATagRepository(db)
    segments = await seg_repo.get_segments_for_contact(contact_id)
    tags = await tag_repo.get_tags_for_contact(contact_id)

    return WAContactDetailResponse(
        id=contact.id,
        phone_e164=contact.phone_e164,
        display_name=contact.display_name,
        email=contact.email,
        opt_in_status=contact.opt_in_status,
        notes=contact.notes,
        source=contact.source,
        metadata_extra=contact.metadata_extra,
        segments=[WASegmentResponse.model_validate(s) for s in segments],
        tags=[WATagResponse.model_validate(t) for t in tags],
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


@router.patch(
    "/contacts/{contact_id}", response_model=WAContactDetailResponse, dependencies=_wa_ct_manage
)
async def update_contact(
    contact_id: UUID,
    body: WAContactUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAContactDetailResponse:
    """Update contact fields and optionally tags."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    contact_repo = WAContactRepository(db)
    contact = await contact_repo.get_by_id(contact_id)
    verify_tenant_ownership(contact, tenant_id, "Contact")

    # Update basic fields
    updates = body.model_dump(exclude_unset=True, exclude={"tag_ids"})
    if updates:
        contact = await contact_repo.update(contact_id, updates)

    # Update tags if provided
    if body.tag_ids is not None:
        tag_repo = WATagRepository(db)
        await tag_repo.set_contact_tags(contact_id, body.tag_ids)

    await db.commit()

    # Return full detail
    return await get_contact_detail(contact_id, current_user_id, db)


# =============================================================================
# Phase A: Agents
# =============================================================================


@router.get("/agents", response_model=list[WAAgentResponse], dependencies=_wa_ct_view)
async def list_agents(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WAAgentResponse]:
    """List agents available for conversation assignment."""
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    agents_data = await user_repo.list_agents()
    return [WAAgentResponse(**a) for a in agents_data]


# =============================================================================
# Phase B: Contacts Management
# =============================================================================


@router.get("/contacts", response_model=WAContactListResponse, dependencies=_wa_ct_view)
async def list_contacts(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(None, min_length=1, max_length=100),
    segment: UUID | None = Query(None),
    tag: UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> WAContactListResponse:
    """List all contacts for the tenant with optional filters."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    contact_repo = WAContactRepository(db)
    seg_repo = WASegmentRepository(db)
    tag_repo = WATagRepository(db)

    items, total = await contact_repo.list_by_tenant(
        tenant_id=tenant_id,
        search=search,
        segment_id=segment,
        tag_id=tag,
        skip=skip,
        limit=limit,
    )

    # Batch-load segments and tags in 2 queries instead of 2*N
    contact_ids = [c.id for c in items]
    segments_map = await seg_repo.get_segments_for_contacts(contact_ids)
    tags_map = await tag_repo.get_tags_for_contacts(contact_ids)

    result_items = []
    for c in items:
        result_items.append(
            WAContactDetailResponse(
                id=c.id,
                phone_e164=c.phone_e164,
                display_name=c.display_name,
                email=c.email,
                opt_in_status=c.opt_in_status,
                notes=c.notes,
                source=c.source,
                metadata_extra=c.metadata_extra,
                segments=[WASegmentResponse.model_validate(s) for s in segments_map.get(c.id, [])],
                tags=[WATagResponse.model_validate(t) for t in tags_map.get(c.id, [])],
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    return WAContactListResponse(items=result_items, total=total)


@router.post(
    "/contacts", response_model=WAContactDetailResponse, status_code=201, dependencies=_wa_ct_manage
)
async def create_contact(
    body: WAContactCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAContactDetailResponse:
    """Create a contact manually."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    contact_repo = WAContactRepository(db)
    phone = WAContactRepository._normalize_phone(body.phone_e164)
    contact, created = await contact_repo.get_or_create_by_phone(
        tenant_id=tenant_id,
        phone_e164=phone,
        display_name=body.display_name,
    )
    if not created:
        raise HTTPException(status_code=409, detail="Contact with this phone already exists")

    if body.email:
        contact.email = body.email
    if body.notes:
        contact.notes = body.notes
    contact.source = body.source
    await db.commit()
    await db.refresh(contact)

    return WAContactDetailResponse(
        id=contact.id,
        phone_e164=contact.phone_e164,
        display_name=contact.display_name,
        email=contact.email,
        opt_in_status=contact.opt_in_status,
        notes=contact.notes,
        source=contact.source,
        metadata_extra=contact.metadata_extra,
        segments=[],
        tags=[],
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


@router.delete("/contacts/{contact_id}", status_code=204, dependencies=_wa_ct_manage)
async def delete_contact(
    contact_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a contact and all related conversations/messages."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    contact_repo = WAContactRepository(db)
    contact = await contact_repo.get_by_id(contact_id)
    verify_tenant_ownership(contact, tenant_id, "Contact")

    # Delete messages → conversations first (FK RESTRICT prevents direct contact delete)
    conv_ids_result = await db.execute(
        select(WAConversation.id).where(WAConversation.contact_id == contact_id)
    )
    conv_ids = [row[0] for row in conv_ids_result.all()]

    if conv_ids:
        await db.execute(sa_delete(WAMessage).where(WAMessage.conversation_id.in_(conv_ids)))
        await db.execute(sa_delete(WAConversation).where(WAConversation.id.in_(conv_ids)))

    await contact_repo.delete(contact_id)
    await db.commit()


@router.post(
    "/contacts/{contact_id}/conversation",
    response_model=WAConversationResponse,
    dependencies=_wa_ct_manage,
)
async def get_or_create_conversation_for_contact(
    contact_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAConversationResponse:
    """Find or create a conversation for a contact (to start a chat from contacts page)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    contact_repo = WAContactRepository(db)
    contact = await contact_repo.get_by_id(contact_id)
    if not contact or contact.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Contact not found")

    conv_repo = WAConversationRepository(db)
    conv = await conv_repo.get_open_for_contact(tenant_id, contact.id)

    if not conv:
        conv = await conv_repo.create(
            {
                "tenant_id": tenant_id,
                "contact_id": contact.id,
                "status": "open",
            }
        )
        await db.flush()

    await db.commit()

    # Reload with contact relationship
    conv = await conv_repo.get_with_contact(conv.id)
    return _build_conversation_response(conv)
