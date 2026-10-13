"""
User management endpoints.
RGPD compliant user data access and modification.
"""

import logging
from typing import Annotated
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import Principal
from app.core.dependencies import (
    get_current_principal,
    get_current_user_id,
    get_db,
    require_admin,
    require_permission,
    require_recent_auth,
)
from app.core.security import get_password_hash, verify_password_async
from app.repositories.gdpr_repository import AuditLogRepository
from app.repositories.user_repository import (
    OrganizationRepository,
    UserPreferencesRepository,
    UserRepository,
    UserSessionRepository,
)
from app.schemas.users import (
    PasswordChangeRequest,
    UserCreateRequest,
    UserListResponse,
    UserPreferences,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


# === ENDPOINTS ===


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current user's profile with decrypted PII.",
)
async def get_current_user(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Get current user's profile.

    RGPD Art. 15: Right of access - user can see their own data.
    """
    try:
        user_repo = UserRepository(db)
        prefs_repo = UserPreferencesRepository(db)
        uid = UUID(current_user_id)

        user_data = await user_repo.get_decrypted_user_data(uid)
        if not user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        preferences = None
        try:
            prefs_data = await prefs_repo.get_preferences(uid)
            if prefs_data:
                preferences = UserPreferences(**prefs_data)
        except (SQLAlchemyError, ValueError) as e:
            logger.warning("Failed to load preferences for user %s: %s", current_user_id, e)

        return UserResponse(**user_data, preferences=preferences)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error("Error in get_current_user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user data",
        )


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Update current user's profile.",
)
async def update_current_user(
    request: Request,
    update_data: UserUpdate,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Update current user's profile.

    RGPD Art. 16: Right to rectification.
    """
    user_repo = UserRepository(db)
    prefs_repo = UserPreferencesRepository(db)
    audit_repo = AuditLogRepository(db)

    old_data = await user_repo.get_decrypted_user_data(current_user_id)
    if not old_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_fields = update_data.model_dump(exclude_unset=True)
    if not update_fields:
        return UserResponse(**old_data)

    # Update encrypted PII fields + email_hash for login lookup
    if "email" in update_fields and update_fields["email"]:
        import hashlib

        new_email = update_fields["email"]
        await prefs_repo.update_encrypted_field(current_user_id, "email", new_email)
        new_hash = hashlib.sha256(new_email.lower().encode()).hexdigest()
        await user_repo.update(current_user_id, {"email_hash": new_hash})

    if "name" in update_fields:
        await prefs_repo.update_encrypted_field(current_user_id, "name", update_fields["name"])

    # Update preferences
    if "preferences" in update_fields and update_fields["preferences"]:
        prefs = update_fields["preferences"]
        await prefs_repo.upsert_preferences(
            current_user_id,
            visible_modules=prefs.get("visibleModules", []),
            theme=prefs.get("theme", "dark"),
        )

    # Audit log
    client_ip = request.client.host if request.client else None
    try:
        await audit_repo.log_action(
            action="UPDATE",
            entity_type="users",
            user_id=current_user_id,
            entity_id=current_user_id,
            changed_fields={"updated_fields": list(update_fields.keys())},
            ip_address=client_ip,
        )
    except SQLAlchemyError:
        pass

    await db.commit()

    updated_data = await user_repo.get_decrypted_user_data(current_user_id)
    preferences = None
    try:
        prefs_data = await prefs_repo.get_preferences(current_user_id)
        if prefs_data:
            preferences = UserPreferences(**prefs_data)
    except (SQLAlchemyError, ValueError) as e:
        logger.warning("Failed to read back preferences for user %s: %s", current_user_id, e)

    return UserResponse(**updated_data, preferences=preferences)


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="Change current user's password.",
    dependencies=[Depends(require_recent_auth())],
)
async def change_password(
    request: Request,
    password_data: PasswordChangeRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Change current user's password."""
    user_repo = UserRepository(db)
    audit_repo = AuditLogRepository(db)

    user = await user_repo.get_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not await verify_password_async(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    await user_repo.update(
        current_user_id, {"password_hash": get_password_hash(password_data.new_password)}
    )

    # Invalidate all existing sessions (security: revoke tokens after credential change)
    session_repo = UserSessionRepository(db)
    await session_repo.invalidate_all_user_sessions(current_user_id, reason="password_changed")

    client_ip = request.client.host if request.client else None
    await audit_repo.log_action(
        action="PASSWORD_CHANGE",
        entity_type="users",
        user_id=current_user_id,
        entity_id=current_user_id,
        ip_address=client_ip,
    )
    await db.commit()


@router.get(
    "/me/features",
    summary="Get tenant features",
    description="Returns enabled features for the user's tenant.",
)
async def get_tenant_features(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return feature flags for the user's tenant."""
    from app.repositories.tenant_repository import TenantRepository

    tenant_repo = TenantRepository(db)
    org_id = await tenant_repo.get_tenant_id_for_user(current_user_id)
    org_repo = OrganizationRepository(db)
    features = await org_repo.get_tenant_features(org_id=org_id)
    return {"features": features}


# === ADMIN ENDPOINTS ===


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users (Admin)",
    dependencies=[Depends(require_admin), Depends(require_permission("users.view"))],
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
    active_only: bool = True,
) -> UserListResponse:
    """List all users (admin only). Scoped to caller's organization.

    Tenant filter, role filter and pagination are applied in SQL so the
    `total` count is correct and pages are not silently clipped after the fact.
    Decrypted name + email are returned so the admin table can render them.
    """
    user_repo = UserRepository(db)

    rows, total = await user_repo.list_users_with_pii(
        organization_id=principal.organization_id,
        skip=skip,
        limit=limit,
        role=role,
        active_only=active_only,
    )

    items = [
        UserResponse(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            company=row.get("company"),
            role=row["role"],
            organization_id=row.get("organization_id"),
            is_active=row["is_active"],
            email_verified=bool(row.get("email_verified")),
            two_factor_enabled=bool(row.get("two_factor_enabled")),
            last_login_at=row.get("last_login_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]

    return UserListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (Admin)",
    dependencies=[Depends(require_admin), Depends(require_permission("users.view"))],
)
async def get_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> UserResponse:
    """Get user by ID (admin only). Enforces tenant isolation."""
    user_repo = UserRepository(db)

    # Tenant isolation: non-superadmin can only view users in their own org
    if principal.organization_id is not None:
        target_user = await user_repo.get_by_id(user_id)
        if not target_user or target_user.organization_id != principal.organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_data = await user_repo.get_decrypted_user_data(user_id)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(**user_data)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user (Admin)",
    dependencies=[
        Depends(require_permission("users.manage")),
        Depends(require_recent_auth()),
    ],
)
async def create_user(
    request: Request,
    user_data: UserCreateRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    caller_role: Annotated[str, Depends(require_admin)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Create new user (admin only)."""
    # Prevent privilege escalation: only superadmin can create superadmin.
    # client_admin can create other client_admin users within their own org —
    # the tenant scoping at organization_id below keeps them inside it.
    if user_data.role == "superadmin" and caller_role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can create superadmin users",
        )
    if user_data.role == "client_admin" and caller_role not in (
        "superadmin",
        "client_admin",
        "admin",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to create admin users",
        )

    user_repo = UserRepository(db)
    audit_repo = AuditLogRepository(db)

    existing = await user_repo.get_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    password_hash = get_password_hash(user_data.password)
    user = await user_repo.create_with_encryption(
        email=user_data.email,
        password_hash=password_hash,
        name=user_data.name,
        role=user_data.role,
        organization_id=principal.organization_id,
    )

    client_ip = request.client.host if request.client else None
    await audit_repo.log_action(
        action="INSERT",
        entity_type="users",
        user_id=current_user_id,
        entity_id=user.id,
        details={"role": user_data.role},
        ip_address=client_ip,
    )
    await db.commit()

    user_decrypted = await user_repo.get_decrypted_user_data(user.id)
    return UserResponse(**user_decrypted)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate user (Admin)",
    dependencies=[
        Depends(require_admin),
        Depends(require_permission("users.manage")),
        Depends(require_recent_auth()),
    ],
)
async def deactivate_user(
    request: Request,
    user_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Deactivate user account (admin only). Enforces tenant isolation."""
    if user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account"
        )

    user_repo = UserRepository(db)
    audit_repo = AuditLogRepository(db)

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Tenant isolation: non-superadmin can only deactivate users in their own org
    if principal.organization_id is not None and user.organization_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await user_repo.soft_delete(user_id)
    await user_repo.update(user_id, {"is_active": False})
    session_repo = UserSessionRepository(db)
    await session_repo.invalidate_all_user_sessions(user_id, reason="user_deactivated")

    client_ip = request.client.host if request.client else None
    await audit_repo.log_action(
        action="DELETE",
        entity_type="users",
        user_id=current_user_id,
        entity_id=user_id,
        ip_address=client_ip,
    )
    await db.commit()
