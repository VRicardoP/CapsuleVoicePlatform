"""Dashboard schemas for frontend compatibility.

Contains all Pydantic models used by dashboard endpoints.
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

# === MAIN DASHBOARD SCHEMAS ===


class FrontendMetrics(BaseModel):
    """Metrics summary for frontend cards."""

    totalCalls: int = 0
    avgDuration: str = "0m 0s"
    totalMinutes: int = 0
    successRate: int = 0
    totalCallsChange: float = 0
    avgDurationChange: float = 0
    totalMinutesChange: float = 0
    successRateChange: float = 0
    periodLabel: str = "mes actual"


class ChartDataPoint(BaseModel):
    """Data point for line/area charts."""

    date: str | None = None
    month: str | None = None
    hour: str | None = None
    calls: int | None = None
    resolved: int | None = None
    avgDuration: int | None = None
    conversiones: int | None = None
    tasa: float | None = None
    llamadas: int | None = None
    Mon: int | None = None
    Tue: int | None = None
    Wed: int | None = None
    Thu: int | None = None
    Fri: int | None = None
    Sat: int | None = None
    Sun: int | None = None

    class Config:
        extra = "allow"


class StatusData(BaseModel):
    """Status distribution for pie chart."""

    name: str
    value: int
    color: str


class CallRecord(BaseModel):
    """Recent call record."""

    id: str
    date: str
    time: str
    duration: str
    caller: str
    phone: str
    status: Literal[
        "completed",
        "transferred",
        "scheduled",
        "rejected",
        "in_progress",
        "cancelled",
        "voicemail",
        "no_answer",
    ]
    sentiment: Literal["positive", "neutral", "negative"]
    direction: Literal["inbound", "outbound", "internal"] = "inbound"
    calledNumber: str | None = None
    hasActiveConsent: bool | None = None
    recordingConsentId: str | None = None


class PerformanceMetric(BaseModel):
    """Performance radar chart data."""

    metric: str
    value: int
    fullMark: int = 100


class Campaign(BaseModel):
    """Campaign data."""

    name: str
    date: str
    minutes: int
    status: str
    agendada: str
    interesado: str
    pendiente: str
    rechazada: str


class DashboardData(BaseModel):
    """Complete dashboard data for frontend."""

    metrics: FrontendMetrics
    callsData: list[dict[str, Any]]
    statusData: list[StatusData]
    recentCalls: list[CallRecord]
    performanceData: list[PerformanceMetric]
    heatmapData: list[dict[str, Any]]
    conversionData: list[dict[str, Any]]
    campaigns: list[Campaign]


# === LEGACY SCHEMAS (kept for /metrics endpoint) ===


class CallMetrics(BaseModel):
    """Call statistics."""

    total_calls: int = 0
    inbound_calls: int = 0
    outbound_calls: int = 0
    answered_calls: int = 0
    abandoned_calls: int = 0
    average_duration_seconds: float = 0
    average_wait_seconds: float = 0


class ConsentMetrics(BaseModel):
    """Consent statistics."""

    total_consents: int = 0
    active_consents: int = 0
    withdrawn_consents: int = 0
    expiring_soon: int = 0


class GDPRMetrics(BaseModel):
    """GDPR compliance statistics."""

    pending_requests: int = 0
    completed_requests: int = 0
    overdue_requests: int = 0
    average_response_days: float = 0


class AIMetrics(BaseModel):
    """AI Agent metrics."""

    total_decisions: int = 0
    decisions_requiring_review: int = 0
    human_overrides: int = 0
    average_confidence: float = 0


class SecurityMetrics(BaseModel):
    """Security metrics."""

    active_breaches: int = 0
    pending_notifications: int = 0
    blocked_data_records: int = 0


class RobinsonMetrics(BaseModel):
    """Robinson list compliance."""

    total_checks: int = 0
    listed_count: int = 0
    exclusion_rate: float = 0


class DashboardMetrics(BaseModel):
    """Complete dashboard metrics (legacy format)."""

    calls: CallMetrics
    consents: ConsentMetrics
    gdpr: GDPRMetrics
    ai: AIMetrics
    security: SecurityMetrics
    robinson: RobinsonMetrics
    generated_at: datetime


# === KPI SCHEMAS ===


class KPIMetrics(BaseModel):
    """Key Performance Indicators (legacy)."""

    service_level_percent: float = 0
    first_call_resolution_percent: float = 0
    average_handling_time_seconds: float = 0
    csat_average: float = 0
    nps_score: float = 0
    calls_per_agent: float = 0
    occupancy_rate: float = 0
    gdpr_compliance_rate: float = 0
    consent_coverage_rate: float = 0
    robinson_compliance_rate: float = 0
    ai_automation_rate: float = 0
    ai_accuracy_rate: float = 0


class KpiData(BaseModel):
    """KPI data for frontend TopMetricsModule."""

    roiPercentage: float = 0
    roiLabel: str = "0%"
    estimatedSavings: float = 0
    estimatedSavingsFormatted: str = "0€"

    avgValuePerCall: float = 0
    avgValuePerCallFormatted: str = "0€"
    avgValueChangePercent: float = 0
    avgValueTrend: Literal["up", "down"] = "up"

    qualifiedLeads: int = 0
    conversionRate: float = 0
    conversionRateLabel: str = "0% conversión"

    avgResponseTimeScore: float = 0
    avgResponseTimeFormatted: str = "0s"
    callsUnder2sPct: float = 0
    callsUnder2sLabel: str = "0% < 2s"

    totalConversionValue: float = 0
    totalConversionValueFormatted: str = "0€"
    conversionChangePercent: float = 0


class KpiSummary(BaseModel):
    """KPI summary statistics."""

    totalCalls: int = 0
    totalDurationMinutes: int = 0
    avgHandleTimeSeconds: float = 0
    periodDays: int = 30


class KpiMetricsResponse(BaseModel):
    """Complete KPI response for frontend."""

    kpis: KpiData
    summary: KpiSummary
    period: dict[str, str]


class TrendDataPoint(BaseModel):
    """Single trend data point."""

    date: date
    value: float


class TrendData(BaseModel):
    """Trend data for charts."""

    calls_trend: list[TrendDataPoint] = []
    consent_trend: list[TrendDataPoint] = []
    gdpr_requests_trend: list[TrendDataPoint] = []


# === CALL STATISTICS BY PERIOD ===


class MonthlyCallStats(BaseModel):
    """Monthly call statistics."""

    month: int
    year: int
    monthName: str
    calls: int


class CallStatsByPeriod(BaseModel):
    """Call statistics organized by time periods."""

    currentYear: int = 0
    currentYearLabel: str = ""
    previousYear: int = 0
    previousYearLabel: str = ""
    yearOverYearChange: float = 0
    yearOverYearTrend: Literal["up", "down", "stable"] = "stable"
    currentYearMonths: list[MonthlyCallStats] = []
    previousYearMonths: list[MonthlyCallStats] = []
    currentWeek: int = 0
    currentWeekLabel: str = ""
    previousWeek: int = 0
    previousWeekLabel: str = ""
    weekOverWeekChange: float = 0
    weekOverWeekTrend: Literal["up", "down", "stable"] = "stable"
    today: int = 0
    todayLabel: str = ""
    yesterday: int = 0
    yesterdayLabel: str = ""
    dayOverDayChange: float = 0
    dayOverDayTrend: Literal["up", "down", "stable"] = "stable"
    generatedAt: str = ""


# === GDPR EXECUTIVE SUMMARY SCHEMAS ===


class GdprComplianceSummary(BaseModel):
    """GDPR compliance summary for dashboard."""

    overallScore: float = 0
    status: Literal["excellent", "good", "needs_attention", "critical"] = "good"
    consentRate: float = 0
    retentionCompliance: float = 0
    requestResponseRate: float = 0
    breachResponseRate: float = 0
    lastUpdated: str = ""


class GdprPendingRequest(BaseModel):
    """GDPR pending request for dashboard."""

    id: str
    requestType: str
    requestTypeLabel: str
    priority: Literal["overdue", "urgent", "warning", "normal"] = "normal"
    daysRemaining: int
    deadlineDate: str
    subjectEmail: str
    createdAt: str


class GdprBreachAlert(BaseModel):
    """GDPR breach alert for dashboard."""

    id: str
    severity: str
    severityLabel: str
    urgency: Literal["overdue", "critical", "urgent", "normal"] = "normal"
    hoursRemaining: int
    notificationDeadline: str
    description: str
    affectedCount: int
    detectedAt: str
    requiresNotification: bool = True


class GdprConsentStatus(BaseModel):
    """GDPR consent status by purpose."""

    purposeId: str
    purposeName: str
    activeConsents: int = 0
    revokedConsents: int = 0
    expiredConsents: int = 0
    totalConsents: int = 0
    activeRate: float = 0


class GdprRetentionAlert(BaseModel):
    """GDPR retention alert."""

    category: str
    recordsNearExpiry: int = 0
    recordsExpired: int = 0
    oldestRecordDate: str
    retentionPeriodDays: int = 365


class GdprExecutiveSummary(BaseModel):
    """Complete GDPR executive summary for frontend."""

    compliance: GdprComplianceSummary
    pendingRequests: list[GdprPendingRequest] = []
    breachAlerts: list[GdprBreachAlert] = []
    consentStatus: list[GdprConsentStatus] = []
    retentionAlerts: list[GdprRetentionAlert] = []
    generatedAt: str = ""


class GdprTrendDataPoint(BaseModel):
    """GDPR trend data point."""

    date: str
    compliance_score: float = 0
    consent_rate: float = 0
    request_response_rate: float = 0
    breach_response_rate: float = 0


class GdprTrendsResponse(BaseModel):
    """GDPR trends response for frontend."""

    trends: list[GdprTrendDataPoint] = []
    periodStart: str = ""
    periodEnd: str = ""


class GdprDashboardMetrics(BaseModel):
    """GDPR dashboard metrics for frontend."""

    complianceScore: float = 0
    totalRequests: int = 0
    pendingRequests: int = 0
    overdueRequests: int = 0
    activeBreaches: int = 0
    totalConsents: int = 0
    activeConsents: int = 0
    revokedConsents: int = 0


class OutboundSummaryData(BaseModel):
    """Outbound module summary for the main dashboard card."""

    active_campaigns: int = 0
    total_campaigns: int = 0
    monthly_calls: int = 0
    monthly_answered: int = 0
    success_rate_pct: float = 0.0
    avg_duration_sec: float = 0.0
