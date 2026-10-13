"""Repository for WhatsApp admin dashboard and analytics queries.

Encapsulates raw SQL queries previously inlined in admin.py endpoints,
following CLAUDE.md rules: SQL in repositories, not in endpoint handlers.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class WhatsAppAdminRepository:
    """Raw-SQL queries for WhatsApp analytics, dashboard overview, and audit."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Messaging analytics
    # ------------------------------------------------------------------

    async def get_messaging_summary(self, tenant_id: UUID, days: int) -> dict[str, Any]:
        """Aggregate message counts (inbound, outbound, template, read, failed)."""
        result = await self._db.execute(
            text("""
            SELECT
                COUNT(*) FILTER (WHERE direction = 'inbound') as inbound_count,
                COUNT(*) FILTER (WHERE direction = 'outbound') as outbound_count,
                COUNT(*) FILTER (WHERE msg_type = 'template') as template_count,
                COUNT(*) FILTER (WHERE delivery_status = 'read') as read_count,
                COUNT(*) FILTER (WHERE delivery_status = 'failed') as failed_count,
                COUNT(DISTINCT conversation_id) as active_conversations
            FROM wa_messages
            WHERE tenant_id = CAST(:tid AS UUID)
              AND created_at >= NOW() - make_interval(days => :days)
        """),
            {"tid": str(tenant_id), "days": days},
        )
        row = result.fetchone()
        return {
            "inbound": row.inbound_count,
            "outbound": row.outbound_count,
            "templates": row.template_count,
            "read": row.read_count,
            "failed": row.failed_count,
            "active_conversations": row.active_conversations,
        }

    async def get_daily_message_counts(self, tenant_id: UUID, days: int) -> list[dict[str, Any]]:
        """Daily inbound/outbound message counts for chart display."""
        result = await self._db.execute(
            text("""
            SELECT
                DATE(created_at) as day,
                COUNT(*) FILTER (WHERE direction = 'inbound') as inbound,
                COUNT(*) FILTER (WHERE direction = 'outbound') as outbound
            FROM wa_messages
            WHERE tenant_id = CAST(:tid AS UUID)
              AND created_at >= NOW() - make_interval(days => :days)
            GROUP BY DATE(created_at)
            ORDER BY day
        """),
            {"tid": str(tenant_id), "days": days},
        )
        return [
            {"day": str(r.day), "inbound": r.inbound, "outbound": r.outbound}
            for r in result.fetchall()
        ]

    async def get_campaign_performance(self, tenant_id: UUID, days: int) -> dict[str, Any]:
        """Aggregate campaign performance metrics."""
        result = await self._db.execute(
            text("""
            SELECT
                COUNT(*) as total_campaigns,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COALESCE(SUM(sent_count), 0) as total_sent,
                COALESCE(SUM(delivered_count), 0) as total_delivered,
                COALESCE(SUM(read_count), 0) as total_read
            FROM wa_campaigns
            WHERE tenant_id = CAST(:tid AS UUID)
              AND created_at >= NOW() - make_interval(days => :days)
        """),
            {"tid": str(tenant_id), "days": days},
        )
        row = result.fetchone()
        return {
            "total": row.total_campaigns,
            "completed": row.completed,
            "total_sent": row.total_sent,
            "total_delivered": row.total_delivered,
            "total_read": row.total_read,
        }

    # ------------------------------------------------------------------
    # Dashboard overview
    # ------------------------------------------------------------------

    async def get_conversations_summary(self, tenant_id: UUID) -> dict[str, Any]:
        """Conversation counts by status."""
        result = await self._db.execute(
            text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'open') as open_count,
                COUNT(*) FILTER (WHERE status = 'closed') as closed_count,
                COUNT(*) FILTER (WHERE assignee_user_id IS NULL AND status = 'open') as unassigned
            FROM wa_conversations
            WHERE tenant_id = CAST(:tid AS UUID)
        """),
            {"tid": str(tenant_id)},
        )
        row = result.fetchone()
        return {
            "total": row.total,
            "open": row.open_count,
            "closed": row.closed_count,
            "unassigned": row.unassigned,
        }

    async def get_messages_today(self, tenant_id: UUID) -> dict[str, int]:
        """Inbound and outbound message counts for today."""
        result = await self._db.execute(
            text("""
            SELECT
                COUNT(*) FILTER (WHERE direction = 'inbound') as inbound_today,
                COUNT(*) FILTER (WHERE direction = 'outbound') as outbound_today
            FROM wa_messages
            WHERE tenant_id = CAST(:tid AS UUID)
              AND created_at >= CURRENT_DATE
        """),
            {"tid": str(tenant_id)},
        )
        row = result.fetchone()
        return {"inbound": row.inbound_today, "outbound": row.outbound_today}

    async def get_contacts_total(self, tenant_id: UUID) -> int:
        """Total contact count for the tenant."""
        result = await self._db.execute(
            text("""
            SELECT COUNT(*) FROM wa_contacts
            WHERE tenant_id = CAST(:tid AS UUID)
        """),
            {"tid": str(tenant_id)},
        )
        return result.scalar_one()

    async def get_active_campaigns_count(self, tenant_id: UUID) -> int:
        """Count of campaigns currently in 'sending' status."""
        result = await self._db.execute(
            text("""
            SELECT COUNT(*) FROM wa_campaigns
            WHERE tenant_id = CAST(:tid AS UUID) AND status = 'sending'
        """),
            {"tid": str(tenant_id)},
        )
        return result.scalar_one()

    async def get_unresolved_sla_breaches(self, tenant_id: UUID) -> int:
        """Count of unresolved SLA breaches."""
        result = await self._db.execute(
            text("""
            SELECT COUNT(*) FROM wa_sla_breaches
            WHERE tenant_id = CAST(:tid AS UUID) AND resolved_at IS NULL
        """),
            {"tid": str(tenant_id)},
        )
        return result.scalar_one()

    async def get_avg_response_minutes(self, tenant_id: UUID) -> float | None:
        """Average first-response time in minutes over last 7 days."""
        result = await self._db.execute(
            text("""
            SELECT AVG(EXTRACT(EPOCH FROM (sla_first_response_at - created_at)) / 60.0) as avg_minutes
            FROM wa_conversations
            WHERE tenant_id = CAST(:tid AS UUID)
              AND sla_first_response_at IS NOT NULL
              AND created_at >= NOW() - interval '7 days'
        """),
            {"tid": str(tenant_id)},
        )
        return result.scalar_one()
