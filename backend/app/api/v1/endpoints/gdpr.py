"""
GDPR Rights endpoints.
Implementation of RGPD Art. 15-22 (ARSOPL rights).

Rights covered:
- Art. 15: Access
- Art. 16: Rectification
- Art. 17: Erasure (with LOPDGDD Art. 33 blocking)
- Art. 18: Restriction
- Art. 20: Portability
- Art. 21: Objection

Additional features:
- Compliance PDF report generation for AEPD submissions
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db, require_dpo
from app.repositories.gdpr_repository import (
    AuditLogRepository,
    BlockedDataRepository,
    DataSubjectRequestRepository,
)
from app.schemas.gdpr import (
    BlockedDataResponse,
    ErasureRequest,
    GDPRExportResponse,
    ObjectionRequest,
    PendingRequestsResponse,
    RectificationRequest,
    RestrictionRequest,
    RightRequestCreate,
    RightRequestResponse,
)
from app.services.compliance_report_service import ComplianceReportService

router = APIRouter()


# === ENDPOINTS ===


@router.get(
    "/export",
    response_model=GDPRExportResponse,
    summary="Export personal data (Art. 15, 20)",
    description="Export all personal data for the current user.",
)
async def export_personal_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    format: str = Query("json", pattern="^(json|csv)$"),
) -> GDPRExportResponse:
    """
    Export personal data.

    RGPD Art. 15: Right of access
    RGPD Art. 20: Right to data portability

    Calls PostgreSQL function export_user_data_gdpr_compliant().
    """
    audit_repo = AuditLogRepository(db)

    # Call the PostgreSQL function for GDPR-compliant export
    data = await audit_repo.export_user_data_gdpr(current_user_id)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found for user",
        )

    # Log the export (RGPD Art. 30)
    await audit_repo.log_action(
        action="DATA_EXPORT",
        entity_type="users",
        user_id=current_user_id,
        entity_id=current_user_id,
        details={"format": format, "export_type": "self_service"},
    )

    await db.commit()

    return GDPRExportResponse(
        user_id=current_user_id,
        export_format=format,
        data=data,
        generated_at=datetime.now(UTC),
    )


@router.post(
    "/requests",
    response_model=RightRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create GDPR rights request",
    description="Submit a GDPR rights request (access, rectification, erasure, etc.).",
)
async def create_rights_request(
    request: Request,
    request_data: RightRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> RightRequestResponse:
    """
    Create a GDPR rights request.

    The request will be processed within 1 month (RGPD Art. 12.3).
    """
    dsr_repo = DataSubjectRequestRepository(db)
    audit_repo = AuditLogRepository(db)

    # Create the request
    dsr = await dsr_repo.create_request(
        request_type=request_data.request_type,
        requester_type="user",
        requester_id=current_user_id,
        request_details=request_data.details,
    )

    # Log request creation
    client_ip = request.client.host if request.client else None
    await audit_repo.log_action(
        action="DATA_ACCESS_REQUEST",
        entity_type="data_subject_requests",
        user_id=current_user_id,
        entity_id=dsr.id,
        details={"request_type": request_data.request_type},
        ip_address=client_ip,
    )

    await db.commit()

    return RightRequestResponse(
        id=dsr.id,
        request_type=dsr.request_type,
        status=dsr.status,
        received_at=dsr.received_at,
        response_due_date=dsr.response_due_date,
    )


@router.get(
    "/requests",
    response_model=list[RightRequestResponse],
    summary="Get my GDPR requests",
    description="Get all GDPR requests for the current user.",
)
async def get_my_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> list[RightRequestResponse]:
    """Get all GDPR requests for current user."""
    from sqlalchemy import select

    from app.models.audit import DataSubjectRequest

    result = await db.execute(
        select(DataSubjectRequest)
        .where(DataSubjectRequest.requester_id == current_user_id)
        .order_by(DataSubjectRequest.received_at.desc())
    )
    requests = result.scalars().all()

    return [
        RightRequestResponse(
            id=r.id,
            request_type=r.request_type,
            status=r.status,
            received_at=r.received_at,
            response_due_date=r.response_due_date,
            responded_at=r.responded_at,
            response_details=r.response_details,
        )
        for r in requests
    ]


@router.post(
    "/rectify",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request data rectification (Art. 16)",
    description="Request correction of personal data.",
)
async def request_rectification(
    request: Request,
    rectification_data: RectificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """
    Request data rectification.

    RGPD Art. 16: Right to rectification.
    Creates a request that will be processed by DPO/admin.
    """
    dsr_repo = DataSubjectRequestRepository(db)

    details = f"Field: {rectification_data.field}, New value: {rectification_data.new_value}"
    if rectification_data.reason:
        details += f", Reason: {rectification_data.reason}"

    dsr = await dsr_repo.create_request(
        request_type="rectification",
        requester_type="user",
        requester_id=current_user_id,
        request_details=details,
    )

    await db.commit()

    return {
        "message": "Rectification request submitted",
        "request_id": str(dsr.id),
        "response_due_date": dsr.response_due_date.isoformat(),
    }


from app.core.dependencies import require_recent_auth as _require_recent_auth_gdpr


@router.post(
    "/erase",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request data erasure (Art. 17)",
    description="Request deletion of personal data.",
    dependencies=[Depends(_require_recent_auth_gdpr())],
)
async def request_erasure(
    request: Request,
    erasure_data: ErasureRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """
    Request data erasure.

    RGPD Art. 17: Right to erasure (right to be forgotten).
    LOPDGDD Art. 33: Data will be blocked before deletion if legal retention applies.

    Note: Some data may be retained under legal obligations (LGT Art. 68).
    """
    if not erasure_data.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must confirm erasure request",
        )

    dsr_repo = DataSubjectRequestRepository(db)

    dsr = await dsr_repo.create_request(
        request_type="erasure",
        requester_type="user",
        requester_id=current_user_id,
        request_details=f"Reason: {erasure_data.reason}",
    )

    await db.commit()

    return {
        "message": "Erasure request submitted. Some data may be retained under legal obligations.",
        "request_id": str(dsr.id),
        "response_due_date": dsr.response_due_date.isoformat(),
        "note": "Data subject to legal retention (e.g., LGT Art. 68) will be blocked per LOPDGDD Art. 33",
    }


@router.post(
    "/restrict",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request processing restriction (Art. 18)",
    description="Request restriction of data processing.",
)
async def request_restriction(
    request: Request,
    restriction_data: RestrictionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """
    Request processing restriction.

    RGPD Art. 18: Right to restriction of processing.
    When restricted, only storage is allowed.
    """
    dsr_repo = DataSubjectRequestRepository(db)

    details = f"Reason: {restriction_data.reason}"
    if restriction_data.scope:
        details += f", Scope: {restriction_data.scope}"

    dsr = await dsr_repo.create_request(
        request_type="restriction",
        requester_type="user",
        requester_id=current_user_id,
        request_details=details,
    )

    await db.commit()

    return {
        "message": "Restriction request submitted",
        "request_id": str(dsr.id),
        "response_due_date": dsr.response_due_date.isoformat(),
    }


@router.post(
    "/object",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Object to processing (Art. 21)",
    description="Object to specific types of data processing.",
)
async def object_to_processing(
    request: Request,
    objection_data: ObjectionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """
    Object to data processing.

    RGPD Art. 21: Right to object.
    Art. 21.2: Objection to direct marketing must be honored immediately.
    """
    dsr_repo = DataSubjectRequestRepository(db)

    # Marketing objection is immediate
    if objection_data.processing_type == "marketing":
        from app.repositories.user_repository import OrganizationRepository

        org_repo = OrganizationRepository(db)
        await org_repo.set_marketing_opt_out(current_user_id)
        await db.commit()

        return {
            "message": "Marketing objection processed immediately (RGPD Art. 21.2)",
            "effective_immediately": True,
        }

    # Other objections go through request process
    details = f"Processing type: {objection_data.processing_type}, Reason: {objection_data.reason}"

    dsr = await dsr_repo.create_request(
        request_type="objection",
        requester_type="user",
        requester_id=current_user_id,
        request_details=details,
    )

    await db.commit()

    return {
        "message": "Objection request submitted",
        "request_id": str(dsr.id),
        "response_due_date": dsr.response_due_date.isoformat(),
    }


# === DPO/ADMIN ENDPOINTS ===


@router.get(
    "/admin/requests/pending",
    response_model=PendingRequestsResponse,
    summary="Get pending requests (DPO)",
    description="Get all pending GDPR requests. Requires DPO role.",
    dependencies=[Depends(require_dpo)],
)
async def get_pending_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> PendingRequestsResponse:
    """Get all pending GDPR requests (DPO only)."""
    dsr_repo = DataSubjectRequestRepository(db)

    pending = await dsr_repo.get_pending_requests(skip=skip, limit=limit)
    overdue = await dsr_repo.get_overdue_requests()

    return PendingRequestsResponse(
        items=[
            RightRequestResponse(
                id=r.id,
                request_type=r.request_type,
                status=r.status,
                received_at=r.received_at,
                response_due_date=r.response_due_date,
                responded_at=r.responded_at,
            )
            for r in pending
        ],
        total=len(pending),
        overdue_count=len(overdue),
    )


@router.post(
    "/admin/requests/{request_id}/process",
    response_model=RightRequestResponse,
    summary="Process GDPR request (DPO)",
    description="Process and respond to a GDPR request. Requires DPO role.",
    dependencies=[Depends(require_dpo)],
)
async def process_request(
    request_id: UUID,
    response_data: dict[str, Any],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> RightRequestResponse:
    """
    Process a GDPR request (DPO only).

    For erasure requests, this will:
    1. Delete data where allowed
    2. Block data where legal retention applies (LOPDGDD Art. 33)
    """
    dsr_repo = DataSubjectRequestRepository(db)
    audit_repo = AuditLogRepository(db)

    # Get the request
    dsr = await dsr_repo.get_by_id(request_id)
    if not dsr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )

    # Process based on type
    if dsr.request_type == "erasure" and response_data.get("approved"):
        await audit_repo.execute_erasure_with_blocking(dsr.requester_id)

    # Complete the request
    dsr = await dsr_repo.complete_request(
        request_id=request_id,
        response_type=response_data.get("response_type", "fulfilled"),
        response_details=response_data.get("response_details"),
        denial_reason=response_data.get("denial_reason"),
    )

    # Log processing
    await audit_repo.log_action(
        action="UPDATE",
        entity_type="data_subject_requests",
        user_id=current_user_id,
        entity_id=request_id,
        details=response_data,
    )

    await db.commit()

    return RightRequestResponse(
        id=dsr.id,
        request_type=dsr.request_type,
        status=dsr.status,
        received_at=dsr.received_at,
        response_due_date=dsr.response_due_date,
        responded_at=dsr.responded_at,
        response_details=dsr.response_details,
    )


@router.get(
    "/admin/blocked-data",
    response_model=list[BlockedDataResponse],
    summary="Get blocked data (DPO)",
    description="Get list of blocked data records. Requires DPO role.",
    dependencies=[Depends(require_dpo)],
)
async def get_blocked_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[BlockedDataResponse]:
    """
    Get blocked data records.

    LOPDGDD Art. 33: Blocked data list for compliance tracking.
    """
    blocked_repo = BlockedDataRepository(db)
    blocked = await blocked_repo.get_all(skip=skip, limit=limit)

    return [
        BlockedDataResponse(
            id=b.id,
            original_table=b.original_table,
            block_reason=b.block_reason,
            blocked_at=b.blocked_at,
            unblock_date=b.unblock_date,
            accessible_by=b.accessible_by,
        )
        for b in blocked
    ]


# === COMPLIANCE REPORT ENDPOINTS ===


@router.get(
    "/compliance/report/pdf",
    summary="Download compliance report PDF",
    description="Generate and download GDPR/AI Act compliance report for AEPD submission.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF compliance report",
        }
    },
)
async def download_compliance_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    days: int = Query(30, ge=7, le=365, description="Report period in days"),
) -> Response:
    """
    Generate GDPR/AI Act compliance report in PDF format.

    This report is designed for AEPD (Agencia Espanola de Proteccion de Datos)
    submissions and includes:

    - RGPD Art. 7: Consent management status
    - RGPD Art. 15-22: ARCO rights requests summary
    - RGPD Art. 30: Audit log integrity verification
    - RGPD Art. 33-34: Security breach notifications
    - AI Act Art. 12: AI decision traceability
    - LOPDGDD Art. 33: Blocked data inventory

    The report includes a SHA-256 hash for integrity verification.
    """
    service = ComplianceReportService(db)

    period_end = datetime.now(UTC)
    period_start = period_end - timedelta(days=days)

    pdf_bytes, report_id = await service.generate_compliance_report(
        organization_id="default",
        period_start=period_start,
        period_end=period_end,
        generated_by=str(current_user_id),
        user_role="Usuario",
    )

    filename = f"informe_cumplimiento_aepd_{period_end.strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Report-ID": report_id,
        },
    )
