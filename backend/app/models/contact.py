"""
Contact model - Maps to sferaai.sql contacts table.
External contacts (customers/leads) - separate from internal users.

RGPD Art. 32: All PII encrypted
RGPD Art. 5.1.d: Accuracy fields for data verification
"""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.call import Call
    from app.models.consent import ContactConsent


class Contact(Base, TimestampMixin, SoftDeleteMixin):
    """
    External contact (customer/lead).

    All PII fields are encrypted using PostgreSQL's encrypt_pii_with_metadata().

    Compliance:
    - RGPD Art. 32: Encryption at rest
    - RGPD Art. 5.1.d: Accuracy (data_verified_at, accuracy_flag)
    - RGPD Art. 17: Deletion support (soft delete + blocking)
    - LOPDGDD Art. 7: Minor consent verification (birth_date)
    """

    __tablename__ = "contacts"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # External reference (for CRM integration)
    external_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    # Encrypted PII fields (JSONB)
    phone: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Encrypted phone - RGPD Art. 32",
    )
    email: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Encrypted email - RGPD Art. 32",
    )
    full_name: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Encrypted full name - RGPD Art. 32",
    )
    address: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Encrypted address - RGPD Art. 32",
    )
    dni_nie: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Encrypted DNI/NIE - RGPD Art. 32",
    )

    # Non-PII identifiers (for lookups)
    phone_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA-256 hash for phone lookup",
    )
    email_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA-256 hash for email lookup",
    )

    # Minor consent verification (LOPDGDD Art. 7)
    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="For minor consent verification - Spain: 14 years",
    )

    # Data accuracy (RGPD Art. 5.1.d)
    data_verified_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Last verification timestamp",
    )
    accuracy_flag: Mapped[str | None] = mapped_column(
        String(20),
        default="unverified",
        comment="verified, unverified, disputed",
    )

    # Marketing preferences (RGPD Art. 21.2)
    marketing_opt_out: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Marketing opposition - immediate effect",
    )
    profiling_opt_out: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Profiling opposition - excludes from sentiment analysis",
    )

    # Processing restriction (RGPD Art. 18)
    processing_restricted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="When true, only storage allowed",
    )
    restriction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    restriction_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # Robinson list tracking (LOPDGDD Art. 34)
    last_robinson_check: Mapped[datetime | None] = mapped_column(nullable=True)
    robinson_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="listed, not_listed, unknown",
    )

    # Organization (multi-tenant)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Source tracking (RGPD Art. 14 - indirect data sources)
    data_source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Origin of contact data",
    )
    data_source_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    calls: Mapped[list["Call"]] = relationship(
        back_populates="contact",
        foreign_keys="Call.contact_id",
    )
    consents: Mapped[list["ContactConsent"]] = relationship(
        back_populates="contact",
    )

    __table_args__ = (
        Index("idx_contacts_phone_hash", "phone_hash"),
        Index("idx_contacts_email_hash", "email_hash"),
        Index("idx_contacts_external_id", "external_id"),
        Index("idx_contacts_organization", "organization_id"),
        Index(
            "idx_contacts_active",
            "id",
            postgresql_where="deleted_at IS NULL AND processing_restricted = false",
        ),
    )

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, external_id={self.external_id})>"
