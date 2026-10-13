"""Pydantic schemas for Marketplace endpoints."""

from pydantic import BaseModel


class MarketplaceModuleResponse(BaseModel):
    """Single module in the marketplace catalog."""

    id: str
    name: str
    description: str
    icon: str
    category: str
    available: bool = False

    model_config = {"from_attributes": True}
