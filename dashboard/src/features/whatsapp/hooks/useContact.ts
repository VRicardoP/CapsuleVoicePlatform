import { useState, useCallback, useRef } from 'react';
import type { WAContactDetail } from '../types';
import { whatsappApi } from '../services/whatsappApi';

export function useContact() {
  const [contact, setContact] = useState<WAContactDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const fetchContact = useCallback(async (contactId: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    try {
      const data = await whatsappApi.getContactDetail(contactId, controller.signal);
      if (controller.signal.aborted) return;
      setContact(data);
    } catch {
      if (controller.signal.aborted) return;
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  const updateContact = useCallback(async (
    contactId: string,
    data: { display_name?: string; email?: string; notes?: string; tag_ids?: string[] },
  ) => {
    const updated = await whatsappApi.updateContact(contactId, data);
    setContact(updated);
    return updated;
  }, []);

  const assignSegments = useCallback(async (contactId: string, segmentIds: string[]) => {
    await whatsappApi.assignContactSegments(contactId, segmentIds);
    await fetchContact(contactId);
  }, [fetchContact]);

  return { contact, loading, fetchContact, updateContact, assignSegments };
}
