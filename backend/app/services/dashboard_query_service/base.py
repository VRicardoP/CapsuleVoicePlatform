"""Dashboard query service.

Encapsulates all database queries for dashboard endpoints.
Endpoints delegate to this service instead of containing raw SQL.
"""

import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dashboard import (
    AIMetrics,
    CallMetrics,
    Campaign,
    ConsentMetrics,
    DashboardMetrics,
    GDPRMetrics,
    RobinsonMetrics,
    SecurityMetrics,
    StatusData,
)

logger = logging.getLogger(__name__)

# === CONSTANTS ===

DAYS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

MONTH_NAMES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

DB_TO_FRONTEND_STATUS = {
    "completed": "completed",
    "scheduled": "scheduled",
    "transferred": "transferred",
    "rejected": "rejected",
    "initiated": "in_progress",
    "ringing": "in_progress",
    "answered": "in_progress",
    "on_hold": "in_progress",
    "abandoned": "no_answer",
    "failed": "rejected",
    "voicemail": "voicemail",
}

STATUS_COLORS = {
    "scheduled": "#10b981",
    "completed": "#10b981",
    "in_progress": "#f59e0b",
    "rejected": "#ef4444",
    "no_answer": "#ef4444",
    "transferred": "#8b5cf6",
    "cancelled": "#6b7280",
    "voicemail": "#f97316",
}

STATUS_LABELS = {
    "scheduled": "Agendada",
    "completed": "Finalizado",
    "in_progress": "Pendiente",
    "rejected": "Rechazada",
    "no_answer": "No respondida",
    "transferred": "Transferida",
    "cancelled": "Cancelada",
    "voicemail": "Voicemail",
}

DEFAULT_STATUS_DATA = [
    StatusData(name="Agendada", value=0, color="#10b981"),
    StatusData(name="Finalizado", value=0, color="#10b981"),
    StatusData(name="Pendiente", value=0, color="#f59e0b"),
    StatusData(name="Rechazada", value=0, color="#ef4444"),
    StatusData(name="No respondida", value=0, color="#ef4444"),
    StatusData(name="Voicemail", value=0, color="#f97316"),
]


# === PURE UTILITY FUNCTIONS ===


def format_duration(seconds: float) -> str:
    """Format seconds to 'Xm Ys' string."""
    if seconds <= 0:
        return "0m 0s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def format_duration_short(seconds: float) -> str:
    """Format seconds to 'M:SS' string."""
    if seconds <= 0:
        return "0:00"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def percentage_change(current: float, previous: float) -> float:
    """Calculate percentage change between two values."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def percentage_change_with_trend(current: int, previous: int) -> tuple[float, str]:
    """Calculate percentage change and trend direction."""
    change = percentage_change(current, previous)
    if change > 0:
        return change, "up"
    elif change < 0:
        return change, "down"
    return 0.0, "stable"


class DashboardBaseMixin:
    """Base mixin with __init__, constants, and composite queries."""

    def __init__(self, db):

        self.db: AsyncSession = db

    async def get_campaigns_data(self) -> list[Campaign]:
        """Get campaign data (placeholder)."""
        return []

    # --- Legacy metrics endpoint ---

    async def get_dashboard_metrics_complete(
        self, start_date: datetime | None, end_date: datetime | None
    ) -> DashboardMetrics:
        """Get comprehensive dashboard metrics (legacy format)."""
        try:
            result = await self.db.execute(
                text("SELECT * FROM get_dashboard_metrics_complete(:start_date, :end_date)"),
                {"start_date": start_date, "end_date": end_date},
            )
            row = result.fetchone()

            if row:
                data = dict(row._mapping)
                return DashboardMetrics(
                    calls=CallMetrics(
                        total_calls=data.get("total_calls", 0) or 0,
                        inbound_calls=data.get("inbound_calls", 0) or 0,
                        outbound_calls=data.get("outbound_calls", 0) or 0,
                        answered_calls=data.get("answered_calls", 0) or 0,
                        abandoned_calls=data.get("abandoned_calls", 0) or 0,
                        average_duration_seconds=float(data.get("avg_duration_seconds", 0) or 0),
                        average_wait_seconds=float(data.get("avg_wait_seconds", 0) or 0),
                    ),
                    consents=ConsentMetrics(
                        total_consents=data.get("total_consents", 0) or 0,
                        active_consents=data.get("active_consents", 0) or 0,
                        withdrawn_consents=data.get("withdrawn_consents", 0) or 0,
                        expiring_soon=data.get("expiring_consents", 0) or 0,
                    ),
                    gdpr=GDPRMetrics(
                        pending_requests=data.get("pending_gdpr_requests", 0) or 0,
                        completed_requests=data.get("completed_gdpr_requests", 0) or 0,
                        overdue_requests=data.get("overdue_gdpr_requests", 0) or 0,
                        average_response_days=float(data.get("avg_gdpr_response_days", 0) or 0),
                    ),
                    ai=AIMetrics(
                        total_decisions=data.get("total_ai_decisions", 0) or 0,
                        decisions_requiring_review=data.get("ai_decisions_pending_review", 0) or 0,
                        human_overrides=data.get("ai_human_overrides", 0) or 0,
                        average_confidence=float(data.get("ai_avg_confidence", 0) or 0),
                    ),
                    security=SecurityMetrics(
                        active_breaches=data.get("active_breaches", 0) or 0,
                        pending_notifications=data.get("pending_breach_notifications", 0) or 0,
                        blocked_data_records=data.get("blocked_data_count", 0) or 0,
                    ),
                    robinson=RobinsonMetrics(
                        total_checks=data.get("robinson_checks_total", 0) or 0,
                        listed_count=data.get("robinson_listed_count", 0) or 0,
                        exclusion_rate=float(data.get("robinson_exclusion_rate", 0) or 0),
                    ),
                    generated_at=datetime.utcnow(),
                )
        except (ProgrammingError, SQLAlchemyError) as e:
            logger.warning("get_dashboard_metrics_complete failed: %s", e)

        return DashboardMetrics(
            calls=CallMetrics(),
            consents=ConsentMetrics(),
            gdpr=GDPRMetrics(),
            ai=AIMetrics(),
            security=SecurityMetrics(),
            robinson=RobinsonMetrics(),
            generated_at=datetime.utcnow(),
        )

    # --- KPI endpoint ---
