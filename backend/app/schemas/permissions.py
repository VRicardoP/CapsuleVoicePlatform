"""Permission-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PermissionItem(BaseModel):
    """Single permission entry in the catalog."""

    key: str
    label: str
    description: str | None = None
    parent: str | None = None

    model_config = {"from_attributes": True}


class ModulePermissions(BaseModel):
    """Permissions grouped by module for the catalog endpoint."""

    key: str
    label: str
    available: bool
    permissions: list[PermissionItem]


class PermissionCatalogResponse(BaseModel):
    """Full permission catalog response."""

    modules: list[ModulePermissions]


class UserPermissionEntry(BaseModel):
    """Single permission assigned to (or denied for) a user.

    source:
      - "role_template": granted by the role, not overridden for this user
      - "user_override": additive grant on top of the role
      - "user_deny": role permission explicitly revoked for this user
    """

    key: str
    source: str
    granted: bool = True  # False when source == "user_deny"
    granted_by: UUID | None = None
    created_at: datetime | None = None


class UserPermissionsResponse(BaseModel):
    """Permissions for a specific user."""

    user_id: UUID
    role: str
    permissions: list[UserPermissionEntry]


class UserPermissionsUpdate(BaseModel):
    """Request to replace user permission overrides.

    - `permissions`: additive grants (permissions to have on top of the role)
    - `denies`: role-template permissions to revoke for this user
    """

    permissions: list[str] = Field(
        default_factory=list,
        description="Permission keys to grant (beyond the role template)",
    )
    denies: list[str] = Field(
        default_factory=list,
        description="Role-template permission keys to revoke for this user",
    )


class UserPermissionsUpdateResponse(BaseModel):
    """Response after updating user permissions."""

    user_id: UUID
    granted: int
    revoked: int


class AuthorizationResponse(BaseModel):
    """Full authorization context for the current user."""

    user: "AuthorizationUser"
    features: dict[str, bool]
    permissions: list[str]


class AuthorizationUser(BaseModel):
    """User info within authorization context."""

    id: UUID
    role: str
    organization_id: UUID | None = None
