"""
Consent models - Maps to sferaai.sql consent tables.
Critical for RGPD Art. 6, 7 and LOPDGDD Art. 6 compliance.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.contact import Contact


class DataProcessingPurpose(Base):
    """
    Processing purposes with legal basis.
    Maps to sferaai.sql line 710.

    RGPD Art. 13: Purposes must be documented with legal basis.
    """

    __tablename__ = "data_processing_purposes"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(50), nullable=False)
    requires_ip_logging: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
    )
    ip_retention_days: Mapped[int | None] = mapped_column(nullable=True)
    ip_legal_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_period_days: Mapped[int] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )


class ConsentVersion(Base):
    """
    Consent text versions for traceability.
    Maps to sferaai.sql line 770.

    Each consent must reference a specific version of the legal text.
    UNIQUE(purpose_id, version).
    """

    __tablename__ = "consent_versions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    purpose_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_processing_purposes.id"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    consent_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full legal text of consent",
    )
    consent_text_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA256 of the displayed consent text",
    )
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default=text("'es'"),
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    effective_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    created_by: Mapped[UUID | None] = mapped_column(nullable=True)

    # Minor-adapted consent (ALTER TABLE addition)
    is_minor_adapted: Mapped[bool | None] = mapped_column(
        Boolean,
        server_default=text("false"),
    )
    reading_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="elementary, middle_school, high_school, adult",
    )

    __table_args__ = (
        UniqueConstraint("purpose_id", "version", name="uq_consent_versions_purpose_version"),
        Index("idx_consent_versions_purpose", "purpose_id", "is_active"),
    )


class DataConsent(Base):
    """
    General data processing consent.

    RGPD Art. 6.1.a: Consent as legal basis
    RGPD Art. 7: Consent conditions
    LOPDGDD Art. 6: Spanish consent requirements

    Subject model uses data_subject_id + data_subject_type (polymorphic)
    instead of separate user_id/contact_id FKs.
    Trigger validate_data_subject_exists() verifies subject exists.
    Trigger sync_consent_links() maintains user_consents/contact_consents junction tables.
    """

    __tablename__ = "data_consents"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # Subject (polymorphic: user or contact)
    data_subject_id: Mapped[UUID] = mapped_column(nullable=False)
    data_subject_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="user or contact",
    )

    # Purpose and version (mandatory FKs)
    purpose_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_processing_purposes.id"),
        nullable=False,
    )
    consent_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("consent_versions.id"),
        nullable=False,
    )

    # Consent status
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # When and how consent was obtained
    obtained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    obtained_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="explicit_checkbox, explicit_verbal, explicit_written, "
        "web_form, phone_ivr, email, in_person",
    )

    # Context
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    ip_anonymized: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Evidence (RGPD Art. 7.1, LOPDGDD Art. 6.3)
    evidence_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="form_submission, audio_recording, email_reply, signed_document, ivr_recording",
    )
    evidence_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of evidence file",
    )

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Revocation (RGPD Art. 7.3)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_method: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Metadata (Python attr 'extra_metadata' maps to SQL column 'metadata')
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        server_default=text("'{}'"),
    )

    # Minor consent (LOPDGDD Art. 7.2)
    parental_consent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("data_consents.id"),
        nullable=True,
    )
    parental_consent_required: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
    )

    # Audit
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )

    __table_args__ = (
        CheckConstraint(
            "data_subject_type IN ('user', 'contact')",
            name="data_consents_subject_type_check",
        ),
        CheckConstraint(
            "obtained_method IN ('explicit_checkbox', 'explicit_verbal', "
            "'explicit_written', 'web_form', 'phone_ivr', 'email', 'in_person')",
            name="data_consents_method_check",
        ),
        CheckConstraint(
            "evidence_type IS NULL OR evidence_type IN ('form_submission', "
            "'audio_recording', 'email_reply', 'signed_document', 'ivr_recording')",
            name="data_consents_evidence_check",
        ),
        Index("idx_consents_subject", "data_subject_id", "data_subject_type"),
        Index("idx_consents_purpose", "purpose_id"),
        Index(
            "idx_consents_active",
            "consent_given",
            "revoked_at",
            postgresql_where="consent_given = true AND revoked_at IS NULL",
        ),
    )


class ContactConsent(Base):
    """
    Junction table linking contacts to data_consents.
    Maps to sferaai.sql line 1138.

    This is NOT a standalone consent table — it links a contact
    to their DataConsent record via consent_id FK.
    """

    __tablename__ = "contact_consents"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    consent_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_consents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    contact: Mapped["Contact"] = relationship(back_populates="consents")
    consent: Mapped["DataConsent"] = relationship()

    __table_args__ = (
        Index("idx_contact_consents_contact", "contact_id"),
        Index("idx_contact_consents_consent", "consent_id"),
    )


class CallProcessingConsent(Base):
    """
    Links a call to a specific consent + processing purpose.
    Maps to sferaai.sql line 1330.

    RGPD Art. 5.1.b: Purpose limitation — each call processing
    must reference a specific consent and purpose.
    UNIQUE(call_id, purpose_id).
    """

    __tablename__ = "call_processing_consents"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    call_id: Mapped[UUID] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_processing_purposes.id"),
        nullable=False,
    )
    consent_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_consents.id"),
        nullable=False,
    )
    processing_enabled: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    retention_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Calculated from data_processing_purposes.retention_period_days",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )

    __table_args__ = (
        UniqueConstraint(
            "call_id", "purpose_id", name="call_processing_consents_call_id_purpose_id_key"
        ),
        Index("idx_call_processing_call", "call_id"),
        Index("idx_call_processing_purpose", "purpose_id"),
        Index("idx_call_processing_consent", "consent_id"),
        Index(
            "idx_call_processing_retention",
            "retention_until",
            postgresql_where="retention_until IS NOT NULL AND processing_enabled = true",
        ),
    )
