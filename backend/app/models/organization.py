"""
Organization model for multi-tenant support.
"""

from uuid import UUID

from sqlalchemy import Boolean, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    """
    Organization entity for multi-tenant support.
    Each organization has its own data isolation via RLS.
    """

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="URL-safe identifier",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Legal info (RGPD Art. 13.1.a)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="CIF/NIF",
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Contact
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # DPO info (RGPD Art. 37.7, LOPDGDD Art. 34)
    dpo_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dpo_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dpo_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Subscription/limits
    max_users: Mapped[int | None] = mapped_column(default=100)
    max_calls_per_month: Mapped[int | None] = mapped_column(nullable=True)

    # Settings
    settings: Mapped[dict | None] = mapped_column(
        JSONB,
        default=dict,
        comment="Organization-specific settings",
    )

    # Compliance settings
    default_retention_days: Mapped[int | None] = mapped_column(
        default=90,
        comment="Default data retention period",
    )
    robinson_check_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    recording_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sentiment_analysis_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("idx_organizations_slug", "slug"),
        Index("idx_organizations_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"


class OrganizationSettings(Base, TimestampMixin):
    """
    Detailed organization settings stored as key-value pairs.
    """

    __tablename__ = "organization_settings"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("idx_org_settings_org_key", "organization_id", "key", unique=True),)
