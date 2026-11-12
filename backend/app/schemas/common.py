"""Common schemas for GDPR-compliant data handling.

These schemas handle:
- Encrypted PII fields (RGPD Art. 32)
- Consent tracking (RGPD Art. 7)
- Data portability format (RGPD Art. 20)
- Audit metadata (RGPD Art. 30)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Generic type for paginated responses
T = TypeVar("T")


class ConsentScope(str, Enum):
    """RGPD consent scopes (Art. 6, Art. 9)."""

    RECORDING = "RECORDING"
    BIOMETRIC_AUTH = "BIOMETRIC_AUTH"
    SENTIMENT_ANALYSIS = "SENTIMENT_ANALYSIS"
    MARKETING = "MARKETING"
    DATA_PROCESSING = "DATA_PROCESSING"
    INTERNATIONAL_TRANSFER = "INTERNATIONAL_TRANSFER"


class LegalBasis(str, Enum):
    """RGPD legal basis for processing (Art. 6)."""

    CONSENT = "CONSENT"
    CONTRACT = "CONTRACT"
    LEGAL_OBLIGATION = "LEGAL_OBLIGATION"
    VITAL_INTERESTS = "VITAL_INTERESTS"
    PUBLIC_INTEREST = "PUBLIC_INTEREST"
    LEGITIMATE_INTEREST = "LEGITIMATE_INTEREST"


class DataLifecycleStatus(str, Enum):
    """Data lifecycle status (LOPDGDD Art. 33)."""

    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"  # LOPDGDD Art. 33 - blocked but not deleted
    PENDING_DELETION = "PENDING_DELETION"
    DELETED = "DELETED"


class EncryptedField(BaseModel):
    """Schema for encrypted PII field from PostgreSQL.

    This represents the JSONB structure returned by encrypt_pii_with_metadata().
    The backend receives this structure and stores it as-is.
    Decryption happens via decrypt_pii_with_metadata() when needed.
    """

    c: str = Field(..., description="Base64 encoded ciphertext")
    iv: str = Field(..., description="Base64 encoded initialization vector")
    tag: str = Field(..., description="Base64 encoded HMAC authentication tag")
    alg: str = Field(default="AES-256-CBC+HMAC-SHA256", description="Algorithm used")
    kid: str = Field(..., description="Encryption key ID")
    v: int = Field(..., description="Key version")


class PaginatedResponse(BaseModel, Generic[T]):  # noqa: UP046
    """Generic paginated response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditMetadata(BaseModel):
    """Audit metadata for RGPD compliance (Art. 30).

    This metadata is attached to responses that involve personal data.
    """

    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str | None = Field(None, description="Requesting user ID")
    purpose: str | None = Field(None, description="Processing purpose")
    legal_basis: LegalBasis | None = Field(None, description="Legal basis for access")


class GDPRDataExport(BaseModel):
    """RGPD Art. 20 data portability export format.

    This is the structure returned by export_user_data_gdpr_compliant().
    """

    export_metadata: dict[str, Any] = Field(
        ...,
        description="Export metadata including timestamp, version, legal basis",
    )
    personal_data: dict[str, Any] = Field(
        ...,
        description="All personal data associated with the user",
    )
    consents: list[dict[str, Any]] = Field(
        default_factory=list,
        description="History of consents given/withdrawn",
    )
    processing_activities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Record of processing activities",
    )
    third_party_data: dict[str, Any] | None = Field(
        None,
        description="Data shared with third parties (anonymized per Art. 15.4)",
    )


class ConsentRecord(BaseModel):
    """Consent record for RGPD Art. 7 compliance.

    Maps to data_consents table (capsulecorp.sql line 788).
    Active = consent_given=True AND revoked_at IS NULL.
    """

    consent_id: str
    purpose_code: str = Field(..., description="Purpose code from data_processing_purposes")
    consent_given: bool = True
    obtained_at: datetime = Field(..., description="When consent was obtained")
    obtained_method: str = Field(
        ..., description="explicit_checkbox, explicit_verbal, web_form, etc."
    )
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_reason: str | None = None


class RightsRequest(BaseModel):
    """RGPD rights request (Arts. 15-22).

    Used for:
    - Access requests (Art. 15)
    - Rectification requests (Art. 16)
    - Erasure requests (Art. 17)
    - Restriction requests (Art. 18)
    - Portability requests (Art. 20)
    - Objection requests (Art. 21)
    """

    request_type: str = Field(
        ...,
        description="ACCESS, RECTIFICATION, ERASURE, RESTRICTION, PORTABILITY, OBJECTION",
    )
    details: str | None = Field(None, description="Additional request details")
    fields_affected: list[str] | None = Field(
        None,
        description="Specific fields for rectification/erasure",
    )


class RightsRequestResponse(BaseModel):
    """Response to a RGPD rights request."""

    request_id: str
    request_type: str
    status: str = Field(..., description="RECEIVED, PROCESSING, COMPLETED, REJECTED")
    received_at: datetime
    response_due_date: datetime = Field(
        ...,
        description="RGPD Art. 12.3: Max 1 month",
    )
    response_sent_at: datetime | None = None
    response_details: str | None = None


class BlockedDataInfo(BaseModel):
    """Information about blocked data (LOPDGDD Art. 33).

    When data is "deleted", it's actually blocked per Spanish law.
    This info shows the blocking status.
    """

    block_id: str
    blocked_at: datetime
    block_reason: str
    unblock_date: datetime = Field(
        ...,
        description="Date when data will be permanently deleted",
    )
    accessible_by: list[str] = Field(
        default_factory=lambda: ["JUDGES", "PROSECUTORS", "COMPETENT_AUTHORITIES"],
        description="LOPDGDD Art. 33.3 - Who can access blocked data",
    )


class AIDecisionInfo(BaseModel):
    """AI decision information for AI Act Art. 12 compliance.

    Maps to ai_decision_logs table (capsulecorp.sql line 1655).
    Used when AI makes or assists in decisions.
    """

    decision_id: str
    model_name: str
    model_version: str
    decision_timestamp: datetime
    output_type: str
    output_summary: str | None = None
    output_confidence: float | None = None
    ai_risk_level: str | None = None
    human_oversight_required: bool = False
    human_reviewer_id: str | None = None
    human_review_decision: str | None = None
