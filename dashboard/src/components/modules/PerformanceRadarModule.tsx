import React from 'react';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip, ResponsiveContainer } from 'recharts';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useDashboardData } from '../../hooks/useDashboardData';

const PerformanceRadarModule: React.FC = () => {
  const { data, loading, error, refetch } = useDashboardData();

  if (loading) return <ModuleWrapper title="Performance del Asistente" icon="🤖"><LoadingSpinner /></ModuleWrapper>;
  if (error) return <ModuleWrapper title="Performance del Asistente" icon="🤖"><ErrorMessage message={error} onRetry={refetch} /></ModuleWrapper>;
  if (!data) return null;

  return (
    <ModuleWrapper title="Performance del Asistente" icon="🤖">
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data.performanceData}>
          <PolarGrid stroke="#374151" />
          <PolarAngleAxis dataKey="metric" stroke="#9ca3af" />
          <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#9ca3af" />
          <Radar name="Performance" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
            labelStyle={{ color: '#ffffff' }}
            itemStyle={{ color: '#22d3ee' }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </ModuleWrapper>
  );
};

export default React.memo(PerformanceRadarModule);