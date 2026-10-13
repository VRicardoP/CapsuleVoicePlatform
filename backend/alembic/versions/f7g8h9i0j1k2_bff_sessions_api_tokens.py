"""Add BFF sessions + API tokens (Phase 1 of BFF migration).

Introduces opaque cookie sessions to hide JWTs from the browser:
- ``frontend_sessions``: opaque cookie ↔ user_sessions mapping.
- ``api_tokens``: bearer-style tokens for server-to-server / CI usage.

The existing JWT flow keeps working in parallel during the 7-day
coexistence window (Phase 1). Phase 1.5 retires the JWT path.

Revision ID: f7g8h9i0j1k2
Revises: e6f7g8h9i0j1
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f7g8h9i0j1k2"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7g8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS frontend_sessions (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cookie_hash          TEXT NOT NULL UNIQUE,
            user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            organization_id      UUID,
            backend_session_id   UUID NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
            -- Plaintext token replayed into app.secure_session_token so that
            -- PostgreSQL RLS policies using get_current_user() validate
            -- against secure_sessions as designed. Never leaves the backend.
            backend_session_token TEXT NOT NULL,
            csrf_token_hash      TEXT NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            idle_expires_at      TIMESTAMPTZ NOT NULL,
            absolute_expires_at  TIMESTAMPTZ NOT NULL,
            recent_auth_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            auth_method          VARCHAR(32) NOT NULL,
            upgraded_from_legacy BOOLEAN NOT NULL DEFAULT FALSE,
            ip_address           INET,
            user_agent           TEXT,
            is_revoked           BOOLEAN NOT NULL DEFAULT FALSE,
            revoked_at           TIMESTAMPTZ,
            revoked_reason       VARCHAR(64)
        );
        """
    )
    # Partial unique on active rows: cookie_hash uniqueness already enforced by
    # the column constraint, but the partial index speeds up the lookup hot path.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_frontend_sessions_cookie_active
            ON frontend_sessions(cookie_hash) WHERE NOT is_revoked;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_frontend_sessions_backend_active
            ON frontend_sessions(backend_session_id) WHERE NOT is_revoked;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_frontend_sessions_user_active
            ON frontend_sessions(user_id) WHERE NOT is_revoked;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_frontend_sessions_cleanup
            ON frontend_sessions(idle_expires_at) WHERE NOT is_revoked;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS api_tokens (
            id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            token_hash            TEXT NOT NULL UNIQUE,
            user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            organization_id       UUID,
            scope                 TEXT[] NOT NULL,
            description           TEXT NOT NULL,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at            TIMESTAMPTZ NOT NULL,
            last_used_at          TIMESTAMPTZ,
            is_revoked            BOOLEAN NOT NULL DEFAULT FALSE,
            revoked_at            TIMESTAMPTZ,
            revoked_reason        VARCHAR(64),
            created_by_session_id UUID REFERENCES frontend_sessions(id) ON DELETE SET NULL
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_api_tokens_hash_active
            ON api_tokens(token_hash) WHERE NOT is_revoked;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_api_tokens_user_active
            ON api_tokens(user_id) WHERE NOT is_revoked;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS api_tokens CASCADE;")
    op.execute("DROP TABLE IF EXISTS frontend_sessions CASCADE;")
