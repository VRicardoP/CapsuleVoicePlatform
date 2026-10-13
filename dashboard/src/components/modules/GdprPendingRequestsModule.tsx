import React from 'react';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useGdprData } from '../../hooks/useGdprData';
import type { RequestPriority, GdprPendingRequest } from '../../types';

const getPriorityStyles = (priority: RequestPriority): { bg: string; text: string; border: string } => {
  switch (priority) {
    case 'overdue':
      return { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500' };
    case 'urgent':
      return { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500' };
    case 'warning':
      return { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500' };
    case 'normal':
      return { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500' };
    default:
      return { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500' };
  }
};

const getPriorityLabel = (priority: RequestPriority): string => {
  switch (priority) {
    case 'overdue':
      return 'Vencida';
    case 'urgent':
      return 'Urgente';
    case 'warning':
      return 'Próxima';
    case 'normal':
      return 'Normal';
    default:
      return priority;
  }
};

const getRequestTypeIcon = (type: string): string => {
  switch (type) {
    case 'access':
      return '👁️';
    case 'erasure':
      return '🗑️';
    case 'rectification':
      return '✏️';
    case 'portability':
      return '📦';
    case 'restriction':
      return '🚫';
    case 'objection':
      return '✋';
    default:
      return '📋';
  }
};

const GdprPendingRequestsModule: React.FC = () => {
  const { summary, loading, error, refetch } = useGdprData();

  if (loading) return <LoadingSpinner message="Cargando solicitudes pendientes..." />;
  if (error) return <ErrorMessage message={error} onRetry={refetch} />;
  if (!summary) return null;

  const { pendingRequests } = summary;
  const overdueCount = pendingRequests.filter(r => r.priority === 'overdue').length;
  const urgentCount = pendingRequests.filter(r => r.priority === 'urgent').length;

  return (
    <ModuleWrapper title="Solicitudes ARCO Pendientes" icon="📋">
      {/* Resumen rápido */}
      <div className="flex gap-4 mb-4">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-700/50 rounded-lg">
          <span className="text-2xl font-bold text-white">{pendingRequests.length}</span>
          <span className="text-xs text-gray-400">Total pendientes</span>
        </div>
        {overdueCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 border border-red-500/50 rounded-lg">
            <span className="text-2xl font-bold text-red-400">{overdueCount}</span>
            <span className="text-xs text-red-400">Vencidas</span>
          </div>
        )}
        {urgentCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-orange-500/20 border border-orange-500/50 rounded-lg">
            <span className="text-2xl font-bold text-orange-400">{urgentCount}</span>
            <span className="text-xs text-orange-400">Urgentes</span>
          </div>
        )}
      </div>

      {/* Lista de solicitudes */}
      {pendingRequests.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <span className="text-4xl mb-2 block">✅</span>
          No hay solicitudes pendientes
        </div>
      ) : (
        <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
          {pendingRequests.map((request) => (
            <RequestCard key={request.id} request={request} />
          ))}
        </div>
      )}
    </ModuleWrapper>
  );
};

interface RequestCardProps {
  request: GdprPendingRequest;
}

const RequestCard: React.FC<RequestCardProps> = ({ request }) => {
  const styles = getPriorityStyles(request.priority);

  return (
    <div className={`${styles.bg} border-l-4 ${styles.border} rounded-r-lg p-3`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">{getRequestTypeIcon(request.requestType)}</span>
          <div>
            <span className="font-medium text-white">{request.requestTypeLabel}</span>
            <div className="text-xs text-gray-400">{request.subjectEmail}</div>
          </div>
        </div>
        <div className="text-right">
          <span className={`text-xs font-medium px-2 py-0.5 rounded ${styles.bg} ${styles.text}`}>
            {getPriorityLabel(request.priority)}
          </span>
          <div className={`text-sm font-semibold mt-1 ${styles.text}`}>
            {request.daysRemaining > 0
              ? `${request.daysRemaining} días restantes`
              : `${Math.abs(request.daysRemaining)} días vencida`
            }
          </div>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
        <span>Creada: {new Date(request.createdAt).toLocaleDateString('es-ES')}</span>
        <span>Límite: {new Date(request.deadlineDate).toLocaleDateString('es-ES')}</span>
      </div>
    </div>
  );
};

export default React.memo(GdprPendingRequestsModule);
