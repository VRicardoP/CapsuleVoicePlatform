"""Dashboard outbound summary mixin."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

logger = logging.getLogger(__name__)


class DashboardOutboundMixin:
    """Outbound module summary query for the main dashboard card."""

    async def get_outbound_summary(self) -> dict:
        """Resumen de campañas y llamadas outbound del tenant (RLS filtra por tenant)."""
        result: dict = {
            "active_campaigns": 0,
            "total_campaigns": 0,
            "monthly_calls": 0,
            "monthly_answered": 0,
            "success_rate_pct": 0.0,
            "avg_duration_sec": 0.0,
        }

        try:
            row = (
                await self.db.execute(
                    text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'running')  AS active_campaigns,
                    COUNT(*)                                     AS total_campaigns,
                    COALESCE(SUM(success_count), 0)             AS total_success,
                    COALESCE(SUM(completed_count + failed_count), 0) AS total_called,
                    COALESCE(AVG(avg_duration_sec)
                        FILTER (WHERE avg_duration_sec IS NOT NULL AND avg_duration_sec > 0), 0
                    ) AS avg_duration_sec
                FROM oc_campaigns
            """)
                )
            ).fetchone()

            if row:
                data = dict(row._mapping)
                total_called = int(data.get("total_called", 0))
                total_success = int(data.get("total_success", 0))
                result["active_campaigns"] = int(data.get("active_campaigns", 0))
                result["total_campaigns"] = int(data.get("total_campaigns", 0))
                result["avg_duration_sec"] = float(data.get("avg_duration_sec", 0) or 0)
                result["success_rate_pct"] = (
                    round(total_success * 100.0 / total_called, 1) if total_called > 0 else 0.0
                )
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_outbound_summary (campaigns) failed: %s", e)

        try:
            row = (
                await self.db.execute(
                    text("""
                SELECT
                    COUNT(*)                                                    AS monthly_calls,
                    COUNT(*) FILTER (WHERE l.status IN ('completed', 'answered')) AS monthly_answered
                FROM oc_call_logs l
                JOIN oc_campaigns c ON c.id = l.campaign_id
                WHERE l.initiated_at >= DATE_TRUNC('month', CURRENT_DATE)
            """)
                )
            ).fetchone()

            if row:
                data = dict(row._mapping)
                result["monthly_calls"] = int(data.get("monthly_calls", 0))
                result["monthly_answered"] = int(data.get("monthly_answered", 0))
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_outbound_summary (call_logs) failed: %s", e)

        return result
