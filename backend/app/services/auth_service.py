"""
Authentication service helpers.

Extracted from auth endpoints to keep handlers thin.
"""

import logging
from urllib.parse import urlparse
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserPreferencesRepository
from app.schemas.auth import UserPreferencesInfo

logger = logging.getLogger(__name__)


def resolve_cookie_settings(request: Request) -> tuple[bool, str]:
    """Decide Secure/SameSite for auth cookies based on request origin."""
    origin = request.headers.get("origin")
    origin_host = None
    try:
        if origin:
            origin_host = urlparse(origin).hostname
    except ValueError:
        origin_host = None

    is_cross_site = bool(origin_host and origin_host != request.url.hostname)
    is_local = request.url.hostname in {"localhost", "127.0.0.1"}

    secure = (request.url.scheme == "https") or (is_cross_site and not is_local)
    samesite = "none" if (is_cross_site and secure) else "lax"

    return secure, samesite


async def load_user_preferences(db: AsyncSession, user_id: UUID) -> UserPreferencesInfo | None:
    """Load user preferences from DB via repository."""
    try:
        prefs_repo = UserPreferencesRepository(db)
        prefs_data = await prefs_repo.get_preferences(user_id)
        if prefs_data:
            return UserPreferencesInfo(**prefs_data)
    except (SQLAlchemyError, ValueError) as e:
        logger.warning("Failed to load preferences for user %s: %s", user_id, e)
    return None
