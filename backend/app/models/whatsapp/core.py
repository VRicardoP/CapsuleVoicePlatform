"""Core WhatsApp models: tenant settings, contacts, conversations, messages, events."""

from datetime import datetime, time
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WATenantSettings(Base, TimestampMixin):
    """WhatsApp configuration per tenant (1:1 with organization)."""

    __tablename__ = "wa_tenant_settings"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, unique=True)
    phone_number_id: Mapped[str] = mapped_column(String(64), nullable=False)
    business_account_id: Mapped[str] = mapped_column(String(64), nullable=False)
    api_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_verify_token: Mapped[str] = mapped_column(String(255), nullable=False)
    app_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    display_phone: Mapped[str | None] = mapped_column(String(20))
    display_name: Mapped[str | None] = mapped_column(String(100))
    quality_rating: Mapped[str] = mapped_column(String(10), default="UNKNOWN")
    messaging_limit: Mapped[str] = mapped_column(String(20), default="TIER_1K")
    retention_days: Mapped[int] = mapped_column(Integer, default=90)
    sla_first_response_sec: Mapped[int] = mapped_column(Integer, default=300)
    business_hours_start: Mapped[time] = mapped_column(Time, default=time(9, 0))
    business_hours_end: Mapped[time] = mapped_column(Time, default=time(18, 0))
    business_hours_tz: Mapped[str] = mapped_column(String(50), default="Europe/Madrid")
    auto_close_hours: Mapped[int] = mapped_column(Integer, default=48)
    auto_assign_config: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        CheckConstraint("retention_days BETWEEN 7 AND 730", name="ck_wa_tenant_retention"),
        CheckConstraint("sla_first_response_sec > 0", name="ck_wa_tenant_sla"),
        CheckConstraint("auto_close_hours BETWEEN 1 AND 720", name="ck_wa_tenant_autoclose"),
        Index("idx_wa_tenant_settings_tenant", "tenant_id"),
    )


class WAContact(Base, TimestampMixin):
    """WhatsApp contact per tenant."""

    __tablename__ = "wa_contacts"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=list)
    opt_in_status: Mapped[str] = mapped_column(String(20), default="unknown")
    opt_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opt_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    source: Mapped[str] = mapped_column(String(50), default="inbound")

    conversations: Mapped[list["WAConversation"]] = relationship(back_populates="contact")

    __table_args__ = (
        CheckConstraint(
            "opt_in_status IN ('opted_in', 'opted_out', 'blocked', 'unknown')",
            name="ck_wa_contact_optin",
        ),
        Index("idx_wa_contacts_tenant", "tenant_id"),
        Index("idx_wa_contacts_phone", "phone_e164"),
        Index("idx_wa_contacts_email", "email"),
        Index("idx_wa_contacts_unique_phone", "tenant_id", "phone_e164", unique=True),
    )


class WAConversation(Base, TimestampMixin):
    """WhatsApp conversation thread."""

    __tablename__ = "wa_conversations"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_contacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    assignee_user_id: Mapped[UUID | None] = mapped_column()
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=list)
    last_message_text: Mapped[str | None] = mapped_column(String(255))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)

    contact: Mapped["WAContact"] = relationship(back_populates="conversations")
    messages: Mapped[list["WAMessage"]] = relationship(back_populates="conversation")

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'assigned', 'snoozed', 'closed', 'expired')",
            name="ck_wa_conv_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_wa_conv_priority",
        ),
        Index("idx_wa_conv_tenant", "tenant_id"),
        Index("idx_wa_conv_tenant_status", "tenant_id", "status"),
        Index("idx_wa_conv_tenant_updated", "tenant_id", "updated_at"),
        Index("idx_wa_conv_contact", "contact_id"),
        Index("idx_wa_conv_assignee", "tenant_id", "assignee_user_id"),
    )


class WAMessage(Base):
    """Individual WhatsApp message."""

    __tablename__ = "wa_messages"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_conversations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    msg_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    provider_message_id: Mapped[str | None] = mapped_column(String(128))
    sender_phone: Mapped[str | None] = mapped_column(String(20))
    text_body: Mapped[str | None] = mapped_column(Text)
    media_url: Mapped[str | None] = mapped_column(Text)
    media_mime_type: Mapped[str | None] = mapped_column(String(50))
    media_sha256: Mapped[str | None] = mapped_column(String(64))
    media_caption: Mapped[str | None] = mapped_column(Text)
    delivery_status: Mapped[str] = mapped_column(String(20), default="pending")
    error_code: Mapped[str | None] = mapped_column(String(20))
    error_detail: Mapped[str | None] = mapped_column(Text)
    is_from_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    conversation: Mapped["WAConversation"] = relationship(back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="ck_wa_msg_direction",
        ),
        CheckConstraint(
            "msg_type IN ('text','template','image','video','audio','document','location','contacts','interactive','reaction','sticker','system')",
            name="ck_wa_msg_type",
        ),
        CheckConstraint(
            "delivery_status IN ('pending','sent','delivered','read','failed')",
            name="ck_wa_msg_status",
        ),
        Index(
            "idx_wa_msg_provider_id",
            "provider_message_id",
            unique=True,
            postgresql_where=text("provider_message_id IS NOT NULL"),
        ),
        Index("idx_wa_msg_conv_created", "conversation_id", "created_at"),
        Index("idx_wa_msg_tenant_created", "tenant_id", "created_at"),
    )


class WAEvent(Base):
    """Raw webhook event log for idempotency and audit."""

    __tablename__ = "wa_events"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID | None] = mapped_column()
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    meta_phone_number_id: Mapped[str | None] = mapped_column(String(64))
    payload_raw: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(20), default="received")
    error_detail: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('message_inbound','message_status','template_status','phone_quality','account_update')",
            name="ck_wa_event_type",
        ),
        CheckConstraint(
            "processing_status IN ('received','processing','processed','failed','skipped_duplicate')",
            name="ck_wa_event_status",
        ),
        Index("idx_wa_events_status", "processing_status"),
        Index("idx_wa_events_tenant_created", "tenant_id", "created_at"),
    )
