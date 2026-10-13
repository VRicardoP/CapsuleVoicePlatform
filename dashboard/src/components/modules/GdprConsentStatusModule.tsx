import React from 'react';
import {
  BarChart,
  Bar,
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
import type { GdprConsentStatus } from '../../types';

const getActiveRateColor = (rate: number): string => {
  if (rate >= 80) return '#22C55E';
  if (rate >= 60) return '#F59E0B';
  if (rate >= 40) return '#F97316';
  return '#EF4444';
};

const GdprConsentStatusModule: React.FC = () => {
  const { summary, loading, error, refetch } = useGdprData();

  if (loading) return <LoadingSpinner message="Cargando estado de consentimientos..." />;
  if (error) return <ErrorMessage message={error} onRetry={refetch} />;
  if (!summary) return null;

  const { consentStatus } = summary;

  // Calcular totales
  const totals = consentStatus.reduce(
    (acc, cs) => ({
      active: acc.active + cs.activeConsents,
      revoked: acc.revoked + cs.revokedConsents,
      expired: acc.expired + cs.expiredConsents,
      total: acc.total + cs.totalConsents,
    }),
    { active: 0, revoked: 0, expired: 0, total: 0 }
  );

  const overallActiveRate = totals.total > 0 ? (totals.active / totals.total) * 100 : 0;

  // Preparar datos para el gráfico
  const chartData = consentStatus.map(cs => ({
    name: cs.purposeName.length > 20 ? cs.purposeName.substring(0, 20) + '...' : cs.purposeName,
    fullName: cs.purposeName,
    activos: cs.activeConsents,
    revocados: cs.revokedConsents,
    expirados: cs.expiredConsents,
    tasa: cs.activeRate,
  }));

  return (
    <ModuleWrapper title="Estado de Consentimientos" icon="✓">
      {/* Resumen general */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Total consentimientos"
          value={totals.total.toLocaleString()}
          icon="📊"
          color="text-blue-400"
        />
        <StatCard
          label="Activos"
          value={totals.active.toLocaleString()}
          subValue={`${overallActiveRate.toFixed(1)}%`}
          icon="✅"
          color="text-green-400"
        />
        <StatCard
          label="Revocados"
          value={totals.revoked.toLocaleString()}
          icon="❌"
          color="text-red-400"
        />
        <StatCard
          label="Expirados"
          value={totals.expired.toLocaleString()}
          icon="⏰"
          color="text-yellow-400"
        />
      </div>

      {/* Gráfico de barras apiladas */}
      <div className="h-64 mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              type="number"
              tick={{ fill: '#9CA3AF', fontSize: 11 }}
              tickLine={{ stroke: '#4B5563' }}
              axisLine={{ stroke: '#4B5563' }}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: '#9CA3AF', fontSize: 11 }}
              tickLine={{ stroke: '#4B5563' }}
              axisLine={{ stroke: '#4B5563' }}
              width={100}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#F3F4F6' }}
              formatter={(value: number, name: string) => [value.toLocaleString(), name]}
              labelFormatter={(label, payload) => payload[0]?.payload?.fullName || label}
            />
            <Legend
              wrapperStyle={{ paddingTop: 10 }}
              formatter={(value) => <span className="text-gray-300 text-xs">{value}</span>}
            />
            <Bar dataKey="activos" name="Activos" stackId="a" fill="#22C55E" />
            <Bar dataKey="revocados" name="Revocados" stackId="a" fill="#EF4444" />
            <Bar dataKey="expirados" name="Expirados" stackId="a" fill="#F59E0B" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Detalle por propósito */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-400">Tasa de consentimiento activo por propósito</h4>
        {consentStatus.map((cs) => (
          <ConsentPurposeRow key={cs.purposeId} consent={cs} />
        ))}
      </div>
    </ModuleWrapper>
  );
};

interface StatCardProps {
  label: string;
  value: string;
  subValue?: string;
  icon: string;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, subValue, icon, color }) => (
  <div className="bg-gray-700/50 rounded-lg p-3">
    <div className="flex items-center gap-2 mb-1">
      <span className="text-lg">{icon}</span>
      <span className="text-xs text-gray-400">{label}</span>
    </div>
    <div className="flex items-baseline gap-2">
      <span className={`text-xl font-bold ${color}`}>{value}</span>
      {subValue && <span className="text-xs text-gray-500">{subValue}</span>}
    </div>
  </div>
);

interface ConsentPurposeRowProps {
  consent: GdprConsentStatus;
}

const ConsentPurposeRow: React.FC<ConsentPurposeRowProps> = ({ consent }) => {
  const rateColor = getActiveRateColor(consent.activeRate);

  return (
    <div className="flex items-center gap-4 p-3 bg-gray-700/30 rounded-lg">
      <div className="flex-1">
        <div className="text-sm font-medium text-white">{consent.purposeName}</div>
        <div className="text-xs text-gray-500">
          {consent.activeConsents.toLocaleString()} activos de {consent.totalConsents.toLocaleString()}
        </div>
      </div>
      <div className="w-32">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-500">Tasa activa</span>
          <span className="text-sm font-bold" style={{ color: rateColor }}>
            {consent.activeRate.toFixed(1)}%
          </span>
        </div>
        <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
          <div
            className="h-full transition-all duration-500"
            style={{
              width: `${consent.activeRate}%`,
              backgroundColor: rateColor,
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default React.memo(GdprConsentStatusModule);
