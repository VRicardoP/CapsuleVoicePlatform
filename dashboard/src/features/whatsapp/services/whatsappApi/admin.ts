import { request, qs, WA_BASE } from './client';
import type {
  WAWidgetConfig, WADashboardOverview, WAAuditLogEntry, WAAdminOverview,
} from '../../types';

export const adminApi = {
  // === Widget Web ===

  getWidgetConfig: () =>
    request<WAWidgetConfig>(`${WA_BASE}/widget/config`),

  updateWidgetConfig: (data: Partial<{
    is_active: boolean; primary_color: string; welcome_message: string;
    position: string; auto_open_seconds: number; allowed_domains: string[];
    avatar_url: string; business_name: string; offline_message: string;
  }>) => request<WAWidgetConfig>(`${WA_BASE}/widget/config`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  getWidgetEmbedCode: () =>
    request<{ embed_code: string; tenant_id: string }>(`${WA_BASE}/widget/embed`),

  // === Dashboard Overview ===

  getDashboardOverview: () =>
    request<WADashboardOverview>(`${WA_BASE}/dashboard/overview`),

  // === Audit Logs ===

  getAuditLogs: (params?: { event_type?: string; skip?: number; limit?: number }) =>
    request<{ items: WAAuditLogEntry[]; total: number }>(`${WA_BASE}/audit/logs${qs(params || {})}`),

  // === Admin BSP ===

  getAdminOverview: () =>
    request<WAAdminOverview>(`${WA_BASE}/admin/overview`),
};
