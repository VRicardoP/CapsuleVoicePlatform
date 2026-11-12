"""
Call management endpoints.
CRUD operations for calls with compliance tracking.

Supports both JWT authentication (for dashboard users) and API Key authentication
(for voice assistants, PBX systems, and other services).
"""

"""
Call management endpoints — CRUD, create, update, list, transcription add.

Recording, transcript retrieval, human review, and lookup endpoints
are in calls_recordings.py.
"""
import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_key_auth import get_service_identity
from app.core.dependencies import (
    get_current_user_id,
    get_db,
    get_db_with_rls,
)
from app.repositories.call_repository import CallRepository, TranscriptionRepository
from app.repositories.gdpr_repository import AuditLogRepository
from app.schemas.calls import (
    CallCreateRequest,
    CallListResponse,
    CallResponse,
    CallUpdateRequest,
    FrontendCallDetailResponse,
    TranscriptionCreateRequest,
    TranscriptionSegment,
)

router = APIRouter()


# === AUTHENTICATION HELPER ===


async def get_auth_identity(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> tuple[str, str]:
    """Resolve identity: API Key (service) OR user (BFF/JWT).

    Order:
      1. ``X-API-Key`` header → service identity (Ultravox, PBX, voice agents).
      2. BFF cookie session populated by ``BFFSessionMiddleware`` → user.
      3. Legacy JWT (Authorization header or ``access_token`` cookie) → user.

    BFF wins over JWT when both are present (e.g. during the auto-upgrade
    transition). API Key always wins when present — that's intentional
    because ``X-API-Key`` is an explicit caller signal.
    """
    # 1. API Key (services)
    if x_api_key:
        service = await get_service_identity(request, x_api_key, db)
        if service:
            return service.service_id, "service"

    # 2. BFF cookie path — middleware already validated and populated state
    state_user_id = getattr(request.state, "user_id", None)
    if state_user_id and getattr(request.state, "auth_source", "").startswith("bff"):
        return state_user_id, "user"

    # 3. Legacy JWT fallback (Bearer header or access_token cookie)
    from fastapi.security import HTTPBearer

    security = HTTPBearer(auto_error=False)
    credentials = await security(request)
    access_token = request.cookies.get("access_token")

    try:
        user_id = await get_current_user_id(request, credentials, db, access_token)
        return user_id, "user"
    except HTTPException:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide cookie, JWT, or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


# === ENDPOINTS ===


@router.post(
    "",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new call",
    description="""
Create a new call record.

**Authentication**: JWT token OR API Key (X-API-Key header)

API Key example:
```
curl -X POST /api/v1/calls \\
  -H "X-API-Key: capsule_ai_agent_abc123..." \\
  -H "Content-Type: application/json" \\
  -d '{"direction": "inbound", "status": "initiated"}'
```
""",
)
async def create_call(
    request: Request,
    call_data: CallCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> CallResponse:
    """
    Create a new call record.

    Used by:
    - Voice assistants (via API Key)
    - PBX integrations (via API Key)
    - Dashboard users (via JWT)

    Compliance:
    - AI Act Art. 50.1: ai_disclosure_timestamp should be set BEFORE conversation
    - RGPD Art. 7: recording_consent must be obtained before recording
    """
    # Get actor info (either user or service)
    auth_id, auth_type = await get_auth_identity(request, db, x_api_key)

    call_repo = CallRepository(db)
    audit_repo = AuditLogRepository(db)

    # Prepare call data
    call_dict = call_data.model_dump(exclude_unset=True)

    # Set default initiated_at if not provided
    if "initiated_at" not in call_dict or call_dict["initiated_at"] is None:
        call_dict["initiated_at"] = datetime.now()

    # Create the call
    call = await call_repo.create(call_dict)

    # Audit log
    await audit_repo.log_action(
        action="INSERT",
        entity_type="calls",
        user_id=auth_id if auth_type == "user" else None,
        entity_id=call.id,
        details={**call_dict, "_actor": f"{auth_type}:{auth_id}"},
    )

    await db.commit()
    await db.refresh(call)

    return CallResponse.model_validate(call)


@router.put(
    "/{call_id}",
    response_model=CallResponse,
    summary="Update a call",
    description="""
Update an existing call record.

**Authentication**: JWT token OR API Key (X-API-Key header)
""",
)
async def update_call(
    request: Request,
    call_id: UUID,
    call_data: CallUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> CallResponse:
    """
    Update an existing call.

    Used to:
    - Update call status (answered, completed, etc.)
    - Add sentiment analysis results
    - Add AI summary after call ends
    - Record disposition codes
    """
    # Get actor info (either user or service)
    auth_id, auth_type = await get_auth_identity(request, db, x_api_key)

    call_repo = CallRepository(db)
    audit_repo = AuditLogRepository(db)

    # Verify call exists
    existing_call = await call_repo.get_by_id(call_id)
    if not existing_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    # Get only the fields that were set
    update_dict = call_data.model_dump(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Update the call
    call = await call_repo.update(call_id, update_dict)

    # Audit log
    await audit_repo.log_action(
        action="UPDATE",
        entity_type="calls",
        user_id=auth_id if auth_type == "user" else None,
        entity_id=call_id,
        changed_fields=update_dict,
        details={"_actor": f"{auth_type}:{auth_id}"},
    )

    await db.commit()
    await db.refresh(call)

    return CallResponse.model_validate(call)


@router.post(
    "/{call_id}/transcription",
    response_model=TranscriptionSegment,
    status_code=status.HTTP_201_CREATED,
    summary="Add transcription segment",
    description="""
Add a transcription segment to a call.

**Authentication**: JWT token OR API Key (X-API-Key header)
""",
)
async def add_transcription(
    request: Request,
    call_id: UUID,
    transcription_data: TranscriptionCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> TranscriptionSegment:
    """
    Add a transcription segment to a call.

    Used by voice assistants to stream transcription segments in real-time
    or add complete transcription after call ends.

    Compliance:
    - RGPD Art. 15: Transcriptions are personal data
    - AI Act Art. 50.2: AI-generated transcriptions must be labeled
    """
    # Authenticate (either user or service)
    await get_auth_identity(request, db, x_api_key)

    call_repo = CallRepository(db)
    transcription_repo = TranscriptionRepository(db)

    # Verify call exists
    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    # Create transcription segment
    transcription_dict = transcription_data.model_dump()
    transcription_dict["call_id"] = call_id

    transcription = await transcription_repo.create(transcription_dict)

    await db.commit()
    await db.refresh(transcription)

    return TranscriptionSegment.model_validate(transcription)


@router.get(
    "",
    response_model=CallListResponse,
    summary="List calls",
    description="List calls with filtering and pagination.",
)
async def list_calls(
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    direction: str | None = Query(None, description="Filter by direction"),
    status: str | None = Query(None, description="Filter by status"),
    contact_id: UUID | None = Query(None, description="Filter by contact"),
    agent_id: UUID | None = Query(None, description="Filter by agent"),
    start_date: datetime | None = Query(None, description="Filter from date"),
    end_date: datetime | None = Query(None, description="Filter to date"),
) -> CallListResponse:
    """List calls with optional filters."""
    call_repo = CallRepository(db)
    calls, total = await call_repo.list_filtered(
        direction=direction,
        call_status=status,
        contact_id=contact_id,
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return CallListResponse(
        items=[CallResponse.model_validate(c) for c in calls],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/active",
    response_model=list[CallResponse],
    summary="Get active calls",
    description="Get all currently active calls.",
)
async def get_active_calls(
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> list[CallResponse]:
    """Get all active (in-progress) calls."""
    call_repo = CallRepository(db)
    calls = await call_repo.get_active_calls()
    return [CallResponse.model_validate(c) for c in calls]


@router.get(
    "/requiring-review",
    response_model=list[CallResponse],
    summary="Get calls requiring human review",
    description="Get calls flagged for human oversight (AI Act Art. 14).",
)
async def get_calls_requiring_review(
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[CallResponse]:
    """
    Get calls requiring human review.

    AI Act Art. 14: Human oversight for high-risk decisions.
    """
    call_repo = CallRepository(db)
    calls = await call_repo.get_calls_requiring_human_review(skip=skip, limit=limit)
    return [CallResponse.model_validate(c) for c in calls]


@router.get(
    "/{call_id}",
    response_model=FrontendCallDetailResponse,
    summary="Get call details",
    description="Get detailed information about a specific call for frontend modal.",
)
async def get_call(
    call_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
) -> FrontendCallDetailResponse:
    """Get call details in frontend-expected format."""
    from app.services.call_detail_service import get_call_detail

    try:
        return await get_call_detail(call_id, db)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )


# Recording, transcript, human review, and lookup endpoints are in calls_recordings.py
