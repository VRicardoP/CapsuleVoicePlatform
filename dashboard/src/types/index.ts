// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface User {
  id: string;
  name: string;
  email: string;
  company: string;
  role: string;
  preferences?: UserPreferences;
}

export interface UserPreferences {
  visibleModules: string[];
  theme: 'dark' | 'light';
}

export interface CallRecord {
  id: string;
  date: string;
  time: string;
  duration: string;
  caller: string;
  phone: string;
  status: 'completed' | 'transferred' | 'scheduled' | 'rejected' | 'in_progress' | 'cancelled' | 'voicemail' | 'no_answer';
  sentiment: 'positive' | 'neutral' | 'negative';
  direction?: 'inbound' | 'outbound' | 'internal';
  calledNumber?: string;
  recording?: string;
  recordingConsentId?: string;
  hasActiveConsent?: boolean;
  recordingAvailable?: boolean;
  recordingExpiresAt?: string;
}

export interface Transcription {
  callId: string;
  timestamp: string;
  speaker: 'assistant' | 'client';
  text: string;
  hasPii?: boolean;
  piiCategories?: string[];
  consentId?: string;
  consentStatus?: 'active' | 'revoked' | 'expired' | 'none';
}

export interface AutomatedAction {
  id: string;
  type: ActionType;
  callId: string;
  description: string;
  status: 'success' | 'pending' | 'failed';
  timestamp: string;
  details?: {
    tool_name?: string;
    tool_args?: Record<string, any>;
    booking?: {
      cita_id?: number;
      fecha?: string;
      hora?: string;
      servicio_nombre?: string;
      cliente_nombre?: string;
      empleado_nombre?: string;
      cliente_nuevo?: boolean;
    };
    success?: boolean;
    cita_id?: number;
  };
}

export type ActionType = 'email' | 'crm' | 'calendar' | 'whatsapp';

export interface ChartDataPoint {
  date?: string;
  month?: string;
  hour?: string;
  calls?: number;
  resolved?: number;
  avgDuration?: number;
  conversiones?: number;
  tasa?: number;
  llamadas?: number;
  [key: string]: string | number | undefined;
}

export interface StatusData {
  name: string;
  value: number;
  color: string;
  [key: string]: string | number;
}

export interface PerformanceMetric {
  metric: string;
  value: number;
  fullMark: number;
}

export interface ModuleConfig {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: 'metrics' | 'charts' | 'tables' | 'analytics' | 'advanced' | 'gdpr';
  defaultVisible: boolean;
  component: React.ComponentType<Record<string, unknown>>;
  requiredPermission?: string;
}

export interface Campaign {
  name: string;
  date: string;
  minutes: number;
  status: string;
  agendada: string;
  interesado: string;
  pendiente: string;
  rechazada: string;
}

export interface DashboardContextType {
  user: User;
  visibleModules: string[];
  toggleModule: (moduleId: string) => void;
  setModules: (moduleIds: string[]) => void;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
}

export interface DashboardData {
  metrics: {
    totalCalls: number;
    avgDuration: string;
    totalMinutes: number;
    successRate: number;
    // Change percentages comparing current month vs previous month
    totalCallsChange: number;
    avgDurationChange: number;
    totalMinutesChange: number;
    successRateChange: number;
    periodLabel: string;
  };
  callsData: ChartDataPoint[];
  statusData: StatusData[];
  recentCalls: CallRecord[];
  performanceData: PerformanceMetric[];
  heatmapData: ChartDataPoint[];
  conversionData: ChartDataPoint[];
  campaigns: Campaign[];
}

// ============================================================================
// RGPD/PRIVACY TYPES
// ============================================================================

// Roles emitted by the new permission system (commit f6ae320). The legacy
// values 'admin' / 'viewer' / 'auditor' are kept in the union only as a
// safety net for cached sessions or any unmigrated user row that might
// still surface them — new code should treat them as deprecated.
export type UserRole =
  | 'superadmin'
  | 'client_admin'
  | 'user'
  // legacy / back-compat
  | 'admin'
  | 'viewer'
  | 'auditor';

export interface ConsentInfo {
  id: string;
  purpose: string;
  given: boolean;
  obtainedAt: string;
  expiresAt?: string;
  revokedAt?: string;
  canRevoke: boolean;
}

export interface PrivacyRequest {
  type: 'access' | 'rectification' | 'erasure' | 'restriction' | 'portability' | 'objection';
  reason?: string;
  details?: string;
}

export interface ModulePermissions {
  moduleId: string;
  requiredRole: UserRole;
  requiresPiiAccess: boolean;
}

// ============================================================================
// GDPR DASHBOARD TYPES
// ============================================================================

export type ComplianceStatus = 'excellent' | 'good' | 'needs_attention' | 'critical';
export type RequestPriority = 'overdue' | 'urgent' | 'warning' | 'normal';
export type BreachUrgency = 'overdue' | 'critical' | 'urgent' | 'normal';

export interface GdprComplianceSummary {
  overallScore: number;
  status: ComplianceStatus;
  consentRate: number;
  retentionCompliance: number;
  requestResponseRate: number;
  breachResponseRate: number;
  lastUpdated: string;
}

export interface GdprPendingRequest {
  id: string;
  requestType: string;
  requestTypeLabel: string;
  priority: RequestPriority;
  daysRemaining: number;
  deadlineDate: string;
  subjectEmail: string;
  createdAt: string;
}

export interface GdprBreachAlert {
  id: string;
  severity: string;
  severityLabel: string;
  urgency: BreachUrgency;
  hoursRemaining: number;
  notificationDeadline: string;
  description: string;
  affectedCount: number;
  detectedAt: string;
  requiresNotification: boolean;
}

export interface GdprConsentStatus {
  purposeId: string;
  purposeName: string;
  activeConsents: number;
  revokedConsents: number;
  expiredConsents: number;
  totalConsents: number;
  activeRate: number;
}

export interface GdprRetentionAlert {
  category: string;
  recordsNearExpiry: number;
  recordsExpired: number;
  oldestRecordDate: string;
  retentionPeriodDays: number;
}

export interface GdprTrendDataPoint {
  date: string;
  compliance_score: number;
  consent_rate: number;
  request_response_rate: number;
  breach_response_rate: number;
}

export interface GdprExecutiveSummary {
  compliance: GdprComplianceSummary;
  pendingRequests: GdprPendingRequest[];
  breachAlerts: GdprBreachAlert[];
  consentStatus: GdprConsentStatus[];
  retentionAlerts: GdprRetentionAlert[];
  generatedAt: string;
}

export interface GdprTrendsResponse {
  trends: GdprTrendDataPoint[];
  periodStart: string;
  periodEnd: string;
}

export interface GdprDashboardMetrics {
  complianceScore: number;
  totalRequests: number;
  pendingRequests: number;
  overdueRequests: number;
  activeBreaches: number;
  totalConsents: number;
  activeConsents: number;
  revokedConsents: number;
}

// ============================================================================
// KPI METRICS TYPES (Punto 2 Auditoría)
// ============================================================================

export interface KpiData {
  roiPercentage: number;
  roiLabel: string;
  estimatedSavings: number;
  estimatedSavingsFormatted: string;

  avgValuePerCall: number;
  avgValuePerCallFormatted: string;
  avgValueChangePercent: number;
  avgValueTrend: 'up' | 'down';

  qualifiedLeads: number;
  conversionRate: number;
  conversionRateLabel: string;

  avgResponseTimeScore: number;
  avgResponseTimeFormatted: string;
  callsUnder2sPct: number;
  callsUnder2sLabel: string;

  totalConversionValue: number;
  totalConversionValueFormatted: string;
  conversionChangePercent: number;
}

export interface KpiSummary {
  totalCalls: number;
  totalDurationMinutes: number;
  avgHandleTimeSeconds: number;
  periodDays: number;
}

export interface KpiMetricsResponse {
  kpis: KpiData;
  summary: KpiSummary;
  period: {
    startDate: string;
    endDate: string;
  };
}

// ============================================================================
// CALL STATISTICS BY PERIOD
// ============================================================================

export interface MonthlyCallStats {
  month: number;
  year: number;
  monthName: string;
  calls: number;
}

export interface CallStatsByPeriod {
  // Annual totals
  currentYear: number;
  currentYearLabel: string;
  previousYear: number;
  previousYearLabel: string;
  yearOverYearChange: number;
  yearOverYearTrend: 'up' | 'down' | 'stable';

  // Monthly breakdown
  currentYearMonths: MonthlyCallStats[];
  previousYearMonths: MonthlyCallStats[];

  // Weekly totals
  currentWeek: number;
  currentWeekLabel: string;
  previousWeek: number;
  previousWeekLabel: string;
  weekOverWeekChange: number;
  weekOverWeekTrend: 'up' | 'down' | 'stable';

  // Daily totals
  today: number;
  todayLabel: string;
  yesterday: number;
  yesterdayLabel: string;
  dayOverDayChange: number;
  dayOverDayTrend: 'up' | 'down' | 'stable';

  // Metadata
  generatedAt: string;
}

// ============================================================================
// TENANT FEATURES
// ============================================================================

export interface TenantFeatures {
  whatsapp: boolean;
  recordings: boolean;
  sentiment: boolean;
  robinson: boolean;
  whatsapp_emoji_filters: boolean;
}