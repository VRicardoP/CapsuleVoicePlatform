/**
 * DataContext - Sistema centralizado de datos del dashboard
 *
 * 4 contextos separados por dominio de datos para evitar re-renders cruzados:
 * - DashboardDataContext: metricas, graficos, llamadas recientes (poll 5s)
 * - CallStatsContext: estadisticas por periodo (poll 5s)
 * - GdprDataContext: cumplimiento, solicitudes, brechas (poll 30s)
 * - KpiDataContext: KPIs avanzados (poll 60s)
 *
 * Cada contexto tiene su propio estado y polling, de modo que una actualizacion
 * en GDPR no re-renderiza los modulos del dashboard y viceversa.
 */

import React, { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo, type ReactNode } from 'react';
import { apiService } from '../services/api';
import type { DashboardData, CallStatsByPeriod, GdprExecutiveSummary, GdprTrendsResponse, GdprDashboardMetrics, KpiMetricsResponse } from '../types';
import { POLLING_INTERVALS } from '../config/pollingConfig';

// =============================================================================
// Generic polling provider factory — eliminates boilerplate repetition
// =============================================================================

interface PollingContextValue<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

function createPollingContext<T>(
  displayName: string,
  fetcher: () => Promise<{ success: boolean; data?: T; error?: string }>,
  interval: number,
) {
  const Ctx = createContext<PollingContextValue<T> | undefined>(undefined);
  Ctx.displayName = displayName;

  const useCtx = () => {
    const ctx = useContext(Ctx);
    if (!ctx) throw new Error(`${displayName} must be used within DataProvider`);
    return ctx;
  };

  const Provider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const firstLoad = useRef(true);

    const fetchData = useCallback(async () => {
      if (firstLoad.current) setLoading(true);
      setError(null);
      const response = await fetcher();
      if (response.success) {
        setData(response.data ?? null);
      } else {
        setError(response.error || 'Error al cargar datos');
      }
      if (firstLoad.current) {
        setLoading(false);
        firstLoad.current = false;
      }
    }, []);

    useEffect(() => {
      fetchData();
      const id = setInterval(fetchData, interval);
      return () => clearInterval(id);
    }, [fetchData]);

    const value = useMemo(() => ({ data, loading, error, refetch: fetchData }), [data, loading, error, fetchData]);

    return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
  };
  Provider.displayName = `${displayName}Provider`;

  return { Provider, useCtx };
}

// =============================================================================
// Dashboard Data Context (REALTIME - 5s)
// =============================================================================

const { Provider: DashboardDataProvider, useCtx: useDashboardDataContext } =
  createPollingContext<DashboardData>('DashboardData', () => apiService.getDashboardData(), POLLING_INTERVALS.REALTIME);
export { useDashboardDataContext };

// =============================================================================
// Call Stats Context (REALTIME - 5s)
// =============================================================================

const { Provider: CallStatsProvider, useCtx: useCallStatsContext } =
  createPollingContext<CallStatsByPeriod>('CallStats', () => apiService.getCallStatsByPeriod(), POLLING_INTERVALS.REALTIME);
export { useCallStatsContext };

// =============================================================================
// KPI Context (STANDARD - 60s)
// =============================================================================

const { Provider: KpiDataProvider, useCtx: useKpiDataContext } =
  createPollingContext<KpiMetricsResponse>('KpiData', () => apiService.getKpiMetrics(30), POLLING_INTERVALS.STANDARD);
export { useKpiDataContext };

// =============================================================================
// GDPR Context (SEMI_REALTIME - 30s) — custom because it fetches 3 endpoints
// =============================================================================

interface GdprDataContextType {
  summary: GdprExecutiveSummary | null;
  trends: GdprTrendsResponse | null;
  metrics: GdprDashboardMetrics | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  refetchTrends: (days?: number) => Promise<void>;
}

const GdprDataContext = createContext<GdprDataContextType | undefined>(undefined);

export const useGdprDataContext = () => {
  const ctx = useContext(GdprDataContext);
  if (!ctx) throw new Error('useGdprDataContext must be used within DataProvider');
  return ctx;
};

const GdprDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [summary, setSummary] = useState<GdprExecutiveSummary | null>(null);
  const [trends, setTrends] = useState<GdprTrendsResponse | null>(null);
  const [metrics, setMetrics] = useState<GdprDashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const firstLoad = useRef(true);

  const fetchData = useCallback(async () => {
    if (firstLoad.current) setLoading(true);
    setError(null);
    try {
      const [summaryRes, metricsRes, trendsRes] = await Promise.all([
        apiService.getGdprExecutiveSummary(),
        apiService.getGdprDashboardMetrics(),
        apiService.getGdprTrends(30),
      ]);
      if (summaryRes.success) setSummary(summaryRes.data);
      if (metricsRes.success) setMetrics(metricsRes.data);
      if (trendsRes.success) setTrends(trendsRes.data);
      if (!summaryRes.success && !metricsRes.success) throw new Error('Error al cargar datos GDPR');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      if (firstLoad.current) { setLoading(false); firstLoad.current = false; }
    }
  }, []);

  const refetchTrends = useCallback(async (days: number = 30) => {
    const response = await apiService.getGdprTrends(days);
    if (response.success) setTrends(response.data);
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, POLLING_INTERVALS.SEMI_REALTIME);
    return () => clearInterval(id);
  }, [fetchData]);

  const value = useMemo(
    () => ({ summary, trends, metrics, loading, error, refetch: fetchData, refetchTrends }),
    [summary, trends, metrics, loading, error, fetchData, refetchTrends]
  );

  return <GdprDataContext.Provider value={value}>{children}</GdprDataContext.Provider>;
};

// =============================================================================
// Composite Provider (wraps all 4 contexts)
// =============================================================================

export const DataProvider: React.FC<{ children: ReactNode }> = ({ children }) => (
  <DashboardDataProvider>
    <CallStatsProvider>
      <GdprDataProvider>
        <KpiDataProvider>
          {children}
        </KpiDataProvider>
      </GdprDataProvider>
    </CallStatsProvider>
  </DashboardDataProvider>
);
