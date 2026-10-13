"""
User repository - Data access for users.
Handles encrypted PII fields via PostgreSQL functions.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserSession
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    User repository with PII encryption support.

    All PII fields (email, full_name) are encrypted using PostgreSQL's
    encrypt_pii_with_metadata() function.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_display_name(self, user_id: UUID) -> str:
        """Get the display name for a user by ID.

        Handles the JSONB-encrypted name field: if name is a dict,
        extracts the 'value' key. Returns 'Unknown' if user not found.
        """
        result = await self.session.execute(
            text("SELECT name FROM users WHERE id = CAST(:uid AS UUID)"),
            {"uid": str(user_id)},
        )
        row = result.fetchone()
        if not row:
            return "Unknown"
        name = row.name
        if isinstance(name, dict):
            return name.get("value", "Unknown")
        return name or "Unknown"

    async def list_agents(self) -> list[dict[str, Any]]:
        """List active users available as agents."""
        result = await self.session.execute(
            text("""
                SELECT id, name, email, role FROM users
                WHERE is_active = true AND role IN ('admin', 'user', 'agent')
                ORDER BY name
            """)
        )
        agents = []
        for row in result.fetchall():
            name = row.name
            email = row.email
            if isinstance(name, dict):
                name = name.get("value", "Unknown")
            if isinstance(email, dict):
                email = email.get("value", None)
            agents.append({"id": row.id, "name": name, "email": email, "role": row.role})
        return agents

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email using email_hash for indexed lookup.

        RGPD Art. 32.1.a compliance:
        - Email is stored encrypted in JSONB
        - We use email_hash (SHA-256) for indexed lookups without decryption
        - This is both secure and performant
        """
        import hashlib

        # Calculate hash of lowercase email for lookup
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()

        result = await self.session.execute(
            select(User).where(User.email_hash == email_hash).where(User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create_with_encryption(
        self,
        email: str,
        password_hash: str,
        name: str | None = None,
        role: str = "user",
        organization_id: UUID | None = None,
        **kwargs: Any,
    ) -> User:
        """
        Create user with encrypted PII fields.
        Uses PostgreSQL's encrypt_pii_with_metadata() for encryption.

        RGPD Art. 32.1.a compliance:
        - Email and name are encrypted using AES-256
        - email_hash is stored for indexed lookups
        """
        import hashlib

        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()

        # Encrypt PII via PostgreSQL function. Cast :name to text so asyncpg
        # can infer the parameter type even when the value is NULL — without
        # the cast it raises AmbiguousParameterError on the IS NOT NULL check.
        # email_verified/is_locked/two_factor_enabled/etc. have NOT NULL
        # constraints without DB defaults, so the application must supply them.
        result = await self.session.execute(
            text("""
                INSERT INTO users (
                    email,
                    email_hash,
                    name,
                    password_hash,
                    password_algorithm,
                    role,
                    is_active,
                    is_locked,
                    failed_login_attempts,
                    last_login_ip_anonymized,
                    must_change_password,
                    two_factor_enabled,
                    email_verified,
                    organization_id
                )
                VALUES (
                    encrypt_pii_with_metadata(CAST(:email AS TEXT)),
                    :email_hash,
                    CASE WHEN CAST(:name AS TEXT) IS NOT NULL
                         THEN encrypt_pii_with_metadata(CAST(:name AS TEXT))
                         ELSE NULL
                    END,
                    :password_hash,
                    'bcrypt',
                    :role,
                    :is_active,
                    FALSE,
                    0,
                    FALSE,
                    TRUE,
                    FALSE,
                    FALSE,
                    CAST(:organization_id AS UUID)
                )
                RETURNING id
            """),
            {
                "email": email,
                "email_hash": email_hash,
                "name": name,
                "password_hash": password_hash,
                "role": role,
                "is_active": kwargs.get("is_active", True),
                "organization_id": str(organization_id) if organization_id else None,
            },
        )
        user_id = result.scalar_one()
        return await self.get_by_id(user_id)

    async def get_decrypted_email(self, user_id: UUID) -> str | None:
        """Get decrypted email for a user."""
        result = await self.session.execute(
            text("""
                SELECT decrypt_pii_with_metadata(email) as email
                FROM users
                WHERE id = :user_id
            """),
            {"user_id": str(user_id)},
        )
        row = result.fetchone()
        return row.email if row else None

    async def get_decrypted_user_data(self, user_id: UUID) -> dict[str, Any] | None:
        """
        Get user with decrypted PII fields.
        Used for GDPR Art. 15 access requests.

        Supports both:
        - Encrypted JSONB fields (production): uses decrypt_pii_with_metadata()
        - Plain VARCHAR fields (development/migration): uses values directly
        """
        try:
            # Use plain text query - works for both encrypted and plain fields
            # The decrypt_pii_with_metadata function handles JSONB internally
            # For plain text, we just return the value directly
            result = await self.session.execute(
                text("""
                    SELECT
                        id,
                        CASE
                            WHEN email IS NULL THEN NULL
                            WHEN email::text LIKE '{%%}' THEN decrypt_pii_with_metadata(email::jsonb)
                            ELSE email::text
                        END as email,
                        CASE
                            WHEN name IS NULL THEN NULL
                            WHEN name::text LIKE '{%%}' THEN decrypt_pii_with_metadata(name::jsonb)
                            ELSE name::text
                        END as name,
                        company,
                        role,
                        is_active,
                        email_verified,
                        two_factor_enabled,
                        last_login_at,
                        created_at,
                        updated_at
                    FROM users
                    WHERE id = :user_id
                    AND deleted_at IS NULL
                """),
                {"user_id": str(user_id)},
            )
            row = result.fetchone()
            if not row:
                return None

            return {
                "id": row.id,
                "email": row.email,
                "name": row.name,
                "company": row.company,
                "role": row.role,
                "is_active": row.is_active,
                "email_verified": row.email_verified,
                "two_factor_enabled": row.two_factor_enabled,
                "last_login_at": row.last_login_at,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        except SQLAlchemyError as e:
            # Fallback: plain text fields (development/simple setup)
            import logging

            logging.error(f"Error in get_decrypted_user_data: {e}")
            # Rollback aborted transaction before fallback query
            try:
                await self.session.rollback()
            except SQLAlchemyError:
                pass  # Defensive rollback — transaction may already be invalidated
            try:
                result = await self.session.execute(
                    text("""
                        SELECT
                            id, email::text, name::text, company, role, is_active,
                            email_verified, two_factor_enabled, last_login_at,
                            created_at, updated_at
                        FROM users
                        WHERE id = :user_id AND deleted_at IS NULL
                    """),
                    {"user_id": str(user_id)},
                )
                row = result.fetchone()
                if row:
                    return {
                        "id": row.id,
                        "email": row.email,
                        "name": row.name,
                        "company": row.company,
                        "role": row.role,
                        "is_active": row.is_active,
                        "email_verified": row.email_verified,
                        "two_factor_enabled": row.two_factor_enabled,
                        "last_login_at": row.last_login_at,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
            except SQLAlchemyError:
                pass
            return None

    async def update_last_login(
        self,
        user_id: UUID,
        ip_address: str | None = None,
    ) -> None:
        """Update last login timestamp and IP."""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=datetime.now(UTC),
                last_login_ip=ip_address,
                failed_login_attempts=0,
                locked_until=None,
            )
        )

    async def increment_failed_attempts(self, user_id: UUID) -> int:
        """Increment failed login attempts atomically and return new count."""
        result = await self.session.execute(
            text("""
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1
                WHERE id = :uid
                RETURNING failed_login_attempts
            """),
            {"uid": str(user_id)},
        )
        row = result.fetchone()
        return row[0] if row else 0

    async def lock_user(self, user_id: UUID, until: datetime) -> None:
        """Lock user until specified time."""
        await self.session.execute(
            update(User).where(User.id == user_id).values(locked_until=until)
        )

    async def get_by_role(
        self,
        role: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """Get users by role."""
        result = await self.session.execute(
            select(User)
            .where(User.role == role)
            .where(User.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """Get all active users."""
        result = await self.session.execute(
            select(User)
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_users_with_pii(
        self,
        *,
        organization_id: UUID | None,
        skip: int = 0,
        limit: int = 100,
        role: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """List users with decrypted PII, filtered by tenant.

        Performs tenant filtering, role/active filters, and decryption in one
        SQL pass. Returns (rows, total) where total is the count of all rows
        matching the filters before pagination — needed for correct page
        navigation in multi-tenant deployments.
        """
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        where = ["deleted_at IS NULL"]
        if organization_id is not None:
            where.append("organization_id = CAST(:org_id AS UUID)")
            params["org_id"] = str(organization_id)
        if role:
            where.append("role = :role")
            params["role"] = role
        if active_only:
            where.append("is_active = TRUE")

        where_sql = " AND ".join(where)

        # Decrypt PII inline (matches get_decrypted_user_data fallback logic
        # so the same query works for encrypted JSONB and plain-text columns).
        result = await self.session.execute(
            text(f"""
                SELECT
                    id,
                    CASE
                        WHEN email IS NULL THEN NULL
                        WHEN email::text LIKE '{{%%}}'
                            THEN decrypt_pii_with_metadata(email::jsonb)
                        ELSE email::text
                    END AS email,
                    CASE
                        WHEN name IS NULL THEN NULL
                        WHEN name::text LIKE '{{%%}}'
                            THEN decrypt_pii_with_metadata(name::jsonb)
                        ELSE name::text
                    END AS name,
                    company,
                    role,
                    is_active,
                    email_verified,
                    two_factor_enabled,
                    last_login_at,
                    created_at,
                    updated_at,
                    organization_id
                FROM users
                WHERE {where_sql}
                ORDER BY created_at DESC
                OFFSET :skip
                LIMIT :limit
            """),
            params,
        )
        rows = [dict(r) for r in result.mappings().all()]

        count_result = await self.session.execute(
            text(f"SELECT COUNT(*) FROM users WHERE {where_sql}"),
            {k: v for k, v in params.items() if k not in ("skip", "limit")},
        )
        total = int(count_result.scalar() or 0)
        return rows, total


class UserSessionRepository(BaseRepository[UserSession]):
    """Repository for user sessions."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, UserSession)

    async def get_by_token(self, token_hash: str) -> UserSession | None:
        """Get session by token hash."""
        result = await self.session.execute(
            select(UserSession)
            .where(UserSession.token_hash == token_hash)
            .where(UserSession.is_revoked.is_(False))
        )
        return result.scalar_one_or_none()

    async def get_active_sessions_for_user(
        self,
        user_id: UUID,
    ) -> list[UserSession]:
        """Get all active sessions for a user."""
        result = await self.session.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_revoked.is_(False))
            .where(UserSession.expires_at > datetime.now(UTC))
        )
        return list(result.scalars().all())

    async def invalidate_session(
        self,
        session_id: UUID,
        reason: str = "logout",
    ) -> bool:
        """Invalidate a session."""
        result = await self.session.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
                revoked_reason=reason,
            )
        )
        return result.rowcount > 0

    async def invalidate_all_user_sessions(
        self,
        user_id: UUID,
        reason: str = "logout_all",
    ) -> int:
        """Invalidate all sessions for a user."""
        result = await self.session.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_revoked.is_(False))
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
                revoked_reason=reason,
            )
        )
        return result.rowcount

    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        result = await self.session.execute(
            update(UserSession)
            .where(UserSession.expires_at < datetime.now(UTC))
            .where(UserSession.is_revoked.is_(False))
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
                revoked_reason="expired",
            )
        )
        return result.rowcount


class UserPreferencesRepository:
    """Repository for user_preferences table (no ORM model)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_rls_context(self, user_id: UUID) -> None:
        """Set RLS context for user_preferences table."""
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": str(user_id)},
        )

    async def get_preferences(self, user_id: UUID) -> dict[str, Any] | None:
        """Get user preferences. Returns None if not found."""
        await self.set_rls_context(user_id)
        result = await self.session.execute(
            text("SELECT visible_modules, theme FROM user_preferences WHERE user_id = :user_id"),
            {"user_id": str(user_id)},
        )
        row = result.fetchone()
        if not row:
            return None
        return {
            "visibleModules": list(row.visible_modules) if row.visible_modules else [],
            "theme": row.theme or "dark",
        }

    async def upsert_preferences(
        self, user_id: UUID, visible_modules: list[str], theme: str = "dark"
    ) -> None:
        """Insert or update user preferences."""
        check = await self.session.execute(
            text("SELECT user_id FROM user_preferences WHERE user_id = :user_id"),
            {"user_id": str(user_id)},
        )
        if check.fetchone():
            await self.session.execute(
                text("""
                    UPDATE user_preferences
                    SET visible_modules = CAST(:modules AS text[]),
                        theme = :theme,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id
                """),
                {"modules": visible_modules, "theme": theme, "user_id": str(user_id)},
            )
        else:
            await self.session.execute(
                text("""
                    INSERT INTO user_preferences (user_id, visible_modules, theme, updated_at)
                    VALUES (:user_id, CAST(:modules AS text[]), :theme, CURRENT_TIMESTAMP)
                """),
                {"user_id": str(user_id), "modules": visible_modules, "theme": theme},
            )

    ALLOWED_PII_FIELDS = {"email", "name"}

    async def update_encrypted_field(self, user_id: UUID, field: str, value: str | None) -> None:
        """Update an encrypted PII field (email or name)."""
        if field not in self.ALLOWED_PII_FIELDS:
            raise ValueError(f"Field {field} not allowed for encrypted update")
        if value:
            await self.session.execute(
                text(f"""
                    UPDATE users
                    SET {field} = encrypt_pii_with_metadata(:{field}),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """),
                {field: value, "user_id": str(user_id)},
            )
        else:
            await self.session.execute(
                text(f"""
                    UPDATE users
                    SET {field} = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """),
                {"user_id": str(user_id)},
            )


class OrganizationRepository:
    """Repository for organization queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tenant_features(self, org_id: UUID | None = None) -> dict[str, bool]:
        """Get feature flags for the tenant. Uses org_id when provided, otherwise first active org."""
        if org_id:
            result = await self.session.execute(
                text("""
                    SELECT settings, recording_enabled, sentiment_analysis_enabled,
                           robinson_check_enabled
                    FROM organizations
                    WHERE id = CAST(:org_id AS UUID)
                """),
                {"org_id": str(org_id)},
            )
        else:
            result = await self.session.execute(
                text("""
                    SELECT settings, recording_enabled, sentiment_analysis_enabled,
                           robinson_check_enabled
                    FROM organizations
                    WHERE is_active = true
                    LIMIT 1
                """)
            )
        row = result.fetchone()
        if not row:
            return {}

        org_settings = row.settings or {}
        return {
            "whatsapp": org_settings.get("whatsapp_enabled", False),
            "calendar": org_settings.get("calendar_enabled", False),
            "recordings": row.recording_enabled if row.recording_enabled is not None else False,
            "sentiment": row.sentiment_analysis_enabled
            if row.sentiment_analysis_enabled is not None
            else False,
            "robinson": row.robinson_check_enabled
            if row.robinson_check_enabled is not None
            else False,
            "outbound": org_settings.get("outbound_enabled", False),
            "newsletter": org_settings.get("newsletter_enabled", False),
            "captacion": org_settings.get("captacion_enabled", False),
            "whatsapp_emoji_filters": org_settings.get("whatsapp_emoji_filters", False),
            "avisos": org_settings.get("avisos_enabled", False),
            "trips": org_settings.get("trips_enabled", False),
        }

    async def set_marketing_opt_out(self, user_id: UUID) -> None:
        """Set marketing opt-out for a user (RGPD Art. 21.2)."""
        await self.session.execute(
            text("UPDATE users SET marketing_opt_out = true WHERE id = :user_id"),
            {"user_id": str(user_id)},
        )
