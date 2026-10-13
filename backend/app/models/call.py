"""
Call model - Maps to sferaai.sql calls table.
Core entity for call center operations.

Compliance:
- AI Act Art. 50: ai_disclosure_timestamp required
- AI Act Art. 50.3: emotion_detection_disclosed for sentiment
- RGPD Art. 7: recording_consent tracking
- LGT Art. 68: Separate traffic data retention
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.ai_decision import AIDecisionLog
    from app.models.contact import Contact
    from app.models.transcription import Transcription
    from app.models.user import User


class Call(Base, TimestampMixin, SoftDeleteMixin):
    """
    Call session entity.

    Compliance:
    - AI Act Art. 50.1: ai_disclosure_timestamp BEFORE conversation
    - AI Act Art. 50.3: emotion_detection_disclosed if sentiment analysis
    - AI Act Art. 14: human_oversight_required for automated decisions
    - RGPD Art. 7: Consent tracking for recording
    - RGPD Art. 22: human_override for automated decisions
    - LGT Art. 68.3: Traffic data retained separately (12 months)
    """

    __tablename__ = "calls"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # External reference (PBX call ID)
    external_call_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    # Direction and type
    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="inbound, outbound, internal",
    )
    call_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="support, sales, collection, survey, etc.",
    )
    purpose: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="commercial, service, informational",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="initiated",
        comment="initiated, ringing, answered, on_hold, transferred, completed, abandoned, failed",
    )

    # Timing
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    answered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Queue/routing
    queue_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    queue_wait_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Participants
    contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Phone numbers (may need to be matched with contact)
    caller_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    called_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # === AI ACT COMPLIANCE (Art. 50) ===
    ai_disclosure_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="AI Act Art. 50.1: MUST be set BEFORE conversation starts",
    )
    ai_disclosure_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="ivr_message, agent_verbal, automated",
    )
    emotion_detection_disclosed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="AI Act Art. 50.3: Must be true if sentiment analysis used",
    )

    # === RECORDING AND CONSENT (RGPD Art. 7) ===
    is_recorded: Mapped[bool] = mapped_column(Boolean, default=False)
    recording_consent: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Explicit consent for recording",
    )
    recording_consent_timestamp: Mapped[datetime | None] = mapped_column(nullable=True)
    recording_informed_timestamp: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="AEPD: Must be BEFORE call_start",
    )
    recording_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === SENTIMENT ANALYSIS (AI Act Art. 50.3) ===
    sentiment: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="positive, neutral, negative",
    )
    sentiment_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="-1.0 to 1.0",
    )
    sentiment_consent: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Consent for emotion detection",
    )

    # === HUMAN OVERSIGHT (AI Act Art. 14) ===
    human_oversight_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="AI Act Art. 14: Requires human review",
    )
    human_override: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human decision overriding AI",
    )
    human_reviewer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # === EMPLOYEE CALL TRACKING (AI Act Art. 5.1.f) ===
    is_employee_call: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="AI Act Art. 5.1.f: PROHIBITED emotion detection on employees",
    )

    # === AGE VERIFICATION (LOPDGDD Art. 7) ===
    age_verification_asked: Mapped[bool] = mapped_column(Boolean, default=False)
    age_verification_response: Mapped[str | None] = mapped_column(String(50), nullable=True)
    age_verification_timestamp: Mapped[datetime | None] = mapped_column(nullable=True)

    # AI summary
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Quality metrics
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    csat_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nps_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Disposition
    disposition_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    disposition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Transfer tracking
    transferred_from_call_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    transfer_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Campaign tracking
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Client info (for PBX integration)
    client_ip: Mapped[str | None] = mapped_column(INET, nullable=True)

    # Extra data
    extra_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Relationships
    contact: Mapped["Contact"] = relationship(back_populates="calls")
    agent: Mapped["User"] = relationship(foreign_keys=[agent_id])
    human_reviewer: Mapped["User"] = relationship(foreign_keys=[human_reviewer_id])
    transcriptions: Mapped[list["Transcription"]] = relationship(back_populates="call")
    ai_decisions: Mapped[list["AIDecisionLog"]] = relationship(back_populates="call")
    transferred_from: Mapped["Call"] = relationship(
        remote_side=[id],
        foreign_keys=[transferred_from_call_id],
    )

    __table_args__ = (
        # Status constraint
        CheckConstraint(
            "status IN ('initiated', 'ringing', 'answered', 'on_hold', "
            "'transferred', 'completed', 'abandoned', 'failed')",
            name="calls_status_check",
        ),
        # Direction constraint
        CheckConstraint(
            "direction IN ('inbound', 'outbound', 'internal')",
            name="calls_direction_check",
        ),
        # Sentiment constraint
        CheckConstraint(
            "sentiment IS NULL OR sentiment IN ('positive', 'neutral', 'negative')",
            name="calls_sentiment_check",
        ),
        # Indexes
        Index("idx_calls_contact", "contact_id"),
        Index("idx_calls_agent", "agent_id"),
        Index("idx_calls_status", "status"),
        Index("idx_calls_initiated", "initiated_at"),
        Index("idx_calls_direction_status", "direction", "status"),
        Index("idx_calls_campaign", "campaign_id"),
        Index("idx_calls_external", "external_call_id"),
    )

    def __repr__(self) -> str:
        return f"<Call(id={self.id}, status={self.status}, direction={self.direction})>"


class CallTrafficData(Base):
    """
    Traffic data for LGT Art. 68 / Ley 25/2007 compliance.
    MUST be retained for exactly 12 months, then destroyed.

    Separate from call_recordings (content) which follows RGPD.
    """

    __tablename__ = "call_traffic_data"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    call_id: Mapped[UUID] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Traffic data (LGT Art. 68.2, Ley 25/2007 Art. 3)
    caller_cli: Mapped[str | None] = mapped_column(String(50), nullable=True)
    called_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    call_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    call_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    equipment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Retention control (LGT Art. 68.3)
    legal_hold_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="call_start + 12 months - MANDATORY retention",
    )
    deletion_blocked_reason: Mapped[str | None] = mapped_column(
        String(100),
        default="LGT Art. 68 / Ley 25/2007 Art. 5",
    )
    scheduled_destruction_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )

    __table_args__ = (
        Index("idx_traffic_call", "call_id"),
        Index("idx_traffic_legal_hold", "legal_hold_until"),
        Index("idx_traffic_destruction", "scheduled_destruction_date"),
    )
