"""Commerce schemas: pipeline, deals, catalog, orders."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

# --- Pipeline ---


class WAPipelineStageResponse(BaseModel):
    """Pipeline stage response."""

    id: UUID
    name: str
    color: str
    sort_order: int
    is_default: bool = False
    is_won: bool = False
    is_lost: bool = False
    deal_count: int = 0
    deal_value: Decimal = Decimal("0")

    model_config = {"from_attributes": True}


class WAPipelineStageCreateRequest(BaseModel):
    """Create a pipeline stage."""

    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int = 0
    is_won: bool = False
    is_lost: bool = False


class WAPipelineStageUpdateRequest(BaseModel):
    """Update a pipeline stage."""

    name: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int | None = None
    is_won: bool | None = None
    is_lost: bool | None = None


# --- Deals ---


class WADealResponse(BaseModel):
    """Deal response."""

    id: UUID
    stage_id: UUID
    stage_name: str | None = None
    contact_id: UUID | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    conversation_id: UUID | None = None
    title: str
    value: Decimal = Decimal("0")
    currency: str = "EUR"
    assignee_user_id: UUID | None = None
    expected_close_date: date | None = None
    closed_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WADealListResponse(BaseModel):
    """Deal list response."""

    items: list[WADealResponse]
    total: int


class WADealCreateRequest(BaseModel):
    """Create a deal."""

    stage_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    contact_id: UUID | None = None
    conversation_id: UUID | None = None
    value: Decimal = Decimal("0")
    currency: str = Field(default="EUR", max_length=3)
    assignee_user_id: UUID | None = None
    expected_close_date: date | None = None
    notes: str | None = None


class WADealUpdateRequest(BaseModel):
    """Update a deal."""

    stage_id: UUID | None = None
    title: str | None = Field(default=None, max_length=255)
    value: Decimal | None = None
    currency: str | None = None
    assignee_user_id: UUID | None = None
    expected_close_date: date | None = None
    notes: str | None = None
    closed_at: datetime | None = None


class WADealMoveRequest(BaseModel):
    """Move a deal to a different stage."""

    stage_id: UUID


class WAPipelineAnalyticsResponse(BaseModel):
    """Pipeline analytics summary."""

    total_deals: int = 0
    total_value: Decimal = Decimal("0")
    won_deals: int = 0
    won_value: Decimal = Decimal("0")
    lost_deals: int = 0
    conversion_rate: float = 0.0
    stages: list[WAPipelineStageResponse] = []


# --- Catalog ---


class WACatalogItemResponse(BaseModel):
    """Catalog item response."""

    id: UUID
    name: str
    description: str | None = None
    price: Decimal
    currency: str = "EUR"
    image_url: str | None = None
    product_url: str | None = None
    category: str | None = None
    sku: str | None = None
    stock: int | None = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WACatalogItemListResponse(BaseModel):
    """Paginated catalog list."""

    items: list[WACatalogItemResponse]
    total: int


class WACatalogItemCreateRequest(BaseModel):
    """Create a catalog item."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    price: Decimal = Field(..., ge=0)
    currency: str = Field(default="EUR", max_length=3)
    image_url: str | None = None
    product_url: str | None = None
    category: str | None = Field(default=None, max_length=100)
    sku: str | None = Field(default=None, max_length=100)
    stock: int | None = None


class WACatalogItemUpdateRequest(BaseModel):
    """Update a catalog item."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    image_url: str | None = None
    product_url: str | None = None
    category: str | None = None
    sku: str | None = None
    stock: int | None = None
    status: str | None = None


# --- Orders ---


class WAOrderItemResponse(BaseModel):
    """Order line item."""

    id: UUID
    catalog_item_id: UUID | None = None
    name: str
    quantity: int
    unit_price: Decimal

    model_config = {"from_attributes": True}


class WAOrderResponse(BaseModel):
    """Order response."""

    id: UUID
    contact_id: UUID | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    conversation_id: UUID | None = None
    status: str
    total: Decimal
    currency: str = "EUR"
    notes: str | None = None
    items: list[WAOrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WAOrderListResponse(BaseModel):
    """Paginated order list."""

    items: list[WAOrderResponse]
    total: int


class WAOrderCreateRequest(BaseModel):
    """Create an order."""

    contact_id: UUID | None = None
    conversation_id: UUID | None = None
    notes: str | None = None
    items: list[dict] = Field(..., min_length=1)


class WAOrderUpdateRequest(BaseModel):
    """Update an order status."""

    status: str | None = None
    notes: str | None = None
