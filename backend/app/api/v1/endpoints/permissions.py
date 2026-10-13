"""
Permission management endpoints for capability-based authorization.

Phase 3: API endpoints that expose the permission system to the frontend.
- GET /permissions/me — current user's authorization context
- GET /permissions/catalog — permission catalog grouped by module (admin only)
- GET /users/{user_id}/permissions — user permissions (admin only)
- PUT /users/{user_id}/permissions — replace user permissions (admin only)
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import FEATURE_KEYS, Principal
from app.core.dependencies import (
    get_current_principal,
    get_db,
)
from app.repositories.permission_repository import PermissionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.permissions import (
    AuthorizationResponse,
    AuthorizationUser,
    ModulePermissions,
    PermissionCatalogResponse,
    PermissionItem,
    UserPermissionEntry,
    UserPermissionsResponse,
    UserPermissionsUpdate,
    UserPermissionsUpdateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /permissions/me — current user's full authorization context
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=AuthorizationResponse,
    summary="Get my authorization context",
    description="Returns features, permissions and role for the current user.",
)
async def get_my_authorization(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthorizationResponse:
    """Return the full authorization context for the authenticated user."""
    features: dict[str, bool] = {}
    if principal.organization_id:
        repo = PermissionRepository(db)
        raw_features = await repo.get_tenant_features(principal.organization_id)
        for module, key in FEATURE_KEYS.items():
            features[module] = raw_features.get(key, False)

    return AuthorizationResponse(
        user=AuthorizationUser(
            id=principal.user_id,
            role=principal.role,
            organization_id=principal.organization_id,
        ),
        features=features,
        permissions=sorted(principal.permissions),
    )


# ---------------------------------------------------------------------------
# GET /permissions/catalog — permission catalog grouped by module
# ---------------------------------------------------------------------------


@router.get(
    "/catalog",
    response_model=PermissionCatalogResponse,
    summary="Get permission catalog",
    description="Returns all permissions grouped by module. Admin only.",
)
async def get_permission_catalog(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PermissionCatalogResponse:
    """Return the permission catalog grouped by module.

    Only client_admin and superadmin can access this endpoint.
    For client_admin, module availability is filtered by tenant features.
    """
    if principal.role not in ("superadmin", "client_admin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    repo = PermissionRepository(db)
    catalog_entries = await repo.get_catalog()

    # Get tenant features for availability check
    tenant_features: dict[str, bool] = {}
    if principal.organization_id:
        raw_features = await repo.get_tenant_features(principal.organization_id)
        for module, key in FEATURE_KEYS.items():
            tenant_features[module] = raw_features.get(key, False)

    # Group by module
    modules_map: dict[str, list[PermissionItem]] = {}
    module_labels: dict[str, str] = {}
    for entry in catalog_entries:
        if entry.module not in modules_map:
            modules_map[entry.module] = []
            # Derive module label from first entry's module name
            module_labels[entry.module] = entry.module.replace("_", " ").title()

        modules_map[entry.module].append(
            PermissionItem(
                key=entry.key,
                label=entry.label,
                description=entry.description,
                parent=entry.parent,
            )
        )

    # Build response with availability info
    modules: list[ModulePermissions] = []
    for module_key, perms in modules_map.items():
        if principal.role == "superadmin":
            available = True
        elif module_key in FEATURE_KEYS:
            available = tenant_features.get(module_key, False)
        else:
            # Core/global permissions are always available
            available = True

        modules.append(
            ModulePermissions(
                key=module_key,
                label=module_labels[module_key],
                available=available,
                permissions=perms,
            )
        )

    return PermissionCatalogResponse(modules=modules)


# ---------------------------------------------------------------------------
# GET /users/{user_id}/permissions — user permissions (admin only)
# ---------------------------------------------------------------------------

# This sub-router is mounted at /users prefix by router.py
user_permissions_router = APIRouter()


@user_permissions_router.get(
    "/{user_id}/permissions",
    response_model=UserPermissionsResponse,
    summary="Get user permissions",
    description="Returns permissions for a specific user. Admin only.",
)
async def get_user_permissions(
    user_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPermissionsResponse:
    """Return permissions for a specific user.

    Access rules:
    - superadmin: can view any user
    - client_admin: can only view users in the same organization
    """
    if principal.role not in ("superadmin", "client_admin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    user_repo = UserRepository(db)
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Tenant isolation: client_admin can only see users in their own org
    if principal.role in ("client_admin", "admin"):
        if target_user.organization_id != principal.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view users in a different organization",
            )

    perm_repo = PermissionRepository(db)

    # Get role template permissions
    role_perms = set(await perm_repo.get_role_template_permissions(target_user.role))

    # Get per-user override permissions (with details: grants AND denies)
    user_perm_details = await perm_repo.get_user_permissions_detailed(user_id)
    deny_keys = {d["key"] for d in user_perm_details if not d.get("granted", True)}

    # Build combined permission list
    entries: list[UserPermissionEntry] = []

    # Role template permissions: mark as denied when the user has a deny override
    for key in sorted(role_perms):
        is_denied = key in deny_keys
        entries.append(
            UserPermissionEntry(
                key=key,
                source="user_deny" if is_denied else "role_template",
                granted=not is_denied,
                granted_by=None,
                created_at=None,
            )
        )

    # User override permissions (additive grants only; denies already shown above)
    for detail in sorted(user_perm_details, key=lambda d: d["key"]):
        if not detail.get("granted", True):
            continue  # deny — already covered by role_template entry above
        if detail["key"] not in role_perms:
            entries.append(
                UserPermissionEntry(
                    key=detail["key"],
                    source="user_override",
                    granted=True,
                    granted_by=detail.get("granted_by"),
                    created_at=detail.get("created_at"),
                )
            )

    return UserPermissionsResponse(
        user_id=user_id,
        role=target_user.role,
        permissions=entries,
    )


# ---------------------------------------------------------------------------
# PUT /users/{user_id}/permissions — replace user permissions (admin only)
# ---------------------------------------------------------------------------


@user_permissions_router.put(
    "/{user_id}/permissions",
    response_model=UserPermissionsUpdateResponse,
    summary="Update user permissions",
    description="Replace all per-user permission overrides. Admin only.",
)
async def update_user_permissions(
    user_id: UUID,
    body: UserPermissionsUpdate,
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPermissionsUpdateResponse:
    """Replace per-user permissions for a specific user.

    Validations:
    - client_admin can only modify users in the same organization
    - client_admin cannot modify superadmin or other client_admin users
    - client_admin cannot grant 'users.permissions.manage' (superadmin only)
    - All permission keys must exist in the catalog
    - Permissions for disabled features are rejected
    """
    if principal.role not in ("superadmin", "client_admin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    user_repo = UserRepository(db)
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # --- Authorization checks for client_admin ---
    is_client_admin = principal.role in ("client_admin", "admin")

    if is_client_admin:
        # Tenant isolation
        if target_user.organization_id != principal.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify users in a different organization",
            )

        # Cannot modify superadmin or other client_admin
        if target_user.role in ("superadmin", "client_admin", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify permissions of admin users",
            )

        # Cannot grant users.permissions.manage
        if "users.permissions.manage" in body.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can grant 'users.permissions.manage'",
            )

    # --- Validate permissions exist in catalog ---
    perm_repo = PermissionRepository(db)
    catalog_entries = await perm_repo.get_catalog()
    valid_keys = {entry.key for entry in catalog_entries}

    all_keys = set(body.permissions) | set(body.denies)
    invalid_keys = all_keys - valid_keys
    if invalid_keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown permission keys: {sorted(invalid_keys)}",
        )

    # --- Reject grants for disabled features (denies on disabled features
    # are a no-op, so we let them through without rejecting them) ---
    if principal.organization_id:
        raw_features = await perm_repo.get_tenant_features(principal.organization_id)
        tenant_features: dict[str, bool] = {}
        for module, key in FEATURE_KEYS.items():
            tenant_features[module] = raw_features.get(key, False)

        for perm_key in body.permissions:
            module = perm_key.split(".")[0]
            feature_key = FEATURE_KEYS.get(module)
            if feature_key is not None and not tenant_features.get(module, False):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Module '{module}' is not enabled for this organization",
                )

    # --- Apply changes ---
    try:
        granted, revoked = await perm_repo.set_user_permissions(
            user_id=user_id,
            permissions=body.permissions,
            denies=body.denies,
            granted_by=principal.user_id,
        )
        await db.commit()
    except SQLAlchemyError as exc:
        logger.error("Failed to update permissions for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update permissions",
        )

    logger.info(
        "Permissions updated for user %s by %s: +%d -%d",
        user_id,
        principal.user_id,
        granted,
        revoked,
    )

    return UserPermissionsUpdateResponse(
        user_id=user_id,
        granted=granted,
        revoked=revoked,
    )
