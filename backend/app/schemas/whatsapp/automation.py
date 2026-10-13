"""Automation schemas: macros, SLA, webhooks, surveys, flows, integrations, widget."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# --- Macros ---


class WAMacroResponse(BaseModel):
    """Macro response."""

    id: UUID
    name: str
    shortcut: str | None = None
    text: str
    category: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WAMacroCreateRequest(BaseModel):
    """Create a macro."""

    name: str = Field(..., min_length=1, max_length=100)
    shortcut: str | None = Field(None, max_length=50)
    text: str = Field(..., min_length=1)
    category: str = "general"


class WAMacroUpdateRequest(BaseModel):
    """Update a macro."""

    name: str | None = Field(None, max_length=100)
    shortcut: str | None = Field(None, max_length=50)
    text: str | None = None
    category: str | None = None
    sort_order: int | None = None


# --- SLA ---


class WASlaPolicyResponse(BaseModel):
    """SLA policy response."""

    id: UUID
    name: str
    first_response_minutes: int
    resolution_minutes: int
    priority: str
    is_active: bool
    escalation_email: str | None = None
    business_hours_only: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WASlaPolicyCreateRequest(BaseModel):
    """Create SLA policy."""

    name: str = Field(..., min_length=1, max_length=100)
    first_response_minutes: int = Field(5, gt=0)
    resolution_minutes: int = Field(60, gt=0)
    priority: str = "normal"
    escalation_email: str | None = None
    business_hours_only: bool = True


class WASlaPolicyUpdateRequest(BaseModel):
    """Update SLA policy."""

    name: str | None = Field(None, max_length=100)
    first_response_minutes: int | None = Field(None, gt=0)
    resolution_minutes: int | None = Field(None, gt=0)
    is_active: bool | None = None
    escalation_email: str | None = None


class WASlaBreachResponse(BaseModel):
    """SLA breach record."""

    id: UUID
    conversation_id: UUID
    policy_id: UUID
    breach_type: str
    breached_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Webhooks ---


class WAWebhookConfigResponse(BaseModel):
    """Webhook config response."""

    id: UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    headers: dict | None = None
    last_triggered_at: datetime | None = None
    failure_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WAWebhookConfigCreateRequest(BaseModel):
    """Create webhook."""

    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1)
    events: list[str] = Field(..., min_length=1)
    secret: str | None = None
    headers: dict | None = None


class WAWebhookConfigUpdateRequest(BaseModel):
    """Update webhook."""

    name: str | None = Field(None, max_length=100)
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None
    secret: str | None = None
    headers: dict | None = None


class WAWebhookLogResponse(BaseModel):
    """Webhook delivery log."""

    id: UUID
    webhook_id: UUID
    event_type: str
    response_code: int | None = None
    success: bool
    sent_at: datetime

    model_config = {"from_attributes": True}


# --- Surveys ---


class WASurveyResponse(BaseModel):
    """Survey definition response."""

    id: UUID
    name: str
    survey_type: str
    questions: dict
    trigger: str
    is_active: bool
    response_count: int
    avg_score: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WASurveyCreateRequest(BaseModel):
    """Create survey."""

    name: str = Field(..., min_length=1, max_length=100)
    survey_type: str = "csat"
    questions: dict = Field(default_factory=lambda: {"items": []})
    trigger: str = "conversation_closed"


class WASurveyUpdateRequest(BaseModel):
    """Update survey."""

    name: str | None = Field(None, max_length=100)
    questions: dict | None = None
    trigger: str | None = None
    is_active: bool | None = None


class WASurveyAnswerResponse(BaseModel):
    """Survey response entry."""

    id: UUID
    survey_id: UUID
    contact_id: UUID | None = None
    answers: dict
    score: int | None = None
    feedback: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Flows ---


class WAFlowResponse(BaseModel):
    """Flow automation response."""

    id: UUID
    name: str
    description: str | None = None
    trigger_type: str
    trigger_config: dict | None = None
    steps: dict
    is_active: bool
    last_triggered_at: datetime | None = None
    execution_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WAFlowCreateRequest(BaseModel):
    """Create a flow."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    trigger_type: str = "message_received"
    trigger_config: dict | None = None
    steps: dict = Field(default_factory=lambda: {"nodes": []})


class WAFlowUpdateRequest(BaseModel):
    """Update a flow."""

    name: str | None = Field(None, max_length=100)
    description: str | None = None
    trigger_type: str | None = None
    trigger_config: dict | None = None
    steps: dict | None = None
    is_active: bool | None = None


# --- Integrations ---


class WAIntegrationResponse(BaseModel):
    """Integration config response."""

    id: UUID
    integration_type: str
    name: str
    config: dict
    is_active: bool
    last_sync_at: datetime | None = None
    status_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WAIntegrationCreateRequest(BaseModel):
    """Create integration."""

    integration_type: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=100)
    config: dict = Field(default_factory=dict)


class WAIntegrationUpdateRequest(BaseModel):
    """Update integration."""

    name: str | None = Field(None, max_length=100)
    config: dict | None = None
    is_active: bool | None = None


# --- Widget ---


class WAWidgetConfigResponse(BaseModel):
    """Widget web config response."""

    id: UUID
    is_active: bool
    primary_color: str
    welcome_message: str
    position: str
    auto_open_seconds: int
    allowed_domains: list[str] | None = None
    avatar_url: str | None = None
    business_name: str | None = None
    offline_message: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WAWidgetConfigUpdateRequest(BaseModel):
    """Update widget config."""

    is_active: bool | None = None
    primary_color: str | None = Field(None, max_length=7)
    welcome_message: str | None = None
    position: str | None = None
    auto_open_seconds: int | None = None
    allowed_domains: list[str] | None = None
    avatar_url: str | None = None
    business_name: str | None = Field(None, max_length=100)
    offline_message: str | None = None
