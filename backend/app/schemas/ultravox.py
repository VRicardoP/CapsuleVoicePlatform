"""Schemas for Ultravox AI webhook integration.

These schemas define the data structures for Ultravox AI voice agent integration.
All operations must comply with:
- RGPD Art. 7: Consent for recording
- AI Act Art. 50.1: AI disclosure before interaction
- AI Act Art. 12: Decision traceability
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# ============================================================================
# ULTRAVOX WEBHOOK EVENT SCHEMAS
# ============================================================================


class UltravoxEventType(str, Enum):
    """Ultravox webhook event types."""

    CALL_CREATED = "call.created"
    CALL_STARTED = "call.started"
    CALL_JOINED = "call.joined"
    CALL_ENDED = "call.ended"
    CALL_BILLED = "call.billed"


class UltravoxTranscriptWord(BaseModel):
    """Word-level transcript data."""

    word: str
    start: float  # seconds
    end: float  # seconds


class UltravoxTranscriptSegment(BaseModel):
    """Transcript segment from Ultravox."""

    role: str = Field(..., description="agent or user")
    content: str = Field(..., description="Text content")
    words: list[UltravoxTranscriptWord] = Field(default_factory=list)


class UltravoxCallAnalysis(BaseModel):
    """Post-call analysis from Ultravox."""

    sentiment: str | None = Field(None, description="positive, neutral, negative")
    call_successful: bool | None = None
    call_summary: str | None = None
    custom_variables: dict[str, Any] = Field(default_factory=dict)


class UltravoxCallData(BaseModel):
    """Call data from Ultravox webhook.

    Ultravox sends fields in camelCase, so we use aliases to map them.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # Core fields - Ultravox uses camelCase
    call_id: str = Field(..., alias="callId", description="Ultravox call ID")
    client_version: str | None = Field(None, alias="clientVersion")
    created: datetime | None = None
    joined: datetime | None = None
    ended: datetime | None = None
    end_reason: str | None = Field(None, alias="endReason")

    # Billing fields
    billed_duration: str | None = Field(None, alias="billedDuration")
    billing_status: str | None = Field(None, alias="billingStatus")

    # Call configuration
    first_speaker: str | None = Field(None, alias="firstSpeaker")
    initial_output_medium: str | None = Field(None, alias="initialOutputMedium")
    join_timeout: str | None = Field(None, alias="joinTimeout")
    max_duration: str | None = Field(None, alias="maxDuration")
    model: str | None = None
    recording_enabled: bool | None = Field(None, alias="recordingEnabled")
    language_hint: str | None = Field(None, alias="languageHint")

    # Medium info (can be object or string)
    medium: Any | None = None

    # Optional fields for backwards compatibility
    agent_id: str | None = Field(None, alias="agentId")
    from_number: str | None = Field(None, alias="fromNumber")
    to_number: str | None = Field(None, alias="toNumber")
    direction: str | None = None
    transcript: str | None = None
    recording_url: str | None = Field(None, alias="recordingUrl")
    call_analysis: UltravoxCallAnalysis | None = Field(None, alias="callAnalysis")

    # Computed property for duration in ms
    @property
    def duration_ms(self) -> int | None:
        """Calculate duration in milliseconds from created/ended timestamps."""
        if self.created and self.ended:
            delta = self.ended - self.created
            return int(delta.total_seconds() * 1000)
        return None


class UltravoxInboundCallData(BaseModel):
    """Inbound call data from phone webhook."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    agent_id: str | None = Field(None, alias="agentId")
    from_number: str | None = Field(None, alias="fromNumber")
    to_number: str | None = Field(None, alias="toNumber")
    medium: str | None = Field(None, description="telnyx, twilio, plivo")


class UltravoxWebhookEvent(BaseModel):
    """Ultravox webhook event payload.

    Supports webhook events from Ultravox:
    - call.created: A call has been created
    - call.started: The call has started
    - call.joined: A client has joined the call
    - call.ended: The call has ended
    - call.billed: Billing information available
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    event: UltravoxEventType
    call: UltravoxCallData | None = None
    # For call.created events
    call_created: UltravoxInboundCallData | None = Field(None, alias="callCreated")
    # Webhook metadata
    webhook_id: str | None = Field(None, alias="webhookId")
    timestamp: datetime | None = None


# ============================================================================
# ULTRAVOX FUNCTION REQUEST/RESPONSE SCHEMAS
# ============================================================================


class AIDisclosureFunctionRequest(BaseModel):
    """Request for AI disclosure function."""

    emotion_detection_disclosed: bool = Field(
        default=True, description="Whether emotion detection was disclosed"
    )


class AIDisclosureFunctionResponse(BaseModel):
    """Response for AI disclosure function."""

    success: bool
    call_id: str
    disclosed_at: datetime
    message: str


class ConsentFunctionRequest(BaseModel):
    """Request for consent function.

    Accepts Ultravox format: user_consent = "yes" | "no"
    Also accepts legacy format: consent_given = true | false
    """

    # Ultravox format (primary)
    user_consent: str | None = Field(None, description="Ultravox format: 'yes' or 'no'")
    # Legacy format (for backwards compatibility)
    consent_given: bool | None = Field(None, description="Legacy format: true or false")
    consent_type: str = Field(
        default="recording", description="Type of consent: recording, marketing, profiling"
    )

    @property
    def is_consent_given(self) -> bool:
        """Get consent as boolean from either format."""
        if self.user_consent is not None:
            return self.user_consent.lower() in ("yes", "si", "sí", "true", "1")
        if self.consent_given is not None:
            return self.consent_given
        return False


class ConsentFunctionResponse(BaseModel):
    """Response for consent function."""

    success: bool
    call_id: str
    consent_given: bool
    consent_type: str
    recorded_at: datetime
    message: str


class EscalationFunctionRequest(BaseModel):
    """Request for human escalation function."""

    reason: str = Field(
        ...,
        description="Reason: customer_request, complex_issue, gdpr_request, complaint, minor_detected, employee_detected",
    )
    priority: str = Field(default="normal", description="Priority: low, normal, high, urgent")
    context: str | None = Field(None, description="Conversation context summary")


class EscalationFunctionResponse(BaseModel):
    """Response for escalation function."""

    success: bool
    call_id: str
    escalation_id: str
    reason: str
    priority: str
    message: str


class RobinsonCheckFunctionResponse(BaseModel):
    """Response for Robinson check function."""

    success: bool
    phone_number_hash: str
    is_listed: bool
    can_contact: bool
    message: str


class CustomerContextFunctionResponse(BaseModel):
    """Response for customer context function."""

    success: bool
    found: bool
    contact_id: str | None = None
    full_name: str | None = None
    previous_calls_count: int = 0
    last_call_date: str | None = None
    active_consents: list[str] = Field(default_factory=list)
    marketing_opt_out: bool = False
    profiling_opt_out: bool = False
    notes: str | None = None


# ============================================================================
# INTERNAL MAPPING SCHEMAS
# ============================================================================


class UltravoxToCapsuleCallMapping(BaseModel):
    """Mapping of Ultravox call data to CapsuleCorp call model."""

    ultravox_call_id: str
    capsule_call_id: str | None = None
    direction: str
    caller_number: str | None
    called_number: str | None
    status: str
    duration_seconds: int | None
    sentiment: str | None
    ai_disclosure_recorded: bool = False
    consent_given: bool | None = None
    transcript_saved: bool = False
    recording_saved: bool = False


# ============================================================================
# ULTRAVOX CUSTOM FUNCTION WRAPPER MODELS
# Ultravox sends: {"call": {...}, "args": {...}}
# ============================================================================


class UltravoxFunctionCall(BaseModel):
    """Base model for Ultravox custom function calls."""

    call_id: str | None = None
    agent_id: str | None = None
    from_number: str | None = None
    to_number: str | None = None


class UltravoxAIDisclosureRequest(BaseModel):
    """Ultravox wrapper for AI disclosure function."""

    call: UltravoxFunctionCall
    args: AIDisclosureFunctionRequest


class UltravoxConsentRequest(BaseModel):
    """Ultravox wrapper for consent function."""

    call: UltravoxFunctionCall
    args: ConsentFunctionRequest


class UltravoxEscalationRequest(BaseModel):
    """Ultravox wrapper for escalation function."""

    call: UltravoxFunctionCall
    args: EscalationFunctionRequest


# ============================================================================
# ZADARMA WEBHOOK SCHEMAS
# ============================================================================


class ZadarmaNotifyEvent(BaseModel):
    """Zadarma webhook notification event."""

    event: str  # NOTIFY_START, NOTIFY_END, NOTIFY_ANSWER, etc.
    call_start: str | None = None
    pbx_call_id: str | None = None
    caller_id: str | None = None
    called_did: str | None = None
    destination: str | None = None
    duration: int | None = None
    disposition: str | None = None
    recording_url: str | None = None
