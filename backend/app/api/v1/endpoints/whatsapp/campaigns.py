"""WhatsApp campaign routes."""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user_id,
    get_db,
    require_feature,
    require_permission,
    require_wa_manager,
)
from app.core.tasks import create_logged_task
from app.core.tenant import verify_tenant_ownership
from app.repositories.whatsapp_repository import (
    WACampaignRecipientRepository,
    WACampaignRepository,
)
from app.schemas.whatsapp import (
    WACampaignCatalogItem,
    WACampaignCreateRequest,
    WACampaignListResponse,
    WACampaignRecipientResponse,
    WACampaignResponse,
    WACampaignUpdateRequest,
)

from ._helpers import _get_campaign_sender, _get_tenant_id

router = APIRouter()
logger = logging.getLogger(__name__)

_wa_camp_view = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.campaigns.view")),
]
_wa_camp_manage = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.campaigns.manage")),
]


async def _campaign_response(db: AsyncSession, campaign) -> WACampaignResponse:
    """Build WACampaignResponse, eagerly loading catalog_item if needed."""
    if campaign.catalog_item_id:
        await db.refresh(campaign, attribute_names=["catalog_item"])
    resp = WACampaignResponse.model_validate(campaign)
    if campaign.catalog_item_id and campaign.catalog_item:
        resp.catalog_item = WACampaignCatalogItem.model_validate(campaign.catalog_item)
    return resp


@router.get("/campaigns", response_model=WACampaignListResponse, dependencies=_wa_camp_view)
async def list_campaigns(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> WACampaignListResponse:
    """List campaigns for the tenant."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACampaignRepository(db)
    items, total = await repo.list_by_tenant(
        tenant_id=tenant_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    result_items = []
    for c in items:
        resp = WACampaignResponse.model_validate(c)
        if c.template:
            resp.template_name = c.template.name
        if c.catalog_item:
            resp.catalog_item = WACampaignCatalogItem.model_validate(c.catalog_item)
        result_items.append(resp)
    return WACampaignListResponse(items=result_items, total=total)


@router.post(
    "/campaigns", response_model=WACampaignResponse, status_code=201, dependencies=_wa_camp_manage
)
async def create_campaign(
    body: WACampaignCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACampaignResponse:
    """Create a campaign (draft or scheduled)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACampaignRepository(db)

    initial_status = "scheduled" if body.scheduled_at else "draft"

    campaign = await repo.create(
        {
            "tenant_id": tenant_id,
            "name": body.name,
            "status": initial_status,
            "template_id": body.template_id,
            "catalog_item_id": body.catalog_item_id,
            "audience_filter": body.audience_filter,
            "scheduled_at": body.scheduled_at,
            "is_ab_test": body.is_ab_test,
            "created_by": UUID(current_user_id),
        }
    )

    # For A/B tests, create variant B campaign
    if body.is_ab_test and body.ab_template_id:
        await repo.create(
            {
                "tenant_id": tenant_id,
                "name": f"{body.name} (Variante B)",
                "status": initial_status,
                "template_id": body.ab_template_id,
                "audience_filter": body.audience_filter,
                "scheduled_at": body.scheduled_at,
                "is_ab_test": True,
                "ab_parent_id": campaign.id,
                "created_by": UUID(current_user_id),
            }
        )

    await db.commit()
    await db.refresh(campaign)
    return await _campaign_response(db, campaign)


@router.get(
    "/campaigns/{campaign_id}", response_model=WACampaignResponse, dependencies=_wa_camp_view
)
async def get_campaign(
    campaign_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACampaignResponse:
    """Get a single campaign."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACampaignRepository(db)
    campaign = await repo.get_with_template(campaign_id)
    verify_tenant_ownership(campaign, tenant_id, "Campaign")
    resp = WACampaignResponse.model_validate(campaign)
    if campaign.template:
        resp.template_name = campaign.template.name
    if campaign.catalog_item:
        resp.catalog_item = WACampaignCatalogItem.model_validate(campaign.catalog_item)
    return resp


@router.patch(
    "/campaigns/{campaign_id}", response_model=WACampaignResponse, dependencies=_wa_camp_manage
)
async def update_campaign(
    campaign_id: UUID,
    body: WACampaignUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACampaignResponse:
    """Update a draft campaign."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id)
    verify_tenant_ownership(campaign, tenant_id, "Campaign")
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft campaigns can be edited")

    updates = body.model_dump(exclude_unset=True)
    if updates:
        campaign = await repo.update(campaign_id, updates)
    await db.commit()
    return await _campaign_response(db, campaign)


@router.delete("/campaigns/{campaign_id}", status_code=204, dependencies=_wa_camp_manage)
async def delete_campaign(
    campaign_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a campaign (draft, cancelled, or completed)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id)
    verify_tenant_ownership(campaign, tenant_id, "Campaign")
    if campaign.status not in ("draft", "cancelled", "completed"):
        raise HTTPException(
            status_code=400, detail="Only draft/cancelled/completed campaigns can be deleted"
        )
    await repo.delete(campaign_id)
    await db.commit()


@router.post(
    "/campaigns/{campaign_id}/start",
    response_model=WACampaignResponse,
    dependencies=_wa_camp_manage,
)
async def start_campaign(
    campaign_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACampaignResponse:
    """Start sending a campaign."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id)
    verify_tenant_ownership(campaign, tenant_id, "Campaign")
    if campaign.status != "draft" and campaign.status != "scheduled":
        raise HTTPException(status_code=400, detail="Campaign cannot be started")

    now = datetime.now(UTC)
    campaign = await repo.update(
        campaign_id,
        {
            "status": "sending",
            "started_at": now,
        },
    )
    await db.commit()

    # Launch background sending task
    sender = _get_campaign_sender()
    create_logged_task(sender.start_campaign(campaign_id), name=f"wa-campaign-{campaign_id}")

    return await _campaign_response(db, campaign)


@router.post(
    "/campaigns/{campaign_id}/pause",
    response_model=WACampaignResponse,
    dependencies=_wa_camp_manage,
)
async def pause_campaign(
    campaign_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACampaignResponse:
    """Pause a sending campaign."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id)
    verify_tenant_ownership(campaign, tenant_id, "Campaign")
    if campaign.status != "sending":
        raise HTTPException(status_code=400, detail="Campaign is not sending")

    # Signal background task to pause
    _get_campaign_sender().pause_campaign(campaign_id)

    campaign = await repo.update(campaign_id, {"status": "paused"})
    await db.commit()
    return await _campaign_response(db, campaign)


@router.post(
    "/campaigns/{campaign_id}/cancel",
    response_model=WACampaignResponse,
    dependencies=_wa_camp_manage,
)
async def cancel_campaign(
    campaign_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACampaignResponse:
    """Cancel a campaign."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id)
    verify_tenant_ownership(campaign, tenant_id, "Campaign")
    if campaign.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Campaign already finished")

    # Signal background task to stop
    _get_campaign_sender().cancel_campaign(campaign_id)

    campaign = await repo.update(campaign_id, {"status": "cancelled"})
    await db.commit()
    return await _campaign_response(db, campaign)


@router.post(
    "/campaigns/{campaign_id}/relaunch",
    response_model=WACampaignResponse,
    dependencies=_wa_camp_manage,
)
async def relaunch_campaign(
    campaign_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACampaignResponse:
    """Relaunch a completed/cancelled campaign — resets recipients and sends again."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id)
    verify_tenant_ownership(campaign, tenant_id, "Campaign")
    if campaign.status not in ("completed", "cancelled"):
        raise HTTPException(
            status_code=400, detail="Only completed/cancelled campaigns can be relaunched"
        )

    # Reset all recipients to pending via repository
    recipient_repo = WACampaignRecipientRepository(db)
    await recipient_repo.reset_all_pending(campaign_id)

    # Reset campaign counters and status
    now = datetime.now(UTC)
    campaign = await repo.update(
        campaign_id,
        {
            "status": "sending",
            "started_at": now,
            "completed_at": None,
            "sent_count": 0,
            "delivered_count": 0,
            "read_count": 0,
            "failed_count": 0,
        },
    )
    await db.commit()

    # Launch background sending task
    sender = _get_campaign_sender()
    create_logged_task(sender.start_campaign(campaign_id), name=f"wa-campaign-{campaign_id}")

    return await _campaign_response(db, campaign)


@router.get(
    "/campaigns/{campaign_id}/recipients",
    response_model=list[WACampaignRecipientResponse],
    dependencies=_wa_camp_view,
)
async def list_campaign_recipients(
    campaign_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[WACampaignRecipientResponse]:
    """List recipients of a campaign."""
    repo = WACampaignRecipientRepository(db)
    items, _ = await repo.list_by_campaign(campaign_id, skip=skip, limit=limit)
    result = []
    for r in items:
        resp = WACampaignRecipientResponse(
            id=r.id,
            contact_id=r.contact_id,
            status=r.status,
            sent_at=r.sent_at,
            delivered_at=r.delivered_at,
            read_at=r.read_at,
            error_detail=r.error_detail,
        )
        if r.contact:
            resp.contact_name = r.contact.display_name
            resp.contact_phone = r.contact.phone_e164
        result.append(resp)
    return result
