"""BFF (Backend-for-Frontend) session models.

Implements opaque cookie sessions that hide JWT tokens from the browser
(RGPD Art. 32, defence in depth against XSS-as-token-theft).

- ``FrontendSession``: opaque cookie ↔ backend ``user_sessions`` mapping.
- ``ApiToken``: bearer-style tokens for server-to-server / CI use only.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, INET
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FrontendSession(Base):
    """Opaque browser session backed by a ``user_sessions`` row.

    The browser only sees a random cookie value; the cookie's SHA-256 hash
    is what we look up here. ``backend_session_id`` points to the
    ``user_sessions`` row that holds the actual session token used by RLS
    and validated by ``validate_session_in_db()``.
    """

    __tablename__ = "frontend_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    cookie_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        comment="SHA-256(cookie_value)",
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[UUID | None] = mapped_column(nullable=True)
    backend_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    backend_session_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Plaintext secure_sessions token. Server-only — used to set "
        "app.secure_session_token for RLS. Never leaves the backend.",
    )

    csrf_token_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="SHA-256(csrf_token); validated against X-CSRF-Token header",
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    idle_expires_at: Mapped[datetime] = mapped_column(nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(nullable=False)

    recent_auth_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Last password / passkey re-auth (gates require_recent_auth)",
    )
    auth_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="'password' | 'passkey'",
    )
    upgraded_from_legacy: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
        comment="True if this session was created by auto-upgrade of a legacy JWT cookie",
    )

    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ApiToken(Base):
    """Bearer-style API token for server-to-server / CI integrations.

    Issued via ``POST /auth/api-token`` after recent re-auth. Scope-limited
    (subset of caller's permissions). NOT used by the dashboard.
    """

    __tablename__ = "api_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[UUID | None] = mapped_column(nullable=True)
    scope: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)

    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_by_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("frontend_sessions.id", ondelete="SET NULL"), nullable=True
    )
