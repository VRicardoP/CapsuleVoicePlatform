"""Tenant repository — shared across modules for organization lookups."""

import logging
from datetime import UTC
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TenantRepository:
    """Encapsulates tenant/organization queries used by multiple modules."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_tenant_id(self) -> UUID | None:
        """Get the first active organization ID (single-tenant per deployment)."""
        result = await self.session.execute(
            text("SELECT id FROM organizations WHERE is_active = true LIMIT 1")
        )
        row = result.fetchone()
        return row.id if row else None

    async def get_tenant_id_for_user(self, user_id: UUID | str) -> UUID | None:
        """Get the organization_id for a specific user."""
        result = await self.session.execute(
            text(
                "SELECT organization_id FROM users WHERE id = CAST(:uid AS UUID) AND deleted_at IS NULL"
            ),
            {"uid": str(user_id)},
        )
        row = result.fetchone()
        return row.organization_id if row and row.organization_id else None

    async def check_rate_limit(
        self, user_id: UUID, action: str, entity_type: str, limit: int, window_hours: int
    ) -> bool:
        """Check if a user has exceeded a rate limit for a given action. Returns True if within limit."""
        from datetime import datetime, timedelta

        window_start = datetime.now(UTC) - timedelta(hours=window_hours)
        result = await self.session.execute(
            text("""
                SELECT COUNT(*) FROM audit_log
                WHERE user_id = CAST(:user_id AS UUID)
                AND action = :action
                AND entity_type = :entity_type
                AND created_at > :window_start
            """),
            {
                "user_id": str(user_id),
                "action": action,
                "entity_type": entity_type,
                "window_start": window_start,
            },
        )
        count = result.scalar() or 0
        return count < limit
