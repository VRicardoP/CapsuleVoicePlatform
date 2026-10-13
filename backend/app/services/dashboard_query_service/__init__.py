"""Dashboard query service package.

Splits the monolith into domain-specific mixins while preserving backward compat:
    from app.services.dashboard_query_service import DashboardQueryService
"""

from .base import (
    DAYS_EN,
    DAYS_ES,
    DB_TO_FRONTEND_STATUS,
    DEFAULT_STATUS_DATA,
    MONTH_NAMES_ES,
    MONTHS_ES,
    STATUS_COLORS,
    STATUS_LABELS,
    DashboardBaseMixin,
    format_duration,
    format_duration_short,
    percentage_change,
    percentage_change_with_trend,
)
from .calls import DashboardCallsMixin
from .gdpr import DashboardGdprMixin
from .kpi import DashboardKpiMixin
from .outbound import DashboardOutboundMixin
from .stats import DashboardStatsMixin


class DashboardQueryService(
    DashboardCallsMixin,
    DashboardGdprMixin,
    DashboardKpiMixin,
    DashboardOutboundMixin,
    DashboardStatsMixin,
    DashboardBaseMixin,
):
    """Dashboard query service — facade combining all domain mixins."""

    pass


__all__ = [
    "DashboardQueryService",
    "DAYS_EN",
    "DAYS_ES",
    "DB_TO_FRONTEND_STATUS",
    "DEFAULT_STATUS_DATA",
    "MONTH_NAMES_ES",
    "MONTHS_ES",
    "STATUS_COLORS",
    "STATUS_LABELS",
    "format_duration",
    "format_duration_short",
    "percentage_change",
    "percentage_change_with_trend",
]
