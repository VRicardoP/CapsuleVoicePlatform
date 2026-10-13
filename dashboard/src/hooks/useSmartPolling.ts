/**
 * Smart polling hook with visibility-aware refresh.
 *
 * - Fetches on mount, then at `interval` ms
 * - Pauses when tab is hidden (saves CPU/network)
 * - Refetches immediately when tab becomes visible again
 * - Silent refresh: no loading spinner after first load
 * - Supports manual refetch via returned `refetch` function
 */
import { useState, useEffect, useRef, useCallback } from 'react';

interface UseSmartPollingOptions {
  /** Polling interval in ms (default 30000) */
  interval?: number;
  /** Skip polling entirely (e.g. when a dependency is missing) */
  enabled?: boolean;
}

interface UseSmartPollingResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useSmartPolling<T>(
  fetcher: () => Promise<T>,
  options: UseSmartPollingOptions = {},
): UseSmartPollingResult<T> {
  const { interval = 30_000, enabled = true } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const firstLoad = useRef(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const doFetch = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
      firstLoad.current = false;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  // Initial fetch + interval
  useEffect(() => {
    if (!enabled) return;

    doFetch(false);

    const startPolling = () => {
      stopPolling();
      intervalRef.current = setInterval(() => doFetch(true), interval);
    };

    const stopPolling = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    const handleVisibility = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        doFetch(true); // immediate refresh on return
        startPolling();
      }
    };

    startPolling();
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [doFetch, interval, enabled]);

  const refetch = useCallback(() => doFetch(!firstLoad.current), [doFetch]);

  return { data, loading: loading && firstLoad.current, error, refetch };
}
