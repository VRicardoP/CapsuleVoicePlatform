// src/components/modules/HeatmapModule.tsx
import React from 'react';
import type { ChartDataPoint } from '../../types';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useDashboardData } from '../../hooks/useDashboardData';

const HeatmapModule: React.FC = () => {
  const { data, loading, error, refetch } = useDashboardData();

  if (loading) return <ModuleWrapper title="Mapa de Calor - Volumen por Hora" icon="🔥"><LoadingSpinner /></ModuleWrapper>;
  if (error) return <ModuleWrapper title="Mapa de Calor - Volumen por Hora" icon="🔥"><ErrorMessage message={error} onRetry={refetch} /></ModuleWrapper>;
  if (!data) return null;

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  return (
    <ModuleWrapper title="Mapa de Calor - Volumen por Hora" icon="🔥">
      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          <div className="grid grid-cols-8 gap-1">
            <div></div>
            {days.map(day => (
              <div key={day} className="text-center text-xs text-gray-400 font-semibold p-2">
                {day}
              </div>
            ))}
            {data.heatmapData.map((row: ChartDataPoint) => (
              <React.Fragment key={row.hour}>
                <div className="text-xs text-gray-400 flex items-center pr-2">{row.hour}</div>
                {days.map(day => {
                  const value = (row[day] as number) || 0;
                  const intensity = Math.min(value / 35, 1);
                  const bgColor = `rgba(59, 130, 246, ${intensity * 0.8})`;
                  return (
                    <div
                      key={`${row.hour}-${day}`}
                      className="aspect-square rounded flex items-center justify-center text-xs font-semibold text-white"
                      style={{ backgroundColor: bgColor }}
                      title={`${day} ${row.hour}: ${value} llamadas`}
                    >
                      {value > 0 ? value : ''}
                    </div>
                  );
                })}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>
    </ModuleWrapper>
  );
};

export default React.memo(HeatmapModule);