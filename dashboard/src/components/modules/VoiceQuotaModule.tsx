import React from 'react';
import { useSmartPolling } from '../../hooks/useSmartPolling';
import { voiceQuotaApi } from '../../services/api/voiceQuotaApi';
import type { VoiceQuotaStatus } from '../../services/api/voiceQuotaApi';
import VoiceQuotaCard from '../ui/VoiceQuotaCard';

const VoiceQuotaModule: React.FC = () => {
  const { data, loading } = useSmartPolling<VoiceQuotaStatus>(
    () => voiceQuotaApi.getMyStatus(),
    { interval: 60_000 },
  );

  const hasAnyQuota = data?.inbound !== null || data?.outbound !== null;

  if (!loading && data && !hasAnyQuota) {
    return null;
  }

  return (
    <div className="flex flex-col gap-3">
      {(loading || data?.inbound) && (
        <VoiceQuotaCard direction="inbound" status={data?.inbound} loading={loading} accentColor="blue" />
      )}
      {(loading || data?.outbound) && (
        <VoiceQuotaCard direction="outbound" status={data?.outbound} loading={loading} accentColor="orange" />
      )}
    </div>
  );
};

export default VoiceQuotaModule;
