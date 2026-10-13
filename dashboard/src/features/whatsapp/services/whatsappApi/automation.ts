import { request, voidRequest, jsonPost, jsonPatch, qs, WA_BASE } from './client';
import type {
  WAMacro, WASlaPolicy, WASlaBreach,
  WAWebhookConfig, WAWebhookLog,
  WASurvey, WASurveyAnswer,
  WAFlow, WAIntegration,
} from '../../types';

export const automationApi = {
  // === Macros ===

  getMacros: (category?: string) =>
    request<WAMacro[]>(`${WA_BASE}/macros${qs({ category })}`),

  createMacro: (data: { name: string; shortcut?: string; text: string; category?: string }) =>
    request<WAMacro>(`${WA_BASE}/macros`, jsonPost(data)),

  updateMacro: (macroId: string, data: Partial<{ name: string; shortcut: string; text: string; category: string; sort_order: number }>) =>
    request<WAMacro>(`${WA_BASE}/macros/${macroId}`, jsonPatch(data)),

  deleteMacro: (macroId: string) =>
    voidRequest(`${WA_BASE}/macros/${macroId}`, { method: 'DELETE' }),

  // === SLA ===

  getSlaPolicies: () =>
    request<WASlaPolicy[]>(`${WA_BASE}/sla/policies`),

  createSlaPolicy: (data: {
    name: string; first_response_minutes?: number; resolution_minutes?: number;
    priority?: string; escalation_email?: string; business_hours_only?: boolean;
  }) => request<WASlaPolicy>(`${WA_BASE}/sla/policies`, jsonPost(data)),

  updateSlaPolicy: (policyId: string, data: Partial<{
    name: string; first_response_minutes: number; resolution_minutes: number;
    is_active: boolean; escalation_email: string;
  }>) => request<WASlaPolicy>(`${WA_BASE}/sla/policies/${policyId}`, jsonPatch(data)),

  deleteSlaPolicy: (policyId: string) =>
    voidRequest(`${WA_BASE}/sla/policies/${policyId}`, { method: 'DELETE' }),

  getSlaBreaches: (params?: { policy_id?: string; skip?: number; limit?: number }) =>
    request<{ items: WASlaBreach[]; total: number }>(`${WA_BASE}/sla/breaches${qs(params || {})}`),

  // === Webhooks ===

  getWebhookConfigs: () =>
    request<WAWebhookConfig[]>(`${WA_BASE}/webhooks/configs`),

  createWebhookConfig: (data: {
    name: string; url: string; events: string[];
    secret?: string; headers?: Record<string, string>;
  }) => request<WAWebhookConfig>(`${WA_BASE}/webhooks/configs`, jsonPost(data)),

  updateWebhookConfig: (webhookId: string, data: Partial<{
    name: string; url: string; events: string[];
    is_active: boolean; secret: string; headers: Record<string, string>;
  }>) => request<WAWebhookConfig>(`${WA_BASE}/webhooks/configs/${webhookId}`, jsonPatch(data)),

  deleteWebhookConfig: (webhookId: string) =>
    voidRequest(`${WA_BASE}/webhooks/configs/${webhookId}`, { method: 'DELETE' }),

  getWebhookLogs: (webhookId: string, params?: { skip?: number; limit?: number }) =>
    request<{ items: WAWebhookLog[]; total: number }>(`${WA_BASE}/webhooks/configs/${webhookId}/logs${qs(params || {})}`),

  testWebhook: (webhookId: string) =>
    request<{ success: boolean; status_code?: number; error?: string }>(`${WA_BASE}/webhooks/configs/${webhookId}/test`, { method: 'POST' }),

  // === Surveys ===

  getSurveys: (params?: { skip?: number; limit?: number }) =>
    request<{ items: WASurvey[]; total: number }>(`${WA_BASE}/surveys${qs(params || {})}`),

  createSurvey: (data: {
    name: string; survey_type?: string;
    questions?: Record<string, unknown>; trigger?: string;
  }) => request<WASurvey>(`${WA_BASE}/surveys`, jsonPost(data)),

  updateSurvey: (surveyId: string, data: Partial<{
    name: string; questions: Record<string, unknown>;
    trigger: string; is_active: boolean;
  }>) => request<WASurvey>(`${WA_BASE}/surveys/${surveyId}`, jsonPatch(data)),

  deleteSurvey: (surveyId: string) =>
    voidRequest(`${WA_BASE}/surveys/${surveyId}`, { method: 'DELETE' }),

  getSurveyResponses: (surveyId: string, params?: { skip?: number; limit?: number }) =>
    request<{ items: WASurveyAnswer[]; total: number }>(`${WA_BASE}/surveys/${surveyId}/responses${qs(params || {})}`),

  // === Flows ===

  getFlows: (params?: { skip?: number; limit?: number }) =>
    request<{ items: WAFlow[]; total: number }>(`${WA_BASE}/flows${qs(params || {})}`),

  createFlow: (data: {
    name: string; description?: string; trigger_type?: string;
    trigger_config?: Record<string, unknown>; steps?: Record<string, unknown>;
  }) => request<WAFlow>(`${WA_BASE}/flows`, jsonPost(data)),

  updateFlow: (flowId: string, data: Partial<{
    name: string; description: string; trigger_type: string;
    trigger_config: Record<string, unknown>; steps: Record<string, unknown>; is_active: boolean;
  }>) => request<WAFlow>(`${WA_BASE}/flows/${flowId}`, jsonPatch(data)),

  deleteFlow: (flowId: string) =>
    voidRequest(`${WA_BASE}/flows/${flowId}`, { method: 'DELETE' }),

  activateFlow: (flowId: string) =>
    request<WAFlow>(`${WA_BASE}/flows/${flowId}/activate`, { method: 'POST' }),

  // === Integrations ===

  getIntegrations: () =>
    request<{ items: WAIntegration[]; total: number }>(`${WA_BASE}/integrations`),

  createIntegration: (data: {
    integration_type: string; name: string; config?: Record<string, unknown>;
  }) => request<WAIntegration>(`${WA_BASE}/integrations`, jsonPost(data)),

  updateIntegration: (integrationId: string, data: Partial<{
    name: string; config: Record<string, unknown>; is_active: boolean;
  }>) => request<WAIntegration>(`${WA_BASE}/integrations/${integrationId}`, jsonPatch(data)),

  deleteIntegration: (integrationId: string) =>
    voidRequest(`${WA_BASE}/integrations/${integrationId}`, { method: 'DELETE' }),

  testIntegration: (integrationId: string) =>
    request<{ success: boolean; status_code?: number; error?: string; message?: string }>(`${WA_BASE}/integrations/${integrationId}/test`, { method: 'POST' }),
};
