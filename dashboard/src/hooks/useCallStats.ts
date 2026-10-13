import { useCallStatsContext } from '../context/DataContext';

/**
 * Hook para acceder a las estadisticas de llamadas por periodo.
 * Suscribe solo al CallStatsContext (no a dashboard, GDPR ni KPI).
 */
export const useCallStats = () => useCallStatsContext();
