export const SECURITY_CONFIG = {
  USE_MOCK_DATA: import.meta.env.VITE_USE_MOCK_DATA === 'true',
  BASE_URL: import.meta.env.VITE_API_URL || '/api/v1',
  REQUEST_TIMEOUT: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10),
  MAX_REQUESTS_PER_MINUTE: 200,

  ENDPOINTS: {
    // Auth
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH_TOKEN: '/auth/refresh',
    SESSIONS: '/auth/sessions',
    // Users
    USER_ME: '/users/me',
    USER_PREFERENCES: '/users/me',
    // Dashboard
    DASHBOARD: '/dashboard',
    DASHBOARD_METRICS: '/dashboard/gdpr-metrics',
    DASHBOARD_KPI: '/dashboard/kpi',
    DASHBOARD_GDPR_SUMMARY: '/dashboard/gdpr-summary',
    DASHBOARD_TRENDS: '/dashboard/gdpr-trends',
    DASHBOARD_ALERTS: '/dashboard/alerts',
    DASHBOARD_COMPLIANCE_GAPS: '/dashboard/compliance-gaps',
    DASHBOARD_CALL_STATS: '/dashboard/call-stats',
    DASHBOARD_OUTBOUND_SUMMARY: '/dashboard/outbound-summary',
    // Calls
    CALLS: '/calls',
    CALL_DETAILS: '/calls/:id',
    CALL_TRANSCRIPTION: '/calls/:id/transcription',
    CALL_HUMAN_REVIEW: '/calls/:id/human-review',
    CALL_RECORDING: '/calls/:id/recording',
    CALL_RECORDING_DOWNLOAD: '/calls/:id/recording/download',
    // GDPR Rights (Art. 15-22)
    GDPR_EXPORT: '/gdpr/export',
    GDPR_REQUESTS: '/gdpr/requests',
    GDPR_RECTIFY: '/gdpr/rectify',
    GDPR_ERASE: '/gdpr/erase',
    GDPR_RESTRICT: '/gdpr/restrict',
    GDPR_OBJECT: '/gdpr/object',
    GDPR_COMPLIANCE_REPORT_PDF: '/gdpr/compliance/report/pdf',
    // Admin GDPR
    GDPR_ADMIN_PENDING: '/gdpr/admin/requests/pending',
    GDPR_ADMIN_BLOCKED: '/gdpr/admin/blocked-data',
    // Legacy compatibility
    EXPORT_DATA: '/gdpr/export',
    DELETE_DATA: '/gdpr/erase',
    CONSENTS: '/gdpr/consents',
    GDPR_DASHBOARD: '/dashboard/metrics',
    GDPR_EXECUTIVE_SUMMARY: '/dashboard/gdpr-summary',
    GDPR_TRENDS: '/dashboard/trends',
    KPI_METRICS: '/dashboard/kpi',
    // Contact
    CONTACT_SEND: '/contact/send',
  },
};
