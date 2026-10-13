"""API Key authentication for service clients (AI Agent, PBX).

This module implements API key authentication for non-user clients:
- AI Agent (conversational): High-frequency writes (transcriptions, decisions)
- PBX/CTI: Call lifecycle management

API keys are validated against PostgreSQL's api_keys table.
Keys are hashed with bcrypt and never stored in plain text.

Compliance:
- RGPD Art. 32: Secure authentication
- AI Act Art. 12: Service identification for traceability
"""

import ipaddress
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db

# Client types
ClientType = Literal["ai_agent", "pbx", "external", "webhook"]


@dataclass
class ServiceIdentity:
    """Authenticated service identity."""

    api_key_id: str
    client_type: ClientType
    service_id: str
    service_name: str
    permissions: dict
    rate_limit: int


class APIKeyAuth:
    """API Key authentication handler."""

    def __init__(
        self,
        allowed_client_types: list[ClientType] | None = None,
        required_permissions: list[str] | None = None,
    ):
        """Initialize API key auth.

        Args:
            allowed_client_types: List of allowed client types for this endpoint
            required_permissions: List of required permission keys
        """
        self.allowed_client_types = allowed_client_types
        self.required_permissions = required_permissions or []

    async def __call__(
        self,
        request: Request,
        x_api_key: Annotated[str | None, Header()] = None,
        x_service_id: Annotated[str | None, Header()] = None,
        db: AsyncSession = Depends(get_db),
    ) -> ServiceIdentity:
        """Validate API key and return service identity.

        Args:
            request: FastAPI request
            x_api_key: API key from header
            x_service_id: Optional service ID for logging
            db: Database session

        Returns:
            ServiceIdentity with authenticated service info

        Raises:
            HTTPException 401/403 if authentication fails
        """
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Validate against PostgreSQL
        result = await db.execute(
            text("SELECT * FROM validate_api_key(:api_key, CAST(:client_ip AS INET))"),
            {"api_key": x_api_key, "client_ip": client_ip},
        )
        row = result.fetchone()

        if not row or not row.is_valid:
            error_msg = row.error_message if row else "Invalid API key"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg,
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Check client type restriction
        if self.allowed_client_types and row.client_type not in self.allowed_client_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Client type '{row.client_type}' not allowed for this endpoint",
            )

        # Check required permissions
        permissions = row.permissions or {}
        for perm in self.required_permissions:
            if not permissions.get(perm):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {perm}",
                )

        # Store in request state for middleware/logging
        identity = ServiceIdentity(
            api_key_id=str(row.api_key_id),
            client_type=row.client_type,
            service_id=row.service_id,
            service_name=row.service_name,
            permissions=permissions,
            rate_limit=row.rate_limit,
        )

        request.state.service_identity = identity
        request.state.client_type = row.client_type

        return identity

    def _get_client_ip(self, request: Request) -> str | None:
        """Extract client IP from request.

        Only trusts X-Forwarded-For/X-Real-IP headers when the direct
        connection comes from a private/loopback IP (i.e. Traefik/Docker).
        """
        if request.client:
            direct_ip = request.client.host
            # Only trust proxy headers from private/loopback IPs (Traefik/Docker)
            try:
                if ipaddress.ip_address(direct_ip).is_private:
                    forwarded = request.headers.get("X-Forwarded-For")
                    if forwarded:
                        return forwarded.split(",")[0].strip()
                    real_ip = request.headers.get("X-Real-IP")
                    if real_ip:
                        return real_ip
            except ValueError:
                pass
            return direct_ip
        return None


# Pre-configured auth dependencies for common use cases

# AI Agent only
ai_agent_auth = APIKeyAuth(allowed_client_types=["ai_agent"])

# PBX/CTI only
pbx_auth = APIKeyAuth(allowed_client_types=["pbx"])

# AI or PBX
ai_or_pbx_auth = APIKeyAuth(allowed_client_types=["ai_agent", "pbx"])

# Any service
any_service_auth = APIKeyAuth()


async def verify_outbound_tool_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Verify a static API key used by Ultravox tool endpoints.

    Compares the incoming `X-API-Key` header against `settings.outbound_tool_api_key`
    in constant time. Returns 403 if the server has no key configured — refusing
    to run an unprotected endpoint is safer than accepting any caller.
    """
    import hmac

    from app.config.settings import settings

    expected = settings.outbound_tool_api_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OUTBOUND_TOOL_API_KEY not configured on the server",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def verify_notices_webhook_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Verify the static API key used by the Ultravox notices webhook endpoint.

    Compares `X-API-Key` against `settings.notices_webhook_api_key` in constant
    time. Returns 403 if the server has no key configured.
    """
    import hmac

    from app.config.settings import settings

    expected = settings.notices_webhook_api_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="NOTICES_WEBHOOK_API_KEY not configured on the server",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def verify_trips_tool_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Verify the static API key used by the Ultravox trips voice tool endpoint.

    Compares `X-API-Key` against `settings.trips_tool_api_key` in constant time.
    Returns 403 if the server has no key configured.
    """
    import hmac

    from app.config.settings import settings

    expected = settings.trips_tool_api_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="TRIPS_TOOL_API_KEY not configured on the server",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def get_service_identity(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> ServiceIdentity | None:
    """Get service identity if API key provided, None otherwise.

    Use this for endpoints that accept both user auth and service auth.
    """
    if not x_api_key:
        return None

    auth = APIKeyAuth()
    try:
        return await auth(request, x_api_key, None, db)
    except HTTPException:
        return None


async def require_ai_agent(
    identity: Annotated[ServiceIdentity, Depends(ai_agent_auth)],
) -> ServiceIdentity:
    """Require AI Agent authentication."""
    return identity


async def require_pbx(
    identity: Annotated[ServiceIdentity, Depends(pbx_auth)],
) -> ServiceIdentity:
    """Require PBX authentication."""
    return identity


async def require_ai_or_pbx(
    identity: Annotated[ServiceIdentity, Depends(ai_or_pbx_auth)],
) -> ServiceIdentity:
    """Require AI Agent or PBX authentication."""
    return identity


async def require_service(
    identity: Annotated[ServiceIdentity, Depends(any_service_auth)],
) -> ServiceIdentity:
    """Require any service authentication."""
    return identity
