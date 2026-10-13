"""Schemas for AI Agent endpoints.

These schemas define the data structures for the AI conversational agent.
All operations must comply with:
- AI Act Art. 12: Traceability (all decisions logged)
- AI Act Art. 14: Human oversight capability
- AI Act Art. 50: Transparency (disclosure verification)
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AIRiskLevel(str, Enum):
    """AI risk level classification (AI Act Annex III)."""

    LOW = "low"
    LIMITED = "limited"
    HIGH = "high"
    UNACCEPTABLE = "unacceptable"


class DecisionCategory(str, Enum):
    """Categories of AI decisions."""

    SENTIMENT = "sentiment"
    ROUTING = "routing"
    RESPONSE_GENERATION = "response_generation"
    INTENT_CLASSIFICATION = "intent_classification"
    ENTITY_EXTRACTION = "entity_extraction"
    ESCALATION = "escalation"
    SUMMARY = "summary"


class SpeakerType(str, Enum):
    """Speaker in transcription."""

    AGENT = "agent"
    CUSTOMER = "customer"
    SYSTEM = "system"


# ============================================================================
# TRANSCRIPTION SCHEMAS
# ============================================================================


class TranscriptionSegmentCreate(BaseModel):
    """Create a transcription segment."""

    call_id: str = Field(..., description="UUID of the call")
    sequence_number: int = Field(..., ge=0, description="Sequence number in call")
    speaker: SpeakerType = Field(..., description="Who is speaking")
    text: str = Field(..., min_length=1, description="Transcribed text")
    segment_timestamp: datetime = Field(..., description="When this was spoken")
    confidence_score: float | None = Field(None, ge=0, le=1, description="ASR confidence")
    language_code: str = Field(default="es", description="ISO 639-1 language code")
    duration_ms: int | None = Field(None, ge=0, description="Segment duration in ms")


class TranscriptionResponse(BaseModel):
    """Transcription creation response."""

    id: str
    call_id: str
    segment_index: int
    created_at: datetime


class TranscriptionBatchCreate(BaseModel):
    """Create multiple transcription segments at once."""

    call_id: str
    segments: list[TranscriptionSegmentCreate] = Field(..., min_length=1, max_length=100)


# ============================================================================
# AI DECISION SCHEMAS
# ============================================================================


class AIDecisionCreate(BaseModel):
    """Create an AI decision log entry.

    REQUIRED by AI Act Art. 12 for traceability.
    """

    call_id: str | None = Field(None, description="Associated call UUID")
    session_id: str | None = Field(None, description="Session UUID")

    # Model information (required for reproducibility)
    model_name: str = Field(..., description="Name of the AI model")
    model_version: str = Field(..., description="Version for reproducibility")
    model_provider: str | None = Field(None, description="openai, anthropic, ultravox, etc.")

    # Decision classification
    decision_category: DecisionCategory | None = Field(None, description="Category")

    # Input tracking (hashed, not raw PII)
    input_type: str = Field(..., description="Type of input (audio, text, etc)")
    input_reference: str | None = Field(None, description="Reference to input data")
    input_hash: str | None = Field(None, description="Hash of input for verification")

    # Output
    output_type: str = Field(..., description="Type of output (classification, text, etc)")
    output_summary: str | None = Field(None, description="Summary of AI output (no PII)")
    output_confidence: float | None = Field(None, ge=0, le=1, description="Confidence 0-1")

    # Risk and compliance
    ai_risk_level: AIRiskLevel = Field(
        default=AIRiskLevel.LIMITED,
        description="AI Act risk classification",
    )
    human_oversight_required: bool = Field(
        default=False,
        description="Art. 14: Does this need human review?",
    )

    # Emotion detection compliance
    emotion_detection_used: bool = Field(
        default=False,
        description="Was emotion/sentiment analyzed?",
    )
    emotion_detection_disclosed: bool = Field(
        default=False,
        description="Art. 50.3: Was user informed about emotion detection?",
    )
    user_informed: bool = Field(
        default=False,
        description="Was user informed of AI interaction?",
    )

    # Validation-only field (not stored in DB)
    is_employee_interaction: bool = Field(
        default=False,
        description="AI Act Art. 5.1.f: Employee emotion prohibition check",
    )

    # Additional
    processing_time_ms: int | None = Field(None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("emotion_detection_disclosed")
    @classmethod
    def validate_emotion_disclosure(cls, v: bool, info) -> bool:
        """Ensure disclosure if emotion detection is used."""
        if info.data.get("emotion_detection_used") and not v:
            raise ValueError(
                "AI Act Art. 50.3: emotion_detection_disclosed must be true "
                "when emotion_detection_used is true"
            )
        return v


class AIDecisionResponse(BaseModel):
    """AI decision log response."""

    id: str
    call_id: str | None
    model_name: str
    output_type: str
    output_summary: str | None = None
    output_confidence: float | None = None
    ai_risk_level: str | None = None
    human_oversight_required: bool = False
    created_at: datetime


# ============================================================================
# SENTIMENT ANALYSIS SCHEMAS
# ============================================================================


class SentimentValue(str, Enum):
    """Sentiment classification."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SentimentAnalysisCreate(BaseModel):
    """Register sentiment analysis result for a call.

    REQUIRES:
    - ai_disclosure_timestamp must be set on call
    - SENTIMENT_ANALYSIS consent must be active
    """

    call_id: str = Field(..., description="UUID of the call")
    sentiment: SentimentValue = Field(..., description="Overall sentiment")
    sentiment_score: float = Field(..., ge=0, le=1, description="Confidence 0-1")

    # For AI decision log
    model_name: str = Field(default="sentiment-analyzer")
    model_version: str = Field(...)

    # Compliance fields
    consent_verified: bool = Field(
        ...,
        description="Confirm SENTIMENT_ANALYSIS consent was verified",
    )
    ai_disclosure_verified: bool = Field(
        ...,
        description="Confirm ai_disclosure_timestamp exists",
    )

    @field_validator("consent_verified", "ai_disclosure_verified")
    @classmethod
    def must_be_true(cls, v: bool, info) -> bool:
        """These must be explicitly true."""
        if not v:
            field_name = info.field_name
            raise ValueError(f"{field_name} must be explicitly true")
        return v


class CallUpdateResponse(BaseModel):
    """Call update response."""

    call_id: str
    updated_fields: list[str]
    updated_at: datetime


# ============================================================================
# CUSTOMER CONTEXT SCHEMAS
# ============================================================================


class CustomerContextRequest(BaseModel):
    """Request customer context for AI processing."""

    customer_id: str | None = Field(None, description="Customer UUID if known")
    phone_number: str | None = Field(None, description="Phone number to lookup")
    include_history: bool = Field(
        default=True,
        description="Include recent call history",
    )
    include_preferences: bool = Field(
        default=True,
        description="Include customer preferences",
    )
    include_consents: bool = Field(
        default=True,
        description="Include active consents",
    )


class CustomerContextResponse(BaseModel):
    """Customer context for AI agent."""

    contact_id: str
    phone: str | None = None
    email: str | None = None
    full_name: str | None = None
    previous_calls_count: int = 0
    last_call_date: datetime | None = None
    active_consents: list[str] = Field(default_factory=list)
    marketing_opt_out: bool = False
    profiling_opt_out: bool = False
    processing_restricted: bool = False
    robinson_status: str | None = None


class ConsentCheckResponse(BaseModel):
    """Consent verification response."""

    has_consent: bool
    scope: str
    granted_at: datetime | None = None
    expires_at: datetime | None = None


# ============================================================================
# HUMAN ESCALATION SCHEMAS
# ============================================================================


class HumanEscalationCreate(BaseModel):
    """Request human escalation (AI Act Art. 14).

    Used when AI determines human oversight is needed.
    """

    call_id: str = Field(..., description="Call to escalate")
    reason: str = Field(..., min_length=10, description="Why escalation is needed")
    urgency: str = Field(
        default="normal",
        description="Urgency level: low, normal, high, critical",
    )
    ai_confidence: float | None = Field(
        None, ge=0, le=1, description="AI's confidence before escalation"
    )
    suggested_action: str | None = Field(None, description="AI's suggested action for human")
    context_summary: str | None = Field(None, description="Summary of conversation so far")


class HumanEscalationResponse(BaseModel):
    """Human escalation response."""

    escalation_id: str
    call_id: str
    reason: str
    priority: str
    created_at: datetime


# ============================================================================
# CLIENT ERROR REPORTING SCHEMAS
# ============================================================================


class ClientErrorReport(BaseModel):
    """Error report from SferaAgentClient.

    Allows automatic error reporting from the Python client used by
    the conversational agent, without requiring manual log sharing.
    """

    client_version: str = Field(..., max_length=20, description="Client version (e.g., 1.1.0)")
    error_type: str = Field(..., max_length=100, description="Exception class name")
    error_message: str = Field(..., description="Error message")
    method: str | None = Field(None, max_length=10, description="HTTP method")
    endpoint: str | None = Field(None, max_length=255, description="API endpoint path")
    request_payload: dict[str, Any] | None = Field(
        None, description="Sanitized request payload (no PII)"
    )
    response_status: int | None = Field(None, ge=100, le=599, description="HTTP response status")
    response_body: str | None = Field(None, max_length=1000, description="Truncated response body")
    call_id: str | None = Field(None, description="Related call UUID if applicable")
    timestamp: datetime = Field(..., description="When the error occurred on client")
    stack_trace: str | None = Field(None, description="Python stack trace")
    environment: str | None = Field(
        None, max_length=20, description="Environment (dev, staging, prod)"
    )
    extra_context: dict[str, Any] | None = Field(None, description="Additional context")


class ClientErrorReportResponse(BaseModel):
    """Response for client error report."""

    status: str = Field(default="received")
    message: str = Field(default="Error logged successfully")
    error_id: str | None = Field(None, description="UUID of the logged error")


class ClientErrorListItem(BaseModel):
    """Client error list item for dashboard."""

    id: str
    client_version: str
    error_type: str
    error_message: str
    endpoint: str | None
    response_status: int | None
    call_id: str | None
    error_timestamp: datetime
    reported_at: datetime
    environment: str | None
    resolved: bool
    resolved_at: datetime | None


class ClientErrorListResponse(BaseModel):
    """Response for client error list."""

    errors: list[ClientErrorListItem]
    total: int
    page: int
    page_size: int
