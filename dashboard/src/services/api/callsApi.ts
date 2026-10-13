import type { CallRecord, Transcription, AutomatedAction, ApiResponse } from '../../types';
import { SECURITY_CONFIG } from './config';
import { secureHttpClient, delay } from './httpClient';

export const callsApi = {
  getCalls: async (filters?: {
    startDate?: string;
    endDate?: string;
    status?: string;
    sentiment?: string;
    page?: number;
    limit?: number;
  }): Promise<ApiResponse<{ calls: CallRecord[]; total: number; page: number }>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      await delay(200);
      const mockData = await import('../../data/mockData.json');
      let calls = mockData.default.recentCalls as CallRecord[];
      if (filters?.status) {
        calls = calls.filter(call => call.status === filters.status);
      }
      return { success: true, data: { calls, total: calls.length, page: filters?.page || 1 } };
    }

    const queryParams = new URLSearchParams(
      Object.entries(filters || {})
        .filter(([_, value]) => value !== undefined)
        .map(([key, value]) => [key, String(value)])
    ).toString();

    return secureHttpClient<{ calls: CallRecord[]; total: number; page: number }>(
      `${SECURITY_CONFIG.ENDPOINTS.CALLS}?${queryParams}`,
      { method: 'GET' }
    );
  },

  getCallDetails: async (
    callId: string
  ): Promise<ApiResponse<{
    call: CallRecord;
    transcriptions: Transcription[];
    actions: AutomatedAction[];
  }>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      await delay(200);
      const mockData = await import('../../data/mockData.json');
      const call = mockData.default.recentCalls.find((c: any) => c.id === callId);
      if (!call) {
        return { success: false, data: null as any, error: 'Llamada no encontrada' };
      }
      return {
        success: true,
        data: {
          call: call as CallRecord,
          transcriptions: mockData.default.transcriptions.filter(
            (t: any) => t.callId === callId
          ) as Transcription[],
          actions: mockData.default.actions.filter(
            (a: any) => a.callId === callId
          ) as AutomatedAction[],
        },
      };
    }

    const endpoint = SECURITY_CONFIG.ENDPOINTS.CALL_DETAILS.replace(':id', callId);
    return secureHttpClient(endpoint, { method: 'GET' });
  },

  getCallTranscription: async (callId: string): Promise<ApiResponse<{
    transcription: Array<{
      timestamp: string;
      speaker: string;
      text: string;
      hasPii?: boolean;
    }>;
  }>> => {
    const endpoint = SECURITY_CONFIG.ENDPOINTS.CALL_TRANSCRIPTION.replace(':id', callId);
    return secureHttpClient(endpoint, { method: 'GET' });
  },

  requestHumanReview: async (
    callId: string,
    data: { reason: string; notes?: string }
  ): Promise<ApiResponse<{ message: string; review_id: string }>> => {
    const endpoint = SECURITY_CONFIG.ENDPOINTS.CALL_HUMAN_REVIEW.replace(':id', callId);
    return secureHttpClient(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
