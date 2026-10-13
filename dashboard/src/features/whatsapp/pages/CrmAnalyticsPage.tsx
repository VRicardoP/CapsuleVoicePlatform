import React, { useState, useEffect } from 'react';
import type { WAPipelineAnalytics, WAMessagingAnalytics } from '../types';
import { whatsappApi } from '../services/whatsappApi';

const CrmAnalyticsPage: React.FC = () => {
  const [pipeline, setPipeline] = useState<WAPipelineAnalytics | null>(null);
  const [messaging, setMessaging] = useState<WAMessagingAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      whatsappApi.getPipelineAnalytics(),
      whatsappApi.getMessagingAnalytics(days),
    ]).then(([p, m]) => {
      setPipeline(p);
      setMessaging(m);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [days]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
      </div>
    );
  }

  const maxDeals = pipeline ? Math.max(...pipeline.stages.map(s => s.deal_count), 1) : 1;
  const maxDaily = messaging ? Math.max(...messaging.daily.map(d => d.inbound + d.outbound), 1) : 1;

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
        </div>
        <div className="flex gap-1">
          {[7, 14, 30].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${days === d ? 'border-green-500/30 text-green-400 bg-green-600/20' : 'border-gray-600 text-gray-400 hover:border-gray-500'}`}>
              {d} días
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto space-y-6">
        {/* Messaging KPIs */}
        {messaging && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Entrantes</p>
                <p className="text-xl font-bold text-blue-400">{messaging.messages.inbound}</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Salientes</p>
                <p className="text-xl font-bold text-green-400">{messaging.messages.outbound}</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Plantillas</p>
                <p className="text-xl font-bold text-purple-400">{messaging.messages.templates}</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Leídos</p>
                <p className="text-xl font-bold text-amber-400">{messaging.messages.read}</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Fallidos</p>
                <p className="text-xl font-bold text-red-400">{messaging.messages.failed}</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Conversaciones activas</p>
                <p className="text-xl font-bold text-white">{messaging.messages.active_conversations}</p>
              </div>
            </div>

            {/* Daily Chart */}
            {messaging.daily.length > 0 && (
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
                <h2 className="text-sm font-bold text-white mb-4">Mensajes diarios</h2>
                <div className="flex items-end gap-1" style={{ height: 160 }}>
                  {messaging.daily.map((d, i) => {
                    const inH = (d.inbound / maxDaily) * 140;
                    const outH = (d.outbound / maxDaily) * 140;
                    const dayLabel = new Date(d.day).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-0.5 group relative" title={`${dayLabel}: ${d.inbound} in / ${d.outbound} out`}>
                        <div className="flex gap-px items-end" style={{ height: 140 }}>
                          <div className="bg-blue-500/70 rounded-t-sm transition-all" style={{ width: 6, height: Math.max(inH, 1) }} />
                          <div className="bg-green-500/70 rounded-t-sm transition-all" style={{ width: 6, height: Math.max(outH, 1) }} />
                        </div>
                        {(i % Math.max(1, Math.floor(messaging.daily.length / 10)) === 0 || i === messaging.daily.length - 1) && (
                          <span className="text-[8px] text-gray-600">{dayLabel}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="flex gap-4 mt-3 text-[10px] text-gray-500">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-500/70 rounded" />Entrantes</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 bg-green-500/70 rounded" />Salientes</span>
                </div>
              </div>
            )}

            {/* Campaign stats */}
            {messaging.campaigns.total > 0 && (
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
                <h2 className="text-sm font-bold text-white mb-3">Campañas ({days} días)</h2>
                <div className="grid grid-cols-5 gap-4 text-center">
                  <div>
                    <p className="text-lg font-bold text-white">{messaging.campaigns.total}</p>
                    <p className="text-[10px] text-gray-500">Total</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-green-400">{messaging.campaigns.completed}</p>
                    <p className="text-[10px] text-gray-500">Completadas</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-blue-400">{messaging.campaigns.total_sent}</p>
                    <p className="text-[10px] text-gray-500">Enviados</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-purple-400">{messaging.campaigns.total_delivered}</p>
                    <p className="text-[10px] text-gray-500">Entregados</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-amber-400">{messaging.campaigns.total_read}</p>
                    <p className="text-[10px] text-gray-500">Leídos</p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Pipeline KPIs */}
        {pipeline && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Total Deals</p>
                <p className="text-2xl font-bold text-white">{pipeline.total_deals}</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Valor Total</p>
                <p className="text-2xl font-bold text-white">{Number(pipeline.total_value).toLocaleString('es-ES')} EUR</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Ganados</p>
                <p className="text-2xl font-bold text-green-400">{pipeline.won_deals}</p>
                <p className="text-xs text-gray-500">{Number(pipeline.won_value).toLocaleString('es-ES')} EUR</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-green-500/30 transition">
                <p className="text-[10px] text-gray-500 mb-1">Conversión</p>
                <p className="text-2xl font-bold text-blue-400">{pipeline.conversion_rate}%</p>
                <p className="text-xs text-gray-500">{pipeline.lost_deals} perdidos</p>
              </div>
            </div>

            {/* Funnel Chart */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
              <h2 className="text-sm font-bold text-white mb-4">Embudo de ventas</h2>
              <div className="space-y-3">
                {pipeline.stages.map(stage => {
                  const width = Math.max((stage.deal_count / maxDeals) * 100, 5);
                  return (
                    <div key={stage.id} className="flex items-center gap-4">
                      <div className="w-32 flex-shrink-0">
                        <p className="text-xs text-white font-medium">{stage.name}</p>
                        <p className="text-[10px] text-gray-500">{stage.deal_count} deals · {Number(stage.deal_value).toLocaleString('es-ES')} EUR</p>
                      </div>
                      <div className="flex-1 h-8 bg-gray-700 rounded overflow-hidden">
                        <div
                          className="h-full rounded flex items-center justify-end px-2 transition-all"
                          style={{ width: `${width}%`, backgroundColor: stage.color }}
                        >
                          {stage.deal_count > 0 && <span className="text-[10px] text-white font-bold">{stage.deal_count}</span>}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default CrmAnalyticsPage;
