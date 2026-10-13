import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useDashboardData } from '../../hooks/useDashboardData';

const WeeklyEvolutionModule: React.FC = () => {
  const { data, loading, error, refetch } = useDashboardData();

  if (loading) return <ModuleWrapper title="Evolución Semanal" icon="📈"><LoadingSpinner /></ModuleWrapper>;
  if (error) return <ModuleWrapper title="Evolución Semanal" icon="📈"><ErrorMessage message={error} onRetry={refetch} /></ModuleWrapper>;
  if (!data) return null;

  return (
    <ModuleWrapper title="Evolución Semanal" icon="📈">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data.callsData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="date" stroke="#9ca3af" />
          <YAxis stroke="#9ca3af" />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
            labelStyle={{ color: '#fff' }}
          />
          <Legend />
          <Line type="monotone" dataKey="calls" stroke="#3b82f6" strokeWidth={2} name="Llamadas" />
          <Line type="monotone" dataKey="resolved" stroke="#10b981" strokeWidth={2} name="Resueltas" />
        </LineChart>
      </ResponsiveContainer>
    </ModuleWrapper>
  );
};

export default React.memo(WeeklyEvolutionModule);