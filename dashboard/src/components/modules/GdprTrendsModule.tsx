import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useGdprData } from '../../hooks/useGdprData';

const METRICS_CONFIG = [
  { key: 'compliance_score', name: 'Cumplimiento', color: '#3B82F6', active: true },
  { key: 'consent_rate', name: 'Consentimientos', color: '#22C55E', active: true },
  { key: 'request_response_rate', name: 'Respuesta solicitudes', color: '#F59E0B', active: true },
  { key: 'breach_response_rate', name: 'Respuesta brechas', color: '#EF4444', active: false },
];

const GdprTrendsModule: React.FC = () => {
  const { trends, loading, error, refetch, refetchTrends } = useGdprData();
  const [activeMetrics, setActiveMetrics] = useState<Record<string, boolean>>(
    METRICS_CONFIG.reduce((acc, m) => ({ ...acc, [m.key]: m.active }), {})
  );
  const [period, setPeriod] = useState<number>(30);

  if (loading) return <LoadingSpinner message="Cargando tendencias RGPD..." />;
  if (error) return <ErrorMessage message={error} onRetry={refetch} />;
  if (!trends) return null;

  const handlePeriodChange = async (days: number) => {
    setPeriod(days);
    await refetchTrends(days);
  };

  const toggleMetric = (key: string) => {
    setActiveMetrics(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const chartData = trends.trends.map(point => ({
    ...point,
    date: new Date(point.date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' }),
  }));

  return (
    <ModuleWrapper title="Evolución del Cumplimiento RGPD" icon="📈">
      {/* Controles */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        {/* Selector de período */}
        <div className="flex gap-2">
          {[7, 14, 30, 90].map(days => (
            <button
              key={days}
              onClick={() => handlePeriodChange(days)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                period === days
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {days}d
            </button>
          ))}
        </div>

        {/* Toggle de métricas */}
        <div className="flex flex-wrap gap-2">
          {METRICS_CONFIG.map(metric => (
            <button
              key={metric.key}
              onClick={() => toggleMetric(metric.key)}
              className={`flex items-center gap-1.5 px-2 py-1 text-xs rounded-lg transition-all ${
                activeMetrics[metric.key]
                  ? 'bg-gray-700 border border-gray-600'
                  : 'bg-gray-800 border border-gray-700 opacity-50'
              }`}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: metric.color }}
              />
              <span className="text-gray-300">{metric.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Gráfico */}
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#9CA3AF', fontSize: 11 }}
              tickLine={{ stroke: '#4B5563' }}
              axisLine={{ stroke: '#4B5563' }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: '#9CA3AF', fontSize: 11 }}
              tickLine={{ stroke: '#4B5563' }}
              axisLine={{ stroke: '#4B5563' }}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#F3F4F6' }}
              formatter={(value: number) => [`${value.toFixed(1)}%`, '']}
            />
            <Legend
              wrapperStyle={{ paddingTop: 10 }}
              formatter={(value) => <span className="text-gray-300 text-xs">{value}</span>}
            />
            {METRICS_CONFIG.map(metric => (
              activeMetrics[metric.key] && (
                <Line
                  key={metric.key}
                  type="monotone"
                  dataKey={metric.key}
                  name={metric.name}
                  stroke={metric.color}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2 }}
                />
              )
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Resumen del período */}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
        {METRICS_CONFIG.filter(m => activeMetrics[m.key]).map(metric => {
          const values = trends.trends.map(t => t[metric.key as keyof typeof t] as number);
          const avg = values.reduce((a, b) => a + b, 0) / values.length;
          const first = values[0];
          const last = values[values.length - 1];
          const trend = last - first;

          return (
            <div key={metric.key} className="bg-gray-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: metric.color }} />
                <span className="text-xs text-gray-400">{metric.name}</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-lg font-bold text-white">{avg.toFixed(1)}%</span>
                <span className={`text-xs ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </ModuleWrapper>
  );
};

export default React.memo(GdprTrendsModule);
