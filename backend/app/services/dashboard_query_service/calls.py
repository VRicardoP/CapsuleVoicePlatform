"""Dashboard call metrics mixin."""

import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

from app.config.settings import settings
from app.schemas.dashboard import (
    CallRecord,
    PerformanceMetric,
    StatusData,
)

from .base import (
    DAYS_EN,
    DAYS_ES,
    DB_TO_FRONTEND_STATUS,
    DEFAULT_STATUS_DATA,
    MONTHS_ES,
    STATUS_COLORS,
    STATUS_LABELS,
    format_duration_short,
)

logger = logging.getLogger(__name__)


class DashboardCallsMixin:
    """Call-related dashboard queries."""

    async def get_call_metrics(self) -> dict:
        """Get call metrics comparing current month vs previous month."""
        try:
            result = await self.db.execute(
                text("""
                WITH current_month AS (
                    SELECT
                        COUNT(*) as total_calls,
                        COALESCE(AVG(duration_seconds), 0) as avg_duration_seconds,
                        COALESCE(SUM(duration_seconds) / 60, 0) as total_minutes,
                        COALESCE(
                            COUNT(*) FILTER (WHERE status IN ('completed', 'scheduled') AND COALESCE(duration_seconds, 0) >= 60) * 100.0 / NULLIF(COUNT(*), 0),
                            0
                        ) as success_rate
                    FROM calls
                    WHERE deleted_at IS NULL
                    AND initiated_at >= DATE_TRUNC('month', CURRENT_DATE)
                    AND initiated_at < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
                ),
                previous_month AS (
                    SELECT
                        COUNT(*) as total_calls,
                        COALESCE(AVG(duration_seconds), 0) as avg_duration_seconds,
                        COALESCE(SUM(duration_seconds) / 60, 0) as total_minutes,
                        COALESCE(
                            COUNT(*) FILTER (WHERE status IN ('completed', 'scheduled') AND COALESCE(duration_seconds, 0) >= 60) * 100.0 / NULLIF(COUNT(*), 0),
                            0
                        ) as success_rate
                    FROM calls
                    WHERE deleted_at IS NULL
                    AND initiated_at >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
                    AND initiated_at < DATE_TRUNC('month', CURRENT_DATE)
                )
                SELECT
                    cm.total_calls,
                    cm.avg_duration_seconds,
                    cm.total_minutes,
                    cm.success_rate,
                    pm.total_calls as prev_total_calls,
                    pm.avg_duration_seconds as prev_avg_duration_seconds,
                    pm.total_minutes as prev_total_minutes,
                    pm.success_rate as prev_success_rate
                FROM current_month cm, previous_month pm
            """)
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_call_metrics failed: %s", e)
        return {}

    async def get_weekly_calls_data(self) -> list[dict]:
        """Get calls data for weekly evolution chart."""
        days = DAYS_ES
        try:
            result = await self.db.execute(
                text("""
                SELECT
                    EXTRACT(DOW FROM initiated_at) as dow,
                    COUNT(*) as calls,
                    COUNT(*) FILTER (WHERE status IN ('completed', 'scheduled') AND COALESCE(duration_seconds, 0) >= 60) as resolved,
                    COALESCE(AVG(duration_seconds), 0) as avg_duration
                FROM calls
                WHERE deleted_at IS NULL
                AND initiated_at >= NOW() - INTERVAL '7 days'
                GROUP BY EXTRACT(DOW FROM initiated_at)
                ORDER BY EXTRACT(DOW FROM initiated_at)
            """)
            )
            rows = result.fetchall()

            data_by_dow = {}
            for row in rows:
                data = dict(row._mapping)
                dow = int(data.get("dow", 0))
                adjusted_dow = (dow - 1) % 7
                data_by_dow[adjusted_dow] = {
                    "calls": int(data.get("calls", 0)),
                    "resolved": int(data.get("resolved", 0)),
                    "avgDuration": int(data.get("avg_duration", 0)),
                }

            result_data = []
            for i, day in enumerate(days):
                day_data = data_by_dow.get(i, {"calls": 0, "resolved": 0, "avgDuration": 0})
                result_data.append(
                    {
                        "date": day,
                        "calls": day_data["calls"],
                        "resolved": day_data["resolved"],
                        "avgDuration": day_data["avgDuration"],
                    }
                )
            return result_data
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_weekly_calls_data failed: %s", e)

        return [{"date": day, "calls": 0, "resolved": 0, "avgDuration": 0} for day in days]

    async def get_status_distribution(self) -> list[StatusData]:
        """Get call status distribution for pie chart."""
        try:
            result = await self.db.execute(
                text("""
                SELECT status, COUNT(*) as count
                FROM calls
                WHERE deleted_at IS NULL
                AND initiated_at >= NOW() - INTERVAL '30 days'
                GROUP BY status
            """)
            )
            rows = result.fetchall()

            aggregated: dict[str, int] = {}
            for row in rows:
                row_data = dict(row._mapping)
                db_status = row_data.get("status", "unknown")
                count = int(row_data.get("count", 0))
                frontend_status = DB_TO_FRONTEND_STATUS.get(db_status)
                if frontend_status:
                    aggregated[frontend_status] = aggregated.get(frontend_status, 0) + count

            data = []
            for status, count in aggregated.items():
                if status in STATUS_COLORS:
                    data.append(
                        StatusData(
                            name=STATUS_LABELS.get(status, status),
                            value=count,
                            color=STATUS_COLORS.get(status, "#6b7280"),
                        )
                    )
            return data if data else list(DEFAULT_STATUS_DATA)
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_status_distribution failed: %s", e)

        return list(DEFAULT_STATUS_DATA)

    async def get_recent_calls(
        self, limit: int | None = None, days: int | None = None
    ) -> list[CallRecord]:
        """Get recent calls for table."""
        if limit is None:
            limit = settings.recent_calls_limit
        if days is None:
            days = settings.recent_calls_days
        try:
            result = await self.db.execute(
                text("""
                SELECT
                    c.id,
                    c.initiated_at AT TIME ZONE 'Europe/Madrid' as initiated_at_local,
                    c.duration_seconds,
                    'Cliente' as caller_name,
                    COALESCE(c.caller_number, '***-***-****') as caller_phone,
                    COALESCE(c.status, 'completed') as status,
                    COALESCE(c.sentiment, 'neutral') as sentiment,
                    c.recording_consent as has_consent,
                    COALESCE(c.direction, 'inbound') as direction,
                    c.called_number
                FROM calls c
                WHERE c.deleted_at IS NULL
                  AND c.initiated_at >= NOW() - make_interval(days => :days)
                ORDER BY c.initiated_at DESC
                LIMIT :limit
            """),
                {"limit": limit, "days": days},
            )
            rows = result.fetchall()

            calls = []
            for row in rows:
                data = dict(row._mapping)
                initiated_at_local = data.get("initiated_at_local")
                duration_secs = data.get("duration_seconds") or 0

                if initiated_at_local:
                    date_str = initiated_at_local.strftime("%Y-%m-%d")
                    time_str = initiated_at_local.strftime("%H:%M")
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    time_str = "00:00"

                db_status = data.get("status", "completed")
                frontend_status = DB_TO_FRONTEND_STATUS.get(db_status, "completed")

                # Abandoned/failed calls: ring time is not conversation time
                if db_status in ("abandoned", "failed", "voicemail"):
                    duration_secs = 0

                calls.append(
                    CallRecord(
                        id=str(data.get("id", "")),
                        date=date_str,
                        time=time_str,
                        duration=format_duration_short(duration_secs),
                        caller=data.get("caller_name", "Cliente"),
                        phone=data.get("caller_phone", "***-***-****"),
                        status=frontend_status,
                        sentiment=data.get("sentiment", "neutral"),
                        direction=data.get("direction", "inbound"),
                        calledNumber=data.get("called_number"),
                        hasActiveConsent=data.get("has_consent") is not None
                        and data.get("has_consent") is True,
                        recordingConsentId=None,
                    )
                )
            return calls
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.error("get_recent_calls failed: %s", e)
        return []

    async def get_performance_data(self) -> list[PerformanceMetric]:
        """Get AI performance metrics for radar chart."""
        try:
            result = await self.db.execute(
                text("""
                SELECT
                    COALESCE(
                        COUNT(*) FILTER (WHERE status = 'completed' AND COALESCE(duration_seconds, 0) >= 60) * 100.0 / NULLIF(COUNT(*), 0),
                        0
                    ) as first_call_resolution,
                    COALESCE(
                        COUNT(*) FILTER (WHERE sentiment = 'positive') * 100.0 / NULLIF(COUNT(*), 0),
                        0
                    ) as satisfaction,
                    85 as response_time,
                    COALESCE(
                        COUNT(*) FILTER (WHERE status IN ('completed', 'scheduled') AND COALESCE(duration_seconds, 0) >= 60) * 100.0 / NULLIF(COUNT(*), 0),
                        0
                    ) as ai_accuracy,
                    COALESCE(
                        COUNT(*) FILTER (WHERE status = 'scheduled') * 100.0 / NULLIF(COUNT(*), 0),
                        0
                    ) as conversion
                FROM calls
                WHERE deleted_at IS NULL
                AND initiated_at >= NOW() - INTERVAL '30 days'
            """)
            )
            row = result.fetchone()
            if row:
                data = dict(row._mapping)
                return [
                    PerformanceMetric(
                        metric="Resolución 1ra Llamada",
                        value=int(data.get("first_call_resolution", 0)),
                    ),
                    PerformanceMetric(
                        metric="Satisfacción", value=int(data.get("satisfaction", 0))
                    ),
                    PerformanceMetric(
                        metric="Tiempo Respuesta", value=int(data.get("response_time", 85))
                    ),
                    PerformanceMetric(metric="Precisión IA", value=int(data.get("ai_accuracy", 0))),
                    PerformanceMetric(metric="Conversión", value=int(data.get("conversion", 0))),
                ]
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_performance_data failed: %s", e)

        return [
            PerformanceMetric(metric="Resolución 1ra Llamada", value=0),
            PerformanceMetric(metric="Satisfacción", value=0),
            PerformanceMetric(metric="Tiempo Respuesta", value=0),
            PerformanceMetric(metric="Precisión IA", value=0),
            PerformanceMetric(metric="Conversión", value=0),
        ]

    async def get_heatmap_data(self) -> list[dict]:
        """Get heatmap data (calls by hour and day)."""
        hours = ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]
        days = DAYS_EN

        try:
            result = await self.db.execute(
                text("""
                SELECT
                    EXTRACT(DOW FROM initiated_at AT TIME ZONE 'Europe/Madrid') as dow,
                    EXTRACT(HOUR FROM initiated_at AT TIME ZONE 'Europe/Madrid') as hour,
                    COUNT(*) as count
                FROM calls
                WHERE deleted_at IS NULL
                AND initiated_at >= NOW() - INTERVAL '7 days'
                GROUP BY
                    EXTRACT(DOW FROM initiated_at AT TIME ZONE 'Europe/Madrid'),
                    EXTRACT(HOUR FROM initiated_at AT TIME ZONE 'Europe/Madrid')
            """)
            )
            rows = result.fetchall()

            data_lookup = {}
            for row in rows:
                data = dict(row._mapping)
                dow = int(data.get("dow", 0))
                hour = int(data.get("hour", 0))
                count = int(data.get("count", 0))
                day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                day = day_names[dow]
                hour_block = (hour // 3) * 3
                key = (hour_block, day)
                data_lookup[key] = data_lookup.get(key, 0) + count

            result_data = []
            for hour in hours:
                hour_int = int(hour.split(":")[0])
                row_data = {"hour": hour}
                for day in days:
                    row_data[day] = data_lookup.get((hour_int, day), 0)
                result_data.append(row_data)
            return result_data
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_heatmap_data failed: %s", e)

        return [
            {"hour": h, "Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0, "Sun": 0}
            for h in hours
        ]

    async def get_conversion_data(self) -> list[dict]:
        """Get monthly conversion data for area chart."""
        months = MONTHS_ES

        try:
            result = await self.db.execute(
                text("""
                SELECT
                    EXTRACT(MONTH FROM initiated_at) as month,
                    COUNT(*) as llamadas,
                    COUNT(*) FILTER (WHERE status = 'scheduled') as conversiones
                FROM calls
                WHERE deleted_at IS NULL
                AND initiated_at >= DATE_TRUNC('year', NOW())
                GROUP BY EXTRACT(MONTH FROM initiated_at)
                ORDER BY EXTRACT(MONTH FROM initiated_at)
            """)
            )
            rows = result.fetchall()

            data_lookup = {}
            for row in rows:
                data = dict(row._mapping)
                month_num = int(data.get("month", 1))
                llamadas = int(data.get("llamadas", 0))
                conversiones = int(data.get("conversiones", 0))
                tasa = (conversiones / llamadas * 100) if llamadas > 0 else 0
                data_lookup[month_num] = {
                    "llamadas": llamadas,
                    "conversiones": conversiones,
                    "tasa": round(tasa, 1),
                }

            current_month = datetime.now().month

            result_data = []
            for i in range(current_month):
                month_data = data_lookup.get(i + 1, {"llamadas": 0, "conversiones": 0, "tasa": 0})
                result_data.append(
                    {
                        "month": months[i],
                        "llamadas": month_data["llamadas"],
                        "conversiones": month_data["conversiones"],
                        "tasa": month_data["tasa"],
                    }
                )
            return (
                result_data
                if result_data
                else [{"month": months[0], "llamadas": 0, "conversiones": 0, "tasa": 0}]
            )
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_conversion_data failed: %s", e)

        return [{"month": "Ene", "llamadas": 0, "conversiones": 0, "tasa": 0}]
