"""Authentication endpoints — BFF (Backend-for-Frontend) flavour.

Phase 1 of the BFF migration:
- ``POST /login``  → creates an opaque ``frontend_sessions`` row, sets
  ``__Host-capsulecorp_session`` + CSRF cookies, and returns the user info.
  Tokens never leave the backend.
- ``POST /logout`` → revokes the frontend session (and the underlying
  ``user_sessions`` row), clears cookies.
- ``POST /refresh`` → shim. Returns 204. The BFF layer auto-refreshes
  internally; this endpoint exists only to keep older frontends from
  failing if they still call it. If a legacy ``access_token`` cookie is
  present, it is opportunistically auto-upgraded to BFF.
- ``POST /api-token`` → issue a scoped bearer token for CI / automation.
  Requires recent re-auth.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.authorization import Principal
from app.core.dependencies import (
    AuthContext,
    get_auth_context,
    get_current_principal,
    get_current_user_id,
    get_db,
    require_recent_auth,
)
from app.core.security import verify_password_async
from app.repositories.bff_session_repository import (
    ApiTokenRepository,
    FrontendSessionRepository,
)
from app.repositories.gdpr_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository, UserSessionRepository
from app.schemas.auth import (
    APITokenCreateRequest,
    APITokenCreateResponse,
    APITokenInfo,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    SessionInfo,
    TokenValidationResponse,
    UserInfo,
)
from app.services import bff_session_service
from app.services.auth_service import load_user_preferences

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


# Rate limiting for login attempts
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# API token format: "capsulecorp_at_<urlsafe-32-bytes>"
API_TOKEN_PREFIX = "capsulecorp_at_"


# ===========================================================================
# Login / Logout
# ===========================================================================


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user and create a BFF session cookie.",
)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """Validate credentials, create a backing ``user_sessions`` row + a
    BFF ``frontend_sessions`` row, and set the opaque session cookie."""
    user_repo = UserRepository(db)
    session_repo = UserSessionRepository(db)
    audit_repo = AuditLogRepository(db)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    user = await user_repo.get_by_email(login_data.email)
    if not user:
        await audit_repo.log_action(
            action="FAILED_LOGIN",
            entity_type="users",
            ip_address=client_ip,
            user_agent=user_agent,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if user.locked_until and user.locked_until > datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked. Try again after {user.locked_until.isoformat()}",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    if not await verify_password_async(login_data.password, user.password_hash):
        new_count = await user_repo.increment_failed_attempts(user.id)
        if new_count >= MAX_LOGIN_ATTEMPTS:
            lock_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            await user_repo.lock_user(user.id, lock_until)
        await audit_repo.log_action(
            action="FAILED_LOGIN",
            entity_type="users",
            user_id=user.id,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Backend session in user_sessions (RLS / dependencies look it up here).
    backend_session_token = secrets.token_urlsafe(32)
    backend_token_hash = hashlib.sha256(backend_session_token.encode()).hexdigest()
    session_lifetime = timedelta(hours=settings.bff_session_absolute_hours)
    session_expires = datetime.now(UTC) + session_lifetime
    backend_session = await session_repo.create(
        {
            "user_id": user.id,
            "token_hash": backend_token_hash,
            "ip_address": client_ip or "0.0.0.0",
            "user_agent": user_agent,
            "expires_at": session_expires,
            "refresh_expires_at": session_expires,
            "is_revoked": False,
        }
    )

    # Frontend opaque session cookie.
    bff_result = await bff_session_service.create_session(
        db,
        request=request,
        user_id=user.id,
        organization_id=user.organization_id,
        backend_session_id=backend_session.id,
        backend_session_token=backend_session_token,
        auth_method="password",
    )

    await db.commit()
    await user_repo.update_last_login(user.id, client_ip)

    decrypted_data = await user_repo.get_decrypted_user_data(user.id)
    user_email = decrypted_data.get("email", "") if decrypted_data else login_data.email
    user_name = decrypted_data.get("name", "") if decrypted_data else ""
    user_preferences = await load_user_preferences(db, user.id)

    await db.commit()

    expires_in_seconds = bff_result.cookie.max_age_seconds
    is_https = request.url.scheme == "https"

    response.set_cookie(
        key=bff_result.cookie.cookie_name,
        value=bff_result.cookie.cookie_value,
        max_age=expires_in_seconds,
        httponly=True,
        secure=is_https,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=bff_session_service.CSRF_COOKIE_NAME,
        value=bff_result.cookie.csrf_token,
        max_age=expires_in_seconds,
        httponly=False,
        secure=is_https,
        samesite="lax",
        path="/",
    )
    # Clear any stale legacy cookies from previous logins.
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    return LoginResponse(
        access_token="",
        refresh_token="",
        token_type="bearer",
        expires_in=expires_in_seconds,
        expiresIn=expires_in_seconds,
        user_id=str(user.id),
        user=UserInfo(
            id=str(user.id),
            name=user_name or "Usuario",
            email=user_email,
            company=user.company or "",
            role=user.role,
            preferences=user_preferences,
        ),
    )


@router.post(
    "/refresh",
    summary="Refresh shim (BFF auto-refreshes internally)",
)
async def refresh_token_shim(request: Request, response: Response) -> None:
    """Compat shim. Older frontends may still call this endpoint.

    Under BFF, the middleware refreshes the session on every request via
    sliding window updates. This endpoint just returns 204. If a legacy
    ``access_token`` cookie is present, the middleware will have already
    auto-upgraded the session and queued the new cookie; we preserve that
    by mutating ``response`` rather than returning a new ``Response``
    object (which would discard the queued Set-Cookie headers).
    """
    if getattr(request.state, "bff_session_id", None):
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    # No active session. Mutate the injected response so middleware
    # outputs (if any) remain intact even on the 401 path.
    response.status_code = status.HTTP_401_UNAUTHORIZED
    return None


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout",
)
async def logout(
    request: Request,
    response: Response,
    logout_data: LogoutRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Revoke the active BFF session(s) + clear cookies.

    Returns ``None`` (not a new ``Response(204)``) so the ``Set-Cookie``
    deletions attached to the injected ``response`` object actually reach
    the browser. Status 204 comes from the decorator.
    """
    session_repo = UserSessionRepository(db)
    fe_repo = FrontendSessionRepository(db)

    bff_session_id = getattr(request.state, "bff_session_id", None)
    if logout_data.invalidate_all:
        await session_repo.invalidate_all_user_sessions(auth.user_id, reason="logout_all")
        # Cascade revoke matching frontend_sessions via a single update.
        from sqlalchemy import text

        await db.execute(
            text(
                """
                UPDATE frontend_sessions
                SET is_revoked = TRUE, revoked_at = NOW(), revoked_reason = 'logout_all'
                WHERE user_id = :uid AND NOT is_revoked
                """
            ),
            {"uid": str(auth.user_id)},
        )
    else:
        if bff_session_id:
            sess = getattr(request.state, "frontend_session", None)
            if sess is not None:
                await session_repo.invalidate_session(sess.backend_session_id, reason="logout")
            await fe_repo.revoke(bff_session_id, "logout")
        else:
            # Legacy fallback: revoke by token hash from JWT.
            token_hash = hashlib.sha256(auth.session_token.encode()).hexdigest()
            current_session = await session_repo.get_by_token(token_hash)
            if current_session:
                await session_repo.invalidate_session(current_session.id, reason="logout")
                await fe_repo.revoke_by_backend_session(current_session.id, "logout")

    # Clear ALL cookies (BFF + legacy).
    for cookie_name in (
        bff_session_service.COOKIE_NAME_PROD,
        bff_session_service.COOKIE_NAME_DEV,
        bff_session_service.CSRF_COOKIE_NAME,
    ):
        response.delete_cookie(key=cookie_name, path="/")
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    await db.commit()
    # IMPORTANT: do NOT return a fresh Response() here — FastAPI would
    # replace ``response`` (which holds our Set-Cookie deletions) with the
    # new object. ``status_code=204`` from the decorator is what takes
    # effect when we return None.


# ===========================================================================
# Sessions management
# ===========================================================================


@router.get(
    "/sessions",
    response_model=list[SessionInfo],
    summary="Get active sessions",
)
async def get_sessions(
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SessionInfo]:
    session_repo = UserSessionRepository(db)
    sessions = await session_repo.get_active_sessions_for_user(current_user_id)
    return [
        SessionInfo(
            id=str(s.id),
            session_id=str(s.id),
            ip_address=str(s.ip_address) if s.ip_address else None,
            client_ip=str(s.ip_address) if s.ip_address else None,
            user_agent=s.user_agent,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_current=False,
        )
        for s in sessions
    ]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a specific session",
    dependencies=[Depends(require_recent_auth())],
)
async def revoke_session(
    session_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    session_repo = UserSessionRepository(db)
    fe_repo = FrontendSessionRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session or session.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await session_repo.invalidate_session(session_id, reason="user_revoked")
    await fe_repo.revoke_by_backend_session(session_id, "user_revoked")
    await db.commit()


@router.post(
    "/validate",
    response_model=TokenValidationResponse,
    summary="Validate current session",
)
async def validate_token(
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenValidationResponse:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return TokenValidationResponse(
        valid=True,
        user_id=str(user.id),
        role=user.role,
        is_active=user.is_active,
    )


# ===========================================================================
# API tokens (server-to-server / CI usage; NOT for browsers)
# ===========================================================================


@router.post(
    "/api-token",
    response_model=APITokenCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a scoped bearer API token",
    dependencies=[Depends(require_recent_auth())],
)
async def create_api_token(
    body: APITokenCreateRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APITokenCreateResponse:
    """Create a bearer API token for server-to-server use.

    Restrictions:
    - Only admin roles can create them.
    - Scope must be a subset of the caller's permissions.
    - TTL ≤ ``settings.bff_api_token_max_ttl_hours``.
    - Max ``settings.bff_api_token_max_active_per_user`` active per user.
    """
    if principal.role not in ("superadmin", "client_admin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to issue API tokens",
        )

    # Scope subset check (superadmin has '*' which trivially passes).
    if principal.role != "superadmin":
        for perm in body.scope:
            if not principal.has_permission(perm):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Cannot grant permission you don't hold: {perm}",
                )

    if body.ttl_hours > settings.bff_api_token_max_ttl_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"ttl_hours exceeds maximum ({settings.bff_api_token_max_ttl_hours})"),
        )

    repo = ApiTokenRepository(db)
    active_count = await repo.count_active_for_user(current_user_id)
    if active_count >= settings.bff_api_token_max_active_per_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Active API token limit reached "
                f"({settings.bff_api_token_max_active_per_user}). "
                "Revoke an existing token before issuing a new one."
            ),
        )

    raw_token = API_TOKEN_PREFIX + secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(hours=body.ttl_hours)
    # bff_session_id: current_user_id is a UUID, not a request — insert NULL (column nullable).
    api_token = await repo.insert(
        {
            "token_hash": token_hash,
            "user_id": str(current_user_id),
            "organization_id": (
                str(principal.organization_id) if principal.organization_id else None
            ),
            "scope": list(body.scope),
            "description": body.description,
            "expires_at": expires_at,
            "created_by_session_id": None,
        }
    )
    await db.commit()

    return APITokenCreateResponse(
        id=str(api_token.id),
        token=raw_token,
        description=api_token.description,
        scope=list(api_token.scope),
        expires_at=api_token.expires_at,
        created_at=api_token.created_at,
    )


@router.get(
    "/api-tokens",
    response_model=list[APITokenInfo],
    summary="List own API tokens",
)
async def list_api_tokens(
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[APITokenInfo]:
    repo = ApiTokenRepository(db)
    tokens = await repo.list_for_user(current_user_id)
    return [
        APITokenInfo(
            id=str(t.id),
            description=t.description,
            scope=list(t.scope),
            created_at=t.created_at,
            expires_at=t.expires_at,
            last_used_at=t.last_used_at,
        )
        for t in tokens
    ]


@router.delete(
    "/api-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API token",
    dependencies=[Depends(require_recent_auth())],
)
async def revoke_api_token(
    token_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = ApiTokenRepository(db)
    revoked = await repo.revoke(token_id, current_user_id, "user_revoked")
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    await db.commit()
