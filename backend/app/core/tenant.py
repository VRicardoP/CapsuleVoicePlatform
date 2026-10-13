"""Shared tenant resolution helpers."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.tenant_repository import TenantRepository


async def get_active_tenant_id(
    db: AsyncSession,
    *,
    organization_id: UUID | None = None,
    user_id: UUID | str | None = None,
    status_code: int = 404,
    detail: str = "No active tenant",
) -> UUID:
    """Get the organization ID for the current context.

    Resolution order:
    1. If ``organization_id`` is provided, use it directly.
    2. If ``user_id`` is provided, look up the user's ``organization_id``.
    3. Fallback: first active organization (legacy single-tenant behaviour).

    Callers that have an authenticated user should always pass
    ``user_id`` or ``organization_id`` to avoid returning the wrong org.
    """
    repo = TenantRepository(db)

    if organization_id:
        return organization_id

    if user_id:
        tenant_id = await repo.get_tenant_id_for_user(user_id)
        if tenant_id:
            return tenant_id

    # Legacy fallback — single-tenant deployments
    tenant_id = await repo.get_active_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=status_code, detail=detail)
    return tenant_id


def verify_tenant_ownership(
    entity,
    tenant_id: UUID | str,
    entity_name: str = "Resource",
) -> None:
    """Verify an entity belongs to the expected tenant.

    Raises 404 if the entity is None or belongs to a different tenant.
    Uses 404 (not 403) to avoid leaking resource existence to other tenants.
    """
    if entity is None:
        raise HTTPException(status_code=404, detail=f"{entity_name} not found")
    entity_tenant = getattr(entity, "tenant_id", None) or getattr(entity, "organization_id", None)
    if entity_tenant and str(entity_tenant) != str(tenant_id):
        raise HTTPException(status_code=404, detail=f"{entity_name} not found")
