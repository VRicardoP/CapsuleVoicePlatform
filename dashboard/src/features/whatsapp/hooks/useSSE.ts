import { useEffect, useMemo, useRef } from 'react';

type SSEHandlers = Record<string, (data: any) => void>;

export function useSSE(url: string, handlers: SSEHandlers) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  // Re-subscribe when the set of event names changes
  const eventNamesKey = useMemo(
    () => Object.keys(handlers).sort().join(','),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [Object.keys(handlers).sort().join(',')]
  );

  useEffect(() => {
    const eventSource = new EventSource(url, { withCredentials: true });

    const eventNames = Object.keys(handlersRef.current);
    const listeners: Array<[string, (e: Event) => void]> = [];

    for (const eventName of eventNames) {
      const listener = (e: Event) => {
        const me = e as MessageEvent;
        let data: any;
        try {
          data = JSON.parse(me.data);
        } catch {
          console.warn('[SSE] Failed to parse event data:', eventName, me.data);
          return;
        }
        try {
          handlersRef.current[eventName]?.(data);
        } catch (err) {
          console.error('[SSE] Handler error for', eventName, err);
        }
      };
      eventSource.addEventListener(eventName, listener);
      listeners.push([eventName, listener]);
    }

    eventSource.onerror = (e) => {
      console.warn('[SSE] Connection error, readyState:', eventSource.readyState, e);
    };

    return () => {
      for (const [name, listener] of listeners) {
        eventSource.removeEventListener(name, listener);
      }
      eventSource.close();
    };
  }, [url, eventNamesKey]);
}
