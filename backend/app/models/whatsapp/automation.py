"""Automation models: macros, SLA, webhooks, surveys, flows, integrations, widget."""

from datetime import datetime
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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WAMacro(Base, TimestampMixin):
    """Quick reply / canned response macro for agents."""

    __tablename__ = "wa_macros"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    shortcut: Mapped[str | None] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    actions: Mapped[list | None] = mapped_column(JSONB)
    created_by: Mapped[UUID | None] = mapped_column()

    __table_args__ = (
        UniqueConstraint("tenant_id", "shortcut", name="uq_wa_macro_shortcut"),
        Index("idx_wa_macros_tenant", "tenant_id"),
    )


class WASlaPolicy(Base, TimestampMixin):
    """Service Level Agreement policy."""

    __tablename__ = "wa_sla_policies"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_response_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    resolution_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    escalation_email: Mapped[str | None] = mapped_column(String(255))
    business_hours_only: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_wa_sla_priority",
        ),
        Index("idx_wa_sla_tenant", "tenant_id"),
    )


class WASlaBreach(Base):
    """Record of an SLA breach event."""

    __tablename__ = "wa_sla_breaches"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_sla_policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    breach_type: Mapped[str] = mapped_column(String(30), nullable=False)
    breached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "breach_type IN ('first_response', 'resolution')",
            name="ck_wa_sla_breach_type",
        ),
        Index("idx_wa_sla_breach_tenant", "tenant_id"),
        Index("idx_wa_sla_breach_conv", "conversation_id"),
    )


class WAWebhookConfig(Base, TimestampMixin):
    """Outgoing webhook configuration."""

    __tablename__ = "wa_webhook_configs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    events: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    headers: Mapped[dict | None] = mapped_column(JSONB)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("idx_wa_webhooks_tenant", "tenant_id"),)


class WAWebhookLog(Base):
    """Delivery log for outgoing webhooks."""

    __tablename__ = "wa_webhook_logs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    webhook_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_webhook_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response_code: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    __table_args__ = (
        Index("idx_wa_whlog_webhook", "webhook_id"),
        Index("idx_wa_whlog_sent", "sent_at"),
    )


class WASurvey(Base, TimestampMixin):
    """Customer satisfaction survey definition."""

    __tablename__ = "wa_surveys"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    survey_type: Mapped[str] = mapped_column(String(20), nullable=False, default="csat")
    questions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    trigger: Mapped[str] = mapped_column(String(30), default="conversation_closed")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    response_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_score: Mapped[float | None] = mapped_column(Numeric(3, 1))

    responses: Mapped[list["WASurveyResponse"]] = relationship(back_populates="survey")

    __table_args__ = (
        CheckConstraint(
            "survey_type IN ('csat', 'nps', 'custom')",
            name="ck_wa_survey_type",
        ),
        CheckConstraint(
            "trigger IN ('conversation_closed', 'manual', 'after_purchase', 'scheduled')",
            name="ck_wa_survey_trigger",
        ),
        Index("idx_wa_surveys_tenant", "tenant_id"),
    )


class WASurveyResponse(Base):
    """Individual survey response."""

    __tablename__ = "wa_survey_responses"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    survey_id: Mapped[UUID] = mapped_column(
        ForeignKey("wa_surveys.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_contacts.id", ondelete="SET NULL"),
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wa_conversations.id", ondelete="SET NULL"),
    )
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    survey: Mapped["WASurvey"] = relationship(back_populates="responses")

    __table_args__ = (
        Index("idx_wa_survey_resp_survey", "survey_id"),
        Index("idx_wa_survey_resp_contact", "contact_id"),
    )


class WAFlow(Base, TimestampMixin):
    """Automation flow definition (simplified flow builder)."""

    __tablename__ = "wa_flows"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    trigger_config: Mapped[dict | None] = mapped_column(JSONB)
    steps: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('message_received', 'keyword', 'conversation_opened', 'conversation_closed', 'contact_created', 'tag_added', 'manual')",
            name="ck_wa_flow_trigger",
        ),
        Index("idx_wa_flows_tenant", "tenant_id"),
        Index("idx_wa_flows_active", "tenant_id", "is_active"),
    )


class WAIntegration(Base, TimestampMixin):
    """Third-party integration configuration."""

    __tablename__ = "wa_integrations"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    integration_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_message: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        CheckConstraint(
            "integration_type IN ('crm', 'helpdesk', 'ecommerce', 'email', 'calendar', 'custom_api')",
            name="ck_wa_integ_type",
        ),
        Index("idx_wa_integrations_tenant", "tenant_id"),
    )


class WAWidgetConfig(Base, TimestampMixin):
    """Web chat widget configuration per tenant."""

    __tablename__ = "wa_widget_configs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_color: Mapped[str] = mapped_column(String(7), default="#25D366")
    welcome_message: Mapped[str] = mapped_column(Text, default="¡Hola! ¿En qué podemos ayudarte?")
    position: Mapped[str] = mapped_column(String(20), default="bottom-right")
    auto_open_seconds: Mapped[int] = mapped_column(Integer, default=0)
    allowed_domains: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    business_name: Mapped[str | None] = mapped_column(String(100))
    offline_message: Mapped[str] = mapped_column(
        Text, default="Estamos fuera de horario. Te responderemos pronto."
    )

    __table_args__ = (
        CheckConstraint(
            "position IN ('bottom-right', 'bottom-left')",
            name="ck_wa_widget_position",
        ),
        Index("idx_wa_widget_tenant", "tenant_id"),
    )
