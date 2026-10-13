import { request, voidRequest, jsonPost, jsonPatch, qs, WA_BASE } from './client';
import type { WACampaign, WACampaignListResponse, WACampaignRecipient } from '../../types';

export const campaignApi = {
  getCampaigns: (params?: { status?: string; skip?: number; limit?: number }) =>
    request<WACampaignListResponse>(`${WA_BASE}/campaigns${qs(params || {})}`),

  getCampaign: (campaignId: string) =>
    request<WACampaign>(`${WA_BASE}/campaigns/${campaignId}`),

  createCampaign: (data: {
    name: string; template_id?: string; catalog_item_id?: string;
    audience_filter?: Record<string, unknown>;
    scheduled_at?: string; is_ab_test?: boolean;
  }) => request<WACampaign>(`${WA_BASE}/campaigns`, jsonPost(data)),

  updateCampaign: (campaignId: string, data: Partial<{
    name: string; template_id: string; catalog_item_id: string;
    audience_filter: Record<string, unknown>; scheduled_at: string;
  }>) => request<WACampaign>(`${WA_BASE}/campaigns/${campaignId}`, jsonPatch(data)),

  deleteCampaign: (campaignId: string) =>
    voidRequest(`${WA_BASE}/campaigns/${campaignId}`, { method: 'DELETE' }),

  startCampaign: (campaignId: string) =>
    request<WACampaign>(`${WA_BASE}/campaigns/${campaignId}/start`, { method: 'POST' }),

  pauseCampaign: (campaignId: string) =>
    request<WACampaign>(`${WA_BASE}/campaigns/${campaignId}/pause`, { method: 'POST' }),

  cancelCampaign: (campaignId: string) =>
    request<WACampaign>(`${WA_BASE}/campaigns/${campaignId}/cancel`, { method: 'POST' }),

  relaunchCampaign: (campaignId: string) =>
    request<WACampaign>(`${WA_BASE}/campaigns/${campaignId}/relaunch`, { method: 'POST' }),

  getCampaignRecipients: (campaignId: string) =>
    request<WACampaignRecipient[]>(`${WA_BASE}/campaigns/${campaignId}/recipients`),
};
