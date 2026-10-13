"""Core schemas: conversations, messages, basic requests."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WAContactSummary(BaseModel):
    """Contact summary embedded in conversation responses."""

    id: UUID
    phone_e164: str
    display_name: str | None = None

    model_config = {"from_attributes": True}


class WATagSummary(BaseModel):
    """Minimal tag info for embedding in conversation responses."""

    id: UUID
    name: str
    color: str

    model_config = {"from_attributes": True}


class WASegmentSummary(BaseModel):
    """Minimal segment info for embedding in conversation responses."""

    id: UUID
    name: str
    color: str

    model_config = {"from_attributes": True}


class WAConversationResponse(BaseModel):
    """Single conversation in list/detail responses."""

    id: UUID
    status: str
    priority: str
    assignee_user_id: UUID | None = None
    last_message_text: str | None = None
    last_message_at: datetime | None = None
    last_inbound_at: datetime | None = None
    last_outbound_at: datetime | None = None
    window_expires_at: datetime | None = None
    unread_count: int = 0
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    contact: WAContactSummary
    contact_tags: list[WATagSummary] = []
    contact_segments: list[WASegmentSummary] = []

    model_config = {"from_attributes": True}


class WAConversationListResponse(BaseModel):
    """Paginated conversation list."""

    items: list[WAConversationResponse]
    total: int


class WAMessageResponse(BaseModel):
    """Single message in conversation."""

    id: UUID
    direction: str
    msg_type: str
    text_body: str | None = None
    media_url: str | None = None
    media_mime_type: str | None = None
    media_caption: str | None = None
    delivery_status: str
    is_from_ai: bool = False
    sender_phone: str | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WAMessageListResponse(BaseModel):
    """Cursor-based paginated message list."""

    items: list[WAMessageResponse]
    has_more: bool
    next_cursor: str | None = None


class WAMessageSendRequest(BaseModel):
    """Request to send a text message."""

    text: str = Field(..., min_length=1, max_length=4096)


class WATemplateSendRequest(BaseModel):
    """Request to send a template message in a conversation."""

    template_id: UUID


class WAConversationAssignRequest(BaseModel):
    """Request to assign a conversation."""

    user_id: UUID
