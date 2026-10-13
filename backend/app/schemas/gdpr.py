"""Schemas for GDPR Rights endpoints.

Pydantic models for RGPD Art. 15-22 (ARSOPL rights).

Compliance:
- Art. 15: Access / Portability
- Art. 16: Rectification
- Art. 17: Erasure
- Art. 18: Restriction
- Art. 21: Objection
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GDPRExportResponse(BaseModel):
    """GDPR data export response (Art. 15, 20)."""

    user_id: UUID
    export_format: str
    data: dict[str, Any]
    generated_at: datetime
    download_url: str | None = None
    expires_at: datetime | None = None


class RightRequestCreate(BaseModel):
    """Create a GDPR rights request."""

    request_type: str = Field(
        ...,
        pattern="^(access|rectification|erasure|restriction|portability|objection)$",
    )
    details: str | None = Field(None, max_length=2000)


class RightRequestResponse(BaseModel):
    """GDPR rights request response."""

    id: UUID
    request_type: str
    status: str
    received_at: datetime
    response_due_date: datetime
    responded_at: datetime | None = None
    response_details: str | None = None


class RectificationRequest(BaseModel):
    """Data rectification request (Art. 16)."""

    field: str = Field(..., description="Field to rectify")
    new_value: str = Field(..., description="New value")
    reason: str | None = Field(None, description="Reason for rectification")


class ErasureRequest(BaseModel):
    """Data erasure request (Art. 17)."""

    reason: str = Field(..., description="Reason for erasure")
    confirm: bool = Field(..., description="Confirm erasure request")


class RestrictionRequest(BaseModel):
    """Processing restriction request (Art. 18)."""

    reason: str = Field(..., description="Reason for restriction")
    scope: str | None = Field(None, description="Scope of restriction")


class ObjectionRequest(BaseModel):
    """Processing objection request (Art. 21)."""

    processing_type: str = Field(..., description="Type of processing to object")
    reason: str = Field(..., description="Grounds for objection")


class BlockedDataResponse(BaseModel):
    """Blocked data info (LOPDGDD Art. 33)."""

    id: UUID
    original_table: str
    block_reason: str
    blocked_at: datetime
    unblock_date: datetime | None = None
    accessible_by: str


class PendingRequestsResponse(BaseModel):
    """List of pending GDPR requests."""

    items: list[RightRequestResponse]
    total: int
    overdue_count: int
