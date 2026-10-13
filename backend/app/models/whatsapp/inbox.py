"""Inbox enhancement models: segments, tags, internal notes."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WASegment(Base, TimestampMixin):
    """Configurable segment per tenant (e.g. 'Pendiente', 'Cliente potencial')."""

    __tablename__ = "wa_segments"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#6B7280")
    icon: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    filter_criteria: Mapped[dict | None] = mapped_column(JSONB)
    contact_count: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    contacts: Mapped[list["WAContactSegment"]] = relationship(
        back_populates="segment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_wa_segment_tenant_slug"),
        Index("idx_wa_segments_tenant", "tenant_id"),
        Index("idx_wa_segments_tenant_order", "tenant_id", "sort_order"),
    )


class WAContactSegment(Base):
    """M2M: contact ↔ segment assignment."""

    __tablename__ = "wa_contact_segments"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_segments.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_by: Mapped[UUID | None] = mapped_column()
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    contact: Mapped["WAContact"] = relationship()  # noqa: F821
    segment: Mapped["WASegment"] = relationship(back_populates="contacts")

    __table_args__ = (
        UniqueConstraint("contact_id", "segment_id", name="uq_wa_contact_segment"),
        Index("idx_wa_cseg_contact", "contact_id"),
        Index("idx_wa_cseg_segment", "segment_id"),
        Index("idx_wa_cseg_tenant", "tenant_id"),
    )


class WAInternalNote(Base):
    """Internal note on a conversation (visible only to agents)."""

    __tablename__ = "wa_internal_notes"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_user_id: Mapped[UUID] = mapped_column(nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    conversation: Mapped["WAConversation"] = relationship()  # noqa: F821

    __table_args__ = (
        Index("idx_wa_notes_conv", "conversation_id"),
        Index("idx_wa_notes_conv_created", "conversation_id", "created_at"),
        Index("idx_wa_notes_tenant", "tenant_id"),
    )


class WATag(Base, TimestampMixin):
    """Colored tag per tenant for contact categorization."""

    __tablename__ = "wa_tags"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#3B82F6")

    contacts: Mapped[list["WAContactTag"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_wa_tag_tenant_name"),
        Index("idx_wa_tags_tenant", "tenant_id"),
    )


class WAContactTag(Base):
    """M2M: contact ↔ tag."""

    __tablename__ = "wa_contact_tags"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_tags.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    contact: Mapped["WAContact"] = relationship()  # noqa: F821
    tag: Mapped["WATag"] = relationship(back_populates="contacts")

    __table_args__ = (
        UniqueConstraint("contact_id", "tag_id", name="uq_wa_contact_tag"),
        Index("idx_wa_ctag_contact", "contact_id"),
        Index("idx_wa_ctag_tag", "tag_id"),
    )
