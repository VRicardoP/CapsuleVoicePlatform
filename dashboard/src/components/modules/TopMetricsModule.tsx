import React from 'react';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useKpiData } from '../../hooks/useKpiData';

const TopMetricsModule: React.FC = () => {
  const { data, loading, error, refetch } = useKpiData();

  if (loading) {
    return (
      <ModuleWrapper title="Metricas Avanzadas" icon="📊">
        <LoadingSpinner />
      </ModuleWrapper>
    );
  }

  if (error) {
    return (
      <ModuleWrapper title="Metricas Avanzadas" icon="📊">
        <ErrorMessage message={error} onRetry={refetch} />
      </ModuleWrapper>
    );
  }

  if (!data) return null;

  const { kpis } = data;

  return (
    <ModuleWrapper title="Metricas Avanzadas" icon="📊">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-900 rounded-lg p-4">
          <h4 className="text-sm text-gray-400 mb-2">ROI de la IA</h4>
          <p className="text-2xl font-bold text-green-400">{kpis.roiLabel}</p>
          <p className="text-xs text-gray-500 mt-1">{kpis.estimatedSavingsFormatted} ahorrados este mes</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-4">
          <h4 className="text-sm text-gray-400 mb-2">Valor Medio por Llamada</h4>
          <p className="text-2xl font-bold text-blue-400">{kpis.avgValuePerCallFormatted}</p>
          <p className="text-xs text-gray-500 mt-1">
            {kpis.avgValueTrend === 'up' ? '↑' : '↓'} {Math.abs(kpis.avgValueChangePercent)}% vs mes anterior
          </p>
        </div>
        <div className="bg-gray-900 rounded-lg p-4">
          <h4 className="text-sm text-gray-400 mb-2">Leads Calificados</h4>
          <p className="text-2xl font-bold text-purple-400">{kpis.qualifiedLeads.toLocaleString()}</p>
          <p className="text-xs text-gray-500 mt-1">{kpis.conversionRateLabel}</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-4">
          <h4 className="text-sm text-gray-400 mb-2">Tiempo Respuesta Medio</h4>
          <p className="text-2xl font-bold text-cyan-400">{kpis.avgResponseTimeFormatted}</p>
          <p className="text-xs text-gray-500 mt-1">{kpis.callsUnder2sLabel}</p>
        </div>
      </div>
    </ModuleWrapper>
  );
};

export default React.memo(TopMetricsModule);
