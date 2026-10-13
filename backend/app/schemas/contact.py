"""Schemas for contact form endpoints."""

from pydantic import BaseModel, Field


class ContactRequest(BaseModel):
    """Contact form request schema."""

    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)


class ContactResponse(BaseModel):
    """Contact form response schema."""

    success: bool
    message: str
