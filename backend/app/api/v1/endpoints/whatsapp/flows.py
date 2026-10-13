"""WhatsApp automation routes: automation flows."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db, require_wa_manager
from app.repositories.whatsapp_repository import WAFlowRepository
from app.schemas.whatsapp import (
    WAFlowCreateRequest,
    WAFlowResponse,
    WAFlowUpdateRequest,
)

from ._helpers import _get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/flows")
async def list_flows(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List automation flows."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAFlowRepository(db)
    items, total = await repo.list_by_tenant(tenant_id, skip=skip, limit=limit)
    return {
        "items": [WAFlowResponse.model_validate(f) for f in items],
        "total": total,
    }


@router.post("/flows", response_model=WAFlowResponse, status_code=201)
async def create_flow(
    body: WAFlowCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAFlowResponse:
    """Create an automation flow."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAFlowRepository(db)
    flow = await repo.create(
        {
            "tenant_id": tenant_id,
            **body.model_dump(),
        }
    )
    await db.commit()
    return WAFlowResponse.model_validate(flow)


@router.patch("/flows/{flow_id}", response_model=WAFlowResponse)
async def update_flow(
    flow_id: UUID,
    body: WAFlowUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAFlowResponse:
    """Update a flow."""
    repo = WAFlowRepository(db)
    updates = body.model_dump(exclude_unset=True)
    flow = await repo.update(flow_id, updates) if updates else await repo.get_by_id(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    await db.commit()
    return WAFlowResponse.model_validate(flow)


@router.delete("/flows/{flow_id}", status_code=204)
async def delete_flow(
    flow_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a flow."""
    repo = WAFlowRepository(db)
    deleted = await repo.delete(flow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Flow not found")
    await db.commit()


@router.post("/flows/{flow_id}/activate", response_model=WAFlowResponse)
async def activate_flow(
    flow_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAFlowResponse:
    """Activate/deactivate a flow (toggle)."""
    repo = WAFlowRepository(db)
    flow = await repo.get_by_id(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    flow = await repo.update(flow_id, {"is_active": not flow.is_active})
    await db.commit()
    return WAFlowResponse.model_validate(flow)
