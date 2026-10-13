import { useKpiDataContext } from '../context/DataContext';

/**
 * Hook para acceder a los KPIs avanzados.
 * Suscribe solo al KpiDataContext (no a dashboard, callStats ni GDPR).
 */
export const useKpiData = () => useKpiDataContext();
