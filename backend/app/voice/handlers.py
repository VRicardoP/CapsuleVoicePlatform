"""Voice provider webhook handlers.

Each handler converts provider-specific webhook payloads to normalized CallEvent.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from app.voice.events import CallEvent, CallEventType, TranscriptSegment
from app.voice.providers import VoiceProvider

logger = logging.getLogger(__name__)


def parse_ultravox_webhook(payload: dict[str, Any]) -> CallEvent | None:
    """Convert Ultravox webhook to normalized CallEvent.

    Ultravox events: call.created, call.started, call.joined, call.ended, call.billed
    We map these to our normalized events.
    """
    event_type = payload.get("event", "")
    call_data = payload.get("call", {})

    # Map Ultravox events to normalized events
    event_mapping = {
        "call.started": CallEventType.CALL_STARTED,
        "call.joined": CallEventType.CALL_ANSWERED,
        "call.ended": CallEventType.CALL_ENDED,
    }

    normalized_event = event_mapping.get(event_type)
    if not normalized_event:
        # Skip events we don't care about (call.created, call.billed)
        return None

    # Extract phone numbers - try metadata first (SIP calls), then medium.sip
    caller_phone = None
    called_phone = None

    # Try metadata['ultravox.sip.caller_id'] first (most reliable for SIP)
    metadata = call_data.get("metadata", {})
    if isinstance(metadata, dict):
        caller_phone = metadata.get("ultravox.sip.caller_id")
        if caller_phone:
            logger.info(f"Got caller_phone from SIP metadata: {caller_phone}")

    # Fallback to medium.sip if not found in metadata
    if not caller_phone:
        medium = call_data.get("medium", {})
        if isinstance(medium, dict):
            sip = medium.get("sip", {})
            if isinstance(sip, dict):
                incoming = sip.get("incoming", {})
                if isinstance(incoming, dict):
                    caller_phone = incoming.get("callerNumber")
                    called_phone = incoming.get("calledNumber")

    # Parse timestamps
    created = _parse_datetime(call_data.get("created"))
    joined = _parse_datetime(call_data.get("joined"))
    ended = _parse_datetime(call_data.get("ended"))

    # Calculate duration
    duration_seconds = None
    if created and ended:
        duration_seconds = int((ended - created).total_seconds())

    # Map end reason to status
    status = None
    end_reason = call_data.get("endReason")
    if normalized_event == CallEventType.CALL_ENDED:
        status = _map_ultravox_end_reason_to_status(end_reason)

    return CallEvent(
        event=normalized_event,
        provider=VoiceProvider.ULTRAVOX,
        provider_call_id=call_data.get("callId", ""),
        direction="inbound",  # Ultravox SIP calls are inbound
        caller_phone=caller_phone,
        called_phone=called_phone,
        started_at=created,
        answered_at=joined,
        ended_at=ended,
        duration_seconds=duration_seconds,
        status=status,
        end_reason=end_reason,
        metadata={
            "ultravox_model": call_data.get("model"),
            "billing_status": call_data.get("billingStatus"),
            "sip_caller_id": metadata.get("ultravox.sip.caller_id")
            if isinstance(metadata, dict)
            else None,
        },
    )


def parse_retell_webhook(payload: dict[str, Any]) -> CallEvent | None:
    """Convert Retell webhook to normalized CallEvent.

    Retell events: call_started, call_ended, call_analyzed
    """
    event_type = payload.get("event", "")
    call_data = payload.get("call", {})

    event_mapping = {
        "call_started": CallEventType.CALL_STARTED,
        "call_ended": CallEventType.CALL_ENDED,
        "call_analyzed": CallEventType.CALL_ENDED,  # Analysis comes after end
    }

    normalized_event = event_mapping.get(event_type)
    if not normalized_event:
        return None

    # Parse timestamps (Retell uses milliseconds)
    start_timestamp = call_data.get("start_timestamp")
    end_timestamp = call_data.get("end_timestamp")

    started_at = (
        datetime.fromtimestamp(start_timestamp / 1000, tz=UTC) if start_timestamp else None
    )
    ended_at = (
        datetime.fromtimestamp(end_timestamp / 1000, tz=UTC) if end_timestamp else None
    )

    duration_seconds = None
    if started_at and ended_at:
        duration_seconds = int((ended_at - started_at).total_seconds())

    # Map Retell's disconnection_reason to status
    status = None
    end_reason = call_data.get("disconnection_reason")
    if normalized_event == CallEventType.CALL_ENDED:
        status = _map_retell_end_reason_to_status(end_reason)

    # Extract transcript if available
    transcript = None
    if call_data.get("transcript"):
        transcript = [
            TranscriptSegment(
                role="agent" if seg.get("role") == "agent" else "user",
                text=seg.get("content", ""),
            )
            for seg in call_data.get("transcript_object", [])
        ]

    # Extract sentiment from call_analysis
    sentiment = None
    call_analysis = call_data.get("call_analysis", {})
    if call_analysis:
        sentiment_raw = call_analysis.get("user_sentiment")
        if sentiment_raw in ["Positive", "Negative", "Neutral"]:
            sentiment = sentiment_raw.lower()

    return CallEvent(
        event=normalized_event,
        provider=VoiceProvider.RETELL,
        provider_call_id=call_data.get("call_id", ""),
        direction="inbound" if call_data.get("direction") == "inbound" else "outbound",
        caller_phone=call_data.get("from_number"),
        called_phone=call_data.get("to_number"),
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration_seconds,
        status=status,
        end_reason=end_reason,
        sentiment=sentiment,
        summary=call_analysis.get("call_summary"),
        transcript=transcript,
        metadata={
            "retell_agent_id": call_data.get("agent_id"),
        },
    )


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string to datetime object."""
    if not value:
        return None
    try:
        # Handle Ultravox format: 2024-01-01T00:00:00.000000Z
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _map_ultravox_end_reason_to_status(end_reason: str | None) -> str:
    """Map Ultravox end reason to normalized status."""
    if not end_reason:
        return "completed"

    mapping = {
        "hangup": "completed",
        "timeout": "missed",
        "error": "failed",
        "transfer": "transferred",
    }
    return mapping.get(end_reason.lower(), "completed")


def _map_retell_end_reason_to_status(end_reason: str | None) -> str:
    """Map Retell disconnection reason to normalized status."""
    if not end_reason:
        return "completed"

    mapping = {
        "user_hangup": "completed",
        "agent_hangup": "completed",
        "call_transfer": "transferred",
        "voicemail_reached": "missed",
        "inactivity": "missed",
        "machine_detected": "missed",
        "max_duration_reached": "completed",
        "concurrency_limit_reached": "failed",
        "dial_busy": "busy",
        "dial_failed": "failed",
        "dial_no_answer": "missed",
        "error_inbound_webhook": "failed",
        "error_llm_websocket": "failed",
        "error_transcriber": "failed",
        "error_unknown": "failed",
    }
    return mapping.get(end_reason, "completed")
