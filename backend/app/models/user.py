"""
User model - Maps to capsulecorp.sql users table.
RGPD Art. 32: Encrypted PII fields.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.call import Call
    from app.models.organization import Organization
    from app.models.permission import UserPermission


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    User model for internal system users (agents, supervisors, admins).

    Maps to the users table in capsulecorp.sql schema.

    Compliance:
    - RGPD Art. 32: Encryption at rest
    - RGPD Art. 5.1.f: Integrity
    - LOPDGDD Art. 5: Confidentiality
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # User info - PII fields encrypted (RGPD Art. 32.1.a)
    # These are JSONB containing encrypted data from encrypt_pii_with_metadata()
    name: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Encrypted name using encrypt_pii_with_metadata()",
    )
    email: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Encrypted email using encrypt_pii_with_metadata()",
    )
    # Hash for indexed lookups without decryption
    email_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        comment="SHA-256 hash of lowercase email for indexed lookups",
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Authentication
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    password_algorithm: Mapped[str] = mapped_column(
        String(50),
        default="bcrypt",
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        server_default=func.current_timestamp(),
    )
    password_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Company
    company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Organization (tenant binding)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=True,
    )

    # Role: superadmin, client_admin, user
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="user",
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)

    # Login tracking
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    last_login_ip_anonymized: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # Password policy
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # Two-factor authentication (NIS2 Art. 21.2.j)
    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    two_factor_secret_encrypted: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    two_factor_backup_codes_encrypted: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization | None"] = relationship(
        foreign_keys=[organization_id],
    )
    calls: Mapped[list["Call"]] = relationship(
        back_populates="agent",
        foreign_keys="Call.agent_id",
    )
    permissions: Mapped[list["UserPermission"]] = relationship(
        back_populates="user",
        foreign_keys="UserPermission.user_id",
        cascade="all, delete-orphan",
    )
    # Note: DataConsent uses polymorphic data_subject_id/data_subject_type
    # instead of a direct user_id FK. Query via ConsentRepository.

    __table_args__ = (
        # Use email_hash for indexed lookups (RGPD Art. 32.1.a - no decryption needed)
        Index(
            "idx_users_email_hash", "email_hash", postgresql_where="deleted_at IS NULL", unique=True
        ),
        Index("idx_users_role", "role", postgresql_where="deleted_at IS NULL"),
        Index(
            "idx_users_org_role", "organization_id", "role", postgresql_where="deleted_at IS NULL"
        ),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class UserSession(Base):
    """
    User session for tracking active sessions.
    Maps to user_sessions table.
    """

    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    token_algorithm: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="hmac-sha256",
    )
    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )
    refresh_token_algorithm: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="hmac-sha256",
    )
    session_fingerprint: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    refresh_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    ip_anonymized: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        server_default=func.current_timestamp(),
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=True,
        server_default=func.current_timestamp(),
    )
