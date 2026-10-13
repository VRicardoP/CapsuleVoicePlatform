// src/components/modules/RecentCallsModule.tsx
import React, { useState, useMemo } from 'react';
import type { CallRecord } from '../../types';
import ModuleWrapper from '../ui/ModuleWrapper';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import { useCallSelection } from '../../context/CallSelectionContext';
import { useDashboardData } from '../../hooks/useDashboardData';
import { usePiiAccess } from '../../hooks/usePiiAccess';
import { SECURITY_CONFIG } from '../../services/api/config';

type CallStatus = 'completed' | 'scheduled' | 'transferred' | 'rejected' | 'in_progress' | 'cancelled' | 'voicemail' | 'no_answer';
type CallSentiment = 'positive' | 'neutral' | 'negative';

// --- Constants moved to module scope (avoid recreation on each render) ---

const STATUS_COLORS: Record<CallStatus, string> = {
  completed: 'bg-green-900/30 text-green-400 border-green-500/30',
  scheduled: 'bg-blue-900/30 text-blue-400 border-blue-500/30',
  transferred: 'bg-purple-900/30 text-purple-400 border-purple-500/30',
  rejected: 'bg-red-900/30 text-red-400 border-red-500/30',
  no_answer: 'bg-red-900/30 text-red-400 border-red-500/30',
  in_progress: 'bg-yellow-900/30 text-yellow-400 border-yellow-500/30',
  cancelled: 'bg-gray-900/30 text-gray-400 border-gray-500/30',
  voicemail: 'bg-orange-900/30 text-orange-400 border-orange-500/30',
};

const STATUS_LABELS: Record<CallStatus, string> = {
  completed: 'Finalizado',
  scheduled: 'Agendada',
  transferred: 'Transferida',
  rejected: 'Rechazada',
  no_answer: 'No respondida',
  in_progress: 'En curso',
  cancelled: 'Cancelada',
  voicemail: 'Voicemail',
};

// AI Act Art. 50.3 - evitamos terminologia de "sentimiento/emocion"
const EXPERIENCE_COLORS: Record<CallSentiment, { text: string; bar: string }> = {
  positive: { text: 'text-green-400', bar: 'bg-green-500' },
  neutral: { text: 'text-gray-400', bar: 'bg-gray-500' },
  negative: { text: 'text-red-400', bar: 'bg-red-500' },
};

const EXPERIENCE_LABELS: Record<CallSentiment, string> = {
  positive: 'Satisfactoria',
  neutral: 'Normal',
  negative: 'Requiere atencion',
};

type CallDirection = 'inbound' | 'outbound' | 'internal';

const DIRECTION_COLORS: Record<CallDirection, string> = {
  inbound: 'bg-blue-900/30 text-blue-400 border-blue-500/30',
  outbound: 'bg-purple-900/30 text-purple-400 border-purple-500/30',
  internal: 'bg-gray-900/30 text-gray-400 border-gray-500/30',
};

const DIRECTION_LABELS: Record<CallDirection, string> = {
  inbound: 'Entrante',
  outbound: 'Saliente',
  internal: 'Interna',
};

const ITEMS_PER_PAGE = 20;
const PAGINATION_WINDOW = 5;

const ExperienceDisplay: React.FC<{ sentiment: CallSentiment }> = ({ sentiment }) => {
  const colors = EXPERIENCE_COLORS[sentiment];
  return (
    <div className="flex items-center gap-2">
      <div className={`w-1.5 h-6 rounded-full ${colors.bar}`} />
      <span className={`text-xs ${colors.text}`}>{EXPERIENCE_LABELS[sentiment]}</span>
    </div>
  );
};

const EXPORT_DAYS = 7;

const RecentCallsModule: React.FC = () => {
  const { setSelectedCall } = useCallSelection();
  const { data, loading, error, refetch } = useDashboardData();
  const { canAccessPII, maskName, maskPhone } = usePiiAccess();
  const [currentPage, setCurrentPage] = useState(1);
  const [phoneFilter, setPhoneFilter] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      const res = await fetch(
        `${SECURITY_CONFIG.BASE_URL}/calls/export.xlsx?days=${EXPORT_DAYS}`,
        { credentials: 'include' },
      );
      if (!res.ok) {
        const detail = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status} ${detail.slice(0, 120)}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      // Filename del Content-Disposition; fallback genérico
      const cd = res.headers.get('Content-Disposition') || '';
      const match = cd.match(/filename="?([^";]+)"?/i);
      const filename = match ? match[1] : `llamadas_${EXPORT_DAYS}d.xlsx`;
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'Error desconocido');
    } finally {
      setIsExporting(false);
    }
  };

  // Memoize pagination calculations
  const { allCalls, totalPages, startIndex, paginatedCalls } = useMemo(() => {
    if (!data) return { allCalls: [], totalPages: 0, startIndex: 0, paginatedCalls: [] };
    const filtered = phoneFilter.trim()
      ? data.recentCalls.filter(c => {
          const q = phoneFilter.trim();
          return (c.phone ?? '').includes(q) || (c.calledNumber ?? '').includes(q);
        })
      : data.recentCalls;
    const pages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return {
      allCalls: filtered,
      totalPages: pages,
      startIndex: start,
      paginatedCalls: filtered.slice(start, start + ITEMS_PER_PAGE),
    };
  }, [data, currentPage, phoneFilter]);

  // Pagination window: show max 5 page buttons around current page
  const visiblePages = useMemo(() => {
    if (totalPages <= PAGINATION_WINDOW) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const half = Math.floor(PAGINATION_WINDOW / 2);
    let start = Math.max(1, currentPage - half);
    const end = Math.min(totalPages, start + PAGINATION_WINDOW - 1);
    if (end - start + 1 < PAGINATION_WINDOW) {
      start = Math.max(1, end - PAGINATION_WINDOW + 1);
    }
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [totalPages, currentPage]);

  if (loading) return <ModuleWrapper title="Ultimas Llamadas" icon="📞"><LoadingSpinner /></ModuleWrapper>;
  if (error) return <ModuleWrapper title="Ultimas Llamadas" icon="📞"><ErrorMessage message={error} onRetry={refetch} /></ModuleWrapper>;
  if (!data) return null;

  return (
    <ModuleWrapper title="Ultimas Llamadas" icon="📞">
      <div className="px-4 pb-3 flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Filtrar por teléfono..."
          value={phoneFilter}
          onChange={(e) => { setPhoneFilter(e.target.value); setCurrentPage(1); }}
          className="flex-1 max-w-xs bg-gray-800 border border-gray-600 text-gray-300 text-sm rounded px-3 py-1.5 placeholder-gray-500"
        />
        {canAccessPII && (
          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting}
            title={`Descarga un Excel con las llamadas de los últimos ${EXPORT_DAYS} días`}
            className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded px-3 py-1.5 transition"
          >
            <span>📥</span>
            <span>{isExporting ? 'Generando…' : `Exportar últimos ${EXPORT_DAYS} días`}</span>
          </button>
        )}
        {exportError && (
          <span className="text-red-400 text-xs">{exportError}</span>
        )}
      </div>
      {!canAccessPII && (
        <div className="mb-4 px-4 py-2 bg-yellow-900/20 border border-yellow-500/30 rounded-lg text-yellow-400 text-sm flex items-center gap-2">
          <span>⚠️</span>
          <span>Datos anonimizados - Permisos limitados de visualizacion PII</span>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Fecha/Hora</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Cliente</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Telefono</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Tipo</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Duracion</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Estado</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Experiencia</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {paginatedCalls.map((call: CallRecord) => (
              <tr
                key={call.id}
                className="hover:bg-gray-700/50 transition"
              >
                <td className="px-4 py-3 text-sm text-gray-300">
                  <div>{call.date}</div>
                  <div className="text-gray-500 text-xs">{call.time}</div>
                </td>
                <td className="px-4 py-3 text-sm font-medium text-white">
                  <div className="flex items-center gap-2">
                    {maskName(call.caller)}
                    {!canAccessPII && <span className="text-yellow-400 text-xs">🔒</span>}
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-gray-400">
                  {call.direction === 'outbound' && call.calledNumber
                    ? maskPhone(call.calledNumber)
                    : maskPhone(call.phone)}
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold border ${DIRECTION_COLORS[call.direction || 'inbound']}`}>
                    {DIRECTION_LABELS[call.direction || 'inbound']}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-400">{call.duration}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold border ${STATUS_COLORS[call.status]}`}>
                    {STATUS_LABELS[call.status]}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <ExperienceDisplay sentiment={call.sentiment} />
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setSelectedCall(call)}
                    className="text-blue-400 hover:text-blue-300 text-sm font-semibold"
                  >
                    Ver detalles →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginacion con ventana */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700">
          <div className="text-sm text-gray-400">
            Mostrando {startIndex + 1}-{Math.min(startIndex + ITEMS_PER_PAGE, allCalls.length)} de {allCalls.length}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className={`px-3 py-1 text-sm rounded-md transition ${
                currentPage === 1
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              ← Anterior
            </button>
            {visiblePages[0] > 1 && (
              <>
                <button onClick={() => setCurrentPage(1)} className="px-3 py-1 text-sm rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600">1</button>
                {visiblePages[0] > 2 && <span className="px-1 text-gray-500">...</span>}
              </>
            )}
            {visiblePages.map(page => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={`px-3 py-1 text-sm rounded-md transition ${
                  currentPage === page
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {page}
              </button>
            ))}
            {visiblePages[visiblePages.length - 1] < totalPages && (
              <>
                {visiblePages[visiblePages.length - 1] < totalPages - 1 && <span className="px-1 text-gray-500">...</span>}
                <button onClick={() => setCurrentPage(totalPages)} className="px-3 py-1 text-sm rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600">{totalPages}</button>
              </>
            )}
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className={`px-3 py-1 text-sm rounded-md transition ${
                currentPage === totalPages
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Siguiente →
            </button>
          </div>
        </div>
      )}
    </ModuleWrapper>
  );
};

export default React.memo(RecentCallsModule);
