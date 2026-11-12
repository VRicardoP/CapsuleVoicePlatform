"""Schemas for PBX/Centralita endpoints.

These schemas define the data structures for call lifecycle management.
All operations must comply with:
- RGPD Art. 7: Consent for recording
- RGPD Art. 13: Prior information
- LOPDGDD Art. 33: Robinson list verification
- AI Act Art. 50.1: AI disclosure before interaction
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CallDirection(str, Enum):
    """Call direction."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class CallStatus(str, Enum):
    """Call lifecycle status."""

    INITIATED = "initiated"
    RINGING = "ringing"
    ANSWERED = "answered"
    ON_HOLD = "on_hold"
    TRANSFERRED = "transferred"
    ENDED = "ended"
    FAILED = "failed"
    ABANDONED = "abandoned"


class CallPurpose(str, Enum):
    """Purpose of the call."""

    SUPPORT = "support"
    SALES = "sales"
    COMMERCIAL = "commercial"
    COLLECTION = "collection"
    SURVEY = "survey"
    INFORMATION = "information"
    OTHER = "other"


class ConsentMethod(str, Enum):
    """Method of obtaining consent."""

    VOICE = "voice"
    DTMF = "dtmf"  # Keypad press
    WEB = "web"
    WRITTEN = "written"
    IMPLICIT = "implicit"  # For legal basis other than consent


# ============================================================================
# CALL CREATION SCHEMAS
# ============================================================================


class CallCreate(BaseModel):
    """Create a new call record.

    This should be called BEFORE the call is connected to establish
    the record for compliance tracking.
    """

    # Call identification
    external_call_id: str | None = Field(
        None, description="External system call ID (e.g., Asterisk uniqueid)"
    )

    # Parties
    caller_number: str = Field(..., description="Calling party number (CLI)")
    called_number: str = Field(..., description="Called party number (DNIS)")
    contact_id: str | None = Field(None, description="Contact UUID if identified")
    agent_id: str | None = Field(None, description="Agent/user UUID if assigned")

    # Call metadata
    direction: CallDirection = Field(...)
    call_type: str | None = Field(None, description="Call type classification")
    purpose: CallPurpose = Field(default=CallPurpose.SUPPORT)
    campaign_id: str | None = Field(None, description="Campaign UUID if outbound campaign call")
    queue_name: str | None = Field(None, description="Queue the call entered")
    ivr_path: str | None = Field(None, description="IVR path taken")
    is_employee_call: bool = Field(False, description="Whether this is an internal employee call")
    metadata: dict | None = Field(None, description="Additional call metadata")

    # Equipment identification (Ley 25/2007 Art. 3.3)
    equipment_id: str | None = Field(None, description="Equipment identifier for legal retention")

    # Robinson verification (for outbound commercial calls)
    robinson_checked: bool = Field(
        default=False,
        description="Was Robinson list checked? Required for outbound commercial",
    )
    robinson_check_id: str | None = Field(None, description="Reference to robinson_checks record")

    @field_validator("robinson_checked")
    @classmethod
    def validate_robinson(cls, v: bool, info) -> bool:
        """Require Robinson check for outbound commercial calls."""
        direction = info.data.get("direction")
        purpose = info.data.get("purpose")

        if (
            direction == CallDirection.OUTBOUND
            and purpose in (CallPurpose.COMMERCIAL, CallPurpose.SALES)
            and not v
        ):
            raise ValueError("LOPDGDD: robinson_checked must be true for outbound commercial calls")
        return v


class CallStatusUpdate(BaseModel):
    """Update call status."""

    status: CallStatus = Field(...)
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this status change occurred",
    )

    # Optional fields for specific status changes
    end_reason: str | None = Field(None, description="Reason for call end (hangup, transfer, etc)")
    transferred_to: str | None = Field(None, description="Destination if transferred")
    hold_duration_seconds: int | None = Field(None, description="Duration of hold if applicable")


# ============================================================================
# AI DISCLOSURE SCHEMAS (AI Act Art. 50.1)
# ============================================================================


class AIDisclosureCreate(BaseModel):
    """Register that AI disclosure was made.

    REQUIRED by AI Act Art. 50.1 BEFORE any AI interaction.
    Typically done by IVR announcement.
    """

    call_id: str = Field(...)
    disclosure_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the disclosure was made",
    )
    disclosure_method: str = Field(
        default="ivr_announcement",
        description="How disclosure was made: ivr_announcement, agent_verbal, etc",
    )
    disclosure_text_version: str = Field(
        default="v1",
        description="Version of the disclosure text used",
    )
    language: str = Field(default="es", description="Language of disclosure")

    # Emotion detection disclosure (AI Act Art. 50.3)
    emotion_detection_disclosed: bool = Field(
        default=False,
        description="Was emotion/sentiment analysis disclosed?",
    )


# ============================================================================
# CONSENT SCHEMAS (RGPD Art. 7)
# ============================================================================


class ConsentCreate(BaseModel):
    """Link a call to a consent + processing purpose.

    Maps to call_processing_consents table (capsulecorp.sql line 1330).
    RGPD Art. 5.1.b: Purpose limitation per call.
    """

    purpose_id: str = Field(..., description="UUID of data_processing_purposes row")
    consent_id: str = Field(..., description="UUID of data_consents row")
    retention_until: datetime | None = Field(
        None,
        description="Optional retention date (calculated from purpose retention_period_days)",
    )


class ConsentResponse(BaseModel):
    """Response for call consent linking."""

    consent_id: str
    call_id: str
    purpose_id: str
    processing_enabled: bool
    created_at: datetime


# ============================================================================
# RECORDING SCHEMAS
# ============================================================================


class RecordingCreate(BaseModel):
    """Register a call recording.

    Recording should only start AFTER:
    1. User is informed (RGPD Art. 13)
    2. Consent is obtained if required (RGPD Art. 7)
    """

    call_id: str = Field(...)
    recording_file_path: str = Field(..., description="Path to recording file")
    recording_format: str = Field(default="wav", description="Audio format")
    sample_rate: int = Field(default=8000, description="Sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")

    # Compliance verification
    consent_verified: bool = Field(..., description="Confirm recording consent was obtained")
    information_provided: bool = Field(..., description="Confirm user was informed about recording")

    # Timing
    recording_start: datetime = Field(...)
    recording_end: datetime | None = Field(None)

    # Retention
    purpose: str = Field(
        default="quality",
        description="Purpose: quality, training, legal, fraud",
    )

    @field_validator("consent_verified", "information_provided")
    @classmethod
    def must_be_true(cls, v: bool, info) -> bool:
        """These must be explicitly true for compliance."""
        if not v:
            raise ValueError(f"{info.field_name} must be true to create recording")
        return v


# ============================================================================
# ROBINSON CHECK SCHEMAS (LOPDGDD)
# ============================================================================


class RobinsonCheckRequest(BaseModel):
    """Check if phone number is in Lista Robinson."""

    phone_number: str = Field(..., description="Phone number to check")
    purpose: CallPurpose = Field(
        default=CallPurpose.COMMERCIAL,
        description="Purpose of intended call",
    )


# ============================================================================
# CALL END SCHEMAS
# ============================================================================


class CallEndCreate(BaseModel):
    """Finalize a call record."""

    status: str | None = Field(None, description="Final call status")
    duration_seconds: int | None = Field(None, ge=0)
    disposition_code: str | None = Field(None, description="Call disposition code")
    notes: str | None = Field(None, description="Agent notes")


# ============================================================================
# ENDPOINT RESPONSE SCHEMAS
# ============================================================================


class PBXCallCreateResponse(BaseModel):
    """Call creation response."""

    call_id: UUID
    external_call_id: str | None
    status: str
    created_at: datetime
    ai_disclosure_required: bool = True
    robinson_check_recommended: bool = False


class PBXCallStatusResponse(BaseModel):
    """Call status response."""

    call_id: UUID
    status: str
    updated_at: datetime
    duration_seconds: int | None = None


class PBXAIDisclosureResponse(BaseModel):
    """AI disclosure response."""

    call_id: UUID
    disclosed_at: datetime
    method: str
    compliant: bool = True


class PBXConsentResponse(BaseModel):
    """Consent recording response."""

    consent_id: UUID
    call_id: UUID
    purpose_id: UUID
    processing_enabled: bool
    created_at: datetime


class PBXRecordingResponse(BaseModel):
    """Recording response."""

    call_id: UUID
    recording_started: bool
    consent_verified: bool
    started_at: datetime | None = None


class PBXRobinsonCheckResponse(BaseModel):
    """Robinson check response."""

    phone_number_hash: str
    is_listed: bool
    can_contact: bool
    check_id: UUID
    valid_until: datetime
    message: str


class PBXCallEndResponse(BaseModel):
    """Call end response."""

    call_id: UUID
    status: str
    duration_seconds: int | None
    ended_at: datetime
    traffic_data_retained: bool = True
    retention_until: datetime
