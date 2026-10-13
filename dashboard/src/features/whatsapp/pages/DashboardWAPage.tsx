import React, { useState, useEffect, useCallback } from 'react';
import type { WADashboardOverview } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import PageShell from '../../../components/ui/PageShell';

const DashboardWAPage: React.FC = () => {
  const { toast } = useToast();
  const [data, setData] = useState<WADashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const d = await whatsappApi.getDashboardOverview();
      setData(d);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Error cargando dashboard';
      setError(msg);
      toast(msg, 'error');
    }
    setLoading(false);
  }, [toast]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (!data && !loading && !error) return <div className="flex items-center justify-center h-full text-gray-500 text-sm">Sin datos disponibles</div>;

  const kpis = data ? [
    { label: 'Conversaciones abiertas', value: data.conversations.open, color: 'text-blue-400' },
    { label: 'Sin asignar', value: data.conversations.unassigned, color: data.conversations.unassigned > 0 ? 'text-amber-400' : 'text-gray-400' },
    { label: 'Cerradas', value: data.conversations.closed, color: 'text-green-400' },
    { label: 'Contactos', value: data.contacts_total, color: 'text-white' },
    { label: 'Campañas activas', value: data.active_campaigns, color: 'text-purple-400' },
    { label: 'Brechas SLA', value: data.sla_breaches_unresolved, color: data.sla_breaches_unresolved > 0 ? 'text-red-400' : 'text-green-400' },
  ] : [];

  return (
    <PageShell title="Dashboard WhatsApp" accent="green" loading={loading} error={error} onRetry={fetchData}>
      <div className="flex-1 overflow-auto space-y-6">
        {/* KPI Grid */}
        <div id="wa-dashboard-kpis" className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          {kpis.map((kpi, i) => (
            <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-green-500/30 transition">
              <p className="text-xs text-gray-400 mb-1">{kpi.label}</p>
              <p className={`text-2xl font-bold ${kpi.color}`}>{kpi.value}</p>
            </div>
          ))}
        </div>

        {/* Response Time */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div id="wa-dashboard-response" className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <h2 className="text-sm font-bold text-white mb-3">Tiempo de respuesta (7 días)</h2>
            {data?.avg_response_minutes !== null && data?.avg_response_minutes !== undefined ? (
              <div className="flex items-baseline gap-2">
                <span className={`text-4xl font-bold ${data.avg_response_minutes <= 5 ? 'text-green-400' : data.avg_response_minutes <= 15 ? 'text-amber-400' : 'text-red-400'}`}>
                  {data.avg_response_minutes}
                </span>
                <span className="text-sm text-gray-500">minutos de media</span>
              </div>
            ) : (
              <p className="text-sm text-gray-500">Sin datos suficientes</p>
            )}
            <div className="mt-3 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all ${
                data?.avg_response_minutes !== null && data?.avg_response_minutes !== undefined && data.avg_response_minutes <= 5 ? 'bg-green-500 w-1/4' :
                data?.avg_response_minutes !== null && data?.avg_response_minutes !== undefined && data.avg_response_minutes <= 15 ? 'bg-amber-500 w-2/4' :
                data?.avg_response_minutes !== null && data?.avg_response_minutes !== undefined ? 'bg-red-500 w-3/4' : 'w-0'
              }`} />
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <h2 className="text-sm font-bold text-white mb-3">Mensajes hoy</h2>
            <div className="flex gap-8">
              <div>
                <p className="text-3xl font-bold text-blue-400">{data?.messages_today?.inbound ?? 0}</p>
                <p className="text-xs text-gray-500">Entrantes</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-green-400">{data?.messages_today?.outbound ?? 0}</p>
                <p className="text-xs text-gray-500">Salientes</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">{(data?.messages_today?.inbound ?? 0) + (data?.messages_today?.outbound ?? 0)}</p>
                <p className="text-xs text-gray-500">Total</p>
              </div>
            </div>
          </div>
        </div>

        {/* Conversation Status Breakdown */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
          <h2 className="text-sm font-bold text-white mb-4">Estado de conversaciones</h2>
          <div className="flex items-center gap-1 h-8 rounded-lg overflow-hidden">
            {(data?.conversations?.total ?? 0) > 0 ? (
              <>
                {(data?.conversations?.open ?? 0) > 0 && (
                  <div className="bg-blue-500 h-full flex items-center justify-center"
                    style={{ width: `${((data?.conversations?.open ?? 0) / (data?.conversations?.total ?? 1)) * 100}%` }}>
                    <span className="text-[10px] text-white font-bold px-1">{data?.conversations?.open}</span>
                  </div>
                )}
                {(data?.conversations?.closed ?? 0) > 0 && (
                  <div className="bg-green-500 h-full flex items-center justify-center"
                    style={{ width: `${((data?.conversations?.closed ?? 0) / (data?.conversations?.total ?? 1)) * 100}%` }}>
                    <span className="text-[10px] text-white font-bold px-1">{data?.conversations?.closed}</span>
                  </div>
                )}
              </>
            ) : (
              <div className="bg-gray-700 h-full w-full flex items-center justify-center">
                <span className="text-[10px] text-gray-500">Sin conversaciones</span>
              </div>
            )}
          </div>
          <div className="flex gap-4 mt-3 text-[10px] text-gray-500">
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-500 rounded" />Abiertas ({data?.conversations?.open ?? 0})</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-green-500 rounded" />Cerradas ({data?.conversations?.closed ?? 0})</span>
            <span className="ml-auto">Total: {data?.conversations?.total ?? 0}</span>
          </div>
        </div>
      </div>
    </PageShell>
  );
};

export default DashboardWAPage;
