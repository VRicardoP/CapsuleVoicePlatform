"""
AI Agent endpoints.
Endpoints for the AI conversational agent (n8n integration).

Requires API Key authentication with client_type='ai_agent'.

Compliance:
- AI Act Art. 12: All decisions logged
- AI Act Art. 14: Human escalation support
- AI Act Art. 50: Disclosure tracking
"""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_key_auth import ServiceIdentity, require_ai_agent
from app.core.dependencies import get_db, require_dpo
from app.repositories.call_repository import CallRepository, TranscriptionRepository
from app.repositories.client_error_repository import (
    ClientErrorRepository,
    CustomerContextRepository,
)
from app.repositories.gdpr_repository import AuditLogRepository
from app.schemas.ai_agent import (
    AIDecisionCreate,
    AIDecisionResponse,
    CallUpdateResponse,
    ClientErrorListItem,
    ClientErrorListResponse,
    ClientErrorReport,
    ClientErrorReportResponse,
    ConsentCheckResponse,
    CustomerContextResponse,
    HumanEscalationCreate,
    HumanEscalationResponse,
    SentimentAnalysisCreate,
    TranscriptionBatchCreate,
    TranscriptionResponse,
    TranscriptionSegmentCreate,
)

router = APIRouter()


# === HELPERS ===


async def _get_call_or_404(call_id: UUID, db: AsyncSession):
    """Fetch a call by ID or raise 404."""
    call_repo = CallRepository(db)
    call = await call_repo.get_by_id(call_id)
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
    return call


# === ENDPOINTS ===


@router.post(
    "/calls/{call_id}/transcription",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save transcription segment",
)
async def save_transcription(
    call_id: UUID,
    segment: TranscriptionSegmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_agent)],
) -> TranscriptionResponse:
    """Save a single transcription segment."""
    await _get_call_or_404(call_id, db)
    transcription_repo = TranscriptionRepository(db)

    transcription = await transcription_repo.create(
        {
            "call_id": call_id,
            "speaker_type": segment.speaker_type,
            "text": segment.text,
            "segment_index": segment.segment_index,
            "start_time_ms": segment.start_time_ms,
            "end_time_ms": segment.end_time_ms,
            "confidence": segment.confidence,
            "language": segment.language,
            "contains_sensitive_data": segment.contains_sensitive_data,
        }
    )
    await db.commit()
    await db.refresh(transcription)

    return TranscriptionResponse(
        id=transcription.id,
        call_id=call_id,
        segment_index=transcription.segment_index,
        created_at=transcription.created_at,
    )


@router.post(
    "/calls/{call_id}/transcription/batch",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save transcription batch",
)
async def save_transcription_batch(
    call_id: UUID,
    batch: TranscriptionBatchCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_agent)],
) -> TranscriptionResponse:
    """Save multiple transcription segments in a batch."""
    await _get_call_or_404(call_id, db)
    transcription_repo = TranscriptionRepository(db)

    for seg in batch.segments:
        await transcription_repo.create(
            {
                "call_id": call_id,
                "speaker_type": seg.speaker_type,
                "text": seg.text,
                "segment_index": seg.segment_index,
                "start_time_ms": seg.start_time_ms,
                "end_time_ms": seg.end_time_ms,
                "confidence": seg.confidence,
                "language": seg.language,
                "contains_sensitive_data": seg.contains_sensitive_data,
            }
        )

    await db.commit()

    return TranscriptionResponse(
        id=None,
        call_id=call_id,
        segment_index=len(batch.segments),
        created_at=datetime.now(UTC),
    )


@router.post(
    "/calls/{call_id}/decisions",
    response_model=AIDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log AI decision",
)
async def log_ai_decision(
    call_id: UUID,
    decision: AIDecisionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_agent)],
) -> AIDecisionResponse:
    """Log an AI agent decision for traceability (AI Act Art. 12)."""
    await _get_call_or_404(call_id, db)
    from app.models.ai_decision import AIDecisionLog

    ai_decision = AIDecisionLog(
        call_id=call_id,
        model_name=decision.model_name,
        model_version=decision.model_version,
        input_type=decision.input_type,
        output_type=decision.output_type,
        output_summary=decision.output_summary,
        confidence_score=float(decision.confidence_score) if decision.confidence_score else None,
        human_oversight_required=decision.human_oversight_required,
        ai_risk_level=decision.ai_risk_level,
        extra_metadata=decision.metadata,
        decision_timestamp=datetime.now(UTC),
    )
    db.add(ai_decision)
    await db.flush()
    await db.commit()

    return AIDecisionResponse(
        decision_id=ai_decision.id,
        call_id=call_id,
        model_name=ai_decision.model_name,
        created_at=ai_decision.decision_timestamp,
    )


@router.post(
    "/calls/{call_id}/sentiment",
    response_model=CallUpdateResponse,
    summary="Update call sentiment",
)
async def update_call_sentiment(
    call_id: UUID,
    sentiment_data: SentimentAnalysisCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_agent)],
) -> CallUpdateResponse:
    """Update AI-analyzed sentiment for a call (AI Act Art. 50.3)."""
    await _get_call_or_404(call_id, db)
    call_repo = CallRepository(db)
    audit_repo = AuditLogRepository(db)

    update_fields: dict[str, Any] = {
        "sentiment": sentiment_data.sentiment,
        "sentiment_score": float(sentiment_data.confidence_score)
        if sentiment_data.confidence_score
        else None,
    }

    if sentiment_data.consent_given is not None:
        update_fields["sentiment_consent"] = sentiment_data.consent_given

    await call_repo.update(call_id, update_fields)

    from app.models.ai_decision import AIDecisionLog

    ai_decision = AIDecisionLog(
        call_id=call_id,
        model_name="sentiment-analysis",
        model_version="1.0",
        input_type="audio",
        output_type="classification",
        output_summary=sentiment_data.sentiment,
        confidence_score=float(sentiment_data.confidence_score)
        if sentiment_data.confidence_score
        else None,
        is_emotion_analysis=True,
        human_oversight_required=False,
        ai_risk_level="limited",
        extra_metadata={
            "consent_given": sentiment_data.consent_given,
            "emotion_disclosed": True,
        },
        decision_timestamp=datetime.now(UTC),
    )
    db.add(ai_decision)

    await audit_repo.log_action(
        action="AI_DECISION_LOGGED",
        entity_type="calls",
        entity_id=call_id,
        severity="info",
        details={"type": "sentiment_analysis", "result": sentiment_data.sentiment},
    )

    await db.commit()

    return CallUpdateResponse(
        call_id=call_id,
        updated_fields=["sentiment", "sentiment_score", "sentiment_consent"],
        updated_at=datetime.now(UTC),
    )


@router.get(
    "/customers/{contact_id}/context",
    response_model=CustomerContextResponse,
    summary="Get customer context",
)
async def get_customer_context(
    contact_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_agent)],
) -> CustomerContextResponse:
    """Get customer context for AI agent (RGPD Art. 32)."""
    ctx_repo = CustomerContextRepository(db)
    data = await ctx_repo.get_customer_context(contact_id)

    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    return CustomerContextResponse(
        contact_id=contact_id,
        phone=data.get("phone"),
        email=data.get("email"),
        full_name=data.get("full_name"),
        previous_calls_count=data.get("previous_calls_count", 0) or 0,
        last_call_date=data.get("last_call_date"),
        active_consents=data.get("active_consents") or [],
        marketing_opt_out=data.get("marketing_opt_out", False),
        profiling_opt_out=data.get("profiling_opt_out", False),
        processing_restricted=data.get("processing_restricted", False),
        robinson_status=data.get("robinson_status"),
    )


@router.get(
    "/customers/{contact_id}/consents/{scope}",
    response_model=ConsentCheckResponse,
    summary="Check customer consent",
)
async def check_customer_consent(
    contact_id: UUID,
    scope: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_agent)],
) -> ConsentCheckResponse:
    """Check if customer has consent for a scope (RGPD Art. 6, 7)."""
    ctx_repo = CustomerContextRepository(db)
    consent = await ctx_repo.check_consent(contact_id, scope)

    if consent:
        return ConsentCheckResponse(
            has_consent=True,
            scope=scope,
            granted_at=consent.get("obtained_at"),
            expires_at=consent.get("expires_at"),
        )
    return ConsentCheckResponse(has_consent=False, scope=scope)


@router.post(
    "/calls/{call_id}/human-escalation",
    response_model=HumanEscalationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request human escalation",
)
async def request_human_escalation(
    call_id: UUID,
    escalation: HumanEscalationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_agent)],
) -> HumanEscalationResponse:
    """Request human escalation for a call (AI Act Art. 14)."""
    await _get_call_or_404(call_id, db)
    call_repo = CallRepository(db)
    audit_repo = AuditLogRepository(db)

    await call_repo.update(call_id, {"human_oversight_required": True})

    from app.models.ai_decision import AIDecisionLog

    ai_decision = AIDecisionLog(
        call_id=call_id,
        model_name="escalation-engine",
        model_version="1.0",
        input_type="conversation",
        output_type="escalation",
        output_summary=f"human_escalation_{escalation.urgency}",
        human_oversight_required=True,
        ai_risk_level="high" if escalation.urgency == "critical" else "limited",
        extra_metadata={"reason": escalation.reason, "context": escalation.context_summary},
        decision_timestamp=datetime.now(UTC),
    )
    db.add(ai_decision)
    await db.flush()

    await audit_repo.log_action(
        action="AI_DECISION_LOGGED",
        entity_type="calls",
        entity_id=call_id,
        severity="warning",
        details={
            "reason": escalation.reason,
            "urgency": escalation.urgency,
            "type": "human_escalation",
        },
    )
    await db.commit()

    return HumanEscalationResponse(
        escalation_id=str(ai_decision.id),
        call_id=str(call_id),
        reason=escalation.reason,
        priority=escalation.urgency,
        created_at=datetime.now(UTC),
    )


@router.post(
    "/calls/{call_id}/summary",
    response_model=CallUpdateResponse,
    summary="Update call summary",
)
async def update_call_summary(
    call_id: UUID,
    summary_data: dict[str, Any],
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_agent)],
) -> CallUpdateResponse:
    """Update AI-generated call summary."""
    await _get_call_or_404(call_id, db)
    call_repo = CallRepository(db)

    update_fields = {}
    if "summary" in summary_data:
        update_fields["ai_summary"] = summary_data["summary"]
    if "category" in summary_data:
        update_fields["ai_category"] = summary_data["category"]
    if "disposition_code" in summary_data:
        update_fields["disposition_code"] = summary_data["disposition_code"]

    if update_fields:
        await call_repo.update(call_id, update_fields)
        await db.commit()

    return CallUpdateResponse(
        call_id=call_id,
        updated_fields=list(update_fields.keys()),
        updated_at=datetime.now(UTC),
    )


# === CLIENT ERROR REPORTING ===


@router.post(
    "/client-errors",
    response_model=ClientErrorReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report client error",
)
async def report_client_error(
    error_report: ClientErrorReport,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ServiceIdentity, Depends(require_ai_agent)],
) -> ClientErrorReportResponse:
    """Receive error reports from CapsuleAgentClient."""
    error_repo = ClientErrorRepository(db)
    error_id = await error_repo.create(
        api_key_id=service.api_key_id,
        client_version=error_report.client_version,
        error_type=error_report.error_type,
        error_message=error_report.error_message,
        method=error_report.method,
        endpoint=error_report.endpoint,
        request_payload=error_report.request_payload,
        response_status=error_report.response_status,
        response_body=error_report.response_body,
        call_id=error_report.call_id,
        error_timestamp=error_report.timestamp,
        stack_trace=error_report.stack_trace,
        environment=error_report.environment,
        extra_context=error_report.extra_context,
        reported_from_ip=request.client.host if request.client else None,
    )
    await db.commit()
    return ClientErrorReportResponse(
        status="received", message="Error logged successfully", error_id=error_id
    )


@router.get(
    "/client-errors",
    response_model=ClientErrorListResponse,
    summary="Get client errors",
)
async def get_client_errors(
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[str, Depends(require_dpo)],
    days: int = Query(7, ge=1, le=90),
    error_type: str | None = Query(None),
    resolved: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> ClientErrorListResponse:
    """Get client errors for debugging (DPO/admin only)."""
    error_repo = ClientErrorRepository(db)
    items, total = await error_repo.list_errors(
        days=days,
        error_type=error_type,
        resolved=resolved,
        page=page,
        page_size=page_size,
    )
    errors = [
        ClientErrorListItem(
            id=str(item["id"]),
            client_version=item.get("client_version"),
            error_type=item["error_type"],
            error_message=item["error_message"],
            endpoint=item.get("endpoint"),
            response_status=item.get("response_status"),
            call_id=str(item["call_id"]) if item.get("call_id") else None,
            error_timestamp=item.get("error_timestamp"),
            reported_at=item.get("reported_at"),
            environment=item.get("environment"),
            resolved=item.get("resolved"),
            resolved_at=item.get("resolved_at"),
        )
        for item in items
    ]
    return ClientErrorListResponse(errors=errors, total=total, page=page, page_size=page_size)
