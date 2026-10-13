"""
PBX/CTI endpoints.
Endpoints for the telephone system (Centralita).

Requires API Key authentication with client_type='pbx' or 'ai_agent'.

Compliance:
- AI Act Art. 50: AI disclosure tracking
- RGPD Art. 7: Consent recording
- LOPDGDD Art. 33: Robinson list verification
- LGT Art. 68: Traffic data management
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_key_auth import ServiceIdentity, require_ai_or_pbx
from app.core.dependencies import get_db
from app.repositories.call_repository import CallRepository
from app.repositories.consent_repository import CallConsentRepository
from app.repositories.gdpr_repository import AuditLogRepository
from app.repositories.robinson_repository import RobinsonCheckRepository
from app.schemas.pbx import (
    AIDisclosureCreate,
    CallCreate,
    CallEndCreate,
    CallStatusUpdate,
    ConsentCreate,
    RecordingCreate,
)
from app.schemas.pbx import (
    PBXAIDisclosureResponse as AIDisclosureResponse,
)
from app.schemas.pbx import (
    PBXCallCreateResponse as CallCreateResponse,
)
from app.schemas.pbx import (
    PBXCallEndResponse as CallEndResponse,
)
from app.schemas.pbx import (
    PBXCallStatusResponse as CallStatusResponse,
)
from app.schemas.pbx import (
    PBXConsentResponse as ConsentResponse,
)
from app.schemas.pbx import (
    PBXRecordingResponse as RecordingResponse,
)
from app.schemas.pbx import (
    PBXRobinsonCheckResponse as RobinsonCheckResponse,
)

router = APIRouter()


# === ENDPOINTS ===


@router.post(
    "/calls",
    response_model=CallCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new call",
    description="Register a new call in the system.",
)
async def create_call(
    call_data: CallCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_or_pbx)],
) -> CallCreateResponse:
    """
    Create a new call record.

    LGT Art. 68: Also creates traffic data record with 12-month retention.
    """
    call_repo = CallRepository(db)
    robinson_repo = RobinsonCheckRepository(db)

    # Check if Robinson check is recommended (for outbound commercial calls)
    robinson_recommended = False
    if call_data.direction == "outbound" and call_data.purpose == "commercial":
        # Check if we have a valid Robinson check
        if call_data.caller_number:
            can_contact, reason = await robinson_repo.can_contact(call_data.caller_number)
            if not can_contact and reason == "robinson_listed":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="LOPDGDD Art. 33: Contact is on Robinson list. Commercial contact PROHIBITED.",
                )
            elif reason == "check_required":
                robinson_recommended = True

    # Create call with traffic data
    call = await call_repo.create_call(
        direction=call_data.direction,
        caller_number=call_data.caller_number,
        called_number=call_data.called_number,
        external_call_id=call_data.external_call_id,
        contact_id=call_data.contact_id,
        agent_id=call_data.agent_id,
        call_type=call_data.call_type,
        purpose=call_data.purpose,
        campaign_id=call_data.campaign_id,
        queue_name=call_data.queue_name,
        is_employee_call=call_data.is_employee_call,
        metadata=call_data.metadata,
    )

    await db.commit()

    return CallCreateResponse(
        call_id=call.id,
        external_call_id=call.external_call_id,
        status=call.status,
        created_at=call.created_at,
        ai_disclosure_required=True,  # Always required per AI Act Art. 50
        robinson_check_recommended=robinson_recommended,
    )


@router.put(
    "/calls/{call_id}/status",
    response_model=CallStatusResponse,
    summary="Update call status",
    description="Update the status of an existing call.",
)
async def update_call_status(
    call_id: UUID,
    status_data: CallStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_or_pbx)],
) -> CallStatusResponse:
    """Update call status."""
    call_repo = CallRepository(db)

    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    # Update status
    updated_call = await call_repo.update_status(
        call_id,
        status_data.status,
        **status_data.model_dump(exclude={"status"}, exclude_unset=True),
    )

    await db.commit()

    return CallStatusResponse(
        call_id=call_id,
        status=updated_call.status,
        updated_at=updated_call.updated_at,
        duration_seconds=updated_call.duration_seconds,
    )


@router.post(
    "/calls/{call_id}/ai-disclosure",
    response_model=AIDisclosureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record AI disclosure",
    description="Record that AI disclosure was made to the caller (AI Act Art. 50.1).",
)
async def record_ai_disclosure(
    call_id: UUID,
    disclosure: AIDisclosureCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_or_pbx)],
) -> AIDisclosureResponse:
    """
    Record AI disclosure.

    AI Act Art. 50.1: MUST inform BEFORE conversation that caller is
    interacting with an AI system.
    """
    call_repo = CallRepository(db)
    audit_repo = AuditLogRepository(db)

    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    # Verify disclosure is BEFORE conversation (answered_at)
    now = datetime.now(UTC)
    if call.answered_at and now > call.answered_at:
        # Log compliance warning but still record
        await audit_repo.log_action(
            action="AI_TRANSPARENCY_WARNING",
            entity_type="calls",
            entity_id=call_id,
            severity="warning",
            details={
                "warning": "AI Act Art. 50.1: Disclosure should be BEFORE conversation",
                "answered_at": call.answered_at.isoformat() if call.answered_at else None,
                "disclosed_at": now.isoformat(),
            },
        )

    # Record disclosure
    await call_repo.record_ai_disclosure(call_id, method=disclosure.method)

    # Also record emotion detection disclosure if applicable
    if disclosure.emotion_detection_disclosed:
        await call_repo.record_emotion_disclosure(call_id)

    await db.commit()

    return AIDisclosureResponse(
        call_id=call_id,
        disclosed_at=now,
        method=disclosure.method,
        compliant=not (call.answered_at and now > call.answered_at),
    )


@router.post(
    "/calls/{call_id}/consent",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record consent",
    description="Record consent obtained during a call.",
)
async def record_consent(
    call_id: UUID,
    consent_data: ConsentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_or_pbx)],
) -> ConsentResponse:
    """
    Record consent obtained during call.

    RGPD Art. 7: Consent must be demonstrable.
    LOPDGDD Art. 6.3: Evidence must be stored.
    """
    call_repo = CallRepository(db)
    consent_repo = CallConsentRepository(db)

    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    # Link call to consent + purpose (RGPD Art. 5.1.b purpose limitation)
    consent = await consent_repo.link_call_consent(
        call_id=call_id,
        purpose_id=UUID(consent_data.purpose_id),
        consent_id=UUID(consent_data.consent_id),
        retention_until=consent_data.retention_until,
    )

    await db.commit()

    return ConsentResponse(
        consent_id=consent.id,
        call_id=call_id,
        purpose_id=consent.purpose_id,
        processing_enabled=consent.processing_enabled,
        created_at=consent.created_at,
    )


@router.post(
    "/calls/{call_id}/recording",
    response_model=RecordingResponse,
    summary="Start/record recording",
    description="Register that recording has started (requires consent).",
)
async def record_recording(
    call_id: UUID,
    recording_data: RecordingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_or_pbx)],
) -> RecordingResponse:
    """
    Register recording start.

    RGPD Art. 7: Recording requires consent (unless other legal basis).
    AEPD: Must inform BEFORE recording starts.
    """
    call_repo = CallRepository(db)
    consent_repo = CallConsentRepository(db)

    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    # Verify recording consent if not using other legal basis
    consent_verified = False
    if recording_data.consent_verified:
        consent_verified = True
    else:
        # Check if any processing consent exists for this call
        call_consents = await consent_repo.get_call_consents(call_id)
        if not call_consents:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="RGPD Art. 7: Recording consent required",
            )
        consent_verified = True

    # Verify informed timestamp is before recording
    if recording_data.informed_timestamp:
        await call_repo.update(
            call_id,
            {"recording_informed_timestamp": recording_data.informed_timestamp},
        )

    # Update call recording status
    now = datetime.now(UTC)
    await call_repo.record_recording_consent(call_id, consent=True)
    await call_repo.update(
        call_id,
        {
            "is_recorded": True,
            "recording_file_path": recording_data.file_path,
        },
    )

    await db.commit()

    return RecordingResponse(
        call_id=call_id,
        recording_started=True,
        consent_verified=consent_verified,
        started_at=now,
    )


@router.get(
    "/robinson/check",
    response_model=RobinsonCheckResponse,
    summary="Check Robinson list",
    description="Check if a phone number is on the Robinson list.",
)
async def check_robinson(
    phone_number: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_or_pbx)],
    purpose: str | None = None,
    campaign_id: UUID | None = None,
) -> RobinsonCheckResponse:
    """
    Check Robinson list.

    Orden ETD/1286/2022:
    - Art. 4.1: MUST check before commercial communications
    - Art. 4.2: Check valid for MAX 30 days
    - Art. 4.3: MUST exclude listed contacts
    """
    robinson_repo = RobinsonCheckRepository(db)

    # Check for existing valid check
    existing = await robinson_repo.get_valid_check(phone_number)

    if existing:
        return RobinsonCheckResponse(
            phone_number_hash=existing.phone_number_hash,
            is_listed=existing.is_listed,
            can_contact=not existing.is_listed,
            check_id=existing.id,
            valid_until=existing.valid_until,
            message="Using cached check (valid per Orden ETD/1286/2022 Art. 4.2)",
        )

    # Simulate Robinson API check (in production, call actual API)
    # For now, return not listed
    is_listed = False  # Would be result from actual Robinson API

    # Record the check
    check = await robinson_repo.record_check(
        phone_number=phone_number,
        is_listed=is_listed,
        purpose=purpose,
        campaign_id=campaign_id,
        checked_by_system="pbx",
    )

    await db.commit()

    message = "Contact CAN be contacted for commercial purposes"
    if is_listed:
        message = "PROHIBITED: Contact is on Robinson list (Orden ETD/1286/2022 Art. 4.3)"

    return RobinsonCheckResponse(
        phone_number_hash=check.phone_number_hash,
        is_listed=is_listed,
        can_contact=not is_listed,
        check_id=check.id,
        valid_until=check.valid_until,
        message=message,
    )


@router.post(
    "/calls/{call_id}/end",
    response_model=CallEndResponse,
    summary="End call",
    description="End a call and finalize all data.",
)
async def end_call(
    call_id: UUID,
    end_data: CallEndCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_or_pbx)],
) -> CallEndResponse:
    """
    End a call.

    LGT Art. 68.3: Traffic data retained for 12 months.
    """
    call_repo = CallRepository(db)

    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    now = datetime.now(UTC)

    # Calculate duration if not provided
    duration = end_data.duration_seconds
    if duration is None and call.answered_at:
        duration = int((now - call.answered_at).total_seconds())

    # Update call
    await call_repo.update(
        call_id,
        {
            "status": end_data.status or "completed",
            "ended_at": now,
            "duration_seconds": duration,
            "disposition_code": end_data.disposition_code,
            "disposition_notes": end_data.notes,
        },
    )

    # Update traffic data destruction date
    await call_repo.update_traffic_data_duration(call_id, duration)

    await db.commit()

    # Get retention date (12 months per LGT Art. 68.3)
    retention_until = (
        call.initiated_at + timedelta(days=365) if call.initiated_at else now + timedelta(days=365)
    )

    return CallEndResponse(
        call_id=call_id,
        status=end_data.status or "completed",
        duration_seconds=duration,
        ended_at=now,
        traffic_data_retained=True,
        retention_until=retention_until,
    )


@router.get(
    "/calls/{call_id}",
    response_model=dict[str, Any],
    summary="Get call details",
    description="Get call details for PBX integration.",
)
async def get_call(
    call_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_or_pbx)],
) -> dict[str, Any]:
    """Get call details."""
    call_repo = CallRepository(db)

    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    return {
        "id": str(call.id),
        "external_call_id": call.external_call_id,
        "direction": call.direction,
        "status": call.status,
        "caller_number": call.caller_number,
        "called_number": call.called_number,
        "initiated_at": call.initiated_at.isoformat() if call.initiated_at else None,
        "answered_at": call.answered_at.isoformat() if call.answered_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "duration_seconds": call.duration_seconds,
        "ai_disclosure_timestamp": call.ai_disclosure_timestamp.isoformat()
        if call.ai_disclosure_timestamp
        else None,
        "is_recorded": call.is_recorded,
        "recording_consent": call.recording_consent,
        "contact_id": str(call.contact_id) if call.contact_id else None,
        "agent_id": str(call.agent_id) if call.agent_id else None,
    }


@router.get(
    "/calls/by-external-id/{external_id}",
    response_model=dict[str, Any],
    summary="Get call by external ID",
    description="Get call by PBX external ID.",
)
async def get_call_by_external_id(
    external_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_or_pbx)],
) -> dict[str, Any]:
    """Get call by external PBX ID."""
    from sqlalchemy import select

    from app.models.call import Call

    result = await db.execute(select(Call).where(Call.external_call_id == external_id))
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    return {
        "id": str(call.id),
        "external_call_id": call.external_call_id,
        "direction": call.direction,
        "status": call.status,
        "initiated_at": call.initiated_at.isoformat() if call.initiated_at else None,
    }
