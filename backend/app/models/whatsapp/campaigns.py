"""Campaign models: broadcast campaigns and recipients."""

from datetime import datetime
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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WACampaign(Base, TimestampMixin):
    """WhatsApp broadcast campaign."""

    __tablename__ = "wa_campaigns"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_templates.id", ondelete="SET NULL"),
    )
    audience_filter: Mapped[dict | None] = mapped_column(JSONB)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_ab_test: Mapped[bool] = mapped_column(Boolean, default=False)
    ab_parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_campaigns.id", ondelete="SET NULL"),
    )
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0)
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[UUID | None] = mapped_column()
    ab_auto_select: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    ab_auto_select_hours: Mapped[int | None] = mapped_column(Integer, default=24, nullable=True)
    ab_winner_variant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_campaigns.id", ondelete="SET NULL"),
    )
    ab_winner_metric: Mapped[str | None] = mapped_column(
        String(20), default="read_rate", nullable=True
    )
    catalog_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_catalog_items.id", ondelete="SET NULL"),
    )

    template: Mapped["WATemplate"] = relationship(foreign_keys=[template_id])  # noqa: F821
    catalog_item: Mapped["WACatalogItem"] = relationship()  # noqa: F821
    recipients: Mapped[list["WACampaignRecipient"]] = relationship(back_populates="campaign")

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'scheduled', 'sending', 'paused', 'completed', 'cancelled')",
            name="ck_wa_campaign_status",
        ),
        Index("idx_wa_campaigns_tenant", "tenant_id"),
        Index("idx_wa_campaigns_tenant_status", "tenant_id", "status"),
    )


class WACampaignRecipient(Base):
    """Individual recipient within a campaign."""

    __tablename__ = "wa_campaign_recipients"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_detail: Mapped[str | None] = mapped_column(Text)

    campaign: Mapped["WACampaign"] = relationship(back_populates="recipients")
    contact: Mapped["WAContact"] = relationship()  # noqa: F821

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'read', 'failed')",
            name="ck_wa_camp_recip_status",
        ),
        UniqueConstraint("campaign_id", "contact_id", name="uq_wa_camp_recip"),
        Index("idx_wa_camp_recip_campaign", "campaign_id"),
        Index("idx_wa_camp_recip_contact", "contact_id"),
    )
