"""Authentication schemas for API requests/responses.

Compliant with:
- RGPD Art. 32: Secure authentication
- LOPDGDD Art. 5: Confidentiality
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserPreferencesInfo(BaseModel):
    """User preferences returned on login."""

    visibleModules: list[str] = Field(default_factory=list, description="Visible dashboard modules")
    theme: str = Field(default="dark", description="UI theme")


class UserInfo(BaseModel):
    """User information returned on login."""

    id: str = Field(..., description="User ID")
    name: str = Field(..., description="User full name")
    email: str = Field(..., description="User email")
    company: str = Field(default="", description="User company")
    role: str = Field(..., description="User role")
    preferences: UserPreferencesInfo | None = Field(default=None, description="User preferences")


class LoginResponse(BaseModel):
    """Login response.

    With BFF (Phase 1), tokens never leave the backend: ``access_token`` and
    ``refresh_token`` are returned empty for backwards-compat with old
    consumers (they will be removed in Phase 1.5). Authentication is
    transported via the ``__Host-sferaai_session`` cookie set on the
    response.
    """

    access_token: str = Field(default="", description="DEPRECATED — empty under BFF")
    refresh_token: str = Field(default="", description="DEPRECATED — empty under BFF")
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(..., description="Session lifetime in seconds")
    user_id: str = Field(..., description="Authenticated user ID")
    user: UserInfo = Field(..., description="User information")
    expiresIn: int = Field(..., description="Expiration in seconds (frontend compat)")


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., description="Valid refresh token")


class TokenValidationResponse(BaseModel):
    """Response for token validation check."""

    valid: bool
    user_id: str | None = None
    role: str | None = None
    is_active: bool | None = None
    expires_at: datetime | None = None


class LogoutRequest(BaseModel):
    """Logout request to invalidate session."""

    # Optional: invalidate all sessions for this user
    invalidate_all: bool = Field(
        default=False,
        description="Invalidate all user sessions (logout everywhere)",
        alias="invalidate_all_sessions",
    )


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def passwords_different(cls, v: str, info) -> str:
        """Ensure new password is different from current."""
        if "current_password" in info.data and v == info.data["current_password"]:
            raise ValueError("New password must be different from current")
        return v


class SessionInfo(BaseModel):
    """Information about a user session."""

    id: str | None = None
    session_id: str | None = None
    created_at: datetime
    expires_at: datetime
    ip_address: str | None = None
    client_ip: str | None = None
    user_agent: str | None = None
    is_current: bool = False


# =============================================================================
# BFF API Tokens (server-to-server / CI usage; NOT for browsers)
# =============================================================================


class APITokenCreateRequest(BaseModel):
    """Issue a scoped bearer token for CI / automation."""

    description: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="What is this token for? Required for audit.",
    )
    scope: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Permission strings the token is allowed to use. "
        "Must be a subset of the caller's permissions.",
    )
    ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Token lifetime in hours (max 168 = 7 days).",
    )


class APITokenCreateResponse(BaseModel):
    """Response after issuing an API token. Token shown once."""

    id: str
    token: str = Field(..., description="The bearer token. Store it now — not retrievable.")
    description: str
    scope: list[str]
    expires_at: datetime
    created_at: datetime


class APITokenInfo(BaseModel):
    """Listing entry for an issued API token (no value disclosed)."""

    id: str
    description: str
    scope: list[str]
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None = None


# =============================================================================
# API Keys Schemas (Machine-to-Machine Authentication)
# =============================================================================


class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key for service authentication."""

    client_type: Literal["ai_agent", "pbx", "external", "webhook"] = Field(
        ...,
        description="Type of client: ai_agent (voice assistant), pbx (phone system), external (third-party), webhook",
    )
    service_name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Human-readable name for the service",
    )
    service_id: str | None = Field(
        None,
        max_length=50,
        description="Unique identifier for the service (auto-generated if not provided)",
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Description of what this API key is used for",
    )
    allowed_ips: list[str] | None = Field(
        None,
        description="List of allowed IP addresses (null = any IP)",
    )
    expires_days: int | None = Field(
        None,
        ge=1,
        le=365,
        description="Number of days until expiration (null = never expires)",
    )


class APIKeyCreateResponse(BaseModel):
    """Response after creating an API key.

    IMPORTANT: The api_key is only shown ONCE. Store it securely immediately.
    """

    api_key: str = Field(
        ...,
        description="The API key in plain text. STORE THIS IMMEDIATELY - it cannot be retrieved again!",
    )
    api_key_id: str = Field(..., description="UUID of the API key record")
    key_prefix: str = Field(..., description="Key prefix for identification in logs")
    client_type: str = Field(..., description="Type of client")
    service_name: str = Field(..., description="Service name")
    service_id: str = Field(..., description="Unique service identifier")
    expires_at: datetime | None = Field(None, description="Expiration date (null = never)")
    message: str = Field(
        default="API key created successfully. Store the api_key securely - it will NOT be shown again!",
        description="Important notice about key storage",
    )


class APIKeyInfo(BaseModel):
    """Information about an existing API key (without the key itself)."""

    id: str = Field(..., description="API key UUID")
    key_prefix: str = Field(..., description="Key prefix for identification")
    client_type: str = Field(..., description="Type of client")
    service_name: str = Field(..., description="Service name")
    service_id: str | None = Field(None, description="Service identifier")
    description: str | None = Field(None, description="Description")
    allowed_ips: list[str] | None = Field(None, description="Allowed IPs")
    is_active: bool = Field(..., description="Whether the key is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    last_used_at: datetime | None = Field(None, description="Last usage timestamp")
    use_count: int = Field(default=0, description="Total number of uses")


class APIKeyRevokeRequest(BaseModel):
    """Request to revoke an API key."""

    reason: str = Field(
        default="Manual revocation",
        max_length=255,
        description="Reason for revoking the key",
    )


# =============================================================================
# API Key Provisioning (Machine-to-Machine without Admin credentials)
# =============================================================================


class APIKeyProvisionRequest(BaseModel):
    """Request to provision an API key using a secret token.

    This allows services (AI agents, PBX, etc.) to obtain API keys
    without requiring admin credentials - using a pre-shared secret instead.
    """

    provision_secret: str = Field(
        ...,
        min_length=32,
        description="Pre-shared secret for provisioning (configured in environment)",
    )
    client_type: Literal["ai_agent", "pbx", "external", "webhook"] = Field(
        ...,
        description="Type of client requesting the key",
    )
    service_name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Human-readable name for the service",
    )
    service_id: str | None = Field(
        None,
        max_length=50,
        description="Unique identifier for the service (auto-generated if not provided)",
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Description of the service",
    )


class APIKeyProvisionResponse(BaseModel):
    """Response after provisioning an API key.

    IMPORTANT: The api_key is only shown ONCE. Store it securely immediately.
    """

    api_key: str = Field(
        ...,
        description="The API key in plain text. STORE THIS IMMEDIATELY!",
    )
    api_key_id: str = Field(..., description="UUID of the API key record")
    key_prefix: str = Field(..., description="Key prefix for identification")
    client_type: str = Field(..., description="Type of client")
    service_name: str = Field(..., description="Service name")
    service_id: str = Field(..., description="Unique service identifier")
    expires_at: datetime | None = Field(None, description="Expiration date (null = never)")
    message: str = Field(
        default="API key provisioned successfully. Store securely - it will NOT be shown again!",
        description="Important notice",
    )
