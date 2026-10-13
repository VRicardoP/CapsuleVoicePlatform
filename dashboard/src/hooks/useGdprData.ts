import { useGdprDataContext } from '../context/DataContext';

/**
 * Hook para acceder a los datos GDPR.
 * Suscribe solo al GdprDataContext (no a dashboard, callStats ni KPI).
 */
export const useGdprData = () => useGdprDataContext();
