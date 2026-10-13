"""
API Keys management endpoints.
Create, list, revoke, and provision API keys for service authentication.
"""

import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.dependencies import get_current_user_id, get_db, require_admin
from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.auth import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyInfo,
    APIKeyProvisionRequest,
    APIKeyProvisionResponse,
    APIKeyRevokeRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API Key",
)
async def create_api_key(
    request: APIKeyCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _admin: Annotated[str, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIKeyCreateResponse:
    """Create a new API key for service-to-service authentication."""
    repo = ApiKeyRepository(db)

    allowed_ips_literal = None
    if request.allowed_ips:
        allowed_ips_literal = "{" + ",".join(request.allowed_ips) + "}"

    try:
        result = await repo.create_api_key(
            client_type=request.client_type,
            service_name=request.service_name,
            service_id=request.service_id,
            description=request.description,
            allowed_ips=allowed_ips_literal,
            expires_days=request.expires_days,
            created_by=current_user_id,
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create API key"
            )

        await db.commit()
        api_key, api_key_id, key_prefix = result

        expires_at = None
        if request.expires_days:
            expires_at = datetime.now(UTC) + timedelta(days=request.expires_days)

        return APIKeyCreateResponse(
            api_key=api_key,
            api_key_id=api_key_id,
            key_prefix=key_prefix,
            client_type=request.client_type,
            service_name=request.service_name,
            service_id=request.service_id or f"{request.service_name}-{key_prefix[-8:]}",
            expires_at=expires_at,
        )
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create API key: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create API key"
        )


@router.get(
    "/api-keys",
    response_model=list[APIKeyInfo],
    summary="List API Keys",
)
async def list_api_keys(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _admin: Annotated[str, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_revoked: bool = False,
) -> list[APIKeyInfo]:
    """List all API keys without revealing actual key values."""
    repo = ApiKeyRepository(db)
    rows = await repo.list_api_keys(include_revoked=include_revoked)
    return [APIKeyInfo(**row) for row in rows]


@router.delete(
    "/api-keys/{api_key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API Key",
)
async def revoke_api_key(
    api_key_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _admin: Annotated[str, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    revoke_data: APIKeyRevokeRequest | None = None,
) -> None:
    """Revoke an API key permanently."""
    repo = ApiKeyRepository(db)
    reason = revoke_data.reason if revoke_data else "Manual revocation"

    revoked = await repo.revoke_api_key(api_key_id, reason, current_user_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found or already revoked"
        )

    await db.commit()


@router.post(
    "/provision-api-key",
    response_model=APIKeyProvisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision API Key (Service-to-Service)",
)
async def provision_api_key(
    request: APIKeyProvisionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIKeyProvisionResponse:
    """Provision an API key for a service using a pre-shared secret."""
    if not settings.api_key_provision_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key provisioning is not configured.",
        )

    if not hmac.compare_digest(
        request.provision_secret.encode(), settings.api_key_provision_secret.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid provision secret"
        )

    repo = ApiKeyRepository(db)

    if request.service_id and await repo.service_id_exists(request.service_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service ID '{request.service_id}' already has an active API key",
        )

    try:
        result = await repo.create_api_key(
            client_type=request.client_type,
            service_name=request.service_name,
            service_id=request.service_id,
            description=request.description or f"Provisioned {request.client_type} service",
            allowed_ips=None,
            expires_days=None,
            created_by=None,
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create API key"
            )

        await db.commit()
        api_key, api_key_id, key_prefix = result

        return APIKeyProvisionResponse(
            api_key=api_key,
            api_key_id=api_key_id,
            key_prefix=key_prefix,
            client_type=request.client_type,
            service_name=request.service_name,
            service_id=request.service_id or f"{request.service_name}-{key_prefix[-8:]}",
            expires_at=None,
        )
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to provision API key: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to provision API key"
        )
