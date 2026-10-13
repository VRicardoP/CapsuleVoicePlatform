import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useDashboardData } from '../../hooks/useDashboardData';

const ConversionTrendsModule: React.FC = () => {
  const { data, loading, error, refetch } = useDashboardData();

  if (loading) return <ModuleWrapper title="Tendencia de Conversión" icon="💰"><LoadingSpinner /></ModuleWrapper>;
  if (error) return <ModuleWrapper title="Tendencia de Conversión" icon="💰"><ErrorMessage message={error} onRetry={refetch} /></ModuleWrapper>;
  if (!data) return null;

  return (
    <ModuleWrapper title="Tendencia de Conversión" icon="💰">
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data.conversionData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="month" stroke="#9ca3af" />
          <YAxis stroke="#9ca3af" />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
            labelStyle={{ color: '#fff' }}
          />
          <Legend />
          <Area type="monotone" dataKey="conversiones" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.6} name="Conversiones" />
          <Area type="monotone" dataKey="tasa" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.3} name="Tasa %" />
        </AreaChart>
      </ResponsiveContainer>
    </ModuleWrapper>
  );
};

export default React.memo(ConversionTrendsModule);