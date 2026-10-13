"""Normalized call event schema.

This schema is provider-agnostic and used for:
- Forwarding to n8n for client-specific automations
- Internal event processing
- Analytics and logging

All voice providers (Ultravox, Retell, Internal) convert their
webhooks to this normalized format.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class CallEventType(str, Enum):
    """Normalized call event types."""

    CALL_STARTED = "call.started"
    CALL_ANSWERED = "call.answered"
    CALL_ENDED = "call.ended"
    CALL_TRANSFERRED = "call.transferred"


class TranscriptSegment(BaseModel):
    """A segment of the call transcript."""

    role: Literal["agent", "user"]
    text: str
    timestamp: datetime | None = None


class CallEvent(BaseModel):
    """Normalized call event for all voice providers.

    This is the single source of truth for call events, regardless
    of whether they come from Ultravox, Retell, or Internal PBX.
    """

    # Event metadata
    event: CallEventType
    event_id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(__import__("datetime").timezone.utc)
    )

    # Provider info
    provider: Literal["ultravox", "retell", "internal"]
    provider_call_id: str  # The call ID in the provider's system

    # Client info (for multi-tenant routing)
    client_id: str | None = None

    # Call details
    direction: Literal["inbound", "outbound"]
    caller_phone: str | None = None
    called_phone: str | None = None

    # Timing
    started_at: datetime | None = None
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None

    # Outcome (populated on call.ended)
    status: Literal["completed", "missed", "busy", "failed", "transferred"] | None = None
    end_reason: str | None = None

    # AI analysis (populated on call.ended if available)
    sentiment: Literal["positive", "neutral", "negative"] | None = None
    summary: str | None = None

    # Transcript (populated on call.ended if consent given)
    transcript: list[TranscriptSegment] | None = None

    # Compliance flags
    ai_disclosed: bool = False
    recording_consent: bool | None = None

    # Extensible metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_n8n_payload(self) -> dict[str, Any]:
        """Convert to payload suitable for n8n webhook."""
        return self.model_dump(mode="json", exclude_none=True)
