import React, { useMemo } from 'react';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useCallStats } from '../../hooks/useCallStats';
import type { MonthlyCallStats } from '../../types';

interface StatCardProps {
  title: string;
  value: number;
  label: string;
  change?: number;
  trend?: 'up' | 'down' | 'stable';
  size?: 'small' | 'medium' | 'large';
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  label,
  change,
  trend,
  size = 'medium'
}) => {
  const getTrendColor = () => {
    if (trend === 'up') return 'text-green-400';
    if (trend === 'down') return 'text-red-400';
    return 'text-gray-400';
  };

  const getTrendIcon = () => {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '→';
  };

  const sizeClasses = {
    small: 'p-3',
    medium: 'p-4',
    large: 'p-6'
  };

  const valueClasses = {
    small: 'text-xl',
    medium: 'text-2xl',
    large: 'text-3xl'
  };

  return (
    <div className={`bg-gray-800/50 rounded-lg border border-gray-700/50 ${sizeClasses[size]}`}>
      <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">{title}</div>
      <div className={`font-bold text-white ${valueClasses[size]}`}>
        {value.toLocaleString()}
      </div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
      {change !== undefined && trend && (
        <div className={`text-xs mt-2 ${getTrendColor()}`}>
          {getTrendIcon()} {Math.abs(change).toFixed(1)}% vs anterior
        </div>
      )}
    </div>
  );
};

interface MonthlyBarProps {
  months: MonthlyCallStats[];
  maxCalls: number;
  year: number;
}

const MonthlyBar: React.FC<MonthlyBarProps> = ({ months, maxCalls, year }) => {
  const allMonths = Array.from({ length: 12 }, (_, i) => {
    const monthData = months.find(m => m.month === i + 1);
    return {
      month: i + 1,
      monthName: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'][i],
      calls: monthData?.calls || 0
    };
  });

  const barHeight = 80; // pixels

  return (
    <div className="space-y-1">
      <div className="text-xs text-gray-400 mb-2">{year}</div>
      <div className="flex gap-1 items-end" style={{ height: `${barHeight}px` }}>
        {allMonths.map((m) => {
          const heightPx = maxCalls > 0 ? (m.calls / maxCalls) * barHeight : 0;
          return (
            <div key={m.month} className="flex-1 flex flex-col items-end justify-end">
              <div
                className="w-full bg-blue-500/70 rounded-t transition-all duration-300 hover:bg-blue-400 cursor-pointer"
                style={{ height: `${Math.max(heightPx, m.calls > 0 ? 4 : 0)}px` }}
                title={`${m.monthName}: ${m.calls} llamadas`}
              />
            </div>
          );
        })}
      </div>
      <div className="flex gap-1">
        {allMonths.map((m) => (
          <div key={m.month} className="flex-1 text-center">
            <span className="text-[10px] text-gray-500">{m.monthName}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const CallStatsModule: React.FC = () => {
  const { data, loading, error, refetch } = useCallStats();

  // useMemo must be called unconditionally (React hooks rule)
  const maxCalls = useMemo(() => {
    if (!data) return 1;
    const allMonthCalls = [
      ...data.currentYearMonths.map(m => m.calls),
      ...data.previousYearMonths.map(m => m.calls)
    ];
    return Math.max(...allMonthCalls, 1);
  }, [data]);

  if (loading) return <LoadingSpinner message="Cargando estadisticas..." />;
  if (error) return <ErrorMessage message={error} onRetry={refetch} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Estadisticas de Llamadas</h3>
        <span className="text-xs text-gray-500">Auto-actualiza cada 5s</span>
      </div>

      {/* Daily & Weekly Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Hoy"
          value={data.today}
          label={data.todayLabel}
          change={data.dayOverDayChange}
          trend={data.dayOverDayTrend}
          size="medium"
        />
        <StatCard
          title="Ayer"
          value={data.yesterday}
          label={data.yesterdayLabel}
          size="medium"
        />
        <StatCard
          title="Esta Semana"
          value={data.currentWeek}
          label={data.currentWeekLabel}
          change={data.weekOverWeekChange}
          trend={data.weekOverWeekTrend}
          size="medium"
        />
        <StatCard
          title="Semana Anterior"
          value={data.previousWeek}
          label={data.previousWeekLabel}
          size="medium"
        />
      </div>

      {/* Annual Stats */}
      <div className="grid grid-cols-2 gap-4">
        <StatCard
          title={`Ano ${data.currentYearLabel}`}
          value={data.currentYear}
          label="llamadas totales"
          change={data.yearOverYearChange}
          trend={data.yearOverYearTrend}
          size="large"
        />
        <StatCard
          title={`Ano ${data.previousYearLabel}`}
          value={data.previousYear}
          label="llamadas totales"
          size="large"
        />
      </div>

      {/* Monthly Charts */}
      <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/30">
        <h4 className="text-sm font-medium text-gray-300 mb-4">Distribucion Mensual</h4>
        <div className="space-y-6">
          <MonthlyBar
            months={data.currentYearMonths}
            maxCalls={maxCalls}
            year={parseInt(data.currentYearLabel)}
          />
          <MonthlyBar
            months={data.previousYearMonths}
            maxCalls={maxCalls}
            year={parseInt(data.previousYearLabel)}
          />
        </div>
      </div>

      {/* Monthly Details Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Current Year Table */}
        <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/30">
          <h4 className="text-sm font-medium text-gray-300 mb-3">
            Detalle {data.currentYearLabel}
          </h4>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {data.currentYearMonths.length > 0 ? (
              data.currentYearMonths.map((m) => (
                <div key={m.month} className="flex justify-between text-sm py-1 border-b border-gray-700/30">
                  <span className="text-gray-400">{m.monthName}</span>
                  <span className="text-white font-medium">{m.calls.toLocaleString()}</span>
                </div>
              ))
            ) : (
              <div className="text-gray-500 text-sm">Sin datos</div>
            )}
          </div>
        </div>

        {/* Previous Year Table */}
        <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/30">
          <h4 className="text-sm font-medium text-gray-300 mb-3">
            Detalle {data.previousYearLabel}
          </h4>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {data.previousYearMonths.length > 0 ? (
              data.previousYearMonths.map((m) => (
                <div key={m.month} className="flex justify-between text-sm py-1 border-b border-gray-700/30">
                  <span className="text-gray-400">{m.monthName}</span>
                  <span className="text-white font-medium">{m.calls.toLocaleString()}</span>
                </div>
              ))
            ) : (
              <div className="text-gray-500 text-sm">Sin datos</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(CallStatsModule);
