"""Repositories for BFF frontend sessions and API tokens.

Sessions are looked up by SHA-256(cookie_value); the raw cookie never
touches storage. The advisory-lock helper is used by the legacy upgrade
path to make concurrent first-requests idempotent.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bff_session import ApiToken, FrontendSession


def _hash_to_int64(value: str) -> int:
    """Map a string to a signed int64 for ``pg_advisory_xact_lock``.

    Uses ``hashlib.sha256`` (deterministic across processes and Python
    instances) instead of Python's built-in ``hash()`` which is
    randomized per process (PYTHONHASHSEED). With multi-worker Uvicorn
    deployments, the built-in hash would yield different lock keys per
    worker and break the serialization guarantee we rely on for
    idempotent legacy-session upgrades.
    """
    digest = hashlib.sha256(value.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, byteorder="big", signed=True)


class FrontendSessionRepository:
    """CRUD + lookup for ``frontend_sessions``."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_cookie_hash(self, cookie_hash: str) -> FrontendSession | None:
        result = await self.session.execute(
            text(
                """
                SELECT * FROM frontend_sessions
                WHERE cookie_hash = :h AND NOT is_revoked
                LIMIT 1
                """
            ),
            {"h": cookie_hash},
        )
        row = result.mappings().first()
        return FrontendSession(**dict(row)) if row else None

    async def get_by_backend_session(self, backend_session_id: UUID) -> FrontendSession | None:
        """Return the **live** frontend session for a backend session, if any.

        Filters out rows that are revoked OR whose ``idle_expires_at`` /
        ``absolute_expires_at`` have passed. This prevents a stale,
        uncollected row (e.g. before the ARQ cleanup job runs) from
        blocking a legitimate re-upgrade of the same backend session.
        """
        result = await self.session.execute(
            text(
                """
                SELECT * FROM frontend_sessions
                WHERE backend_session_id = :sid
                  AND NOT is_revoked
                  AND idle_expires_at > NOW()
                  AND absolute_expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"sid": str(backend_session_id)},
        )
        row = result.mappings().first()
        return FrontendSession(**dict(row)) if row else None

    async def acquire_upgrade_lock(self, backend_session_id: UUID) -> None:
        """Take a transaction-scoped advisory lock keyed by backend session.

        Released automatically on COMMIT/ROLLBACK. Used by the legacy
        upgrade path to serialize concurrent first-requests for the same
        ``user_sessions`` row, so we only ever create one
        ``frontend_sessions`` row.
        """
        key = _hash_to_int64(f"bff_upgrade:{backend_session_id}")
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})

    async def insert(self, data: dict[str, Any]) -> FrontendSession:
        """Insert a new session row and return it."""
        cols = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data)
        result = await self.session.execute(
            text(
                f"""
                INSERT INTO frontend_sessions ({cols})
                VALUES ({placeholders})
                RETURNING *
                """
            ),
            data,
        )
        row = result.mappings().one()
        return FrontendSession(**dict(row))

    async def touch_last_seen(
        self,
        session_id: UUID,
        new_idle_expires_at: datetime,
        throttle_seconds: int,
    ) -> bool:
        """Update last_seen_at only if older than ``throttle_seconds``.

        Returns True if a row was actually updated.
        """
        result = await self.session.execute(
            text(
                """
                UPDATE frontend_sessions
                SET last_seen_at    = NOW(),
                    idle_expires_at = :new_idle
                WHERE id = :id
                  AND NOT is_revoked
                  AND last_seen_at < NOW() - (:throttle * INTERVAL '1 second')
                """
            ),
            {
                "id": str(session_id),
                "new_idle": new_idle_expires_at,
                "throttle": throttle_seconds,
            },
        )
        return result.rowcount > 0

    async def update_recent_auth(self, session_id: UUID, method: str) -> None:
        await self.session.execute(
            text(
                """
                UPDATE frontend_sessions
                SET recent_auth_at = NOW(),
                    auth_method    = :m
                WHERE id = :id
                """
            ),
            {"id": str(session_id), "m": method},
        )

    async def revoke(self, session_id: UUID, reason: str) -> None:
        await self.session.execute(
            text(
                """
                UPDATE frontend_sessions
                SET is_revoked = TRUE,
                    revoked_at = NOW(),
                    revoked_reason = :r
                WHERE id = :id AND NOT is_revoked
                """
            ),
            {"id": str(session_id), "r": reason[:64]},
        )

    async def revoke_by_backend_session(self, backend_session_id: UUID, reason: str) -> int:
        """Revoke any frontend session bound to a given backend session.

        Returns the number of rows revoked. Used on logout / password change.
        """
        result = await self.session.execute(
            text(
                """
                UPDATE frontend_sessions
                SET is_revoked = TRUE,
                    revoked_at = NOW(),
                    revoked_reason = :r
                WHERE backend_session_id = :sid AND NOT is_revoked
                """
            ),
            {"sid": str(backend_session_id), "r": reason[:64]},
        )
        return result.rowcount


class ApiTokenRepository:
    """CRUD + lookup for ``api_tokens``."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_token_hash(self, token_hash: str) -> ApiToken | None:
        result = await self.session.execute(
            text(
                """
                SELECT * FROM api_tokens
                WHERE token_hash = :h
                  AND NOT is_revoked
                  AND expires_at > NOW()
                LIMIT 1
                """
            ),
            {"h": token_hash},
        )
        row = result.mappings().first()
        return ApiToken(**dict(row)) if row else None

    async def count_active_for_user(self, user_id: UUID) -> int:
        result = await self.session.execute(
            text(
                """
                SELECT COUNT(*) FROM api_tokens
                WHERE user_id = :uid
                  AND NOT is_revoked
                  AND expires_at > NOW()
                """
            ),
            {"uid": str(user_id)},
        )
        return int(result.scalar() or 0)

    async def list_for_user(self, user_id: UUID) -> list[ApiToken]:
        result = await self.session.execute(
            text(
                """
                SELECT * FROM api_tokens
                WHERE user_id = :uid AND NOT is_revoked
                ORDER BY created_at DESC
                """
            ),
            {"uid": str(user_id)},
        )
        return [ApiToken(**dict(r)) for r in result.mappings().all()]

    async def insert(self, data: dict[str, Any]) -> ApiToken:
        cols = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data)
        result = await self.session.execute(
            text(
                f"""
                INSERT INTO api_tokens ({cols})
                VALUES ({placeholders})
                RETURNING *
                """
            ),
            data,
        )
        row = result.mappings().one()
        return ApiToken(**dict(row))

    async def touch_last_used(self, token_id: UUID) -> None:
        await self.session.execute(
            text("UPDATE api_tokens SET last_used_at = NOW() WHERE id = :id"),
            {"id": str(token_id)},
        )

    async def revoke(self, token_id: UUID, user_id: UUID, reason: str) -> bool:
        """Revoke a token. Returns True if the token belonged to the user
        and was actually revoked (idempotent against re-revoke)."""
        result = await self.session.execute(
            text(
                """
                UPDATE api_tokens
                SET is_revoked = TRUE,
                    revoked_at = NOW(),
                    revoked_reason = :r
                WHERE id = :id AND user_id = :uid AND NOT is_revoked
                """
            ),
            {"id": str(token_id), "uid": str(user_id), "r": reason[:64]},
        )
        return result.rowcount > 0
