"""Contact-related schemas: segments, tags, notes, contact detail, agents."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# --- Segments ---


class WASegmentResponse(BaseModel):
    """Segment with contact count."""

    id: UUID
    name: str
    slug: str
    color: str
    icon: str | None = None
    description: str | None = None
    is_system: bool = False
    contact_count: int = 0
    sort_order: int = 0

    model_config = {"from_attributes": True}


class WASegmentListResponse(BaseModel):
    """List of segments for sidebar."""

    items: list[WASegmentResponse]


class WASegmentCreateRequest(BaseModel):
    """Create a custom segment."""

    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=255)


class WASegmentUpdateRequest(BaseModel):
    """Update a segment (only custom segments)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = None
    description: str | None = None
    sort_order: int | None = None


class WAContactSegmentsRequest(BaseModel):
    """Assign segments to a contact (replaces all)."""

    segment_ids: list[UUID]


# --- Tags ---


class WATagResponse(BaseModel):
    """Tag response."""

    id: UUID
    name: str
    color: str

    model_config = {"from_attributes": True}


class WATagListResponse(BaseModel):
    """List of tags."""

    items: list[WATagResponse]


class WATagCreateRequest(BaseModel):
    """Create a tag."""

    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")


# --- Internal Notes ---


class WAInternalNoteResponse(BaseModel):
    """Internal note on a conversation."""

    id: UUID
    author_user_id: UUID
    author_name: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WAInternalNoteListResponse(BaseModel):
    """List of notes for a conversation."""

    items: list[WAInternalNoteResponse]


class WAInternalNoteCreateRequest(BaseModel):
    """Create an internal note."""

    content: str = Field(..., min_length=1, max_length=2000)


class WAInternalNoteUpdateRequest(BaseModel):
    """Update an internal note."""

    content: str = Field(..., min_length=1, max_length=2000)


# --- Contact Detail ---


class WAContactDetailResponse(BaseModel):
    """Full contact detail with segments, tags, and metadata."""

    id: UUID
    phone_e164: str
    display_name: str | None = None
    email: str | None = None
    opt_in_status: str = "unknown"
    notes: str | None = None
    source: str = "inbound"
    metadata_extra: dict | None = None
    segments: list[WASegmentResponse] = []
    tags: list[WATagResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WAContactUpdateRequest(BaseModel):
    """Update contact fields."""

    display_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    tag_ids: list[UUID] | None = None


# --- Agent ---


class WAAgentResponse(BaseModel):
    """Agent available for conversation assignment."""

    id: UUID
    name: str
    email: str | None = None
    role: str


# --- Contact List & Create ---


class WAContactListResponse(BaseModel):
    """Paginated contact list."""

    items: list[WAContactDetailResponse]
    total: int


class WAContactCreateRequest(BaseModel):
    """Create a contact manually."""

    phone_e164: str = Field(..., min_length=1, max_length=20)
    display_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    source: str = Field(default="manual", max_length=50)


# --- Bulk Operations ---


class WABulkSegmentAssignRequest(BaseModel):
    """Bulk assign segments to multiple contacts."""

    contact_ids: list[UUID] = Field(..., min_length=1, max_length=500)
    segment_ids: list[UUID] = Field(..., min_length=1)


class WAAutoAssignSettingsRequest(BaseModel):
    """Configure auto-assignment settings."""

    enabled: bool = True
    agent_ids: list[UUID] = Field(default_factory=list)
