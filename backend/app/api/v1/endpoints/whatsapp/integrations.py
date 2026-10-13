"""WhatsApp automation routes: third-party integrations."""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import http_clients
from app.core.dependencies import (
    get_current_user_id,
    get_db,
    require_feature,
    require_permission,
    require_wa_admin,
)
from app.repositories.whatsapp_repository import WAIntegrationRepository
from app.schemas.whatsapp import (
    WAIntegrationCreateRequest,
    WAIntegrationResponse,
    WAIntegrationUpdateRequest,
)

from ._helpers import _get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()

_wa_int_settings = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.settings.manage")),
]


@router.get("/integrations", dependencies=_wa_int_settings)
async def list_integrations(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """List third-party integrations."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAIntegrationRepository(db)
    items, total = await repo.list_by_tenant(tenant_id)
    return {
        "items": [WAIntegrationResponse.model_validate(i) for i in items],
        "total": total,
    }


@router.post(
    "/integrations",
    response_model=WAIntegrationResponse,
    status_code=201,
    dependencies=_wa_int_settings,
)
async def create_integration(
    body: WAIntegrationCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAIntegrationResponse:
    """Create an integration."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAIntegrationRepository(db)
    integration = await repo.create(
        {
            "tenant_id": tenant_id,
            **body.model_dump(),
        }
    )
    await db.commit()
    return WAIntegrationResponse.model_validate(integration)


@router.patch(
    "/integrations/{integration_id}",
    response_model=WAIntegrationResponse,
    dependencies=_wa_int_settings,
)
async def update_integration(
    integration_id: UUID,
    body: WAIntegrationUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAIntegrationResponse:
    """Update an integration."""
    repo = WAIntegrationRepository(db)
    updates = body.model_dump(exclude_unset=True)
    integration = (
        await repo.update(integration_id, updates)
        if updates
        else await repo.get_by_id(integration_id)
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    await db.commit()
    return WAIntegrationResponse.model_validate(integration)


@router.delete("/integrations/{integration_id}", status_code=204, dependencies=_wa_int_settings)
async def delete_integration(
    integration_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete an integration."""
    repo = WAIntegrationRepository(db)
    deleted = await repo.delete(integration_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    await db.commit()


@router.post("/integrations/{integration_id}/test", dependencies=_wa_int_settings)
async def test_integration(
    integration_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Test an integration connection."""
    repo = WAIntegrationRepository(db)
    integration = await repo.get_by_id(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    # Simple connectivity test based on type
    config = integration.config or {}
    if "url" in config or "api_url" in config:
        test_url = config.get("url") or config.get("api_url")
        try:
            client = http_clients.whatsapp_client
            if not client:
                raise HTTPException(status_code=503, detail="HTTP client not initialized")
            resp = await client.get(test_url)
            success = 200 <= resp.status_code < 400
        except HTTPException:
            raise
        except (httpx.HTTPError, OSError) as e:
            return {"success": False, "error": str(e)}
        await repo.update(
            integration_id,
            {
                "status_message": "OK" if success else f"HTTP {resp.status_code}",
                "last_sync_at": datetime.now(UTC),
            },
        )
        await db.commit()
        return {"success": success, "status_code": resp.status_code}
    return {"success": True, "message": "No URL to test — config saved"}
