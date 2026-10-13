"""
Transcription model - Maps to sferaai.sql transcriptions table.
AI-generated transcriptions with compliance tracking.

AI Act Art. 12: Full traceability of AI outputs
AI Act Art. 50.2: Mark content as AI-generated
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.call import Call


class Transcription(Base, TimestampMixin):
    """
    Call transcription segment.

    Compliance:
    - AI Act Art. 12: Traceability (model_version, input/output tracking)
    - AI Act Art. 50.2: is_ai_generated flag
    - RGPD Art. 5.1.c: Minimization (retention policies)
    """

    __tablename__ = "transcriptions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    call_id: Mapped[UUID] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Segment positioning
    segment_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Order of segment in call",
    )
    start_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Start time in milliseconds from call start",
    )
    end_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="End time in milliseconds from call start",
    )

    # Speaker identification
    speaker_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="agent, customer, ivr, unknown",
    )
    speaker_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Agent ID if speaker_type=agent",
    )

    # Transcription content
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Transcribed text content",
    )
    language: Mapped[str | None] = mapped_column(
        String(10),
        default="es",
        comment="ISO 639-1 language code",
    )

    # AI Generation metadata (AI Act Art. 50.2)
    is_ai_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="AI Act Art. 50.2: Mark as AI-generated",
    )
    model_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="AI Act Art. 12: Model version for traceability",
    )
    model_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="whisper, google, azure, etc.",
    )

    # Confidence and quality
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="0.0 to 1.0 confidence",
    )

    # Segment-level sentiment (if analyzed)
    sentiment: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="positive, neutral, negative",
    )
    sentiment_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    # Word-level timestamps (optional, for advanced features)
    word_timestamps: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="[{word, start_ms, end_ms, confidence}, ...]",
    )

    # Review status
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    review_corrections: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sensitive data detection (RGPD Art. 9)
    contains_sensitive_data: Mapped[bool] = mapped_column(Boolean, default=False)
    sensitive_data_categories: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="health, financial, religious, etc.",
    )
    sensitive_data_redacted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    call: Mapped["Call"] = relationship(back_populates="transcriptions")

    __table_args__ = (
        CheckConstraint(
            "speaker_type IN ('agent', 'customer', 'ivr', 'unknown')",
            name="transcriptions_speaker_type_check",
        ),
        CheckConstraint(
            "sentiment IS NULL OR sentiment IN ('positive', 'neutral', 'negative')",
            name="transcriptions_sentiment_check",
        ),
        CheckConstraint(
            "start_time_ms <= end_time_ms",
            name="transcriptions_time_order_check",
        ),
        Index("idx_transcriptions_call", "call_id"),
        Index("idx_transcriptions_call_segment", "call_id", "segment_index"),
        Index("idx_transcriptions_speaker", "speaker_type"),
        Index(
            "idx_transcriptions_sensitive",
            "contains_sensitive_data",
            postgresql_where="contains_sensitive_data = true",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Transcription(id={self.id}, call_id={self.call_id}, segment={self.segment_index})>"
        )
