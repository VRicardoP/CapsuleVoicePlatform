"""
AI Decision Log model - Maps to capsulecorp.sql ai_decision_logs table.
Critical for AI Act compliance (Art. 12 - Traceability).

Every AI decision MUST be logged with full context.
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.call import Call
    from app.models.user import User


class AIDecisionLog(Base):
    """
    AI Decision audit log.

    AI Act Art. 12: ALL automated decisions must be logged with:
    - Input data reference
    - Output/decision made
    - Model version
    - Confidence score
    - Human oversight status

    AI Act Art. 14: Track human oversight and overrides
    AI Act Art. 50.3: Track emotion detection disclosure
    """

    __tablename__ = "ai_decision_logs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # Timestamps
    decision_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Context
    session_id: Mapped[UUID | None] = mapped_column(nullable=True)
    call_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Model information (AI Act Art. 12)
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Model identifier",
    )
    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Model version for reproducibility",
    )
    model_provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="openai, anthropic, ultravox, etc.",
    )

    # Input (AI Act Art. 12.2)
    input_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="audio, text, structured_data, etc.",
    )
    input_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Reference to input data (e.g., transcription segment ID)",
    )
    input_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of input for integrity verification",
    )

    # Output (AI Act Art. 12.1)
    output_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="classification, recommendation, generation, etc.",
    )
    output_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Summary of output (no PII)",
    )
    output_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="0.0 to 1.0",
    )

    # Risk assessment (AI Act Art. 9)
    ai_risk_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="minimal, limited, high, unacceptable",
    )
    decision_category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="service, sales, compliance, quality",
    )

    # Human oversight (AI Act Art. 14)
    human_oversight_required: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        comment="AI Act Art. 14: Requires human review",
    )
    human_override_occurred: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
    )
    human_reviewer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    human_review_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    human_review_decision: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human decision overriding AI",
    )

    # Transparency (AI Act Art. 50)
    user_informed: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
    )
    emotion_detection_used: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
    )
    emotion_detection_disclosed: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        comment="AI Act Art. 50.3: Was user informed about emotion detection?",
    )

    # Performance
    processing_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Time taken for AI processing",
    )

    # Error tracking
    error_occurred: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata (Python attr 'extra_metadata' maps to SQL column 'metadata')
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        server_default=text("'{}'"),
    )

    # Retention (AI Act minimum 180 days)
    retention_period: Mapped[int | None] = mapped_column(
        Integer,
        server_default=text("180"),
    )

    # Audit timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    call: Mapped["Call"] = relationship(back_populates="ai_decisions")
    human_reviewer: Mapped["User"] = relationship(foreign_keys=[human_reviewer_id])

    __table_args__ = (
        CheckConstraint(
            "output_confidence IS NULL OR (output_confidence BETWEEN 0 AND 1)",
            name="ai_decisions_confidence_check",
        ),
        CheckConstraint(
            "ai_risk_level IS NULL OR ai_risk_level IN "
            "('minimal', 'limited', 'high', 'unacceptable')",
            name="ai_decisions_risk_check",
        ),
        CheckConstraint(
            "retention_period IS NULL OR retention_period >= 180",
            name="ai_decisions_retention_check",
        ),
        Index("idx_ai_decisions_timestamp", "decision_timestamp"),
        Index("idx_ai_decisions_call", "call_id", postgresql_where="call_id IS NOT NULL"),
        Index("idx_ai_decisions_model", "model_name", "model_version"),
        Index(
            "idx_ai_decisions_risk",
            "ai_risk_level",
            postgresql_where="ai_risk_level IN ('high', 'unacceptable')",
        ),
        Index(
            "idx_ai_decisions_human_override",
            "human_override_occurred",
            postgresql_where="human_override_occurred = true",
        ),
        Index("idx_ai_decisions_category", "decision_category", "decision_timestamp"),
        Index(
            "idx_ai_decisions_emotion",
            "emotion_detection_used",
            postgresql_where="emotion_detection_used = true",
        ),
    )

    def __repr__(self) -> str:
        return f"<AIDecisionLog(id={self.id}, model={self.model_name}, call_id={self.call_id})>"
