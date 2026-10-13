"""API v1 endpoints."""

from app.api.v1.endpoints import ai_agent, auth, calls, contact, dashboard, gdpr, pbx, users

__all__ = [
    "auth",
    "users",
    "dashboard",
    "calls",
    "gdpr",
    "ai_agent",
    "pbx",
    "contact",
]
