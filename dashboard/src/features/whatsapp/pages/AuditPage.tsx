import React, { useState } from 'react';
import type { WAAuditLogEntry } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { usePaginatedFetch } from '../../../hooks/usePaginatedFetch';

const EVENT_TYPE_COLORS: Record<string, string> = {
  'message.received': 'bg-blue-600/20 text-blue-400',
  'message.sent': 'bg-green-600/20 text-green-400',
  'message.delivered': 'bg-teal-600/20 text-teal-400',
  'message.read': 'bg-purple-600/20 text-purple-400',
  'message.failed': 'bg-red-600/20 text-red-400',
  'conversation.opened': 'bg-amber-600/20 text-amber-400',
  'conversation.closed': 'bg-gray-600/20 text-gray-400',
};

const AuditPage: React.FC = () => {
  const [filter, setFilter] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { items: entries, total, loading, page, setPage, totalPages } = usePaginatedFetch<WAAuditLogEntry>(
    (skip, limit, filters) => whatsappApi.getAuditLogs({ event_type: filters.event_type, skip, limit }),
    { pageSize: 30, filters: { event_type: filter || undefined } },
  );

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div>
        <h1 className="text-2xl font-bold text-white">Auditoría</h1>
        <p className="text-gray-400 text-sm">Registro de todos los eventos del módulo WhatsApp</p>
      </div>

      <div className="flex items-center gap-2">
        <input type="text" value={filter} onChange={e => setFilter(e.target.value)}
          placeholder="Filtrar por tipo de evento..." className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
        <span className="text-xs text-gray-500">{total} eventos</span>
      </div>

      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : entries.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500 text-sm">No hay eventos</div>
          ) : (
            <div className="divide-y divide-gray-700/50">
              {entries.map(entry => (
                <div key={entry.id} className="px-4 py-3 hover:bg-gray-900/30 transition cursor-pointer"
                  onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${EVENT_TYPE_COLORS[entry.event_type] || 'bg-gray-700 text-gray-400'}`}>
                        {entry.event_type}
                      </span>
                      {entry.provider_event_id && (
                        <span className="text-[10px] text-gray-600 font-mono">{entry.provider_event_id.slice(0, 12)}...</span>
                      )}
                    </div>
                    <span className="text-[10px] text-gray-500">
                      {entry.created_at ? new Date(entry.created_at).toLocaleString('es-ES') : '-'}
                    </span>
                  </div>
                  {expandedId === entry.id && (
                    <div className="mt-2 bg-gray-900 rounded-lg p-3 overflow-auto max-h-48">
                      <pre className="text-[10px] text-gray-400 font-mono whitespace-pre-wrap">
                        {JSON.stringify(entry.payload, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between text-sm text-gray-400">
            <span>{total} eventos</span>
            <div className="flex gap-2">
              <button disabled={page === 0} onClick={() => setPage(p => p - 1)}
                className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 transition disabled:opacity-50">Anterior</button>
              <span className="px-3 py-1.5">{page + 1} / {totalPages}</span>
              <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}
                className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 transition disabled:opacity-50">Siguiente</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditPage;
