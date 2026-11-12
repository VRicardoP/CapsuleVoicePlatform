"""WhatsApp automation routes: outgoing webhook configurations and logs."""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import http_clients
from app.core.dependencies import (
    get_current_user_id,
    get_db,
    require_feature,
    require_permission,
    require_wa_admin,
)
from app.repositories.whatsapp_repository import (
    WAWebhookConfigRepository,
    WAWebhookLogRepository,
)
from app.schemas.whatsapp import (
    WAWebhookConfigCreateRequest,
    WAWebhookConfigResponse,
    WAWebhookConfigUpdateRequest,
    WAWebhookLogResponse,
)

from ._helpers import _get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()

_wa_wh_settings = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.settings.manage")),
]


@router.get(
    "/webhooks/configs", response_model=list[WAWebhookConfigResponse], dependencies=_wa_wh_settings
)
async def list_webhook_configs(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WAWebhookConfigResponse]:
    """List outgoing webhook configurations."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAWebhookConfigRepository(db)
    items = await repo.list_by_tenant(tenant_id)
    return [WAWebhookConfigResponse.model_validate(w) for w in items]


@router.post(
    "/webhooks/configs",
    response_model=WAWebhookConfigResponse,
    status_code=201,
    dependencies=_wa_wh_settings,
)
async def create_webhook_config(
    body: WAWebhookConfigCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAWebhookConfigResponse:
    """Create a webhook configuration."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAWebhookConfigRepository(db)
    webhook = await repo.create(
        {
            "tenant_id": tenant_id,
            **body.model_dump(),
        }
    )
    await db.commit()
    return WAWebhookConfigResponse.model_validate(webhook)


@router.patch(
    "/webhooks/configs/{webhook_id}",
    response_model=WAWebhookConfigResponse,
    dependencies=_wa_wh_settings,
)
async def update_webhook_config(
    webhook_id: UUID,
    body: WAWebhookConfigUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAWebhookConfigResponse:
    """Update a webhook configuration."""
    repo = WAWebhookConfigRepository(db)
    updates = body.model_dump(exclude_unset=True)
    webhook = (
        await repo.update(webhook_id, updates) if updates else await repo.get_by_id(webhook_id)
    )
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.commit()
    return WAWebhookConfigResponse.model_validate(webhook)


@router.delete("/webhooks/configs/{webhook_id}", status_code=204, dependencies=_wa_wh_settings)
async def delete_webhook_config(
    webhook_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a webhook configuration."""
    repo = WAWebhookConfigRepository(db)
    deleted = await repo.delete(webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.commit()


@router.get("/webhooks/configs/{webhook_id}/logs", dependencies=_wa_wh_settings)
async def list_webhook_logs(
    webhook_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List delivery logs for a webhook."""
    repo = WAWebhookLogRepository(db)
    items, total = await repo.list_by_webhook(webhook_id, skip=skip, limit=limit)
    return {
        "items": [WAWebhookLogResponse.model_validate(log) for log in items],
        "total": total,
    }


@router.post("/webhooks/configs/{webhook_id}/test", dependencies=_wa_wh_settings)
async def test_webhook(
    webhook_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Send a test payload to a webhook endpoint."""
    repo = WAWebhookConfigRepository(db)
    webhook = await repo.get_by_id(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_payload = {
        "event": "test",
        "timestamp": datetime.now(UTC).isoformat(),
        "data": {"message": "Test webhook from CapsuleCorp"},
    }
    try:
        client = http_clients.whatsapp_client
        if not client:
            raise HTTPException(status_code=503, detail="HTTP client not initialized")
        headers = dict(webhook.headers or {})
        headers["Content-Type"] = "application/json"
        resp = await client.post(webhook.url, json=test_payload, headers=headers)
        success = 200 <= resp.status_code < 300
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}

    # Log the test
    log_repo = WAWebhookLogRepository(db)
    await log_repo.create(
        {
            "webhook_id": webhook_id,
            "event_type": "test",
            "payload": test_payload,
            "response_code": resp.status_code,
            "response_body": resp.text[:500],
            "success": success,
        }
    )
    await db.commit()

    return {"success": success, "status_code": resp.status_code}
