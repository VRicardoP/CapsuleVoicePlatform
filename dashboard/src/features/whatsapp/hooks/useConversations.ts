import { useState, useEffect, useCallback, useRef } from 'react';
import type { WAConversation } from '../types';
import { whatsappApi } from '../services/whatsappApi';

/** True when the customer wrote last and we have not replied yet. */
export function isUnanswered(c: WAConversation): boolean {
  if (!c.last_inbound_at) return false;
  if (!c.last_outbound_at) return true;
  return c.last_inbound_at > c.last_outbound_at;
}

/** Sort: unanswered conversations first, then by most recent activity. */
function sortConversations(list: WAConversation[]): WAConversation[] {
  return [...list].sort((a, b) => {
    const aRank = isUnanswered(a) ? 0 : 1;
    const bRank = isUnanswered(b) ? 0 : 1;
    if (aRank !== bRank) return aRank - bRank;
    const aTime = a.last_message_at || a.updated_at;
    const bTime = b.last_message_at || b.updated_at;
    return bTime.localeCompare(aTime);
  });
}

// Initial page size and increment for "load more". Inboxes can hold hundreds
// of conversations (some tenants exceed 750), asi que una pagina por
// debajo del total hacia que una conversacion recien respondida cayera fuera
// de la ventana cargada y "desapareciera" de la lista.
const PAGE_SIZE = 1000;

export function useConversations(
  segmentId: string | null = null,
  unanswered: boolean = false,
  /** Conversacion abierta ahora mismo: nunca debe desaparecer bajo el agente. */
  activeId: string | null = null,
) {
  const [conversations, setConversations] = useState<WAConversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  // How many conversations we are currently requesting. Grows with "load more".
  // A ref mirrors it so SSE-triggered refetches reuse the expanded window
  // instead of collapsing back to the first page.
  const [limit, setLimit] = useState(PAGE_SIZE);
  const limitRef = useRef(limit);
  limitRef.current = limit;

  // Refs to always read the latest filter values (avoids stale closures in SSE/callbacks)
  const segmentIdRef = useRef(segmentId);
  segmentIdRef.current = segmentId;
  const unansweredRef = useRef(unanswered);
  unansweredRef.current = unanswered;

  // "Pinned" conversations: ones we have just replied to. A reply makes a
  // conversation drop in rank (answered sorts below unanswered) or leave the
  // "unanswered" filter, so a later refetch (e.g. triggered by an SSE event)
  // would make it vanish from view while the agent is still working on it.
  // We keep pinned conversations visible across refetches until the agent
  // changes the view (segment/filter) or reloads. Ref drives the merge logic;
  // state drives re-render of the "respondida" marker.
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const pinnedRef = useRef(pinnedIds);
  pinnedRef.current = pinnedIds;

  // La conversacion abierta se protege igual que una pineada.
  const activeIdRef = useRef(activeId);
  activeIdRef.current = activeId;

  const pinConversation = useCallback((id: string) => {
    setPinnedIds(prev => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }, []);

  // `spinner` controls the full-list loading state. We only want it on the
  // initial load / view change — NOT on SSE-triggered refetches, which would
  // otherwise blank the whole list on every background event.
  const fetchConversations = useCallback(async (opts?: { spinner?: boolean }) => {
    if (opts?.spinner) setLoading(true);
    try {
      const currentSegment = segmentIdRef.current;
      const currentUnanswered = unansweredRef.current;
      const params: { segment?: string; unanswered?: boolean; limit?: number } = {
        limit: limitRef.current,
      };
      if (currentSegment) params.segment = currentSegment;
      if (currentUnanswered) params.unanswered = true;
      const data = await whatsappApi.getConversations(params);
      // Ignore stale responses if filters changed during fetch
      if (
        segmentIdRef.current !== currentSegment ||
        unansweredRef.current !== currentUnanswered
      ) return;
      setTotal(data.total);
      // Merge: keep pinned (just-replied) conversations visible even if the
      // server no longer returns them (dropped by the unanswered filter or
      // pushed past the page limit by the answered-last ranking).
      setConversations(prev => {
        const pins = pinnedRef.current;
        const openId = activeIdRef.current;
        if (pins.size === 0 && !openId) return sortConversations(data.items);
        const freshIds = new Set(data.items.map(c => c.id));
        const keep = (c: WAConversation) =>
          (pins.has(c.id) || c.id === openId) && !freshIds.has(c.id);
        const survivors = prev.filter(keep);
        return sortConversations(
          survivors.length ? [...data.items, ...survivors] : data.items,
        );
      });
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      if (opts?.spinner) setLoading(false);
    }
  }, []);

  // Load the next page by growing the requested window and refetching.
  const loadMore = useCallback(async () => {
    const next = limitRef.current + PAGE_SIZE;
    limitRef.current = next;
    setLimit(next);
    setLoadingMore(true);
    try {
      await fetchConversations();
    } finally {
      setLoadingMore(false);
    }
  }, [fetchConversations]);

  // Refetch when filters change. Changing the view (segment/filter) is an
  // explicit user action, so we drop the pins and reset paging — the agent is
  // no longer looking at the conversations they had replied to before.
  useEffect(() => {
    pinnedRef.current = new Set();
    setPinnedIds(new Set());
    limitRef.current = PAGE_SIZE;
    setLimit(PAGE_SIZE);
    fetchConversations({ spinner: true });
  }, [segmentId, unanswered, fetchConversations]);

  const updateConversationFromSSE = useCallback((conversationId: string, changes: Partial<WAConversation>) => {
    setConversations(prev =>
      sortConversations(prev.map(c => c.id === conversationId ? { ...c, ...changes } : c))
    );
  }, []);

  const addOrUpdateMessagePreview = useCallback((
    conversationId: string,
    text: string | null,
    timestamp: string,
    direction: 'inbound' | 'outbound' = 'inbound',
    isFromAi: boolean = false,
  ) => {
    setConversations(prev => {
      const updated = prev.map(c => {
        if (c.id !== conversationId) return c;
        // Una respuesta automatica (flujo/IA) NO cuenta como atendida por el
        // centro: el backend tampoco actualiza last_outbound_at para ellas.
        // Si la contaramos, la conversacion saldria del filtro "sin responder"
        // en local y volveria a entrar en el siguiente refetch del servidor
        // (el "desaparece y reaparece" que reportaban los centros).
        const countsAsReply = direction === 'outbound' && !isFromAi;
        return {
          ...c,
          last_message_text: text,
          last_message_at: timestamp,
          updated_at: timestamp,
          last_inbound_at: direction === 'inbound' ? timestamp : c.last_inbound_at,
          last_outbound_at: countsAsReply ? timestamp : c.last_outbound_at,
        };
      });
      return sortConversations(updated);
    });
  }, []);

  return {
    conversations,
    loading,
    loadingMore,
    error,
    total,
    hasMore: limit < total,
    loadMore,
    refetch: fetchConversations,
    updateConversationFromSSE,
    addOrUpdateMessagePreview,
    pinnedIds,
    pinConversation,
  };
}
