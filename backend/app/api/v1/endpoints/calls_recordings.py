"""Call recording, transcript, and human review endpoints.

Split from calls.py to stay under 500 LOC per CLAUDE.md guidelines.
"""

import logging
from io import BytesIO
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user_id,
    get_db,
    get_db_with_rls,
)
from app.repositories.call_repository import CallRepository, TranscriptionRepository
from app.repositories.gdpr_repository import AuditLogRepository
from app.schemas.calls import (
    CallListResponse,
    CallResponse,
    CallTranscript,
    TranscriptionSegment,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# === RECORDING HELPERS ===


async def _get_decrypted_recording(
    call_id: UUID,
    db: AsyncSession,
) -> tuple[bytes, Any]:
    """Fetch, validate, and decrypt a call recording.

    Expects ``db`` to already have RLS context set (via ``get_db_with_rls``).
    """
    import os

    from app.config.settings import settings as app_settings
    from app.services.recording_service import RecordingService

    call_repo = CallRepository(db)
    info = await call_repo.get_recording_info(call_id)

    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

    if not os.path.exists(info["recording_file_path"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recording file not found"
        )

    try:
        rec_service = RecordingService(app_settings)
        ogg_bytes = await rec_service.decrypt_recording(info["recording_file_path"])
    except (OSError, ValueError) as e:
        logger.error("Recording decryption failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to decrypt recording"
        )

    return ogg_bytes, info


# === RECORDING ENDPOINTS ===


@router.get(
    "/{call_id}/recording",
    summary="Stream call recording",
    description="Stream the decrypted recording audio for playback.",
)
async def stream_recording(
    call_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
) -> StreamingResponse:
    """Stream decrypted recording for audio player playback."""
    ogg_bytes, _ = await _get_decrypted_recording(call_id, db)

    return StreamingResponse(
        BytesIO(ogg_bytes),
        media_type="audio/ogg",
        headers={"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=300"},
    )


@router.get(
    "/{call_id}/recording/download",
    summary="Download call recording",
    description="Download the recording as an OGG file.",
)
async def download_recording(
    call_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
) -> StreamingResponse:
    """Download decrypted recording as attachment."""
    ogg_bytes, row = await _get_decrypted_recording(call_id, db)

    initiated_at = (
        row.get("initiated_at") if isinstance(row, dict) else getattr(row, "initiated_at", None)
    )
    call_date = initiated_at.strftime("%Y%m%d") if initiated_at else "unknown"
    filename = f"grabacion_{str(call_id)[:8]}_{call_date}.ogg"

    return StreamingResponse(
        BytesIO(ogg_bytes),
        media_type="audio/ogg",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-cache",
        },
    )


# === TRANSCRIPT ENDPOINT ===


@router.get(
    "/{call_id}/transcript",
    response_model=CallTranscript,
    summary="Get call transcript",
    description="Get full transcript for a call.",
)
async def get_call_transcript(
    call_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> CallTranscript:
    """Get call transcript. RGPD Art. 15 + AI Act Art. 50.2."""
    call_repo = CallRepository(db)
    transcription_repo = TranscriptionRepository(db)

    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    segments = await transcription_repo.get_by_call(call_id)
    full_text = await transcription_repo.get_full_transcript(call_id)

    return CallTranscript(
        call_id=call_id,
        segments=[TranscriptionSegment.model_validate(s) for s in segments],
        total_segments=len(segments),
        full_text=full_text,
    )


# === HUMAN REVIEW ENDPOINT ===


@router.post(
    "/{call_id}/human-review",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Submit human review",
    description="Submit human review decision for a call (AI Act Art. 14).",
)
async def submit_human_review(
    call_id: UUID,
    review_data: dict[str, Any],
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> None:
    """Submit human review for a call. AI Act Art. 14."""
    call_repo = CallRepository(db)
    audit_repo = AuditLogRepository(db)

    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    if not call.human_oversight_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Call does not require human review"
        )

    await call_repo.update(
        call_id,
        {
            "human_reviewer_id": current_user_id,
            "human_override": review_data.get("decision"),
            "human_oversight_required": False,
        },
    )

    await audit_repo.log_action(
        action="AI_DECISION_LOGGED",
        entity_type="calls",
        user_id=current_user_id,
        entity_id=call_id,
        details=review_data,
    )
    await db.commit()


# === LOOKUP ENDPOINTS ===


@router.get(
    "/{call_id}/phone",
    summary="Get caller phone number",
    description="Look up caller phone number by Ultravox call ID. Used by n8n workflows.",
)
async def get_call_phone(
    call_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | None]:
    """Return caller_number for a call by external_call_id.

    Called by internal n8n workflows via Docker network. The call_id is
    the Ultravox external UUID (unguessable), which is sufficient protection
    for this single non-critical field.
    """
    call_repo = CallRepository(db)
    caller_number = await call_repo.get_caller_by_external_id(call_id)

    if caller_number is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    return {"caller_number": caller_number}


@router.get(
    "/contact/{contact_id}",
    response_model=CallListResponse,
    summary="Get calls by contact",
    description="Get all calls for a specific contact.",
)
async def get_calls_by_contact(
    contact_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> CallListResponse:
    """Get all calls for a contact. RGPD Art. 15."""
    call_repo = CallRepository(db)
    calls, total = await call_repo.get_calls_by_contact(contact_id, skip=skip, limit=limit)
    return CallListResponse(
        items=[CallResponse.model_validate(c) for c in calls], total=total, skip=skip, limit=limit
    )


@router.get(
    "/agent/{agent_id}",
    response_model=CallListResponse,
    summary="Get calls by agent",
    description="Get all calls handled by a specific agent.",
)
async def get_calls_by_agent(
    agent_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> CallListResponse:
    """Get all calls for an agent."""
    call_repo = CallRepository(db)
    calls, total = await call_repo.get_calls_by_agent(agent_id, skip=skip, limit=limit)
    return CallListResponse(
        items=[CallResponse.model_validate(c) for c in calls], total=total, skip=skip, limit=limit
    )
