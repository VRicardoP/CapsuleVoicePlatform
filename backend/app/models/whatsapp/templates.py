"""WhatsApp message template model."""

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WATemplate(Base, TimestampMixin):
    """WhatsApp message template (synced with Meta)."""

    __tablename__ = "wa_templates"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="es")
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="MARKETING")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    header_type: Mapped[str | None] = mapped_column(String(20))
    header_content: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    footer: Mapped[str | None] = mapped_column(String(60))
    buttons: Mapped[dict | None] = mapped_column(JSONB)
    variables: Mapped[dict | None] = mapped_column(JSONB)
    meta_template_id: Mapped[str | None] = mapped_column(String(128))
    meta_rejected_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "category IN ('MARKETING', 'UTILITY', 'AUTHENTICATION')",
            name="ck_wa_tpl_category",
        ),
        CheckConstraint(
            "status IN ('draft', 'pending', 'approved', 'rejected', 'paused', 'disabled')",
            name="ck_wa_tpl_status",
        ),
        Index("idx_wa_templates_tenant", "tenant_id"),
        Index("idx_wa_templates_tenant_status", "tenant_id", "status"),
        UniqueConstraint("tenant_id", "name", "language", name="uq_wa_template_name_lang"),
    )
