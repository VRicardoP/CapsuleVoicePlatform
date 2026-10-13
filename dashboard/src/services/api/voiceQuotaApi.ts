import { createModuleClient } from './moduleClient';

const { request, BASE } = createModuleClient('/api/v1/organizations');

export interface VoiceDirectionStatus {
  limit_minutes: number | null;
  used_minutes: number;
  reserved_minutes: number;
  remaining_minutes: number | null;
  is_exceeded: boolean;
}

export interface VoiceQuotaStatus {
  month_key: string;
  inbound: VoiceDirectionStatus | null;
  outbound: VoiceDirectionStatus | null;
}

export const voiceQuotaApi = {
  getMyStatus: (): Promise<VoiceQuotaStatus> =>
    request<VoiceQuotaStatus>(`${BASE}/me/voice-quota`),
};
