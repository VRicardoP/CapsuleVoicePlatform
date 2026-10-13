"""Dashboard call statistics mixin — trends and period comparisons."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

from app.schemas.dashboard import (
    CallStatsByPeriod,
    MonthlyCallStats,
    TrendData,
    TrendDataPoint,
)

from .base import MONTH_NAMES_ES, percentage_change_with_trend

logger = logging.getLogger(__name__)


class DashboardStatsMixin:
    """Trend and period comparison queries."""

    async def get_trends(self, days: int) -> TrendData:
        """Get trend data for dashboard charts."""
        calls_trend: list[TrendDataPoint] = []
        consent_trend: list[TrendDataPoint] = []
        gdpr_trend: list[TrendDataPoint] = []

        try:
            result = await self.db.execute(
                text("SELECT * FROM get_gdpr_trends(:days)"),
                {"days": days},
            )
            for row in result.fetchall():
                data = dict(row._mapping)
                trend_date = data.get("trend_date")
                if trend_date:
                    if data.get("calls_count") is not None:
                        calls_trend.append(
                            TrendDataPoint(date=trend_date, value=float(data.get("calls_count", 0)))
                        )
                    if data.get("consents_count") is not None:
                        consent_trend.append(
                            TrendDataPoint(
                                date=trend_date, value=float(data.get("consents_count", 0))
                            )
                        )
                    if data.get("gdpr_requests_count") is not None:
                        gdpr_trend.append(
                            TrendDataPoint(
                                date=trend_date, value=float(data.get("gdpr_requests_count", 0))
                            )
                        )
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_trends failed: %s", e)

        return TrendData(
            calls_trend=calls_trend, consent_trend=consent_trend, gdpr_requests_trend=gdpr_trend
        )

    async def get_call_stats_by_period(self) -> CallStatsByPeriod:
        """Get call statistics organized by time periods."""
        now = datetime.utcnow()
        current_year = now.year
        previous_year = current_year - 1
        today = now.date()
        yesterday = today - timedelta(days=1)

        days_since_monday = today.weekday()
        current_week_start = today - timedelta(days=days_since_monday)
        current_week_end = current_week_start + timedelta(days=6)
        previous_week_start = current_week_start - timedelta(days=7)
        previous_week_end = current_week_start - timedelta(days=1)

        stats = CallStatsByPeriod(
            currentYearLabel=str(current_year),
            previousYearLabel=str(previous_year),
            currentWeekLabel=f"{current_week_start.strftime('%d/%m')} - {current_week_end.strftime('%d/%m')}",
            previousWeekLabel=f"{previous_week_start.strftime('%d/%m')} - {previous_week_end.strftime('%d/%m')}",
            todayLabel=today.strftime("%d/%m/%Y"),
            yesterdayLabel=yesterday.strftime("%d/%m/%Y"),
            generatedAt=now.isoformat(),
        )

        try:
            # Annual statistics
            result = await self.db.execute(
                text("""
                SELECT EXTRACT(YEAR FROM initiated_at)::int as year, COUNT(*) as calls
                FROM calls WHERE deleted_at IS NULL
                AND EXTRACT(YEAR FROM initiated_at) IN (:current_year, :previous_year)
                GROUP BY EXTRACT(YEAR FROM initiated_at)
            """),
                {"current_year": current_year, "previous_year": previous_year},
            )

            for row in result.fetchall():
                data = dict(row._mapping)
                if data["year"] == current_year:
                    stats.currentYear = int(data["calls"])
                elif data["year"] == previous_year:
                    stats.previousYear = int(data["calls"])

            change, trend = percentage_change_with_trend(stats.currentYear, stats.previousYear)
            stats.yearOverYearChange = change
            stats.yearOverYearTrend = trend

            # Monthly statistics
            monthly_query = text("""
                SELECT EXTRACT(MONTH FROM initiated_at)::int as month, COUNT(*) as calls
                FROM calls WHERE deleted_at IS NULL
                AND EXTRACT(YEAR FROM initiated_at) = :year
                GROUP BY EXTRACT(MONTH FROM initiated_at) ORDER BY month
            """)

            for year, attr in [
                (current_year, "currentYearMonths"),
                (previous_year, "previousYearMonths"),
            ]:
                result = await self.db.execute(monthly_query, {"year": year})
                months_data = [
                    MonthlyCallStats(
                        month=dict(row._mapping)["month"],
                        year=year,
                        monthName=MONTH_NAMES_ES.get(dict(row._mapping)["month"], ""),
                        calls=int(dict(row._mapping)["calls"]),
                    )
                    for row in result.fetchall()
                ]
                setattr(stats, attr, months_data)

            # Weekly statistics
            result = await self.db.execute(
                text("""
                SELECT
                    CASE
                        WHEN initiated_at::date >= :cws AND initiated_at::date <= :cwe THEN 'current'
                        WHEN initiated_at::date >= :pws AND initiated_at::date <= :pwe THEN 'previous'
                    END as week_type,
                    COUNT(*) as calls
                FROM calls WHERE deleted_at IS NULL
                AND ((initiated_at::date >= :cws AND initiated_at::date <= :cwe)
                  OR (initiated_at::date >= :pws AND initiated_at::date <= :pwe))
                GROUP BY week_type
            """),
                {
                    "cws": current_week_start,
                    "cwe": current_week_end,
                    "pws": previous_week_start,
                    "pwe": previous_week_end,
                },
            )

            for row in result.fetchall():
                data = dict(row._mapping)
                if data["week_type"] == "current":
                    stats.currentWeek = int(data["calls"])
                elif data["week_type"] == "previous":
                    stats.previousWeek = int(data["calls"])

            change, trend = percentage_change_with_trend(stats.currentWeek, stats.previousWeek)
            stats.weekOverWeekChange = change
            stats.weekOverWeekTrend = trend

            # Daily statistics
            result = await self.db.execute(
                text("""
                SELECT initiated_at::date as call_date, COUNT(*) as calls
                FROM calls WHERE deleted_at IS NULL
                AND initiated_at::date IN (:today, :yesterday)
                GROUP BY initiated_at::date
            """),
                {"today": today, "yesterday": yesterday},
            )

            for row in result.fetchall():
                data = dict(row._mapping)
                if data["call_date"] == today:
                    stats.today = int(data["calls"])
                elif data["call_date"] == yesterday:
                    stats.yesterday = int(data["calls"])

            change, trend = percentage_change_with_trend(stats.today, stats.yesterday)
            stats.dayOverDayChange = change
            stats.dayOverDayTrend = trend

        except (ProgrammingError, SQLAlchemyError) as e:
            logger.error("Error fetching call stats: %s", e)

        return stats
