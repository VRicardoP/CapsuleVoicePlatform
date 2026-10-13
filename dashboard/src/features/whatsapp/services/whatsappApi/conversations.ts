import { request, voidRequest, jsonPost, jsonPatch, qs, WA_BASE } from './client';
import type {
  WAConversationListResponse, WAConversation,
  WAMessageListResponse, WAMessage,
  WAInternalNote, WAInternalNoteListResponse,
  WAMessagingAnalytics,
} from '../../types';

export const conversationApi = {
  // === Conversations ===

  getConversations: (params?: {
    status?: string; skip?: number; limit?: number;
    segment?: string; search?: string; assignee?: string;
    unanswered?: boolean;
  }) => request<WAConversationListResponse>(
    `${WA_BASE}/conversations${qs(params || {})}`
  ),

  getConversation: (conversationId: string) =>
    request<WAConversation>(`${WA_BASE}/conversations/${conversationId}`),

  getMessages: (conversationId: string, params?: { before?: string; limit?: number }, signal?: AbortSignal) =>
    request<WAMessageListResponse>(
      `${WA_BASE}/conversations/${conversationId}/messages${qs(params || {})}`,
      signal ? { signal } : undefined,
    ),

  sendMessage: (conversationId: string, text: string) =>
    request<WAMessage>(`${WA_BASE}/conversations/${conversationId}/messages`, jsonPost({ text })),

  sendTemplate: (conversationId: string, templateId: string) =>
    request<WAMessage>(`${WA_BASE}/conversations/${conversationId}/template`, jsonPost({ template_id: templateId })),

  markAsRead: (conversationId: string) =>
    voidRequest(`${WA_BASE}/conversations/${conversationId}/read`, { method: 'POST' }),

  closeConversation: (conversationId: string) =>
    voidRequest(`${WA_BASE}/conversations/${conversationId}/close`, { method: 'POST' }),

  assignConversation: (conversationId: string, userId: string) =>
    voidRequest(`${WA_BASE}/conversations/${conversationId}/assign`, jsonPost({ user_id: userId })),

  // === Internal Notes ===

  getNotes: (conversationId: string, signal?: AbortSignal) =>
    request<WAInternalNoteListResponse>(`${WA_BASE}/conversations/${conversationId}/notes`, signal ? { signal } : undefined),

  createNote: (conversationId: string, content: string) =>
    request<WAInternalNote>(`${WA_BASE}/conversations/${conversationId}/notes`, jsonPost({ content })),

  updateNote: (conversationId: string, noteId: string, content: string) =>
    request<WAInternalNote>(`${WA_BASE}/conversations/${conversationId}/notes/${noteId}`, jsonPatch({ content })),

  deleteNote: (conversationId: string, noteId: string) =>
    voidRequest(`${WA_BASE}/conversations/${conversationId}/notes/${noteId}`, { method: 'DELETE' }),

  // === Messaging Analytics ===

  getMessagingAnalytics: (days: number = 30) =>
    request<WAMessagingAnalytics>(`${WA_BASE}/analytics/messaging?days=${days}`),
};
