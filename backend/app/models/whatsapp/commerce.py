"""Commerce models: pipeline, deals, catalog, orders."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WAPipelineStage(Base, TimestampMixin):
    """Pipeline stage for deal management."""

    __tablename__ = "wa_pipeline_stages"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#6B7280")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False)

    deals: Mapped[list["WADeal"]] = relationship(back_populates="stage")

    __table_args__ = (
        Index("idx_wa_pipeline_tenant", "tenant_id"),
        Index("idx_wa_pipeline_tenant_order", "tenant_id", "sort_order"),
    )


class WADeal(Base, TimestampMixin):
    """Sales deal tracked in the pipeline."""

    __tablename__ = "wa_deals"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_contacts.id", ondelete="SET NULL"),
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_conversations.id", ondelete="SET NULL"),
    )
    stage_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_pipeline_stages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    assignee_user_id: Mapped[UUID | None] = mapped_column()
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    stage: Mapped["WAPipelineStage"] = relationship(back_populates="deals")
    contact: Mapped["WAContact | None"] = relationship()  # noqa: F821
    conversation: Mapped["WAConversation | None"] = relationship()  # noqa: F821

    __table_args__ = (
        Index("idx_wa_deals_tenant", "tenant_id"),
        Index("idx_wa_deals_stage", "stage_id"),
        Index("idx_wa_deals_contact", "contact_id"),
    )


class WACatalogItem(Base, TimestampMixin):
    """Product in the WhatsApp catalog."""

    __tablename__ = "wa_catalog_items"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    image_url: Mapped[str | None] = mapped_column(Text)
    product_url: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    sku: Mapped[str | None] = mapped_column(String(100))
    stock: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="active")
    meta_retailer_id: Mapped[str | None] = mapped_column(String(128))

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'out_of_stock')",
            name="ck_wa_catalog_status",
        ),
        Index("idx_wa_catalog_tenant", "tenant_id"),
        Index("idx_wa_catalog_tenant_status", "tenant_id", "status"),
    )


class WAOrder(Base, TimestampMixin):
    """Order placed through WhatsApp."""

    __tablename__ = "wa_orders"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_contacts.id", ondelete="SET NULL"),
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_conversations.id", ondelete="SET NULL"),
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    notes: Mapped[str | None] = mapped_column(Text)

    contact: Mapped["WAContact | None"] = relationship()  # noqa: F821
    items: Mapped[list["WAOrderItem"]] = relationship(back_populates="order")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')",
            name="ck_wa_order_status",
        ),
        Index("idx_wa_orders_tenant", "tenant_id"),
        Index("idx_wa_orders_tenant_status", "tenant_id", "status"),
        Index("idx_wa_orders_contact", "contact_id"),
    )


class WAOrderItem(Base):
    """Line item within an order."""

    __tablename__ = "wa_order_items"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    catalog_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_catalog_items.id", ondelete="SET NULL"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["WAOrder"] = relationship(back_populates="items")
    catalog_item: Mapped["WACatalogItem | None"] = relationship()

    __table_args__ = (Index("idx_wa_oitems_order", "order_id"),)
