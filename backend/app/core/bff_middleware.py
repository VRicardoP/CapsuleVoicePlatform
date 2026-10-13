"""BFFSessionMiddleware — opaque cookie sessions + CSRF.

Pipeline (order matters):
1. Skip excluded paths (auth/login, webhooks, marketplace, health…).
2. Resolve the active session:
   a. If ``__Host-sferaai_session`` (or ``sferaai_session`` in dev) is
      present and valid → use BFF, populate ``request.state``.
   b. Else if a legacy ``access_token`` cookie is present and valid AND
      ``bff_legacy_cookie_compat`` is enabled → auto-upgrade to BFF and
      issue the new cookie on the response.
   c. Otherwise leave ``request.state`` untouched; downstream
      dependencies handle 401 themselves (or accept the legacy JWT).
3. Validate CSRF (Origin/Referer + double-submit token) for mutator
   methods on cookie-authenticated requests. NOT applied when the
   request is authenticated via API key (``X-API-Key`` header) or bearer
   ``sferaai_at_*`` token — those are not CSRF-vulnerable.
4. Throttled sliding-window update of ``last_seen_at``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from urllib.parse import urlparse
from uuid import UUID

import structlog
from fastapi import Request, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.database import async_session_maker
from app.config.settings import settings
from app.core.security import decode_token
from app.services.bff_session_service import (
    COOKIE_NAME_DEV,
    COOKIE_NAME_PROD,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    hash_cookie_value,
    hash_csrf_token,
    is_session_expired,
    touch_session,
    upgrade_legacy_session,
)

logger = structlog.get_logger(__name__)
_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------

# Prefixes that NEVER touch BFF / CSRF: webhooks (HMAC verified), unauth
# auth flows (no session yet), and public marketplace / health endpoints.
EXCLUDED_PREFIXES: tuple[str, ...] = (
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/passkey/login",
    "/api/v1/marketplace",
    "/api/v1/newsletter/unsubscribe",
    "/api/v1/newsletter/webhooks",
    "/api/v1/whatsapp/webhooks/meta",
    "/api/v1/captacion/webhooks",
    "/api/v1/calendar/webhooks",
    "/api/v1/ultravox/webhook",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/media",
)

MUTATOR_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _is_excluded(path: str) -> bool:
    if any(path.startswith(p) for p in EXCLUDED_PREFIXES):
        return True
    # GET /calls/{external_call_id}/phone — callable from Docker network by n8n
    # without a session. The Ultravox external_call_id (UUID v4) is unguessable.
    if path.startswith("/api/v1/calls/") and path.endswith("/phone"):
        return True
    return False


def _origin_matches_host(request: Request) -> bool:
    """Validate Origin/Referer against the request host.

    Allows ``localhost:*`` in non-prod for Vite dev server cross-port
    requests. Treats a missing Origin AND missing Referer as a fail —
    every legitimate browser sends at least one for cross-origin
    requests; same-origin requests typically include them too.
    """
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    candidate = origin or referer
    if not candidate:
        # Same-origin GETs from <a> clicks legitimately omit Origin and
        # Referrer-Policy can strip Referer. We only enforce this on
        # MUTATOR methods (caller already filtered), where browsers
        # always send Origin. So treat missing as fail.
        return False

    try:
        candidate_host = urlparse(candidate).hostname
    except ValueError:
        return False
    if not candidate_host:
        return False

    request_host = request.url.hostname
    if candidate_host == request_host:
        return True

    # Dev convenience: localhost on any port
    if settings.environment != "production" and candidate_host in {
        "localhost",
        "127.0.0.1",
    }:
        return True

    return False


def _read_cookie(request: Request, name: str) -> str | None:
    val = request.cookies.get(name)
    return val if val else None


def _get_bff_cookie(request: Request) -> str | None:
    """Read the BFF cookie regardless of which name applies (prod/dev).

    Both names are checked because the same backend serves HTTPS prod
    and HTTP dev with the same code path.
    """
    return _read_cookie(request, COOKIE_NAME_PROD) or _read_cookie(request, COOKIE_NAME_DEV)


def _expire_cookie(response: Response, name: str, path: str = "/") -> None:
    """Send a Set-Cookie that immediately removes ``name``."""
    response.delete_cookie(key=name, path=path)


def _set_session_cookies(
    request: Request,
    response: Response,
    *,
    cookie_name: str,
    cookie_value: str,
    csrf_token: str,
    max_age_seconds: int,
) -> None:
    """Set the BFF session cookie + the readable CSRF cookie.

    The session cookie is HttpOnly. The CSRF cookie is readable by JS
    so the dashboard can echo it back via ``X-CSRF-Token`` (double-submit).
    """
    is_https = request.url.scheme == "https"
    samesite = "lax"

    response.set_cookie(
        key=cookie_name,
        value=cookie_value,
        max_age=max_age_seconds,
        httponly=True,
        secure=is_https,
        samesite=samesite,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age_seconds,
        httponly=False,  # Must be readable by JS for double-submit
        secure=is_https,
        samesite=samesite,
        path="/",
    )


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class BFFSessionMiddleware(BaseHTTPMiddleware):
    """Resolve, refresh, and (optionally) upgrade BFF sessions per request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Excluded paths bypass entirely. Webhooks and login are handled
        # by their own auth (HMAC, password, etc.).
        if _is_excluded(path):
            return await call_next(request)

        # Authenticated via API key or bearer api_token? Skip BFF + CSRF.
        # Those auth modes are not cookie-based and therefore not
        # CSRF-vulnerable.
        if request.headers.get("x-api-key"):
            return await call_next(request)
        authz = request.headers.get("authorization") or ""
        if authz.lower().startswith("bearer sferaai_at_"):
            return await call_next(request)

        # Pre-allocate the response cookie queue so legacy upgrade can
        # piggy-back the new Set-Cookie on the eventual response.
        pending_cookies: list[dict] = []
        request.state.bff_pending_cookies = pending_cookies

        try:
            await self._resolve_session(request)
        except (SQLAlchemyError, RuntimeError, ValueError) as exc:
            # Never fail open: if BFF resolution blew up, log and continue
            # without a session. Downstream auth dependencies will return
            # 401 if needed.
            _log.exception("BFFSessionMiddleware resolution failed: %s", exc)

        # CSRF check on cookie-authenticated mutators.
        if request.method in MUTATOR_METHODS and getattr(request.state, "bff_session_id", None):
            if not _origin_matches_host(request):
                return self._csrf_fail("Origin/Referer mismatch")
            csrf_header = request.headers.get(CSRF_HEADER_NAME, "")
            csrf_cookie = _read_cookie(request, CSRF_COOKIE_NAME) or ""
            if not csrf_header or csrf_header != csrf_cookie:
                return self._csrf_fail("CSRF token mismatch")
            # Hash compare against stored hash (defence in depth: even if
            # someone managed to inject a header without the cookie, the
            # hash check would still need to match).
            stored_hash = getattr(request.state, "bff_csrf_hash", None)
            if stored_hash and hash_csrf_token(csrf_header) != stored_hash:
                return self._csrf_fail("CSRF token hash mismatch")

        response = await call_next(request)

        # Apply any cookies the upgrade path queued.
        for kw in pending_cookies:
            response.set_cookie(**kw)

        return response

    async def _resolve_session(self, request: Request) -> None:
        """Populate ``request.state`` if a valid BFF session is found."""
        async with async_session_maker() as db:
            cookie_value = _get_bff_cookie(request)
            if cookie_value:
                await self._use_bff_cookie(db, request, cookie_value)
                return

            # Legacy compatibility: accept the old JWT cookie and silently
            # auto-upgrade to BFF. Disabled by setting once Phase 1.5 lands.
            if settings.bff_legacy_cookie_compat:
                legacy = _read_cookie(request, "access_token")
                if legacy:
                    await self._use_legacy_cookie(db, request, legacy)

    async def _use_bff_cookie(
        self,
        db,
        request: Request,
        cookie_value: str,
    ) -> None:
        from app.repositories.bff_session_repository import (
            FrontendSessionRepository,
        )

        repo = FrontendSessionRepository(db)
        sess = await repo.get_by_cookie_hash(hash_cookie_value(cookie_value))
        if sess is None:
            return
        if is_session_expired(sess):
            return

        # Verify the backing user_sessions row is still alive.
        if not await self._backend_session_active(db, sess.backend_session_id):
            return

        request.state.bff_session_id = sess.id
        request.state.bff_csrf_hash = sess.csrf_token_hash
        request.state.frontend_session = sess
        # Replay the real secure_sessions token into request.state so
        # set_rls_context() writes it to app.secure_session_token. This is
        # what makes PostgreSQL RLS policies that use get_current_user()
        # work under BFF — no synthetic sentinel.
        request.state.session_token = sess.backend_session_token
        request.state.user_id = str(sess.user_id)
        request.state.organization_id = str(sess.organization_id) if sess.organization_id else None
        request.state.bff_recent_auth_at = sess.recent_auth_at
        request.state.auth_source = "bff"

        # Sliding throttle handles "do nothing if not stale enough".
        try:
            await touch_session(db, sess)
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            _log.warning("BFF touch_session failed: %s", exc)

    async def _use_legacy_cookie(
        self,
        db,
        request: Request,
        legacy_token: str,
    ) -> None:
        """Decode legacy JWT cookie + auto-upgrade to BFF (idempotent).

        Failure to upgrade is non-fatal: the legacy JWT path in
        ``dependencies.py`` will still authenticate the request.
        """
        payload = decode_token(legacy_token)
        if payload is None or payload.type != "access":
            return

        # Look up the backing user_sessions row by its session token.
        from app.core.security import validate_session_in_db

        user_id_str = await validate_session_in_db(db, payload.sst)
        if not user_id_str:
            return

        # Fetch the secure_sessions / user_sessions row id (NOT the token).
        result = await db.execute(
            text(
                """
                SELECT us.id, u.organization_id
                FROM user_sessions us
                JOIN users u ON u.id = us.user_id
                WHERE us.token_hash = encode(digest(:tok, 'sha256'), 'hex')
                  AND NOT us.is_revoked
                LIMIT 1
                """
            ),
            {"tok": payload.sst},
        )
        row = result.fetchone()
        if not row:
            # digest() requires pgcrypto; if not installed, fall back to
            # Python-side hash + lookup. We avoid pgcrypto dependency
            # because not every client has it enabled.
            import hashlib as _hashlib

            tok_hash = _hashlib.sha256(payload.sst.encode()).hexdigest()
            result = await db.execute(
                text(
                    """
                    SELECT us.id, u.organization_id
                    FROM user_sessions us
                    JOIN users u ON u.id = us.user_id
                    WHERE us.token_hash = :h AND NOT us.is_revoked
                    LIMIT 1
                    """
                ),
                {"h": tok_hash},
            )
            row = result.fetchone()
            if not row:
                return

        backend_session_id = row[0]
        organization_id = row[1]

        try:
            result = await upgrade_legacy_session(
                db,
                request=request,
                user_id=UUID(user_id_str),
                organization_id=organization_id,
                backend_session_id=backend_session_id,
                # The legacy JWT's sst claim IS the real secure_sessions
                # token. Carry it into the new frontend_session row so RLS
                # keeps working identically post-upgrade.
                backend_session_token=payload.sst,
            )
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            _log.warning("Legacy upgrade failed: %s", exc)
            return

        if result is None:
            # Another concurrent request already upgraded; that's fine.
            return

        # Queue cookie + populate request.state so this very request is
        # already BFF-authenticated.
        is_https = request.url.scheme == "https"
        request.state.bff_pending_cookies.append(
            {
                "key": result.cookie.cookie_name,
                "value": result.cookie.cookie_value,
                "max_age": result.cookie.max_age_seconds,
                "httponly": True,
                "secure": is_https,
                "samesite": "lax",
                "path": "/",
            }
        )
        request.state.bff_pending_cookies.append(
            {
                "key": CSRF_COOKIE_NAME,
                "value": result.cookie.csrf_token,
                "max_age": result.cookie.max_age_seconds,
                "httponly": False,
                "secure": is_https,
                "samesite": "lax",
                "path": "/",
            }
        )
        request.state.bff_session_id = result.session.id
        request.state.bff_csrf_hash = result.session.csrf_token_hash
        request.state.frontend_session = result.session
        # Use the real token from the JWT — identical to what would be in
        # the newly-inserted frontend_session.backend_session_token.
        request.state.session_token = payload.sst
        request.state.user_id = user_id_str
        request.state.organization_id = str(organization_id) if organization_id else None
        request.state.bff_recent_auth_at = result.session.recent_auth_at
        request.state.auth_source = "bff_upgraded"

    async def _backend_session_active(self, db, backend_session_id: UUID) -> bool:
        """Check that the backing ``user_sessions`` row is alive."""
        result = await db.execute(
            text(
                """
                SELECT 1
                FROM user_sessions
                WHERE id = :id
                  AND NOT is_revoked
                  AND expires_at > NOW()
                LIMIT 1
                """
            ),
            {"id": str(backend_session_id)},
        )
        return result.fetchone() is not None

    @staticmethod
    def _csrf_fail(reason: str) -> Response:
        logger.warning("CSRF rejected", reason=reason)
        return Response(
            content=f'{{"detail":"CSRF validation failed: {reason}"}}',
            status_code=403,
            media_type="application/json",
        )
