"""Schemas for Call management endpoints.

Pydantic models for CRUD operations on calls, transcriptions, and recordings.

Compliance:
- AI Act Art. 50.1: AI disclosure tracking fields
- RGPD Art. 7: Recording consent fields
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# === Request Schemas ===


class CallCreateRequest(BaseModel):
    """Request to create a new call."""

    external_call_id: str | None = Field(None, description="External PBX call ID")
    direction: str = Field(..., description="inbound, outbound, internal")
    call_type: str | None = Field(None, description="support, sales, collection, survey")
    purpose: str | None = Field(None, description="commercial, service, informational")
    status: str = Field(
        "initiated",
        description="initiated, ringing, answered, on_hold, transferred, completed, abandoned, failed",
    )
    initiated_at: datetime | None = Field(None, description="Call start time (defaults to now)")
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    contact_id: UUID | None = None
    agent_id: UUID | None = None
    caller_number: str | None = None
    called_number: str | None = None
    queue_name: str | None = None
    ai_disclosure_timestamp: datetime | None = Field(
        None, description="AI Act Art. 50.1: When AI was disclosed"
    )
    ai_disclosure_method: str | None = Field(
        None, description="ivr_message, agent_verbal, automated"
    )
    emotion_detection_disclosed: bool = Field(
        False, description="AI Act Art. 50.3: Emotion detection disclosed"
    )
    is_recorded: bool = False
    recording_consent: bool | None = None
    sentiment: str | None = Field(None, description="positive, neutral, negative")
    sentiment_score: float | None = Field(None, ge=-1.0, le=1.0)
    ai_summary: str | None = None
    ai_category: str | None = None
    disposition_code: str | None = None
    disposition_notes: str | None = None
    campaign_id: UUID | None = None
    extra_data: dict | None = None


class CallUpdateRequest(BaseModel):
    """Request to update an existing call."""

    status: str | None = Field(
        None,
        description="initiated, ringing, answered, on_hold, transferred, completed, abandoned, failed",
    )
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    agent_id: UUID | None = None
    ai_disclosure_timestamp: datetime | None = None
    ai_disclosure_method: str | None = None
    emotion_detection_disclosed: bool | None = None
    is_recorded: bool | None = None
    recording_consent: bool | None = None
    recording_consent_timestamp: datetime | None = None
    sentiment: str | None = None
    sentiment_score: float | None = Field(None, ge=-1.0, le=1.0)
    ai_summary: str | None = None
    ai_category: str | None = None
    quality_score: float | None = Field(None, ge=0, le=1)
    csat_score: int | None = Field(None, ge=1, le=5)
    nps_score: int | None = Field(None, ge=-100, le=100)
    disposition_code: str | None = None
    disposition_notes: str | None = None
    human_oversight_required: bool | None = None
    human_override: str | None = None
    extra_data: dict | None = None


class TranscriptionCreateRequest(BaseModel):
    """Request to add a transcription segment."""

    segment_index: int = Field(..., ge=0, description="Segment order index")
    speaker_type: str = Field(..., description="agent, customer, system, ai")
    text: str = Field(..., min_length=1, description="Transcription text")
    start_time_ms: int = Field(..., ge=0, description="Start time in milliseconds")
    end_time_ms: int = Field(..., ge=0, description="End time in milliseconds")
    confidence_score: float | None = Field(
        None, ge=0, le=1, description="Speech recognition confidence"
    )
    sentiment: str | None = Field(None, description="positive, neutral, negative")
    language: str | None = Field("es", description="ISO 639-1 language code")


# === Response Schemas ===


class CallResponse(BaseModel):
    """Call response."""

    id: UUID
    external_call_id: str | None = None
    direction: str
    call_type: str | None = None
    status: str
    initiated_at: datetime
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    contact_id: UUID | None = None
    agent_id: UUID | None = None
    caller_number: str | None = None
    called_number: str | None = None
    ai_disclosure_timestamp: datetime | None = None
    is_recorded: bool = False
    sentiment: str | None = None
    ai_summary: str | None = None
    disposition_code: str | None = None

    model_config = {"from_attributes": True}


class CallListResponse(BaseModel):
    """Paginated call list."""

    items: list[CallResponse]
    total: int
    skip: int
    limit: int


class TranscriptionSegment(BaseModel):
    """Transcription segment."""

    id: UUID
    segment_index: int
    speaker_type: str
    text: str
    start_time_ms: int
    end_time_ms: int
    sentiment: str | None = None
    confidence_score: float | None = None

    model_config = {"from_attributes": True}


class CallTranscript(BaseModel):
    """Full call transcript."""

    call_id: UUID
    segments: list[TranscriptionSegment]
    total_segments: int
    full_text: str


class CallDetailResponse(BaseModel):
    """Detailed call response including transcript summary."""

    call: CallResponse
    transcript_available: bool = False
    transcript_segments_count: int = 0
    ai_decisions_count: int = 0


class FrontendTranscription(BaseModel):
    """Transcription format expected by frontend."""

    callId: str
    timestamp: str
    speaker: str  # 'assistant' or 'client'
    text: str
    hasPii: bool = False
    consentId: str | None = None
    consentStatus: str = "active"


class FrontendAction(BaseModel):
    """Automated action format expected by frontend."""

    id: str
    type: str  # email, crm, calendar, whatsapp
    callId: str
    description: str
    status: str  # success, pending, failed
    timestamp: str
    details: dict[str, Any] | None = None


class FrontendCallRecord(BaseModel):
    """Call record format expected by frontend."""

    id: str
    date: str
    time: str
    duration: str
    caller: str
    phone: str
    status: str
    sentiment: str
    recording: str | None = None
    recordingConsentId: str | None = None
    hasActiveConsent: bool = False
    recordingAvailable: bool = False
    recordingExpiresAt: str | None = None


class FrontendCallDetailResponse(BaseModel):
    """Response format expected by frontend for call details modal."""

    call: FrontendCallRecord
    transcriptions: list[FrontendTranscription]
    actions: list[FrontendAction]
