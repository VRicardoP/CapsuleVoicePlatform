import React from 'react';
import MetricCard from '../ui/MetricCard';
import { useDashboardData } from '../../hooks/useDashboardData';
import { withModuleData } from './withModuleData';
import type { DashboardData } from '../../types';

// Format change percentage with + or - sign
const formatChange = (value: number): string => {
  if (value === 0) return '0%';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value}%`;
};

const MetricsOverview: React.FC<{ data: DashboardData }> = ({ data }) => {
  const { metrics } = data;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <MetricCard
        title="Llamadas Totales"
        value={metrics.totalCalls.toLocaleString()}
        change={formatChange(metrics.totalCallsChange)}
        changeLabel="vs mes anterior"
        icon="📞"
        color="blue"
      />
      <MetricCard
        title="Duración Promedio"
        value={metrics.avgDuration}
        change={formatChange(metrics.avgDurationChange)}
        changeLabel="vs mes anterior"
        icon="⏱️"
        color="green"
      />
      <MetricCard
        title="Minutos Totales"
        value={metrics.totalMinutes.toLocaleString()}
        change={formatChange(metrics.totalMinutesChange)}
        changeLabel="vs mes anterior"
        icon="📊"
        color="orange"
      />
      <MetricCard
        title="Tasa de Éxito"
        value={`${metrics.successRate}%`}
        change={formatChange(metrics.successRateChange)}
        changeLabel="vs mes anterior"
        icon="✅"
        color="purple"
      />
    </div>
  );
};

export default withModuleData(useDashboardData, 'Cargando métricas...', MetricsOverview);
