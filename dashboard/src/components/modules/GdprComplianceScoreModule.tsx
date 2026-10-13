import React from 'react';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useGdprData } from '../../hooks/useGdprData';
import type { ComplianceStatus } from '../../types';

const getStatusColor = (status: ComplianceStatus): string => {
  switch (status) {
    case 'excellent':
      return 'text-green-400';
    case 'good':
      return 'text-blue-400';
    case 'needs_attention':
      return 'text-yellow-400';
    case 'critical':
      return 'text-red-400';
    default:
      return 'text-gray-400';
  }
};

const getStatusLabel = (status: ComplianceStatus): string => {
  switch (status) {
    case 'excellent':
      return 'Excelente';
    case 'good':
      return 'Bueno';
    case 'needs_attention':
      return 'Requiere atención';
    case 'critical':
      return 'Crítico';
    default:
      return 'Desconocido';
  }
};

const getScoreGradient = (score: number): string => {
  if (score >= 90) return 'from-green-500 to-green-400';
  if (score >= 75) return 'from-blue-500 to-blue-400';
  if (score >= 50) return 'from-yellow-500 to-yellow-400';
  return 'from-red-500 to-red-400';
};

const GdprComplianceScoreModule: React.FC = () => {
  const { summary, loading, error, refetch } = useGdprData();

  if (loading) return <LoadingSpinner message="Cargando cumplimiento RGPD..." />;
  if (error) return <ErrorMessage message={error} onRetry={refetch} />;
  if (!summary) return null;

  const { compliance } = summary;
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (compliance.overallScore / 100) * circumference;

  return (
    <ModuleWrapper title="Cumplimiento RGPD" icon="🛡️">
      <div className="flex flex-col lg:flex-row items-center gap-8">
        {/* Gauge circular */}
        <div className="relative">
          <svg className="w-40 h-40 transform -rotate-90">
            <circle
              cx="80"
              cy="80"
              r="45"
              stroke="currentColor"
              strokeWidth="10"
              fill="none"
              className="text-gray-700"
            />
            <circle
              cx="80"
              cy="80"
              r="45"
              stroke="url(#scoreGradient)"
              strokeWidth="10"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-1000 ease-out"
            />
            <defs>
              <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" className={`stop-color-${getScoreGradient(compliance.overallScore).split(' ')[0].replace('from-', '')}`} stopColor={compliance.overallScore >= 75 ? '#3B82F6' : '#EF4444'} />
                <stop offset="100%" stopColor={compliance.overallScore >= 90 ? '#22C55E' : compliance.overallScore >= 75 ? '#60A5FA' : '#F59E0B'} />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold text-white">{compliance.overallScore.toFixed(1)}%</span>
            <span className={`text-sm font-medium ${getStatusColor(compliance.status)}`}>
              {getStatusLabel(compliance.status)}
            </span>
          </div>
        </div>

        {/* Métricas detalladas */}
        <div className="flex-1 grid grid-cols-2 gap-4">
          <MetricItem
            label="Tasa de consentimientos"
            value={compliance.consentRate}
            icon="✓"
          />
          <MetricItem
            label="Cumplimiento retención"
            value={compliance.retentionCompliance}
            icon="📅"
          />
          <MetricItem
            label="Respuesta a solicitudes"
            value={compliance.requestResponseRate}
            icon="📋"
          />
          <MetricItem
            label="Respuesta a brechas"
            value={compliance.breachResponseRate}
            icon="🔒"
          />
        </div>
      </div>

      <div className="mt-4 text-xs text-gray-500 text-right">
        Actualizado: {new Date(compliance.lastUpdated).toLocaleString('es-ES')}
      </div>
    </ModuleWrapper>
  );
};

interface MetricItemProps {
  label: string;
  value: number;
  icon: string;
}

const MetricItem: React.FC<MetricItemProps> = ({ label, value, icon }) => {
  const getBarColor = (val: number): string => {
    if (val >= 90) return 'bg-green-500';
    if (val >= 75) return 'bg-blue-500';
    if (val >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="bg-gray-700/50 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{icon}</span>
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-600 rounded-full overflow-hidden">
          <div
            className={`h-full ${getBarColor(value)} transition-all duration-500`}
            style={{ width: `${value}%` }}
          />
        </div>
        <span className="text-sm font-semibold text-white w-12 text-right">
          {value.toFixed(1)}%
        </span>
      </div>
    </div>
  );
};

export default React.memo(GdprComplianceScoreModule);
