import { useDashboardDataContext } from '../context/DataContext';

/**
 * Hook para acceder a los datos del dashboard.
 * Suscribe solo al DashboardDataContext (no a GDPR, KPI ni CallStats).
 */
export const useDashboardData = () => useDashboardDataContext();
