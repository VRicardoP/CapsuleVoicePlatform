import { request, voidRequest, jsonPost, jsonPatch, qs, WA_BASE } from './client';
import type { WATemplate, WATemplateListResponse } from '../../types';

export const templateApi = {
  getTemplates: (params?: { status?: string; category?: string; skip?: number; limit?: number }) =>
    request<WATemplateListResponse>(`${WA_BASE}/templates${qs(params || {})}`),

  getTemplate: (templateId: string) =>
    request<WATemplate>(`${WA_BASE}/templates/${templateId}`),

  createTemplate: (data: {
    name: string; language?: string; category?: string;
    body_text: string; header_type?: string; header_content?: string;
    footer?: string; buttons?: Record<string, unknown>; variables?: Record<string, unknown>;
  }) => request<WATemplate>(`${WA_BASE}/templates`, jsonPost(data)),

  updateTemplate: (templateId: string, data: Partial<{
    name: string; body_text: string; footer: string;
    header_type: string; header_content: string;
    buttons: Record<string, unknown>; variables: Record<string, unknown>;
  }>) => request<WATemplate>(`${WA_BASE}/templates/${templateId}`, jsonPatch(data)),

  deleteTemplate: (templateId: string) =>
    voidRequest(`${WA_BASE}/templates/${templateId}`, { method: 'DELETE' }),

  submitTemplate: (templateId: string) =>
    request<WATemplate>(`${WA_BASE}/templates/${templateId}/submit`, { method: 'POST' }),

  syncTemplates: () =>
    request<{ synced: number; created: number; updated: number }>(`${WA_BASE}/templates/sync`, { method: 'POST' }),

  uploadTemplateMedia: (imageUrl: string) =>
    request<{ handle: string }>(`${WA_BASE}/templates/upload-media?image_url=${encodeURIComponent(imageUrl)}`, { method: 'POST' }),
};
