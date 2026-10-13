"""
Robinson List models - LOPDGDD Art. 34 / Orden ETD/1286/2022.
Tracking of Robinson list checks for marketing campaigns.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class RobinsonCheck(Base, TimestampMixin):
    """
    Robinson list check record.

    Orden ETD/1286/2022:
    - Art. 4.1: MUST check before commercial communications
    - Art. 4.2: Check valid for MAX 30 days
    - Art. 4.3: MUST exclude listed contacts
    - Art. 6: MUST document all checks
    """

    __tablename__ = "robinson_checks"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # Contact being checked
    contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Phone number checked (may not have contact record)
    phone_number_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of phone number checked",
    )

    # Check details
    check_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="phone, email, postal",
    )
    check_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Result
    is_listed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="True if number is on Robinson list",
    )
    result_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="API response code",
    )

    # Validity (Orden ETD/1286/2022 Art. 4.2 - max 30 days)
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="check_timestamp + 30 days",
    )

    # Campaign context
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    purpose: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Marketing purpose for the check",
    )

    # Who initiated the check
    checked_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    checked_by_system: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="ai_agent, pbx, crm, manual",
    )

    # API details (for audit)
    api_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    api_response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "check_type IN ('phone', 'email', 'postal')",
            name="robinson_check_type_check",
        ),
        Index("idx_robinson_contact", "contact_id"),
        Index("idx_robinson_phone_hash", "phone_number_hash"),
        Index(
            "idx_robinson_valid",
            "phone_number_hash",
            "valid_until",
            postgresql_where="is_listed = false",
        ),
        Index("idx_robinson_campaign", "campaign_id"),
        Index("idx_robinson_timestamp", "check_timestamp"),
    )


class Campaign(Base, TimestampMixin):
    """
    Marketing campaign tracking.
    """

    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # Campaign details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="outbound_calls, email, sms, mixed",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="draft",
        comment="draft, scheduled, active, paused, completed, cancelled",
    )

    # Schedule
    start_date: Mapped[datetime | None] = mapped_column(nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # Robinson compliance
    robinson_check_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Should always be true for commercial campaigns",
    )
    robinson_last_batch_check: Mapped[datetime | None] = mapped_column(nullable=True)

    # Statistics
    total_contacts: Mapped[int] = mapped_column(Integer, default=0)
    robinson_excluded: Mapped[int] = mapped_column(Integer, default=0)
    calls_made: Mapped[int] = mapped_column(Integer, default=0)
    calls_connected: Mapped[int] = mapped_column(Integer, default=0)

    # Organization
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'scheduled', 'active', 'paused', 'completed', 'cancelled')",
            name="campaigns_status_check",
        ),
        Index("idx_campaigns_status", "status"),
        Index("idx_campaigns_organization", "organization_id"),
        Index("idx_campaigns_dates", "start_date", "end_date"),
    )
