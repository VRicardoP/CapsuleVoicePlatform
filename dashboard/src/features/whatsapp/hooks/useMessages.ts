import { useState, useCallback, useRef } from 'react';
import type { WAMessage } from '../types';
import { whatsappApi } from '../services/whatsappApi';

/**
 * Manages messages for the active conversation.
 *
 * Race-condition strategy (rapid chat switching):
 *  1. AbortController cancels the in-flight HTTP request.
 *  2. `activeRef` holds the conv ID we actually want — stale responses
 *     whose convId doesn't match are silently discarded.
 *  3. A per-conversation cache shows previous messages instantly so the
 *     panel is never blank while the fresh fetch is in-flight.
 */
export function useMessages(conversationId: string | null) {
  void conversationId;
  const [messages, setMessages] = useState<WAMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const activeRef = useRef<string | null>(null);
  const requestSeqRef = useRef(0);
  const cacheRef = useRef(new Map<string, WAMessage[]>());

  const fetchMessages = useCallback(async (convId: string) => {
    // 1. Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestSeq = ++requestSeqRef.current;

    // 2. Mark as the conversation we care about
    activeRef.current = convId;

    // 3. Show cached messages instantly (prevents blank screen)
    const cached = cacheRef.current.get(convId);
    setMessages(cached ?? []);
    setHasMore(false);
    setNextCursor(null);
    setLoading(true);

    try {
      const data = await whatsappApi.getMessages(convId, undefined, controller.signal);

      // Guard: only apply if still the active conversation
      if (
        controller.signal.aborted ||
        activeRef.current !== convId ||
        requestSeqRef.current !== requestSeq
      ) return;

      setMessages(data.items);
      setHasMore(data.has_more);
      setNextCursor(data.next_cursor);

      // Update cache (cap at 30 conversations)
      cacheRef.current.set(convId, data.items);
      if (cacheRef.current.size > 30) {
        const oldest = cacheRef.current.keys().next().value;
        if (oldest) cacheRef.current.delete(oldest);
      }
    } catch {
      if (
        controller.signal.aborted ||
        activeRef.current !== convId ||
        requestSeqRef.current !== requestSeq
      ) return;

      // Retry once for transient network/API failures that may happen
      // during very fast chat switches.
      try {
        const retryData = await whatsappApi.getMessages(convId, undefined, controller.signal);
        if (
          controller.signal.aborted ||
          activeRef.current !== convId ||
          requestSeqRef.current !== requestSeq
        ) return;

        setMessages(retryData.items);
        setHasMore(retryData.has_more);
        setNextCursor(retryData.next_cursor);

        cacheRef.current.set(convId, retryData.items);
        if (cacheRef.current.size > 30) {
          const oldest = cacheRef.current.keys().next().value;
          if (oldest) cacheRef.current.delete(oldest);
        }
      } catch {
        // Keep cached/previous state when retry also fails.
      }
    } finally {
      if (
        !controller.signal.aborted &&
        activeRef.current === convId &&
        requestSeqRef.current === requestSeq
      ) {
        setLoading(false);
      }
    }
  }, []);

  const loadMore = useCallback(async () => {
    const convId = activeRef.current;
    if (!convId || !hasMore || !nextCursor) return;

    try {
      const data = await whatsappApi.getMessages(convId, { before: nextCursor });
      if (activeRef.current !== convId) return;
      setMessages(prev => {
        const updated = [...data.items, ...prev];
        cacheRef.current.set(convId, updated);
        return updated;
      });
      setHasMore(data.has_more);
      setNextCursor(data.next_cursor);
    } catch {
      // silently ignored
    }
  }, [hasMore, nextCursor]);

  const addMessage = useCallback((message: WAMessage) => {
    setMessages(prev => {
      if (prev.some(m => m.id === message.id)) return prev;
      // Insert in chronological position, NOT blindly at the end. A message
      // that arrives over SSE while the agent is typing can be older than the
      // reply they are about to send; appending it would show an order that
      // contradicts the server's (which sorts by created_at), so the message
      // appeared to "jump above" the reply on the next reload.
      const updated = [...prev, message].sort((a, b) =>
        a.created_at.localeCompare(b.created_at),
      );
      // Keep cache in sync
      if (activeRef.current) cacheRef.current.set(activeRef.current, updated);
      return updated;
    });
  }, []);

  const updateMessageStatus = useCallback((messageId: string, status: string, timestamp: string) => {
    setMessages(prev =>
      prev.map(m => {
        if (m.id !== messageId) return m;
        const updates: Partial<WAMessage> = { delivery_status: status as WAMessage['delivery_status'] };
        if (status === 'delivered') updates.delivered_at = timestamp;
        if (status === 'read') updates.read_at = timestamp;
        return { ...m, ...updates };
      })
    );
  }, []);

  return {
    messages,
    loading,
    hasMore,
    fetchMessages,
    loadMore,
    addMessage,
    updateMessageStatus,
  };
}
