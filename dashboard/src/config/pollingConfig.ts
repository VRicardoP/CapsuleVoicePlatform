/**
 * Configuración de intervalos de polling para auto-actualización de módulos.
 *
 * Estrategia de actualización:
 * - REALTIME: Para datos que incluyen llamadas en curso (5s)
 * - SEMI_REALTIME: Para alertas y solicitudes activas (30s)
 * - STANDARD: Para datos históricos agregados (60s)
 * - SLOW: Para datos que cambian muy poco (5 min)
 *
 * Esta configuración minimiza la carga en la base de datos mientras
 * mantiene los datos relevantes actualizados.
 */

export const POLLING_INTERVALS = {
  /** Tiempo real: llamadas en curso, últimas llamadas (5 segundos) */
  REALTIME: 5000,

  /** Semi-tiempo real: alertas GDPR, solicitudes pendientes (30 segundos) */
  SEMI_REALTIME: 30000,

  /** Estándar: métricas agregadas, gráficos (60 segundos) */
  STANDARD: 60000,

  /** Lento: datos históricos que cambian poco (5 minutos) */
  SLOW: 300000,

  /** Sin auto-actualización */
  DISABLED: 0,
} as const;

export type PollingInterval = typeof POLLING_INTERVALS[keyof typeof POLLING_INTERVALS];

/**
 * Mapeo de hooks a sus intervalos de actualización recomendados.
 *
 * Clasificación por tipo de datos:
 *
 * REALTIME (5s):
 * - useDashboardData: incluye recentCalls con llamadas en curso
 * - useCallStats: estadísticas del día actual que cambian con cada llamada
 *
 * SEMI_REALTIME (30s):
 * - useGdprData: solicitudes ARCO pendientes y alertas de brechas
 *
 * STANDARD (60s):
 * - useKpiData: KPIs calculados sobre períodos largos (30 días)
 */
export const HOOK_POLLING_INTERVALS = {
  useDashboardData: POLLING_INTERVALS.REALTIME,
  useCallStats: POLLING_INTERVALS.REALTIME,
  useGdprData: POLLING_INTERVALS.SEMI_REALTIME,
  useKpiData: POLLING_INTERVALS.STANDARD,
} as const;
