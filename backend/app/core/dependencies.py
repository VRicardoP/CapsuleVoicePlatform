"""FastAPI dependencies for authentication and database access.

Implements secure session validation against PostgreSQL's secure_sessions table.
Compliant with RGPD Art. 32, LOPDGDD Art. 33 (access control).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, NamedTuple
from uuid import UUID

if TYPE_CHECKING:
    from app.core.authorization import Principal

from fastapi import Cookie, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_session
from app.core.security import decode_token, validate_session_in_db

# HTTP Bearer token scheme (for Authorization header)
security = HTTPBearer(auto_error=False)


@dataclass
class PaginationParams:
    """Standardized pagination parameters for list endpoints.

    Use as a FastAPI dependency: ``pagination: PaginationParams = Depends()``
    Converts page-based input to skip/limit for the repository layer.
    """

    page: int = Query(1, ge=1, description="Page number (1-based)")
    limit: int = Query(50, ge=1, le=100, description="Items per page")

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.limit


class AuthContext(NamedTuple):
    """Authentication context with user_id and session token for RLS."""

    user_id: UUID
    session_token: str


async def get_db() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_session():
        yield session


async def _resolve_api_token(
    db: AsyncSession,
    bearer_value: str,
    request: Request | None = None,
) -> tuple[str, str | None] | None:
    """Validate ``Bearer sferaai_at_*`` tokens against ``api_tokens``.

    If ``request`` is provided, populate ``request.state`` with:
    - ``auth_source = "api_token"``
    - ``api_token_scope = frozenset(token.scope)``
    - ``api_token_user_id``, ``api_token_organization_id``

    These are consumed by ``get_current_principal`` / ``get_current_user_role``
    so that downstream authorization uses the token's declared scope
    instead of the issuer's full role permissions.

    Returns ``(user_id, organization_id)`` if valid, else ``None``.
    """
    import hashlib

    from app.repositories.bff_session_repository import ApiTokenRepository

    token_hash = hashlib.sha256(bearer_value.encode()).hexdigest()
    repo = ApiTokenRepository(db)
    api_token = await repo.get_by_token_hash(token_hash)
    if api_token is None:
        return None
    # Best-effort touch; failure is non-fatal.
    try:
        await repo.touch_last_used(api_token.id)
        await db.commit()
    except Exception:
        await db.rollback()

    uid = str(api_token.user_id)
    org = str(api_token.organization_id) if api_token.organization_id else None

    if request is not None:
        request.state.auth_source = "api_token"
        request.state.api_token_scope = frozenset(api_token.scope or ())
        request.state.api_token_user_id = uid
        request.state.api_token_organization_id = org

    return uid, org


async def get_current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> str:
    """Resolve the authenticated user_id.

    Resolution order:
      1. BFFSessionMiddleware already populated ``request.state``? Use that.
      2. ``Authorization: Bearer sferaai_at_*`` → API token table.
      3. Legacy JWT in Authorization header or ``access_token`` cookie.
    """
    # 1. BFF cookie path (populated by BFFSessionMiddleware)
    state_user_id = getattr(request.state, "user_id", None)
    if state_user_id and getattr(request.state, "auth_source", "").startswith("bff"):
        return state_user_id

    # 2. API token path
    if credentials and credentials.credentials.startswith("sferaai_at_"):
        resolved = await _resolve_api_token(db, credentials.credentials, request)
        if resolved:
            return resolved[0]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Legacy JWT path (kept until Phase 1.5 retires it)
    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = await validate_session_in_db(db, payload.sst)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user_id != payload.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session user mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )

    request.state.auth_source = "legacy_jwt"
    return user_id


async def get_auth_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> AuthContext:
    """Get the full authentication context (user_id + session_token).

    BFF path uses the backend session_token harvested by middleware; the
    legacy JWT path keeps decoding the bearer/cookie token. Order matches
    ``get_current_user_id`` for consistency.
    """
    # 1. BFF cookie path
    state_user_id = getattr(request.state, "user_id", None)
    state_session_token = getattr(request.state, "session_token", None)
    if (
        state_user_id
        and state_session_token
        and getattr(request.state, "auth_source", "").startswith("bff")
    ):
        return AuthContext(
            user_id=UUID(state_user_id),
            session_token=state_session_token,
        )

    # 2. API token path — by design does NOT produce an RLS session token
    # because API tokens are scope-restricted and should not acquire the
    # full user's RLS context. Endpoints that need RLS (those depending
    # on get_db_with_rls) will surface a clear 403 instead of silently
    # running with a fake token.
    if credentials and credentials.credentials.startswith("sferaai_at_"):
        if await _resolve_api_token(db, credentials.credentials, request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires a user session; API tokens "
                "cannot provide the required RLS context.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Legacy JWT path
    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = await validate_session_in_db(db, payload.sst)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user_id != payload.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session user mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthContext(user_id=UUID(user_id), session_token=payload.sst)


async def set_rls_context(db: AsyncSession, auth: AuthContext) -> None:
    """Set PostgreSQL session context for RLS policies.

    This function configures the PostgreSQL GUC variables that are used
    by RLS policies to determine row-level access:
    - app.secure_session_token: Used by get_current_user() function
    - app.current_user_id: Fallback for direct user_id access

    Must be called before any database queries that rely on RLS.

    Args:
        db: Database session
        auth: Authentication context from get_auth_context
    """
    await db.execute(
        text("SELECT set_config('app.secure_session_token', :token, true)"),
        {"token": auth.session_token},
    )
    await db.execute(
        text("SELECT set_config('app.current_user_id', :user_id, true)"),
        {"user_id": str(auth.user_id)},
    )


async def get_db_with_rls(
    db: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> AsyncSession:
    """Get database session with RLS context already set.

    Combines get_db + get_auth_context + set_rls_context into a single
    dependency. Use this instead of manually calling set_rls_context()
    in every endpoint.
    """
    await set_rls_context(db, auth)
    return db


async def get_current_user_role(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> str:
    """Resolve the current user's role.

    BFF path doesn't carry the role in a token; we look it up from
    ``users.role`` on the fly. JWT/legacy path keeps the embedded claim
    for zero-DB cost.
    """
    # 1. BFF path
    state_user_id = getattr(request.state, "user_id", None)
    if state_user_id and getattr(request.state, "auth_source", "").startswith("bff"):
        result = await db.execute(
            text("SELECT role FROM users WHERE id = :uid"),
            {"uid": state_user_id},
        )
        row = result.fetchone()
        return (row[0] if row else None) or "none"

    # 2. API token path — NOT the user's real role. Returning a dedicated
    # "api_token" role blocks require_admin() / require_dpo() / etc. from
    # accepting API tokens for admin operations, which is the intended
    # principle of least privilege.
    if credentials and credentials.credentials.startswith("sferaai_at_"):
        resolved = await _resolve_api_token(db, credentials.credentials, request)
        if not resolved:
            return "none"
        return "api_token"

    # 3. Legacy JWT path
    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token

    if not token:
        return "none"

    payload = decode_token(token)
    if not payload:
        return "none"

    return payload.role or "none"


async def require_admin(
    role: Annotated[str, Depends(get_current_user_role)],
    _user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> str:
    """Require admin role for endpoint access.

    Accepts superadmin and client_admin (backward compat: also 'admin').
    Also validates session via get_current_user_id.
    """
    if role not in ("superadmin", "client_admin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return role


async def require_dpo(
    role: Annotated[str, Depends(get_current_user_role)],
    _user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> str:
    """Require DPO or admin role for GDPR operations (LOPDGDD Art. 34).

    Also validates session via get_current_user_id.
    """
    if role not in ("superadmin", "client_admin", "admin", "dpo"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DPO privileges required for this operation",
        )
    return role


def _require_wa_role_factory(allowed_roles: list[str]):
    """Create a WhatsApp role-check dependency.

    Manual role mapping: Owner→admin, Supervisor→admin/user, Agent→user, ReadOnly→viewer.
    Also validates session via get_current_user_id.
    """

    async def _check(
        role: Annotated[str, Depends(get_current_user_role)],
        _user_id: Annotated[str, Depends(get_current_user_id)],  # validates session
    ) -> str:
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient WhatsApp permissions",
            )
        return role

    return _check


# Pre-built WhatsApp role dependencies
require_wa_admin = _require_wa_role_factory(["superadmin", "client_admin", "admin"])
require_wa_manager = _require_wa_role_factory(["superadmin", "client_admin", "admin", "user"])


async def get_current_principal(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    role: Annotated[str, Depends(get_current_user_role)],
) -> "Principal":
    """Load full authorization context from DB.

    Resolves the Principal with permissions based on role:
    - superadmin: wildcard '*' (all permissions)
    - client_admin: all permissions from role template, filtered by tenant features
    - user: role template base + per-user overrides, filtered by tenant features
    - api_token: permissions = the token's declared scope (INTERSECTED with
      whatever the issuer held when the token was created; enforcement at
      issue time means we don't need to re-intersect here)
    """
    from app.core.authorization import FEATURE_KEYS, Principal
    from app.repositories.permission_repository import PermissionRepository

    uid = UUID(user_id)
    repo = PermissionRepository(db)

    # API token auth source: use ONLY the scope declared at issue time.
    # Critical: this is what makes scopes real — otherwise a token issued by
    # a superadmin with scope ["calls.read"] would silently inherit '*'.
    if role == "api_token" and getattr(request.state, "auth_source", "") == "api_token":
        org = getattr(request.state, "api_token_organization_id", None)
        scope = getattr(request.state, "api_token_scope", frozenset())
        return Principal(
            user_id=uid,
            role="api_token",
            organization_id=UUID(org) if org else None,
            permissions=frozenset(scope),
        )

    if role == "superadmin":
        return Principal(
            user_id=uid,
            role=role,
            organization_id=None,
            permissions=frozenset({"*"}),
        )

    # Get user's organization_id
    result = await db.execute(
        text("SELECT organization_id FROM users WHERE id = :uid"),
        {"uid": str(uid)},
    )
    row = result.fetchone()
    org_id = row[0] if row else None

    if role in ("client_admin", "admin"):
        # All permissions from template, filtered by tenant features.
        # Legacy 'admin' is treated as client_admin for backward compat — kept
        # in sync with require_admin() which also accepts both labels.
        all_perms = set(await repo.get_role_template_permissions("client_admin"))
    else:
        # Effective set = (role template ∪ grants) \ denies.
        # Denies let an admin revoke a role-granted permission for a single
        # user without removing it from the role template as a whole.
        base = set(await repo.get_role_template_permissions("user"))
        grants, denies = await repo.get_user_grants_and_denies(uid)
        all_perms = (base | grants) - denies

    # Filter by tenant features
    if org_id:
        features = await repo.get_tenant_features(org_id)
        filtered = set()
        for perm in all_perms:
            module = perm.split(".")[0]
            feature_key = FEATURE_KEYS.get(module)
            if feature_key is None or features.get(feature_key, False):
                filtered.add(perm)
        all_perms = filtered

    return Principal(
        user_id=uid,
        role=role,
        organization_id=org_id,
        permissions=frozenset(all_perms),
    )


def require_feature(feature: str):
    """Dependency factory: verify tenant has the module enabled.

    Usage in endpoints:
        principal: Annotated[Principal, Depends(require_feature("whatsapp"))]
    """

    async def _check(
        principal: Annotated["Principal", Depends(get_current_principal)],
    ) -> "Principal":
        if "*" in principal.permissions:
            return principal
        from app.core.authorization import FEATURE_KEYS

        if feature in FEATURE_KEYS:
            # Principal permissions are already filtered by features,
            # so if any perm for this module exists, the feature is enabled
            if not any(p == feature or p.startswith(f"{feature}.") for p in principal.permissions):
                raise HTTPException(
                    status_code=403,
                    detail=f"Module {feature} not enabled",
                )
        return principal

    return _check


def require_recent_auth(max_age_seconds: int | None = None):
    """Require that the BFF session has authenticated within the window.

    Used by sensitive endpoints (passkey CRUD, password change, GDPR
    erase, API token issuance, permission grants).

    Behaviour:
    - If the request is BFF-authenticated and ``recent_auth_at`` is
      within the window → pass.
    - If the request is BFF-authenticated but ``recent_auth_at`` is
      stale → 401 with ``WWW-Authenticate: SferaAI re-auth-required``.
    - If the request is on the legacy JWT path → pass (the legacy flow
      has no concept of recent_auth, and we don't want to break the
      coexistence window). After Phase 1.5 retires legacy, this
      automatically becomes universal because all sessions will be BFF.
    - API tokens fail immediately (server-to-server can't re-auth a user).
    """
    from app.services import bff_session_service

    async def _check(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    ) -> None:
        # API tokens cannot satisfy recent-auth requirements; reject.
        if credentials and credentials.credentials.startswith("sferaai_at_"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API tokens cannot perform sensitive operations",
            )

        sess = getattr(request.state, "frontend_session", None)
        if sess is None:
            # Legacy JWT path → permit during coexistence; the endpoint
            # still requires `get_current_user_id` to pass.
            return

        if bff_session_service.is_recently_authenticated(sess, max_age_seconds):
            return

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Re-authentication required",
            headers={
                "WWW-Authenticate": "SferaAI re-auth-required",
                "X-Reauth-Code": "REAUTH_REQUIRED",
            },
        )

    return _check


def require_permission(permission: str):
    """Dependency factory: verify user has a specific permission.

    Supports hierarchical checks via Principal.has_permission().

    Usage in endpoints:
        principal: Annotated[Principal, Depends(require_permission("whatsapp.inbox.view"))]
    """

    async def _check(
        principal: Annotated["Principal", Depends(get_current_principal)],
    ) -> "Principal":
        if not principal.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission required: {permission}",
            )
        return principal

    return _check


async def require_superadmin(
    principal: Annotated["Principal", Depends(get_current_principal)],
) -> "Principal":
    """Dependency: restrict endpoint to superadmin only.

    Usage:
        dependencies=[Depends(require_superadmin)]
    """
    if principal.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return principal


class DatabaseSessionWithContext:
    """Database session with security context established.

    This class wraps an AsyncSession and ensures the PostgreSQL session
    context is properly set before any database operations.

    Usage:
        async with DatabaseSessionWithContext(db, user_id, client_ip) as session:
            result = await session.execute(...)
    """

    def __init__(
        self,
        session: AsyncSession,
        user_id: str | None = None,
        client_ip: str | None = None,
    ):
        self.session = session
        self.user_id = user_id
        self.client_ip = client_ip

    async def __aenter__(self) -> AsyncSession:
        """Set up PostgreSQL session context."""
        if self.user_id:
            # The session token should already be set by get_current_user_id
            # This is a secondary check/refresh
            await self.session.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": self.user_id},
            )

        if self.client_ip:
            await self.session.execute(
                text("SELECT set_config('app.client_ip', :ip, true)"),
                {"ip": self.client_ip},
            )

        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up on exit."""
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
