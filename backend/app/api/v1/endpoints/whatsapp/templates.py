"""WhatsApp template management routes."""

import logging
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user_id,
    get_db,
    require_feature,
    require_permission,
    require_wa_manager,
)
from app.core.tenant import verify_tenant_ownership
from app.repositories.whatsapp_repository import WATemplateRepository
from app.schemas.whatsapp import (
    WATemplateCreateRequest,
    WATemplateListResponse,
    WATemplateResponse,
    WATemplateUpdateRequest,
)
from app.services.whatsapp_service import WhatsAppAPIError, whatsapp_service

from ._helpers import _get_tenant_id, _get_tenant_settings, _get_wa_token

router = APIRouter()
logger = logging.getLogger(__name__)

_wa_tpl_view = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.templates.view")),
]
_wa_tpl_manage = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.templates.manage")),
]


@router.get("/templates", response_model=WATemplateListResponse, dependencies=_wa_tpl_view)
async def list_templates(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> WATemplateListResponse:
    """List templates for the tenant."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WATemplateRepository(db)
    items, total = await repo.list_by_tenant(
        tenant_id=tenant_id,
        status=status_filter,
        category=category,
        skip=skip,
        limit=limit,
    )
    return WATemplateListResponse(
        items=[WATemplateResponse.model_validate(t) for t in items],
        total=total,
    )


@router.post("/templates/sync", dependencies=_wa_tpl_manage)
async def sync_templates_from_meta(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Sync templates from Meta WhatsApp API into local database."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    ts = await _get_tenant_settings(db, tenant_id)
    token = _get_wa_token(ts)

    try:
        meta_templates = await whatsapp_service.fetch_templates(
            waba_id=ts.business_account_id,
            token=token,
        )
    except WhatsAppAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Meta API error: {e.message}. "
            "Verify the token has whatsapp_business_management permission.",
        ) from e

    repo = WATemplateRepository(db)
    created = 0
    updated = 0

    meta_ids: set[str] = set()

    for mt in meta_templates:
        parsed = whatsapp_service.parse_meta_template(mt)
        meta_ids.add(parsed["meta_template_id"])
        existing = await repo.get_by_meta_id(tenant_id, parsed["meta_template_id"])

        # Fallback: match by (name, language) for templates created before sync existed
        if not existing:
            existing = await repo.get_by_name_lang(tenant_id, parsed["name"], parsed["language"])

        update_fields = {
            "status": parsed["status"],
            "category": parsed["category"],
            "header_type": parsed["header_type"],
            "header_content": parsed["header_content"],
            "body_text": parsed["body_text"],
            "footer": parsed["footer"],
            "buttons": parsed["buttons"],
            "meta_rejected_reason": parsed["meta_rejected_reason"],
            "meta_template_id": parsed["meta_template_id"],
        }

        if existing:
            await repo.update(existing.id, update_fields)
            updated += 1
        else:
            await repo.create({"tenant_id": tenant_id, **parsed})
            created += 1

    # Eliminar localmente las plantillas aprobadas/pendientes que ya no existen en Meta
    deleted = await repo.delete_stale_synced(tenant_id, meta_ids)

    await db.commit()
    return {
        "synced": len(meta_templates),
        "created": created,
        "updated": updated,
        "deleted": deleted,
    }


@router.post(
    "/templates", response_model=WATemplateResponse, status_code=201, dependencies=_wa_tpl_manage
)
async def create_template(
    body: WATemplateCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WATemplateResponse:
    """Create a message template (draft)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WATemplateRepository(db)
    template = await repo.create(
        {
            "tenant_id": tenant_id,
            "name": body.name,
            "language": body.language,
            "category": body.category,
            "status": "draft",
            "header_type": body.header_type,
            "header_content": body.header_content,
            "body_text": body.body_text,
            "footer": body.footer,
            "buttons": body.buttons,
            "variables": body.variables,
        }
    )
    await db.commit()
    return WATemplateResponse.model_validate(template)


@router.get(
    "/templates/{template_id}", response_model=WATemplateResponse, dependencies=_wa_tpl_view
)
async def get_template(
    template_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WATemplateResponse:
    """Get a single template."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WATemplateRepository(db)
    template = await repo.get_by_id(template_id)
    verify_tenant_ownership(template, tenant_id, "Template")
    return WATemplateResponse.model_validate(template)


@router.patch(
    "/templates/{template_id}", response_model=WATemplateResponse, dependencies=_wa_tpl_manage
)
async def update_template(
    template_id: UUID,
    body: WATemplateUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WATemplateResponse:
    """Update a template (only drafts)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WATemplateRepository(db)
    template = await repo.get_by_id(template_id)
    verify_tenant_ownership(template, tenant_id, "Template")
    if template.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft templates can be edited")

    updates = body.model_dump(exclude_unset=True)
    if updates:
        template = await repo.update(template_id, updates)
    await db.commit()
    return WATemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", status_code=204, dependencies=_wa_tpl_manage)
async def delete_template(
    template_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Elimina una plantilla local y, si existe en Meta, también la borra allí."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WATemplateRepository(db)
    template = await repo.get_by_id(template_id)
    verify_tenant_ownership(template, tenant_id, "Template")

    # Si la plantilla existe en Meta, borrarla primero
    if template.meta_template_id:
        ts = await _get_tenant_settings(db, tenant_id)
        token = _get_wa_token(ts)
        try:
            await whatsapp_service.delete_template(
                waba_id=ts.business_account_id,
                template_name=template.name,
                token=token,
            )
        except WhatsAppAPIError as e:
            logger.error("No se pudo borrar la plantilla en Meta: %s", e.message)
            raise HTTPException(status_code=502, detail=f"Meta rechazó el borrado: {e.message}")

    await repo.delete(template_id)
    await db.commit()


@router.post("/templates/upload-media", dependencies=_wa_tpl_manage)
async def upload_template_media(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
    image_url: str = Query(..., description="Public URL of image to upload to Meta"),
) -> dict:
    """Upload an image to Meta for use as template header.

    Downloads the image from the URL and uploads it via Meta Resumable Upload API.
    Returns the file handle needed for IMAGE header templates.
    """
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    ts = await _get_tenant_settings(db, tenant_id)
    token = _get_wa_token(ts)

    try:
        handle = await whatsapp_service.upload_media_for_template(image_url, token)
        return {"handle": handle}
    except WhatsAppAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/templates/{template_id}/submit",
    response_model=WATemplateResponse,
    dependencies=_wa_tpl_manage,
)
async def submit_template(
    template_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WATemplateResponse:
    """Submit a draft template for Meta review."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    ts = await _get_tenant_settings(db, tenant_id)
    token = _get_wa_token(ts)

    repo = WATemplateRepository(db)
    template = await repo.get_by_id(template_id)
    verify_tenant_ownership(template, tenant_id, "Template")
    if template.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft templates can be submitted")

    header_type = template.header_type
    header_content = template.header_content

    # For IMAGE/VIDEO/DOCUMENT headers with a URL, upload to Meta first
    if header_type and header_type.upper() in ("IMAGE", "VIDEO", "DOCUMENT") and header_content:
        if header_content.startswith("http"):
            try:
                handle = await whatsapp_service.upload_media_for_template(header_content, token)
                header_content = handle
            except WhatsAppAPIError as e:
                raise HTTPException(
                    status_code=502, detail=f"Failed to upload header media: {e.message}"
                )

    # Extract body variable examples from template.variables
    body_examples = None
    variables = template.variables or {}
    if variables.get("body_examples"):
        body_examples = variables["body_examples"]

    # Submit to Meta API
    try:
        meta_result = await whatsapp_service.submit_template(
            waba_id=ts.business_account_id,
            name=template.name,
            language=template.language,
            category=template.category,
            body_text=template.body_text,
            token=token,
            header_type=header_type,
            header_content=header_content,
            footer=template.footer,
            buttons=template.buttons.get("buttons") if template.buttons else None,
            body_examples=body_examples,
        )
        meta_template_id = meta_result.get("id")
        update_data: dict = {"status": "pending"}
        if meta_template_id:
            update_data["meta_template_id"] = meta_template_id
    except WhatsAppAPIError as e:
        logger.error("Meta API rejected template: %s", e.message)
        raise HTTPException(status_code=502, detail=f"Meta rechazó la plantilla: {e.message}")
    except (httpx.HTTPError, ValueError, KeyError):
        logger.error("Failed to submit template to Meta", exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to submit template to Meta for review")

    template = await repo.update(template_id, update_data)
    await db.commit()
    return WATemplateResponse.model_validate(template)
