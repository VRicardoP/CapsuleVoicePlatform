// src/components/modules/StatusDistributionModule.tsx
import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import type { StatusData } from '../../types';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useDashboardData } from '../../hooks/useDashboardData';

const StatusDistributionModule: React.FC = () => {
  const { data, loading, error, refetch } = useDashboardData();

  if (loading) return <ModuleWrapper title="Distribución de Resultados" icon="📊"><LoadingSpinner /></ModuleWrapper>;
  if (error) return <ModuleWrapper title="Distribución de Resultados" icon="📊"><ErrorMessage message={error} onRetry={refetch} /></ModuleWrapper>;
  if (!data) return null;

  return (
    <ModuleWrapper title="Distribución de Resultados" icon="📊">
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data.statusData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={(props: any) => {
              const RADIAN = Math.PI / 180;
              const { cx, cy, midAngle, innerRadius, outerRadius, percent, name } = props;
              const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
              const x = cx + radius * Math.cos(-midAngle * RADIAN);
              const y = cy + radius * Math.sin(-midAngle * RADIAN);
              
              return (
                  <text 
                  x={x} 
                  y={y} 
                  fill="white" 
                  textAnchor={x > cx ? 'start' : 'end'} 
                  dominantBaseline="central"
                  >
                  {`${name} ${(percent * 100).toFixed(0)}%`}
                  </text>
              );
            }}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {data.statusData.map((entry: StatusData, index: number) => (
              <Cell key={`cell-${entry.name}-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
            itemStyle={{ color: '#22d3ee' }}
            labelStyle={{ color: '#22d3ee' }}
          />
        </PieChart>
      </ResponsiveContainer>
    </ModuleWrapper>
  );
};

export default React.memo(StatusDistributionModule);