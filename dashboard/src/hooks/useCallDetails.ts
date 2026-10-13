import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import type { CallRecord, Transcription, AutomatedAction } from '../types';

export const useCallDetails = (callId: string | null) => {
  const [call, setCall] = useState<CallRecord | null>(null);
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [actions, setActions] = useState<AutomatedAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!callId) {
      setCall(null);
      setTranscriptions([]);
      setActions([]);
      return;
    }

    const fetchCallDetails = async () => {
      setLoading(true);
      setError(null);

      const response = await apiService.getCallDetails(callId);

      if (response.success) {
        setCall(response.data.call);
        setTranscriptions(response.data.transcriptions);
        setActions(response.data.actions);
      } else {
        setError(response.error || 'Error al cargar los detalles');
      }

      setLoading(false);
    };

    fetchCallDetails();
  }, [callId]);

  return { call, transcriptions, actions, loading, error };
};