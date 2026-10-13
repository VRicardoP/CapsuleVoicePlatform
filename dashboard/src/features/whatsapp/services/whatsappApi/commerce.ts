import { request, voidRequest, jsonPost, jsonPatch, qs, WA_BASE } from './client';
import type {
  WAPipelineStage, WADeal, WADealListResponse, WAPipelineAnalytics,
  WACatalogItem, WACatalogItemListResponse,
  WAOrder, WAOrderListResponse,
} from '../../types';

export const commerceApi = {
  // === Pipeline ===

  getPipelineStages: () =>
    request<WAPipelineStage[]>(`${WA_BASE}/pipeline/stages`),

  createPipelineStage: (data: { name: string; color?: string; sort_order?: number; is_won?: boolean; is_lost?: boolean }) =>
    request<WAPipelineStage>(`${WA_BASE}/pipeline/stages`, jsonPost(data)),

  updatePipelineStage: (stageId: string, data: Partial<{ name: string; color: string; sort_order: number }>) =>
    request<WAPipelineStage>(`${WA_BASE}/pipeline/stages/${stageId}`, jsonPatch(data)),

  deletePipelineStage: (stageId: string) =>
    voidRequest(`${WA_BASE}/pipeline/stages/${stageId}`, { method: 'DELETE' }),

  getDeals: (params?: { stage?: string; skip?: number; limit?: number }) =>
    request<WADealListResponse>(`${WA_BASE}/pipeline/deals${qs(params || {})}`),

  createDeal: (data: {
    stage_id: string; title: string; contact_id?: string; value?: number;
    currency?: string; assignee_user_id?: string; expected_close_date?: string; notes?: string;
  }) => request<WADeal>(`${WA_BASE}/pipeline/deals`, jsonPost(data)),

  updateDeal: (dealId: string, data: Partial<{
    stage_id: string; title: string; value: number; notes: string;
    assignee_user_id: string; expected_close_date: string;
  }>) => request<WADeal>(`${WA_BASE}/pipeline/deals/${dealId}`, jsonPatch(data)),

  moveDeal: (dealId: string, stageId: string) =>
    request<WADeal>(`${WA_BASE}/pipeline/deals/${dealId}/move`, jsonPost({ stage_id: stageId })),

  deleteDeal: (dealId: string) =>
    voidRequest(`${WA_BASE}/pipeline/deals/${dealId}`, { method: 'DELETE' }),

  getPipelineAnalytics: () =>
    request<WAPipelineAnalytics>(`${WA_BASE}/pipeline/analytics`),

  // === Catalog ===

  getCatalogItems: (params?: { status?: string; category?: string; search?: string; skip?: number; limit?: number }) =>
    request<WACatalogItemListResponse>(`${WA_BASE}/catalog${qs(params || {})}`),

  getCatalogItem: (itemId: string) =>
    request<WACatalogItem>(`${WA_BASE}/catalog/${itemId}`),

  createCatalogItem: (data: {
    name: string; price: number; description?: string; currency?: string;
    image_url?: string; product_url?: string; category?: string; sku?: string; stock?: number;
  }) => request<WACatalogItem>(`${WA_BASE}/catalog`, jsonPost(data)),

  updateCatalogItem: (itemId: string, data: Partial<{
    name: string; price: number; description: string; status: string;
    image_url: string; product_url: string; category: string; sku: string; stock: number;
  }>) => request<WACatalogItem>(`${WA_BASE}/catalog/${itemId}`, jsonPatch(data)),

  deleteCatalogItem: (itemId: string) =>
    voidRequest(`${WA_BASE}/catalog/${itemId}`, { method: 'DELETE' }),

  // === Orders ===

  getOrders: (params?: { status?: string; skip?: number; limit?: number }) =>
    request<WAOrderListResponse>(`${WA_BASE}/orders${qs(params || {})}`),

  getOrder: (orderId: string) =>
    request<WAOrder>(`${WA_BASE}/orders/${orderId}`),

  createOrder: (data: {
    contact_id?: string; conversation_id?: string; notes?: string;
    items: { name: string; catalog_item_id?: string; quantity: number; unit_price: number }[];
  }) => request<WAOrder>(`${WA_BASE}/orders`, jsonPost(data)),

  updateOrder: (orderId: string, data: { status?: string; notes?: string }) =>
    request<WAOrder>(`${WA_BASE}/orders/${orderId}`, jsonPatch(data)),

  // === Export CSV ===

  exportContactsCsvUrl: () => `${WA_BASE}/contacts/export`,

  exportDealsCsvUrl: () => `${WA_BASE}/pipeline/deals/export`,
};
