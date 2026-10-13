import React from 'react';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useGdprData } from '../../hooks/useGdprData';
import type { BreachUrgency, GdprBreachAlert } from '../../types';

const getUrgencyStyles = (urgency: BreachUrgency): { bg: string; text: string; border: string; pulse: boolean } => {
  switch (urgency) {
    case 'overdue':
      return { bg: 'bg-red-600/30', text: 'text-red-300', border: 'border-red-500', pulse: true };
    case 'critical':
      return { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500', pulse: true };
    case 'urgent':
      return { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500', pulse: false };
    case 'normal':
      return { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500', pulse: false };
    default:
      return { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500', pulse: false };
  }
};

const getUrgencyLabel = (urgency: BreachUrgency): string => {
  switch (urgency) {
    case 'overdue':
      return 'Plazo vencido';
    case 'critical':
      return 'Crítico';
    case 'urgent':
      return 'Urgente';
    case 'normal':
      return 'Normal';
    default:
      return urgency;
  }
};

const getSeverityIcon = (severity: string): string => {
  switch (severity.toLowerCase()) {
    case 'critical':
      return '🔴';
    case 'high':
      return '🟠';
    case 'medium':
      return '🟡';
    case 'low':
      return '🟢';
    default:
      return '⚪';
  }
};

const GdprBreachAlertsModule: React.FC = () => {
  const { summary, loading, error, refetch } = useGdprData();

  if (loading) return <LoadingSpinner message="Cargando alertas de brechas..." />;
  if (error) return <ErrorMessage message={error} onRetry={refetch} />;
  if (!summary) return null;

  const { breachAlerts } = summary;
  const criticalCount = breachAlerts.filter(b => b.urgency === 'critical' || b.urgency === 'overdue').length;

  return (
    <ModuleWrapper title="Alertas de Brechas de Seguridad" icon="🚨">
      {/* Estado general */}
      <div className="mb-4">
        {breachAlerts.length === 0 ? (
          <div className="flex items-center gap-3 p-4 bg-green-500/20 border border-green-500/50 rounded-lg">
            <span className="text-3xl">✅</span>
            <div>
              <span className="font-semibold text-green-400">Sin brechas activas</span>
              <p className="text-xs text-green-300/70">No hay incidentes de seguridad pendientes de gestión</p>
            </div>
          </div>
        ) : (
          <div className={`flex items-center gap-3 p-4 ${criticalCount > 0 ? 'bg-red-500/20 border-red-500/50' : 'bg-yellow-500/20 border-yellow-500/50'} border rounded-lg`}>
            <span className="text-3xl">{criticalCount > 0 ? '⚠️' : '📢'}</span>
            <div>
              <span className={`font-semibold ${criticalCount > 0 ? 'text-red-400' : 'text-yellow-400'}`}>
                {breachAlerts.length} brecha{breachAlerts.length > 1 ? 's' : ''} activa{breachAlerts.length > 1 ? 's' : ''}
              </span>
              {criticalCount > 0 && (
                <p className="text-xs text-red-300/70">
                  {criticalCount} requiere{criticalCount > 1 ? 'n' : ''} atención inmediata (Art. 33 RGPD - 72h)
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Lista de brechas */}
      {breachAlerts.length > 0 && (
        <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
          {breachAlerts.map((breach) => (
            <BreachCard key={breach.id} breach={breach} />
          ))}
        </div>
      )}

      {/* Recordatorio legal */}
      <div className="mt-4 p-3 bg-gray-700/30 rounded-lg border border-gray-600">
        <p className="text-xs text-gray-400">
          <strong className="text-gray-300">Art. 33 RGPD:</strong> Las brechas de seguridad deben notificarse
          a la autoridad de control en un plazo máximo de <strong className="text-yellow-400">72 horas</strong> desde
          su detección si existe riesgo para los derechos de los interesados.
        </p>
      </div>
    </ModuleWrapper>
  );
};

interface BreachCardProps {
  breach: GdprBreachAlert;
}

const BreachCard: React.FC<BreachCardProps> = ({ breach }) => {
  const styles = getUrgencyStyles(breach.urgency);

  return (
    <div className={`${styles.bg} border ${styles.border} rounded-lg p-4 ${styles.pulse ? 'animate-pulse' : ''}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{getSeverityIcon(breach.severity)}</span>
          <div>
            <span className="font-medium text-white">Severidad: {breach.severityLabel}</span>
            <span className={`ml-2 text-xs px-2 py-0.5 rounded ${styles.bg} ${styles.text} border ${styles.border}`}>
              {getUrgencyLabel(breach.urgency)}
            </span>
          </div>
        </div>
        {breach.requiresNotification && (
          <span className="text-xs bg-red-500/30 text-red-300 px-2 py-1 rounded border border-red-500/50">
            Requiere notificación
          </span>
        )}
      </div>

      <p className="text-sm text-gray-300 mb-3">{breach.description}</p>

      <div className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <span className="text-gray-500">Afectados:</span>
          <span className="ml-2 text-white font-semibold">{breach.affectedCount.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-gray-500">Detectada:</span>
          <span className="ml-2 text-white">{new Date(breach.detectedAt).toLocaleString('es-ES')}</span>
        </div>
      </div>

      {breach.requiresNotification && (
        <div className={`mt-3 p-2 rounded ${styles.bg} border ${styles.border}`}>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">Plazo de notificación:</span>
            <span className={`font-bold ${styles.text}`}>
              {breach.hoursRemaining > 0
                ? `${breach.hoursRemaining}h restantes`
                : `${Math.abs(breach.hoursRemaining)}h vencido`
              }
            </span>
          </div>
          <div className="mt-1 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${breach.hoursRemaining <= 0 ? 'bg-red-500' : breach.hoursRemaining <= 24 ? 'bg-orange-500' : 'bg-yellow-500'}`}
              style={{ width: `${Math.max(0, Math.min(100, (breach.hoursRemaining / 72) * 100))}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default React.memo(GdprBreachAlertsModule);
