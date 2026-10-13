"""Security module for authentication and session management.

Implements secure session handling compatible with PostgreSQL's secure_sessions table.
Compliant with RGPD Art. 32 (security), LOPDGDD Art. 5 (confidentiality).
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config.settings import settings


class TokenData(BaseModel):
    """JWT token payload structure."""

    user_id: str
    session_token: str  # PostgreSQL secure_sessions token
    exp: datetime


class JWTPayload(BaseModel):
    """Full JWT payload for API authentication."""

    sub: str  # user_id
    sst: str  # secure_session_token from PostgreSQL
    exp: int
    iat: int
    type: str  # "access" or "refresh"
    role: str | None = None


def _verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    """Synchronous bcrypt verification (CPU-bound, ~100ms)."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash (sync wrapper for non-async callers)."""
    return _verify_password_sync(plain_password, hashed_password)


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash without blocking the event loop."""
    return await asyncio.to_thread(_verify_password_sync, plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(
    user_id: str,
    session_token: str,
    role: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT access token containing PostgreSQL session reference.

    The session_token is the secure_sessions.session_token from PostgreSQL.
    This token is validated against the database on each request.

    Args:
        user_id: UUID of the authenticated user
        session_token: Token from PostgreSQL set_current_user()
        role: User role for authorization
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT string
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    payload = {
        "sub": user_id,
        "sst": session_token,  # PostgreSQL secure session token
        "role": role,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "type": "access",
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: str,
    session_token: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT refresh token for session renewal."""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    payload = {
        "sub": user_id,
        "sst": session_token,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "type": "refresh",
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> JWTPayload | None:
    """Decode and validate JWT token.

    Note: This only validates the JWT signature and expiration.
    The session_token (sst) must still be validated against PostgreSQL.

    Args:
        token: JWT string to decode

    Returns:
        JWTPayload if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return JWTPayload(**payload)
    except JWTError:
        return None


async def validate_session_in_db(
    session: Any,  # AsyncSession
    session_token: str,
) -> str | None:
    """Validate session token against PostgreSQL user_sessions.

    This validates that the session exists and is not expired or revoked.

    Args:
        session: SQLAlchemy async session
        session_token: Token from JWT's sst claim (unhashed)

    Returns:
        user_id if valid, None if invalid
    """
    import hashlib

    from sqlalchemy import text

    # Hash the token to match against stored hash
    token_hash = hashlib.sha256(session_token.encode()).hexdigest()

    # Validate against user_sessions + user state (is_active, deleted_at, locked_until)
    result = await session.execute(
        text("""
            SELECT us.user_id::text
            FROM user_sessions us
            JOIN users u ON u.id = us.user_id
            WHERE us.token_hash = :token_hash
              AND us.is_revoked = false
              AND us.expires_at > CURRENT_TIMESTAMP
              AND u.is_active = true
              AND u.deleted_at IS NULL
              AND (u.locked_until IS NULL OR u.locked_until < CURRENT_TIMESTAMP)
        """),
        {"token_hash": token_hash},
    )
    row = result.fetchone()

    return row[0] if row else None
