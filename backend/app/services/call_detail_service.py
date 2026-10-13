"""Call detail service.

Encapsulates the complex SQL queries and data formatting for call detail views.
Extracted from endpoints/calls.py to maintain thin HTTP handlers.
"""

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings as app_settings
from app.schemas.calls import (
    FrontendAction,
    FrontendCallDetailResponse,
    FrontendCallRecord,
    FrontendTranscription,
)

logger = logging.getLogger(__name__)

# Status mapping from DB to frontend
_STATUS_MAP = {
    "completed": "completed",
    "scheduled": "scheduled",
    "transferred": "transferred",
    "rejected": "rejected",
    "initiated": "in_progress",
    "ringing": "in_progress",
    "answered": "in_progress",
    "on_hold": "in_progress",
    "abandoned": "rejected",
    "failed": "rejected",
}

# Action type mapping from decision_type to frontend
_ACTION_TYPE_MAP = {
    "email": "email",
    "crm_update": "crm",
    "calendar": "calendar",
    "whatsapp": "whatsapp",
    "sms": "whatsapp",
    "transfer": "crm",
    "internal_notification": "crm",
    "knowledge_update": "crm",
    "routing": "crm",
    "sentiment": "crm",
    "classification": "crm",
    "recommendation": "crm",
    "escalation": "crm",
    "verification": "crm",
    "summary": "crm",
    "categorization": "crm",
    "priority": "crm",
}

# Tool name to action type mapping
_TOOL_ACTION_MAP = {
    "identificar_cliente": "crm",
    "consultar_servicios": "crm",
    "buscar_servicio": "crm",
    "consultar_disponibilidad": "calendar",
    "agendar_cita": "calendar",
    "cancelar_cita": "calendar",
    "crear_recado": "crm",
}

_ACTION_STATUS_MAP = {
    "success": "success",
    "pending": "pending",
    "failed": "failed",
    "declined_by_customer": "success",
}


def _format_duration(seconds: int) -> str:
    """Format duration as 'Xm Ys'."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}m {secs}s"


def _check_recording_availability(
    recording_url: str | None, is_recorded: bool
) -> tuple[bool, str | None]:
    """Check if a recording is available and not expired."""
    recording_available = bool(recording_url) and bool(is_recorded)
    recording_expires_at = None

    if recording_available and recording_url:
        from app.services.recording_service import RecordingService

        try:
            rec_service = RecordingService(app_settings)
            exp_date = rec_service.get_expiration_date(recording_url)
            if exp_date:
                if exp_date < datetime.now(UTC):
                    recording_available = False
                else:
                    recording_expires_at = exp_date.isoformat()
        except (ValueError, TypeError, OSError):
            pass

    return recording_available, recording_expires_at


async def get_call_detail(
    call_id: UUID,
    db: AsyncSession,
) -> FrontendCallDetailResponse:
    """Get call details in frontend-expected format.

    Raises ValueError if call not found.
    """
    result = await db.execute(
        text("""
            SELECT
                c.id,
                (c.initiated_at AT TIME ZONE 'Europe/Madrid')::date as call_date,
                (c.initiated_at AT TIME ZONE 'Europe/Madrid')::time as call_time,
                c.initiated_at,
                c.duration_seconds,
                'Cliente' as caller_name,
                COALESCE(c.caller_number, '***-***-****') as caller_phone,
                c.status,
                COALESCE(c.sentiment, 'neutral') as sentiment,
                c.recording_file_path as recording_url,
                c.is_recorded,
                CASE WHEN c.recording_consent = true THEN true ELSE false END as has_consent
            FROM calls c
            WHERE c.id = :call_id
              AND c.deleted_at IS NULL
        """),
        {"call_id": str(call_id)},
    )
    row = result.fetchone()

    if not row:
        raise ValueError("Call not found")

    # Format call data
    duration_seconds = row.duration_seconds or 0
    call_date = str(row.call_date) if row.call_date else ""
    call_time = str(row.call_time)[:5] if row.call_time else ""
    frontend_status = _STATUS_MAP.get(row.status, "completed")
    recording_available, recording_expires_at = _check_recording_availability(
        row.recording_url, row.is_recorded
    )

    frontend_call = FrontendCallRecord(
        id=str(row.id),
        date=call_date,
        time=call_time,
        duration=_format_duration(duration_seconds),
        caller=row.caller_name or "Cliente",
        phone=row.caller_phone or "***-***-****",
        status=frontend_status,
        sentiment=row.sentiment or "neutral",
        recording=row.recording_url,
        recordingConsentId=None,
        hasActiveConsent=row.has_consent or False,
        recordingAvailable=recording_available,
        recordingExpiresAt=recording_expires_at,
    )

    # Get transcriptions
    frontend_transcriptions = await _get_transcriptions(db, call_id, row.has_consent)

    # Get actions
    frontend_actions = await _get_actions(db, call_id)

    logger.debug(
        "Response: hasActiveConsent=%s, transcriptions_count=%d",
        frontend_call.hasActiveConsent,
        len(frontend_transcriptions),
    )

    return FrontendCallDetailResponse(
        call=frontend_call,
        transcriptions=frontend_transcriptions,
        actions=frontend_actions,
    )


async def _get_transcriptions(
    db: AsyncSession,
    call_id: UUID,
    has_consent: bool,
) -> list[FrontendTranscription]:
    """Get transcriptions for a call."""
    if not has_consent:
        return []

    trans_result = await db.execute(
        text("""
            SELECT
                t.segment_index,
                t.speaker_type,
                t.text,
                t.start_time_ms,
                t.contains_sensitive_data
            FROM transcriptions t
            WHERE t.call_id = :call_id
            ORDER BY t.segment_index
        """),
        {"call_id": str(call_id)},
    )
    trans_rows = trans_result.fetchall()
    logger.debug("Found %d transcript segments for call %s", len(trans_rows), call_id)

    transcriptions: list[FrontendTranscription] = []
    for t_row in trans_rows:
        total_seconds = (t_row.start_time_ms or 0) // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        timestamp = f"{minutes}:{seconds:02d}"
        speaker = "assistant" if t_row.speaker_type == "agent" else "client"
        transcriptions.append(
            FrontendTranscription(
                callId=str(call_id),
                timestamp=timestamp,
                speaker=speaker,
                text=t_row.text or "",
                hasPii=t_row.contains_sensitive_data or False,
                consentId=None,
                consentStatus="active",
            )
        )

    return transcriptions


async def _get_actions(
    db: AsyncSession,
    call_id: UUID,
) -> list[FrontendAction]:
    """Get AI decision actions for a call."""
    try:
        actions_result = await db.execute(
            text("""
                SELECT
                    id,
                    decision_type,
                    COALESCE(decision_value, '') as description,
                    created_at,
                    decision_details->>'action_type' as action_type,
                    decision_details->>'status' as action_status,
                    decision_details as metadata_raw
                FROM ai_decision_logs
                WHERE call_id = :call_id
                ORDER BY created_at ASC
            """),
            {"call_id": str(call_id)},
        )
    except SQLAlchemyError as e:
        logger.debug("ai_decision_logs query failed (table may not exist): %s", e)
        return []

    actions: list[FrontendAction] = []
    for a_row in actions_result.fetchall():
        action_type = _ACTION_TYPE_MAP.get(a_row.decision_type, "crm")
        action_status = _ACTION_STATUS_MAP.get(a_row.action_status or "success", "success")
        timestamp = a_row.created_at.strftime("%H:%M") if a_row.created_at else ""

        details = _extract_action_details(a_row, action_type)
        if details and "action_type" in details:
            action_type = details.pop("action_type")

        actions.append(
            FrontendAction(
                id=str(a_row.id),
                type=action_type,
                callId=str(call_id),
                description=a_row.description or "",
                status=action_status,
                timestamp=timestamp,
                details=details,
            )
        )

    return actions


def _extract_action_details(a_row, action_type: str) -> dict | None:
    """Extract details from action metadata."""
    raw_details = a_row.metadata_raw
    if not raw_details:
        return None

    try:
        dd = raw_details if isinstance(raw_details, dict) else json.loads(raw_details)
        if not dd.get("tool_name"):
            return None

        details: dict = {"tool_name": dd["tool_name"]}
        if dd.get("booking"):
            details["booking"] = dd["booking"]
        if dd.get("tool_args"):
            details["tool_args"] = dd["tool_args"]

        tool_result = dd.get("tool_result", {})
        if isinstance(tool_result, dict):
            details["success"] = tool_result.get("success")
            if tool_result.get("cita_id"):
                details["cita_id"] = tool_result["cita_id"]

        if a_row.decision_type in ("other", "tool_call"):
            resolved_type = _TOOL_ACTION_MAP.get(dd["tool_name"])
            if resolved_type:
                details["action_type"] = resolved_type

        return details
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None
