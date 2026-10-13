"""User-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserPreferences(BaseModel):
    """User preferences schema."""

    visibleModules: list[str] = []
    theme: str = "dark"


class UserResponse(BaseModel):
    """User response with decrypted PII (for authorized access)."""

    id: UUID
    email: str | None = None
    name: str | None = None
    company: str | None = None
    role: str
    organization_id: UUID | None = None
    is_active: bool
    email_verified: bool = False
    two_factor_enabled: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    preferences: UserPreferences | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """User update request."""

    name: str | None = Field(None, max_length=200)
    email: EmailStr | None = None
    preferences: dict | None = None


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=12)


class UserCreateRequest(BaseModel):
    """Admin user creation request."""

    email: EmailStr
    name: str | None = Field(None, max_length=200)
    password: str = Field(..., min_length=12)
    role: str = Field(default="user", pattern="^(superadmin|client_admin|user)$")
    permissions: list[str] = Field(default_factory=list)


class UserListResponse(BaseModel):
    """Paginated user list response."""

    items: list[UserResponse]
    total: int
    skip: int
    limit: int
