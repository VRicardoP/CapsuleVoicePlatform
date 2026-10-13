import type { DashboardData, CallRecord, KpiMetricsResponse, ApiResponse } from '../../types';
import { SECURITY_CONFIG } from './config';
import { secureHttpClient, delay } from './httpClient';

export const dashboardApi = {
  getDashboardData: async (): Promise<ApiResponse<DashboardData>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      await delay(300);
      const mockData = await import('../../data/mockData.json');
      return {
        success: true,
        data: {
          metrics: mockData.default.metrics,
          callsData: mockData.default.callsData,
          statusData: mockData.default.statusData,
          recentCalls: mockData.default.recentCalls as CallRecord[],
          performanceData: mockData.default.performanceData,
          heatmapData: mockData.default.heatmapData,
          conversionData: mockData.default.conversionData,
          campaigns: mockData.default.campaigns,
        },
      };
    }

    return secureHttpClient<DashboardData>(
      SECURITY_CONFIG.ENDPOINTS.DASHBOARD,
      { method: 'GET' }
    );
  },

  getKpiMetrics: async (days: number = 30): Promise<ApiResponse<KpiMetricsResponse>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      await delay(300);
      return {
        success: true,
        data: {
          kpis: {
            roiPercentage: 342,
            roiLabel: '+342%',
            estimatedSavings: 45000,
            estimatedSavingsFormatted: '€45,000.00',
            avgValuePerCall: 127,
            avgValuePerCallFormatted: '€127.00',
            avgValueChangePercent: 15,
            avgValueTrend: 'up',
            qualifiedLeads: 1847,
            conversionRate: 39,
            conversionRateLabel: '39% tasa de calificación',
            avgResponseTimeScore: 80,
            avgResponseTimeFormatted: '0.8s',
            callsUnder2sPct: 95,
            callsUnder2sLabel: '95% bajo 2 segundos',
            totalConversionValue: 234500,
            totalConversionValueFormatted: '€234,500.00',
            conversionChangePercent: 12,
          },
          summary: {
            totalCalls: 4736,
            totalDurationMinutes: 90000,
            avgHandleTimeSeconds: 180,
            periodDays: days,
          },
          period: {
            startDate: new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            endDate: new Date().toISOString().split('T')[0],
          },
        },
      };
    }

    return secureHttpClient<KpiMetricsResponse>(
      `${SECURITY_CONFIG.ENDPOINTS.DASHBOARD_KPI}?days=${days}`,
      { method: 'GET' }
    );
  },

  getCallStatsByPeriod: async (): Promise<ApiResponse<import('../../types').CallStatsByPeriod>> => {
    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.DASHBOARD_CALL_STATS, {
      method: 'GET',
    });
  },


};
