import { request, voidRequest, jsonPost, jsonPatch, qs, WA_BASE } from './client';
import type {
  WASegment, WASegmentListResponse,
  WATag, WATagListResponse,
  WAContactDetail, WAAgent, WAConversation,
} from '../../types';

export const contactApi = {
  // === Segments ===

  getSegments: () => request<WASegmentListResponse>(`${WA_BASE}/segments`),

  createSegment: (data: { name: string; color?: string; icon?: string; description?: string }) =>
    request<WASegment>(`${WA_BASE}/segments`, jsonPost(data)),

  updateSegment: (segmentId: string, data: Partial<{ name: string; color: string; sort_order: number }>) =>
    request<WASegment>(`${WA_BASE}/segments/${segmentId}`, jsonPatch(data)),

  deleteSegment: (segmentId: string) =>
    voidRequest(`${WA_BASE}/segments/${segmentId}`, { method: 'DELETE' }),

  assignContactSegments: (contactId: string, segmentIds: string[]) =>
    voidRequest(`${WA_BASE}/contacts/${contactId}/segments`, jsonPost({ segment_ids: segmentIds })),

  // === Tags ===

  getTags: () => request<WATagListResponse>(`${WA_BASE}/tags`),

  createTag: (data: { name: string; color?: string }) =>
    request<WATag>(`${WA_BASE}/tags`, jsonPost(data)),

  updateTag: (tagId: string, data: { name: string; color: string }) =>
    request<WATag>(`${WA_BASE}/tags/${tagId}`, jsonPatch(data)),

  deleteTag: (tagId: string) =>
    voidRequest(`${WA_BASE}/tags/${tagId}`, { method: 'DELETE' }),

  // === Contacts ===

  getContacts: (params?: { search?: string; segment?: string; tag?: string; skip?: number; limit?: number }) =>
    request<{ items: WAContactDetail[]; total: number }>(
      `${WA_BASE}/contacts${qs(params || {})}`
    ),

  getContactDetail: (contactId: string, signal?: AbortSignal) =>
    request<WAContactDetail>(`${WA_BASE}/contacts/${contactId}`, signal ? { signal } : undefined),

  createContact: (data: { phone_e164: string; display_name?: string; email?: string; notes?: string }) =>
    request<WAContactDetail>(`${WA_BASE}/contacts`, jsonPost(data)),

  updateContact: (contactId: string, data: {
    display_name?: string; email?: string; notes?: string; tag_ids?: string[];
  }) => request<WAContactDetail>(`${WA_BASE}/contacts/${contactId}`, jsonPatch(data)),

  deleteContact: (contactId: string) =>
    voidRequest(`${WA_BASE}/contacts/${contactId}`, { method: 'DELETE' }),

  startConversation: (contactId: string) =>
    request<WAConversation>(`${WA_BASE}/contacts/${contactId}/conversation`, { method: 'POST' }),

  // === Agents ===

  getAgents: () => request<WAAgent[]>(`${WA_BASE}/agents`),

  // === Bulk Operations ===

  bulkAssignSegments: (contactIds: string[], segmentIds: string[]) =>
    voidRequest(`${WA_BASE}/contacts/bulk/segments`, jsonPost({ contact_ids: contactIds, segment_ids: segmentIds })),

  // === Auto-Assignment ===

  getAutoAssignSettings: () =>
    request<{ enabled: boolean; agent_ids: string[] }>(`${WA_BASE}/auto-assign/settings`),

  setAutoAssignSettings: (data: { enabled: boolean; agent_ids: string[] }) =>
    voidRequest(`${WA_BASE}/auto-assign/settings`, jsonPost(data)),
};
