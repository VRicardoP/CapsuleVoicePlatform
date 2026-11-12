import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Response shape for paginated API endpoints.
 * Most CapsuleCorp list endpoints return { items: T[], total: number }.
 */
interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

interface UsePaginatedFetchOptions {
  /** Items per page (default 20) */
  pageSize?: number;
  /** Extra filter values that trigger a re-fetch + page reset when changed */
  filters?: Record<string, string | undefined>;
  /** Auto-refresh interval in ms (0 = disabled). Refreshes data silently without showing loading state. */
  refreshInterval?: number;
}

interface UsePaginatedFetchResult<T> {
  items: T[];
  total: number;
  loading: boolean;
  page: number;
  setPage: (pageOrFn: number | ((prev: number) => number)) => void;
  totalPages: number;
  refetch: () => void;
}

/**
 * Shared hook for paginated list endpoints with filters.
 *
 * Includes request versioning to prevent stale responses from overwriting
 * newer data when filters/pages change rapidly.
 *
 * @example
 * const { items, loading, page, setPage, totalPages, refetch } = usePaginatedFetch(
 *   (skip, limit, filters) => api.getCampaigns({ status: filters.status, skip, limit }),
 *   { pageSize: 15, filters: { status: statusFilter } }
 * );
 */
export function usePaginatedFetch<T>(
  fetchFn: (skip: number, limit: number, filters: Record<string, string | undefined>) => Promise<PaginatedResponse<T>>,
  options: UsePaginatedFetchOptions = {},
): UsePaginatedFetchResult<T> {
  const pageSize = options.pageSize ?? 20;
  const filters = options.filters ?? {};

  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPageRaw] = useState(0);

  const totalPages = Math.ceil(total / pageSize);

  // Request versioning: each fetch gets a version number. Only the latest
  // version's response is applied to state, preventing race conditions
  // when filters/page change faster than requests complete.
  const versionRef = useRef(0);

  // Serialize filters for dependency tracking
  const filterKey = JSON.stringify(filters);

  const isFirstLoad = useRef(true);

  const doFetch = useCallback(async (silent = false) => {
    const version = ++versionRef.current;
    if (!silent) setLoading(true);
    try {
      const res = await fetchFn(page * pageSize, pageSize, filters);
      if (version === versionRef.current) {
        setItems(res.items);
        setTotal(res.total);
      }
    } catch (err) {
      if (version === versionRef.current) {
        console.error('usePaginatedFetch error:', err);
      }
    }
    if (version === versionRef.current) {
      setLoading(false);
      isFirstLoad.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filterKey]);

  const setPage = (pageOrFn: number | ((prev: number) => number)) => {
    setPageRaw(typeof pageOrFn === 'function' ? pageOrFn : pageOrFn);
  };

  // Reset page when filters change
  useEffect(() => {
    setPageRaw(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  useEffect(() => {
    doFetch();
  }, [doFetch]);

  // Auto-refresh (silent — no loading spinner)
  const refreshInterval = options.refreshInterval ?? 0;
  useEffect(() => {
    if (!refreshInterval) return;
    const interval = setInterval(() => doFetch(true), refreshInterval);
    return () => clearInterval(interval);
  }, [doFetch, refreshInterval]);

  return { items, total, loading, page, setPage, totalPages, refetch: doFetch };
}
