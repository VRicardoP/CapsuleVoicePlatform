"""Repository for API key management via PostgreSQL functions."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ApiKeyRepository:
    """Repository wrapping PostgreSQL API key functions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_api_key(
        self,
        client_type: str,
        service_name: str,
        service_id: str | None,
        description: str | None,
        allowed_ips: str | None,
        expires_days: int | None,
        created_by: str | None,
    ) -> tuple[str, str, str] | None:
        """Call create_api_key() PostgreSQL function.

        Returns (api_key, api_key_id, key_prefix) or None on failure.
        """
        result = await self.session.execute(
            text("""
                SELECT * FROM create_api_key(
                    :client_type,
                    :service_name,
                    :service_id,
                    :description,
                    CAST(:allowed_ips AS INET[]),
                    :expires_days,
                    CAST(:created_by AS UUID)
                )
            """),
            {
                "client_type": client_type,
                "service_name": service_name,
                "service_id": service_id,
                "description": description,
                "allowed_ips": allowed_ips,
                "expires_days": expires_days,
                "created_by": created_by,
            },
        )
        row = result.fetchone()
        if not row:
            return None
        return row[0], str(row[1]), row[2]

    async def revoke_api_key(self, api_key_id: UUID, reason: str, revoked_by: str) -> bool:
        """Call revoke_api_key() PostgreSQL function."""
        result = await self.session.execute(
            text(
                "SELECT revoke_api_key(CAST(:api_key_id AS UUID), :reason, CAST(:revoked_by AS UUID))"
            ),
            {
                "api_key_id": str(api_key_id),
                "reason": reason,
                "revoked_by": revoked_by,
            },
        )
        return bool(result.scalar())

    async def list_api_keys(self, include_revoked: bool = False) -> list[dict[str, Any]]:
        """List all API keys (metadata only, no key values)."""
        query = """
            SELECT id, key_prefix, client_type, service_name, service_id,
                   description, allowed_ips::TEXT[], is_active, created_at,
                   expires_at, last_used_at, use_count
            FROM api_keys
        """
        if not include_revoked:
            query += " WHERE is_active = true"
        query += " ORDER BY created_at DESC"

        result = await self.session.execute(text(query))
        return [
            {
                "id": str(r[0]),
                "key_prefix": r[1],
                "client_type": r[2],
                "service_name": r[3],
                "service_id": r[4],
                "description": r[5],
                "allowed_ips": r[6],
                "is_active": r[7],
                "created_at": r[8],
                "expires_at": r[9],
                "last_used_at": r[10],
                "use_count": r[11] or 0,
            }
            for r in result.fetchall()
        ]

    async def service_id_exists(self, service_id: str) -> bool:
        """Check if an active API key with this service_id exists."""
        result = await self.session.execute(
            text("SELECT id FROM api_keys WHERE service_id = :service_id AND is_active = true"),
            {"service_id": service_id},
        )
        return result.fetchone() is not None
