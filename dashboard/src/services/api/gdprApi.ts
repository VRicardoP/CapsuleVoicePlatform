import type {
  ApiResponse,
  GdprExecutiveSummary,
  GdprTrendsResponse,
  GdprDashboardMetrics,
} from '../../types';
import { SECURITY_CONFIG } from './config';
import { secureHttpClient, secureBlobFetch, delay } from './httpClient';

export const gdprApi = {
  // ==========================================================================
  // GDPR RIGHTS (Art. 15-22)
  // ==========================================================================

  requestRectification: async (data: {
    field: string;
    new_value: string;
    reason?: string;
  }): Promise<ApiResponse<{ message: string; request_id: string }>> => {
    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.GDPR_RECTIFY, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  requestRestriction: async (data: {
    reason: string;
    scope?: string;
  }): Promise<ApiResponse<{ message: string; request_id: string }>> => {
    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.GDPR_RESTRICT, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  requestObjection: async (data: {
    processing_type: string;
    reason: string;
  }): Promise<ApiResponse<{ message: string; request_id?: string; effective_immediately?: boolean }>> => {
    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.GDPR_OBJECT, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getGdprRequests: async (): Promise<ApiResponse<Array<{
    id: string;
    request_type: string;
    status: string;
    received_at: string;
    response_due_date: string;
    responded_at?: string;
    response_details?: string;
  }>>> => {
    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.GDPR_REQUESTS, {
      method: 'GET',
    });
  },

  createGdprRequest: async (data: {
    request_type: 'access' | 'rectification' | 'erasure' | 'restriction' | 'portability' | 'objection';
    details?: string;
  }): Promise<ApiResponse<{
    id: string;
    request_type: string;
    status: string;
    received_at: string;
    response_due_date: string;
  }>> => {
    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.GDPR_REQUESTS, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  exportUserData: async (): Promise<ApiResponse<Blob>> => {
    return secureBlobFetch(SECURITY_CONFIG.ENDPOINTS.EXPORT_DATA, {
      accept: 'application/json',
    });
  },

  requestDataDeletion: async (reason: string): Promise<ApiResponse<void>> => {
    return secureHttpClient<void>(SECURITY_CONFIG.ENDPOINTS.GDPR_ERASE, {
      method: 'POST',
      body: JSON.stringify({ reason, confirm: true }),
    });
  },

  updateConsents: async (consents: Record<string, boolean>): Promise<ApiResponse<void>> => {
    return secureHttpClient<void>(SECURITY_CONFIG.ENDPOINTS.CONSENTS, {
      method: 'PUT',
      body: JSON.stringify({ consents }),
    });
  },

  // ==========================================================================
  // GDPR DASHBOARD METRICS
  // ==========================================================================

  getGdprDashboardMetrics: async (): Promise<ApiResponse<GdprDashboardMetrics>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      await delay(300);
      return {
        success: true,
        data: {
          complianceScore: 87.5,
          totalRequests: 156,
          pendingRequests: 12,
          overdueRequests: 2,
          activeBreaches: 1,
          totalConsents: 4523,
          activeConsents: 3891,
          revokedConsents: 632,
        },
      };
    }

    return secureHttpClient<GdprDashboardMetrics>(
      SECURITY_CONFIG.ENDPOINTS.DASHBOARD_METRICS,
      { method: 'GET' }
    );
  },

  getGdprExecutiveSummary: async (): Promise<ApiResponse<GdprExecutiveSummary>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      await delay(400);
      return {
        success: true,
        data: {
          compliance: {
            overallScore: 87.5,
            status: 'good',
            consentRate: 86.0,
            retentionCompliance: 94.2,
            requestResponseRate: 91.7,
            breachResponseRate: 100.0,
            lastUpdated: new Date().toISOString(),
          },
          pendingRequests: [
            {
              id: 'req-001',
              requestType: 'access',
              requestTypeLabel: 'Acceso a datos',
              priority: 'urgent',
              daysRemaining: 3,
              deadlineDate: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
              subjectEmail: 'usuario@ejemplo.com',
              createdAt: new Date(Date.now() - 27 * 24 * 60 * 60 * 1000).toISOString(),
            },
            {
              id: 'req-002',
              requestType: 'erasure',
              requestTypeLabel: 'Derecho al olvido',
              priority: 'warning',
              daysRemaining: 12,
              deadlineDate: new Date(Date.now() + 12 * 24 * 60 * 60 * 1000).toISOString(),
              subjectEmail: 'cliente@empresa.es',
              createdAt: new Date(Date.now() - 18 * 24 * 60 * 60 * 1000).toISOString(),
            },
            {
              id: 'req-003',
              requestType: 'portability',
              requestTypeLabel: 'Portabilidad',
              priority: 'normal',
              daysRemaining: 25,
              deadlineDate: new Date(Date.now() + 25 * 24 * 60 * 60 * 1000).toISOString(),
              subjectEmail: 'contacto@demo.com',
              createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
            },
          ],
          breachAlerts: [
            {
              id: 'breach-001',
              severity: 'medium',
              severityLabel: 'Media',
              urgency: 'urgent',
              hoursRemaining: 48,
              notificationDeadline: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
              description: 'Acceso no autorizado detectado en sistema de backups',
              affectedCount: 127,
              detectedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
              requiresNotification: true,
            },
          ],
          consentStatus: [
            {
              purposeId: 'marketing',
              purposeName: 'Comunicaciones comerciales',
              activeConsents: 2341,
              revokedConsents: 456,
              expiredConsents: 123,
              totalConsents: 2920,
              activeRate: 80.2,
            },
            {
              purposeId: 'analytics',
              purposeName: 'Análisis y mejora del servicio',
              activeConsents: 3102,
              revokedConsents: 234,
              expiredConsents: 89,
              totalConsents: 3425,
              activeRate: 90.6,
            },
            {
              purposeId: 'profiling',
              purposeName: 'Perfilado automatizado',
              activeConsents: 1876,
              revokedConsents: 892,
              expiredConsents: 67,
              totalConsents: 2835,
              activeRate: 66.2,
            },
            {
              purposeId: 'third_party',
              purposeName: 'Cesión a terceros',
              activeConsents: 1203,
              revokedConsents: 1567,
              expiredConsents: 234,
              totalConsents: 3004,
              activeRate: 40.0,
            },
          ],
          retentionAlerts: [
            {
              category: 'call_recordings',
              recordsNearExpiry: 234,
              recordsExpired: 12,
              oldestRecordDate: new Date(Date.now() - 360 * 24 * 60 * 60 * 1000).toISOString(),
              retentionPeriodDays: 365,
            },
            {
              category: 'transcriptions',
              recordsNearExpiry: 89,
              recordsExpired: 0,
              oldestRecordDate: new Date(Date.now() - 170 * 24 * 60 * 60 * 1000).toISOString(),
              retentionPeriodDays: 180,
            },
          ],
          generatedAt: new Date().toISOString(),
        },
      };
    }

    return secureHttpClient<GdprExecutiveSummary>(
      SECURITY_CONFIG.ENDPOINTS.DASHBOARD_GDPR_SUMMARY,
      { method: 'GET' }
    );
  },

  getGdprTrends: async (days: number = 30): Promise<ApiResponse<GdprTrendsResponse>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      await delay(350);
      const trends = [];
      const now = new Date();
      for (let i = days - 1; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        trends.push({
          date: date.toISOString().split('T')[0],
          compliance_score: 80 + Math.random() * 15,
          consent_rate: 82 + Math.random() * 10,
          request_response_rate: 85 + Math.random() * 12,
          breach_response_rate: 95 + Math.random() * 5,
        });
      }
      return {
        success: true,
        data: {
          trends,
          periodStart: new Date(now.getTime() - days * 24 * 60 * 60 * 1000).toISOString(),
          periodEnd: now.toISOString(),
        },
      };
    }

    return secureHttpClient<GdprTrendsResponse>(
      `${SECURITY_CONFIG.ENDPOINTS.DASHBOARD_TRENDS}?days=${days}`,
      { method: 'GET' }
    );
  },

  // ==========================================================================
  // COMPLIANCE REPORT
  // ==========================================================================

  downloadComplianceReportPdf: async (days: number = 30): Promise<ApiResponse<Blob>> => {
    return secureBlobFetch(
      `${SECURITY_CONFIG.ENDPOINTS.GDPR_COMPLIANCE_REPORT_PDF}?days=${days}`,
      { accept: 'application/pdf', timeoutMultiplier: 2 }
    );
  },
};
