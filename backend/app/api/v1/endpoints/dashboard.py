"""Dashboard endpoints.

Thin HTTP handlers that delegate to DashboardQueryService.
"""

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_with_rls, require_feature, require_permission
from app.schemas.dashboard import (
    CallStatsByPeriod,
    DashboardData,
    DashboardMetrics,
    FrontendMetrics,
    GdprDashboardMetrics,
    GdprExecutiveSummary,
    GdprTrendsResponse,
    KpiMetricsResponse,
    OutboundSummaryData,
    TrendData,
)
from app.services.dashboard_query_service import (
    DashboardQueryService,
    format_duration,
    percentage_change,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Type alias for the RLS-protected DB session dependency
RlsDb = Annotated[AsyncSession, Depends(get_db_with_rls)]


@router.get(
    "",
    response_model=DashboardData,
    summary="Get dashboard data",
    description="Get complete dashboard data for frontend.",
    dependencies=[Depends(require_permission("dashboard.calls.view"))],
)
async def get_dashboard_data(
    db: RlsDb,
) -> DashboardData:
    """Get complete dashboard data in the format expected by the frontend."""
    svc = DashboardQueryService(db)

    call_metrics = await svc.get_call_metrics()

    total_calls = int(call_metrics.get("total_calls", 0))
    avg_duration_secs = float(call_metrics.get("avg_duration_seconds", 0))
    total_minutes = int(call_metrics.get("total_minutes", 0))
    success_rate = float(call_metrics.get("success_rate", 0))

    prev_total_calls = int(call_metrics.get("prev_total_calls", 0))
    prev_avg_duration_secs = float(call_metrics.get("prev_avg_duration_seconds", 0))
    prev_total_minutes = int(call_metrics.get("prev_total_minutes", 0))
    prev_success_rate = float(call_metrics.get("prev_success_rate", 0))

    metrics = FrontendMetrics(
        totalCalls=total_calls,
        avgDuration=format_duration(avg_duration_secs),
        totalMinutes=total_minutes,
        successRate=int(success_rate),
        totalCallsChange=percentage_change(total_calls, prev_total_calls),
        avgDurationChange=percentage_change(avg_duration_secs, prev_avg_duration_secs),
        totalMinutesChange=percentage_change(total_minutes, prev_total_minutes),
        successRateChange=percentage_change(success_rate, prev_success_rate),
        periodLabel="mes actual",
    )

    calls_data = await svc.get_weekly_calls_data()
    status_data = await svc.get_status_distribution()
    recent_calls = await svc.get_recent_calls()
    performance_data = await svc.get_performance_data()
    heatmap_data = await svc.get_heatmap_data()
    conversion_data = await svc.get_conversion_data()
    campaigns = await svc.get_campaigns_data()

    return DashboardData(
        metrics=metrics,
        callsData=calls_data,
        statusData=status_data,
        recentCalls=recent_calls,
        performanceData=performance_data,
        heatmapData=heatmap_data,
        conversionData=conversion_data,
        campaigns=campaigns,
    )


@router.get(
    "/metrics",
    response_model=DashboardMetrics,
    summary="Get dashboard metrics (legacy)",
    description="Get dashboard metrics in legacy format.",
    dependencies=[Depends(require_permission("dashboard.calls.view"))],
)
async def get_dashboard_metrics(
    db: RlsDb,
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
) -> DashboardMetrics:
    """Get comprehensive dashboard metrics (legacy format)."""
    svc = DashboardQueryService(db)
    return await svc.get_dashboard_metrics_complete(start_date, end_date)


@router.get(
    "/kpi",
    response_model=KpiMetricsResponse,
    summary="Get KPI metrics",
    description="Get key performance indicators for frontend.",
    dependencies=[Depends(require_permission("dashboard.calls.view"))],
)
async def get_kpi_metrics(
    db: RlsDb,
    days: int = Query(30, ge=1, le=365, description="Number of days for KPI calculation"),
) -> KpiMetricsResponse:
    """Get KPI metrics in the format expected by the frontend."""
    svc = DashboardQueryService(db)
    return await svc.get_kpi_metrics(days)


@router.get(
    "/gdpr-metrics",
    response_model=GdprDashboardMetrics,
    summary="Get GDPR dashboard metrics",
    description="Get GDPR metrics for dashboard widgets.",
    dependencies=[Depends(require_permission("dashboard.gdpr.view"))],
)
async def get_gdpr_metrics(
    db: RlsDb,
) -> GdprDashboardMetrics:
    """Get GDPR dashboard metrics in format expected by frontend."""
    svc = DashboardQueryService(db)
    return await svc.get_gdpr_metrics()


@router.get(
    "/gdpr-summary",
    response_model=GdprExecutiveSummary,
    summary="Get GDPR executive summary",
    description="Get GDPR compliance executive summary.",
    dependencies=[Depends(require_permission("dashboard.gdpr.view"))],
)
async def get_gdpr_summary(
    db: RlsDb,
) -> GdprExecutiveSummary:
    """Get GDPR executive summary in format expected by frontend."""
    svc = DashboardQueryService(db)
    return await svc.get_gdpr_summary()


@router.get(
    "/trends",
    response_model=TrendData,
    summary="Get trend data",
    description="Get trend data for charts.",
    dependencies=[Depends(require_permission("dashboard.calls.view"))],
)
async def get_trends(
    db: RlsDb,
    days: int = Query(30, ge=7, le=365, description="Number of days for trend"),
) -> TrendData:
    """Get trend data for dashboard charts."""
    svc = DashboardQueryService(db)
    return await svc.get_trends(days)


@router.get(
    "/gdpr-trends",
    response_model=GdprTrendsResponse,
    summary="Get GDPR trends",
    description="Get GDPR compliance trends for charts.",
    dependencies=[Depends(require_permission("dashboard.gdpr.view"))],
)
async def get_gdpr_trends(
    db: RlsDb,
    days: int = Query(30, ge=7, le=365, description="Number of days for trend"),
) -> GdprTrendsResponse:
    """Get GDPR trends in format expected by frontend."""
    svc = DashboardQueryService(db)
    return await svc.get_gdpr_trends(days)


@router.get(
    "/compliance-gaps",
    response_model=dict[str, Any],
    summary="Get compliance gaps",
    description="Get summary of compliance gaps and issues.",
    dependencies=[Depends(require_permission("dashboard.gdpr.view"))],
)
async def get_compliance_gaps(
    db: RlsDb,
) -> dict[str, Any]:
    """Get compliance gaps summary."""
    svc = DashboardQueryService(db)
    return await svc.get_compliance_gaps()


@router.get(
    "/alerts",
    response_model=dict[str, Any],
    summary="Get dashboard alerts",
    description="Get active alerts requiring attention.",
    dependencies=[Depends(require_permission("dashboard.calls.view"))],
)
async def get_alerts(
    db: RlsDb,
) -> dict[str, Any]:
    """Get active alerts from various views."""
    svc = DashboardQueryService(db)
    return await svc.get_alerts()


@router.get(
    "/call-stats",
    response_model=CallStatsByPeriod,
    summary="Get call statistics by period",
    description="Get call counts for various time periods: years, months, weeks, days.",
    dependencies=[Depends(require_permission("dashboard.calls.view"))],
)
async def get_call_stats_by_period(
    db: RlsDb,
) -> CallStatsByPeriod:
    """Get call statistics organized by time periods."""
    svc = DashboardQueryService(db)
    return await svc.get_call_stats_by_period()


@router.get(
    "/outbound-summary",
    response_model=OutboundSummaryData,
    summary="Get outbound module summary",
    description="Resumen de campañas y llamadas salientes del tenant para el dashboard principal.",
    dependencies=[
        Depends(require_feature("outbound")),
        Depends(require_permission("outbound.campaigns.view")),
    ],
)
async def get_outbound_summary(
    db: RlsDb,
) -> OutboundSummaryData:
    """Outbound summary card data for the main dashboard."""
    svc = DashboardQueryService(db)
    data = await svc.get_outbound_summary()
    return OutboundSummaryData(**data)
