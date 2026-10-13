"""WhatsApp Commerce endpoints: Pipeline, Catalog, and Orders."""

import csv
import io
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select
from sqlalchemy import func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db, require_feature, require_permission
from app.core.tenant import verify_tenant_ownership
from app.models.whatsapp import WADeal, WAOrderItem
from app.repositories.whatsapp_repository import (
    WACatalogItemRepository,
    WADealRepository,
    WAOrderRepository,
    WAPipelineStageRepository,
)
from app.schemas.whatsapp import (
    WACatalogItemCreateRequest,
    WACatalogItemListResponse,
    WACatalogItemResponse,
    WACatalogItemUpdateRequest,
    WADealCreateRequest,
    WADealListResponse,
    WADealMoveRequest,
    WADealResponse,
    WADealUpdateRequest,
    WAOrderCreateRequest,
    WAOrderItemResponse,
    WAOrderListResponse,
    WAOrderResponse,
    WAOrderUpdateRequest,
    WAPipelineAnalyticsResponse,
    WAPipelineStageCreateRequest,
    WAPipelineStageResponse,
    WAPipelineStageUpdateRequest,
)

from ._helpers import _get_tenant_id

router = APIRouter()
logger = logging.getLogger(__name__)

_wa_com_view = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.commerce.view")),
]
_wa_com_manage = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.commerce.manage")),
]


def _build_deal_response(deal) -> WADealResponse:
    """Build a WADealResponse with stage/contact enrichment."""
    resp = WADealResponse(
        id=deal.id,
        stage_id=deal.stage_id,
        title=deal.title,
        value=deal.value,
        currency=deal.currency,
        assignee_user_id=deal.assignee_user_id,
        expected_close_date=deal.expected_close_date,
        closed_at=deal.closed_at,
        notes=deal.notes,
        contact_id=deal.contact_id,
        conversation_id=deal.conversation_id,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
    )
    if deal.stage:
        resp.stage_name = deal.stage.name
    if deal.contact:
        resp.contact_name = deal.contact.display_name
        resp.contact_phone = deal.contact.phone_e164
    return resp


# =============================================================================
# Pipeline Stages
# =============================================================================


@router.get(
    "/pipeline/stages", response_model=list[WAPipelineStageResponse], dependencies=_wa_com_view
)
async def list_pipeline_stages(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WAPipelineStageResponse]:
    """List pipeline stages (seeds defaults on first access)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAPipelineStageRepository(db)
    stages = await repo.list_by_tenant(tenant_id)

    # Only seed defaults if no stages exist (avoids write transaction on every read)
    if not stages:
        await repo.seed_default_stages(tenant_id)
        await db.commit()
        stages = await repo.list_by_tenant(tenant_id)
    result = []
    for s in stages:
        count_result = await db.execute(
            select(sa_func.count(), sa_func.coalesce(sa_func.sum(WADeal.value), 0))
            .select_from(WADeal)
            .where(and_(WADeal.tenant_id == tenant_id, WADeal.stage_id == s.id))
        )
        row = count_result.fetchone()
        result.append(
            WAPipelineStageResponse(
                id=s.id,
                name=s.name,
                color=s.color,
                sort_order=s.sort_order,
                is_default=s.is_default,
                is_won=s.is_won,
                is_lost=s.is_lost,
                deal_count=row[0],
                deal_value=row[1],
            )
        )
    return result


@router.post(
    "/pipeline/stages",
    response_model=WAPipelineStageResponse,
    status_code=201,
    dependencies=_wa_com_manage,
)
async def create_pipeline_stage(
    body: WAPipelineStageCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAPipelineStageResponse:
    """Create a pipeline stage."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAPipelineStageRepository(db)
    stage = await repo.create(
        {
            "tenant_id": tenant_id,
            "name": body.name,
            "color": body.color,
            "sort_order": body.sort_order,
            "is_won": body.is_won,
            "is_lost": body.is_lost,
        }
    )
    await db.commit()
    return WAPipelineStageResponse(
        id=stage.id,
        name=stage.name,
        color=stage.color,
        sort_order=stage.sort_order,
        is_default=stage.is_default,
        is_won=stage.is_won,
        is_lost=stage.is_lost,
        deal_count=0,
        deal_value=0,
    )


@router.patch(
    "/pipeline/stages/{stage_id}",
    response_model=WAPipelineStageResponse,
    dependencies=_wa_com_manage,
)
async def update_pipeline_stage(
    stage_id: UUID,
    body: WAPipelineStageUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAPipelineStageResponse:
    """Update a pipeline stage."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAPipelineStageRepository(db)
    stage = await repo.get_by_id(stage_id)
    verify_tenant_ownership(stage, tenant_id, "Stage")
    updates = body.model_dump(exclude_unset=True)
    if updates:
        stage = await repo.update(stage_id, updates)
    await db.commit()
    return WAPipelineStageResponse.model_validate(stage)


@router.delete("/pipeline/stages/{stage_id}", status_code=204, dependencies=_wa_com_manage)
async def delete_pipeline_stage(
    stage_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a pipeline stage (must have no deals)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAPipelineStageRepository(db)
    stage = await repo.get_by_id(stage_id)
    verify_tenant_ownership(stage, tenant_id, "Stage")
    if stage.deals:
        raise HTTPException(status_code=400, detail="Cannot delete stage with deals")
    await repo.delete(stage_id)
    await db.commit()


# =============================================================================
# Deals
# =============================================================================


@router.get("/pipeline/deals/export", dependencies=_wa_com_view)
async def export_deals_csv(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Export all deals as CSV."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WADealRepository(db)
    items, _ = await repo.list_by_tenant(tenant_id=tenant_id, skip=0, limit=10000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Título",
            "Etapa",
            "Valor",
            "Moneda",
            "Contacto",
            "Teléfono",
            "Fecha cierre esperada",
            "Notas",
            "Fecha creación",
        ]
    )

    for d in items:
        writer.writerow(
            [
                d.title,
                d.stage.name if d.stage else "",
                str(d.value),
                d.currency,
                d.contact.display_name if d.contact else "",
                d.contact.phone_e164 if d.contact else "",
                str(d.expected_close_date) if d.expected_close_date else "",
                d.notes or "",
                d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else "",
            ]
        )

    csv_content = output.getvalue()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=deals_whatsapp.csv"},
    )


@router.get("/pipeline/deals", response_model=WADealListResponse, dependencies=_wa_com_view)
async def list_deals(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    stage: UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> WADealListResponse:
    """List deals for the tenant."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WADealRepository(db)
    items, total = await repo.list_by_tenant(
        tenant_id=tenant_id,
        stage_id=stage,
        skip=skip,
        limit=limit,
    )
    result = [_build_deal_response(d) for d in items]
    return WADealListResponse(items=result, total=total)


@router.post(
    "/pipeline/deals", response_model=WADealResponse, status_code=201, dependencies=_wa_com_manage
)
async def create_deal(
    body: WADealCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WADealResponse:
    """Create a deal."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WADealRepository(db)
    deal = await repo.create(
        {
            "tenant_id": tenant_id,
            "stage_id": body.stage_id,
            "title": body.title,
            "contact_id": body.contact_id,
            "conversation_id": body.conversation_id,
            "value": body.value,
            "currency": body.currency,
            "assignee_user_id": body.assignee_user_id,
            "expected_close_date": body.expected_close_date,
            "notes": body.notes,
        }
    )
    await db.commit()
    deal = await repo.get_with_relations(deal.id)
    resp = _build_deal_response(deal)
    return resp


@router.patch(
    "/pipeline/deals/{deal_id}", response_model=WADealResponse, dependencies=_wa_com_manage
)
async def update_deal(
    deal_id: UUID,
    body: WADealUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WADealResponse:
    """Update a deal."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WADealRepository(db)
    deal = await repo.get_by_id(deal_id)
    verify_tenant_ownership(deal, tenant_id, "Deal")
    updates = body.model_dump(exclude_unset=True)
    if updates:
        deal = await repo.update(deal_id, updates)
    await db.commit()
    deal = await repo.get_with_relations(deal_id)
    resp = _build_deal_response(deal)
    return resp


@router.post(
    "/pipeline/deals/{deal_id}/move", response_model=WADealResponse, dependencies=_wa_com_manage
)
async def move_deal(
    deal_id: UUID,
    body: WADealMoveRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WADealResponse:
    """Move a deal to a different pipeline stage."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WADealRepository(db)
    deal = await repo.get_by_id(deal_id)
    verify_tenant_ownership(deal, tenant_id, "Deal")

    stage_repo = WAPipelineStageRepository(db)
    new_stage = await stage_repo.get_by_id(body.stage_id)
    if not new_stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    update_data: dict = {"stage_id": body.stage_id}
    if new_stage.is_won or new_stage.is_lost:
        update_data["closed_at"] = datetime.now(UTC)

    await repo.update(deal_id, update_data)
    await db.commit()
    deal = await repo.get_with_relations(deal_id)
    resp = _build_deal_response(deal)
    return resp


@router.delete("/pipeline/deals/{deal_id}", status_code=204, dependencies=_wa_com_manage)
async def delete_deal(
    deal_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a deal."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WADealRepository(db)
    deal = await repo.get_by_id(deal_id)
    verify_tenant_ownership(deal, tenant_id, "Deal")
    await repo.delete(deal_id)
    await db.commit()


# =============================================================================
# Pipeline Analytics
# =============================================================================


@router.get(
    "/pipeline/analytics", response_model=WAPipelineAnalyticsResponse, dependencies=_wa_com_view
)
async def get_pipeline_analytics(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAPipelineAnalyticsResponse:
    """Get pipeline analytics summary."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WADealRepository(db)
    analytics = await repo.get_analytics(tenant_id)
    return WAPipelineAnalyticsResponse(
        total_deals=analytics["total_deals"],
        total_value=analytics["total_value"],
        won_deals=analytics["won_deals"],
        won_value=analytics["won_value"],
        lost_deals=analytics["lost_deals"],
        conversion_rate=analytics["conversion_rate"],
        stages=[WAPipelineStageResponse(**s) for s in analytics["stages"]],
    )


# =============================================================================
# Catalog
# =============================================================================


@router.get("/catalog", response_model=WACatalogItemListResponse, dependencies=_wa_com_view)
async def list_catalog_items(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> WACatalogItemListResponse:
    """List catalog items."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACatalogItemRepository(db)
    items, total = await repo.list_by_tenant(
        tenant_id=tenant_id,
        status=status_filter,
        category=category,
        search=search,
        skip=skip,
        limit=limit,
    )
    return WACatalogItemListResponse(
        items=[WACatalogItemResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post(
    "/catalog", response_model=WACatalogItemResponse, status_code=201, dependencies=_wa_com_manage
)
async def create_catalog_item(
    body: WACatalogItemCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACatalogItemResponse:
    """Create a catalog item."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACatalogItemRepository(db)
    item = await repo.create(
        {
            "tenant_id": tenant_id,
            **body.model_dump(),
        }
    )
    await db.commit()
    return WACatalogItemResponse.model_validate(item)


@router.get("/catalog/{item_id}", response_model=WACatalogItemResponse, dependencies=_wa_com_view)
async def get_catalog_item(
    item_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACatalogItemResponse:
    """Get a single catalog item."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACatalogItemRepository(db)
    item = await repo.get_by_id(item_id)
    verify_tenant_ownership(item, tenant_id, "Catalog item")
    return WACatalogItemResponse.model_validate(item)


@router.patch(
    "/catalog/{item_id}", response_model=WACatalogItemResponse, dependencies=_wa_com_manage
)
async def update_catalog_item(
    item_id: UUID,
    body: WACatalogItemUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WACatalogItemResponse:
    """Update a catalog item."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACatalogItemRepository(db)
    item = await repo.get_by_id(item_id)
    verify_tenant_ownership(item, tenant_id, "Catalog item")
    updates = body.model_dump(exclude_unset=True)
    if updates:
        item = await repo.update(item_id, updates)
    await db.commit()
    return WACatalogItemResponse.model_validate(item)


@router.delete("/catalog/{item_id}", status_code=204, dependencies=_wa_com_manage)
async def delete_catalog_item(
    item_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a catalog item."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WACatalogItemRepository(db)
    item = await repo.get_by_id(item_id)
    verify_tenant_ownership(item, tenant_id, "Catalog item")
    await repo.delete(item_id)
    await db.commit()


# =============================================================================
# Orders
# =============================================================================


@router.get("/orders", response_model=WAOrderListResponse, dependencies=_wa_com_view)
async def list_orders(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> WAOrderListResponse:
    """List orders."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAOrderRepository(db)
    items, total = await repo.list_by_tenant(
        tenant_id=tenant_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    result = []
    for o in items:
        resp = WAOrderResponse(
            id=o.id,
            status=o.status,
            total=o.total,
            currency=o.currency,
            notes=o.notes,
            contact_id=o.contact_id,
            conversation_id=o.conversation_id,
            items=[WAOrderItemResponse.model_validate(i) for i in o.items],
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        if o.contact:
            resp.contact_name = o.contact.display_name
            resp.contact_phone = o.contact.phone_e164
        result.append(resp)
    return WAOrderListResponse(items=result, total=total)


@router.post(
    "/orders", response_model=WAOrderResponse, status_code=201, dependencies=_wa_com_manage
)
async def create_order(
    body: WAOrderCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAOrderResponse:
    """Create an order."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAOrderRepository(db)

    total = Decimal("0")
    order_items = []
    for item_data in body.items:
        qty = item_data.get("quantity", 1)
        unit_price = Decimal(str(item_data.get("unit_price", 0)))
        total += unit_price * qty
        order_items.append(
            {
                "name": item_data.get("name", "Item"),
                "catalog_item_id": item_data.get("catalog_item_id"),
                "quantity": qty,
                "unit_price": unit_price,
            }
        )

    order = await repo.create(
        {
            "tenant_id": tenant_id,
            "contact_id": body.contact_id,
            "conversation_id": body.conversation_id,
            "status": "pending",
            "total": total,
            "notes": body.notes,
        }
    )
    await db.flush()

    for oi_data in order_items:
        db.add(WAOrderItem(order_id=order.id, **oi_data))

    await db.commit()
    order = await repo.get_with_items(order.id)

    return WAOrderResponse(
        id=order.id,
        status=order.status,
        total=order.total,
        currency=order.currency,
        notes=order.notes,
        contact_id=order.contact_id,
        conversation_id=order.conversation_id,
        items=[WAOrderItemResponse.model_validate(i) for i in order.items],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("/orders/{order_id}", response_model=WAOrderResponse, dependencies=_wa_com_view)
async def get_order(
    order_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAOrderResponse:
    """Get a single order."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAOrderRepository(db)
    order = await repo.get_with_items(order_id)
    verify_tenant_ownership(order, tenant_id, "Order")
    resp = WAOrderResponse(
        id=order.id,
        status=order.status,
        total=order.total,
        currency=order.currency,
        notes=order.notes,
        contact_id=order.contact_id,
        conversation_id=order.conversation_id,
        items=[WAOrderItemResponse.model_validate(i) for i in order.items],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
    if order.contact:
        resp.contact_name = order.contact.display_name
        resp.contact_phone = order.contact.phone_e164
    return resp


@router.patch("/orders/{order_id}", response_model=WAOrderResponse, dependencies=_wa_com_manage)
async def update_order(
    order_id: UUID,
    body: WAOrderUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAOrderResponse:
    """Update an order status."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAOrderRepository(db)
    order = await repo.get_by_id(order_id)
    verify_tenant_ownership(order, tenant_id, "Order")
    updates = body.model_dump(exclude_unset=True)
    if updates:
        order = await repo.update(order_id, updates)
    await db.commit()
    return await get_order(order_id, current_user_id, db)
