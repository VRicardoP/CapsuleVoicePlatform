"""Template schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WATemplateResponse(BaseModel):
    """Template response."""

    id: UUID
    name: str
    language: str
    category: str
    status: str
    header_type: str | None = None
    header_content: str | None = None
    body_text: str
    footer: str | None = None
    buttons: dict | None = None
    variables: dict | None = None
    meta_template_id: str | None = None
    meta_rejected_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WATemplateListResponse(BaseModel):
    """Paginated template list."""

    items: list[WATemplateResponse]
    total: int


class WATemplateCreateRequest(BaseModel):
    """Create a template."""

    name: str = Field(..., min_length=1, max_length=512)
    language: str = Field(default="es", max_length=10)
    category: str = Field(default="MARKETING")
    header_type: str | None = None
    header_content: str | None = None
    body_text: str = Field(..., min_length=1)
    footer: str | None = Field(default=None, max_length=60)
    buttons: dict | None = None
    variables: dict | None = None


class WATemplateUpdateRequest(BaseModel):
    """Update a template (only drafts)."""

    name: str | None = Field(default=None, max_length=512)
    language: str | None = Field(default=None, max_length=10)
    category: str | None = None
    header_type: str | None = None
    header_content: str | None = None
    body_text: str | None = None
    footer: str | None = None
    buttons: dict | None = None
    variables: dict | None = None
