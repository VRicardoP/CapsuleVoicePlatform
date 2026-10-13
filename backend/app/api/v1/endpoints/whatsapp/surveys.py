"""WhatsApp automation routes: surveys and survey responses."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db, require_wa_manager
from app.repositories.whatsapp_repository import (
    WASurveyRepository,
    WASurveyResponseRepository,
)
from app.schemas.whatsapp import (
    WASurveyAnswerResponse,
    WASurveyCreateRequest,
    WASurveyUpdateRequest,
)
from app.schemas.whatsapp import (
    WASurveyResponse as WASurveySchemaResponse,
)

from ._helpers import _get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/surveys")
async def list_surveys(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List surveys."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WASurveyRepository(db)
    items, total = await repo.list_by_tenant(tenant_id, skip=skip, limit=limit)
    return {
        "items": [WASurveySchemaResponse.model_validate(s) for s in items],
        "total": total,
    }


@router.post("/surveys", response_model=WASurveySchemaResponse, status_code=201)
async def create_survey(
    body: WASurveyCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WASurveySchemaResponse:
    """Create a survey."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WASurveyRepository(db)
    survey = await repo.create(
        {
            "tenant_id": tenant_id,
            **body.model_dump(),
        }
    )
    await db.commit()
    return WASurveySchemaResponse.model_validate(survey)


@router.patch("/surveys/{survey_id}", response_model=WASurveySchemaResponse)
async def update_survey(
    survey_id: UUID,
    body: WASurveyUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WASurveySchemaResponse:
    """Update a survey."""
    repo = WASurveyRepository(db)
    updates = body.model_dump(exclude_unset=True)
    survey = await repo.update(survey_id, updates) if updates else await repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    await db.commit()
    return WASurveySchemaResponse.model_validate(survey)


@router.delete("/surveys/{survey_id}", status_code=204)
async def delete_survey(
    survey_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a survey."""
    repo = WASurveyRepository(db)
    deleted = await repo.delete(survey_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Survey not found")
    await db.commit()


@router.get("/surveys/{survey_id}/responses")
async def list_survey_responses(
    survey_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List responses for a survey."""
    repo = WASurveyResponseRepository(db)
    items, total = await repo.list_by_survey(survey_id, skip=skip, limit=limit)
    return {
        "items": [WASurveyAnswerResponse.model_validate(r) for r in items],
        "total": total,
    }
