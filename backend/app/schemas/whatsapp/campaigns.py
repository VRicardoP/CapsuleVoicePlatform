"""Campaign schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class WACampaignCatalogItem(BaseModel):
    """Embedded catalog item summary for campaign responses."""

    id: UUID
    name: str
    price: Decimal
    currency: str = "EUR"
    image_url: str | None = None
    product_url: str | None = None
    description: str | None = None
    category: str | None = None

    model_config = {"from_attributes": True}


class WACampaignResponse(BaseModel):
    """Campaign response."""

    id: UUID
    name: str
    status: str
    template_id: UUID | None = None
    template_name: str | None = None
    catalog_item_id: UUID | None = None
    catalog_item: WACampaignCatalogItem | None = None
    audience_filter: dict | None = None
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    is_ab_test: bool = False
    total_recipients: int = 0
    sent_count: int = 0
    delivered_count: int = 0
    read_count: int = 0
    failed_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WACampaignListResponse(BaseModel):
    """Paginated campaign list."""

    items: list[WACampaignResponse]
    total: int


class WACampaignCreateRequest(BaseModel):
    """Create a campaign."""

    name: str = Field(..., min_length=1, max_length=255)
    template_id: UUID | None = None
    ab_template_id: UUID | None = None
    catalog_item_id: UUID | None = None
    audience_filter: dict | None = None
    scheduled_at: datetime | None = None
    is_ab_test: bool = False


class WACampaignUpdateRequest(BaseModel):
    """Update a draft campaign."""

    name: str | None = Field(default=None, max_length=255)
    template_id: UUID | None = None
    catalog_item_id: UUID | None = None
    audience_filter: dict | None = None
    scheduled_at: datetime | None = None


class WACampaignRecipientResponse(BaseModel):
    """Recipient status within a campaign."""

    id: UUID
    contact_id: UUID
    contact_name: str | None = None
    contact_phone: str | None = None
    status: str
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    error_detail: str | None = None

    model_config = {"from_attributes": True}
