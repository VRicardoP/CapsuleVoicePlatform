"""BFF session service: create / refresh / revoke / upgrade.

Encapsulates the lifecycle of opaque browser sessions backed by
``user_sessions`` rows. Endpoints and middleware call into here; they
never touch the repositories directly.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.bff_session import FrontendSession
from app.repositories.bff_session_repository import FrontendSessionRepository

logger = logging.getLogger(__name__)


# Cookie names. ``__Host-`` enforces host-only + Secure + Path=/ but only
# works over HTTPS, so dev keeps a plain name.
COOKIE_NAME_PROD = "__Host-capsulecorp_session"
COOKIE_NAME_DEV = "capsulecorp_session"
CSRF_COOKIE_NAME = "capsulecorp_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

# Cookie value entropy in bytes. token_urlsafe rounds up to base64.
COOKIE_BYTES = 48
CSRF_BYTES = 32


@dataclass(frozen=True)
class IssuedCookie:
    """Plaintext cookie material returned to the caller for ``Set-Cookie``."""

    cookie_name: str
    cookie_value: str
    csrf_token: str
    max_age_seconds: int


@dataclass(frozen=True)
class SessionCreationResult:
    """What ``create_session`` returns: the row + the cookie material."""

    session: FrontendSession
    cookie: IssuedCookie


def cookie_name_for_request(request: Request) -> str:
    """Pick the right cookie name for the request scheme.

    ``__Host-`` requires HTTPS — fall back to a plain name on HTTP dev.
    """
    if request.url.scheme == "https":
        return COOKIE_NAME_PROD
    return COOKIE_NAME_DEV


def hash_cookie_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_csrf_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _client_ip(request: Request) -> str | None:
    return getattr(request.state, "client_ip", None) or (
        request.client.host if request.client else None
    )


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


async def create_session(
    db: AsyncSession,
    *,
    request: Request,
    user_id: UUID,
    organization_id: UUID | None,
    backend_session_id: UUID,
    backend_session_token: str,
    auth_method: Literal["password", "passkey"],
    upgraded_from_legacy: bool = False,
) -> SessionCreationResult:
    """Create a new ``frontend_sessions`` row and return cookie material.

    ``backend_session_token`` is the plaintext secure_sessions token. It is
    stored server-side so the middleware can replay it into
    ``app.secure_session_token`` on each request, which is what the SQL
    ``get_current_user()`` function validates. It NEVER leaves the backend.

    Caller is responsible for COMMITting and for setting the cookie on the
    outgoing response (we don't have it here).
    """
    cookie_value = secrets.token_urlsafe(COOKIE_BYTES)
    csrf_token = secrets.token_urlsafe(CSRF_BYTES)

    now = datetime.now(UTC)
    idle_expires = now + timedelta(minutes=settings.bff_session_idle_minutes)
    absolute_expires = now + timedelta(hours=settings.bff_session_absolute_hours)
    cookie_max_age = int((absolute_expires - now).total_seconds())

    repo = FrontendSessionRepository(db)
    session_row = await repo.insert(
        {
            "cookie_hash": hash_cookie_value(cookie_value),
            "user_id": str(user_id),
            "organization_id": str(organization_id) if organization_id else None,
            "backend_session_id": str(backend_session_id),
            "backend_session_token": backend_session_token,
            "csrf_token_hash": hash_csrf_token(csrf_token),
            "idle_expires_at": idle_expires,
            "absolute_expires_at": absolute_expires,
            "auth_method": auth_method,
            "upgraded_from_legacy": upgraded_from_legacy,
            "ip_address": _client_ip(request),
            "user_agent": _user_agent(request),
        }
    )

    return SessionCreationResult(
        session=session_row,
        cookie=IssuedCookie(
            cookie_name=cookie_name_for_request(request),
            cookie_value=cookie_value,
            csrf_token=csrf_token,
            max_age_seconds=cookie_max_age,
        ),
    )


def is_session_expired(session: FrontendSession) -> bool:
    """Either timeout fires ⇒ session is no longer valid."""
    now = datetime.now(UTC)
    if session.idle_expires_at and session.idle_expires_at <= now:
        return True
    if session.absolute_expires_at and session.absolute_expires_at <= now:
        return True
    return False


async def touch_session(db: AsyncSession, session: FrontendSession) -> None:
    """Throttled sliding-window update of ``last_seen_at``.

    Idempotent against being called every request; the SQL UPDATE is gated
    by ``last_seen_at < NOW() - throttle``.
    """
    repo = FrontendSessionRepository(db)
    new_idle = datetime.now(UTC) + timedelta(minutes=settings.bff_session_idle_minutes)
    await repo.touch_last_seen(
        session.id,
        new_idle_expires_at=new_idle,
        throttle_seconds=settings.bff_session_sliding_throttle_seconds,
    )


async def revoke_session(
    db: AsyncSession,
    session_id: UUID,
    reason: str = "logout",
) -> None:
    repo = FrontendSessionRepository(db)
    await repo.revoke(session_id, reason)


async def revoke_by_backend_session(
    db: AsyncSession,
    backend_session_id: UUID,
    reason: str = "backend_session_revoked",
) -> int:
    repo = FrontendSessionRepository(db)
    return await repo.revoke_by_backend_session(backend_session_id, reason)


async def update_recent_auth(
    db: AsyncSession,
    session_id: UUID,
    method: Literal["password", "passkey"],
) -> None:
    repo = FrontendSessionRepository(db)
    await repo.update_recent_auth(session_id, method)


def is_recently_authenticated(
    session: FrontendSession,
    max_age_seconds: int | None = None,
) -> bool:
    """True if ``recent_auth_at`` is within the configured window."""
    if max_age_seconds is None:
        max_age_seconds = settings.bff_recent_auth_window_seconds
    age = (datetime.now(UTC) - session.recent_auth_at).total_seconds()
    return age <= max_age_seconds


# ---------------------------------------------------------------------------
# Legacy auto-upgrade
# ---------------------------------------------------------------------------


async def upgrade_legacy_session(
    db: AsyncSession,
    *,
    request: Request,
    user_id: UUID,
    organization_id: UUID | None,
    backend_session_id: UUID,
    backend_session_token: str,
) -> SessionCreationResult | None:
    """Idempotent upgrade of a legacy JWT-cookie session to BFF.

    Two concurrent first-requests for the same ``user_sessions`` must NOT
    create two ``frontend_sessions`` rows — we serialize on
    ``backend_session_id`` with a transaction-scoped advisory lock.

    Returns the new session + cookie material, or ``None`` if another
    request beat us to it (caller keeps using the legacy path until the
    next request, when the cookie will be present).
    """
    repo = FrontendSessionRepository(db)
    await repo.acquire_upgrade_lock(backend_session_id)

    # Re-check inside the lock. If another worker already upgraded, do
    # nothing — the user will pick up the new cookie on their next request.
    existing = await repo.get_by_backend_session(backend_session_id)
    if existing is not None:
        return None

    return await create_session(
        db,
        request=request,
        user_id=user_id,
        organization_id=organization_id,
        backend_session_id=backend_session_id,
        backend_session_token=backend_session_token,
        auth_method="password",  # legacy sessions came from password login
        upgraded_from_legacy=True,
    )
