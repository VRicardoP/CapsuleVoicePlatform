import React, { useState, useEffect } from 'react';
import type { WATemplate, WASegment } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';

const BroadcastPage: React.FC = () => {
  const { toast } = useToast();
  const [templates, setTemplates] = useState<WATemplate[]>([]);
  const [segments, setSegments] = useState<WASegment[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [audienceType, setAudienceType] = useState<'all' | 'segment'>('all');
  const [selectedSegments, setSelectedSegments] = useState<string[]>([]);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    Promise.all([
      whatsappApi.getTemplates({ status: 'approved', limit: 100 }),
      whatsappApi.getSegments(),
    ]).then(([tRes, sRes]) => {
      setTemplates(tRes.items);
      setSegments(sRes.items);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleSend = async () => {
    if (!selectedTemplate) { toast('Selecciona una plantilla', 'warning'); return; }
    if (audienceType === 'segment' && selectedSegments.length === 0) { toast('Selecciona al menos un segmento', 'warning'); return; }
    setSending(true);
    try {
      const audienceFilter = audienceType === 'segment' ? { segment_ids: selectedSegments } : undefined;
      const campaign = await whatsappApi.createCampaign({
        name: `Broadcast ${new Date().toLocaleDateString('es-ES')} ${new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`,
        template_id: selectedTemplate,
        audience_filter: audienceFilter,
      });
      await whatsappApi.startCampaign(campaign.id);
      toast('Broadcast enviado');
      setSent(true);
    } catch { toast('Error enviando broadcast', 'error'); }
    setSending(false);
  };

  const reset = () => {
    setSelectedTemplate('');
    setAudienceType('all');
    setSelectedSegments([]);
    setSent(false);
  };

  const template = templates.find(t => t.id === selectedTemplate);
  const totalContacts = audienceType === 'all'
    ? segments.reduce((sum, s) => Math.max(sum, s.contact_count), 0)
    : segments.filter(s => selectedSegments.includes(s.id)).reduce((sum, s) => sum + s.contact_count, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
      </div>
    );
  }

  if (sent) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="w-16 h-16 rounded-full bg-green-600/20 flex items-center justify-center">
          <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-lg font-bold text-white">Broadcast enviado</h2>
        <p className="text-sm text-gray-400">Puedes ver el progreso en la sección de Campañas.</p>
        <button onClick={reset} className="px-4 py-2 bg-gray-700 text-white text-sm rounded-lg hover:bg-gray-600 font-medium transition">Enviar otro</button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex-shrink-0">
        <h1 className="text-2xl font-bold text-white">Broadcast rápido</h1>
        <p className="text-gray-400 text-sm mt-1">Envía un mensaje masivo a tus contactos de forma rápida. Selecciona una plantilla aprobada y la audiencia.</p>
      </div>

      <div className="flex-1 overflow-auto space-y-6">
        <div className="max-w-xl space-y-6">
          {/* Step 1: Template */}
          <div>
            <h2 className="text-sm font-medium text-white mb-3">1. Selecciona plantilla</h2>
            {templates.length === 0 ? (
              <p className="text-xs text-gray-500">No hay plantillas aprobadas. Crea y envía una plantilla en la sección de Plantillas.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-auto">
                {templates.map(t => (
                  <button key={t.id} onClick={() => setSelectedTemplate(t.id)}
                    className={`w-full text-left p-3 rounded-xl border transition ${selectedTemplate === t.id
                      ? 'border-green-500 bg-green-500/10' : 'border-gray-700 hover:border-gray-600'}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-white font-medium">{t.name}</span>
                      <span className="text-[10px] text-gray-500">{t.language.toUpperCase()}</span>
                    </div>
                    <p className="text-xs text-gray-400 line-clamp-2 mt-1">{t.body_text}</p>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Step 2: Audience */}
          <div>
            <h2 className="text-sm font-medium text-white mb-3">2. Audiencia</h2>
            <div className="space-y-2">
              <button onClick={() => { setAudienceType('all'); setSelectedSegments([]); }}
                className={`w-full text-left p-3 rounded-xl border text-sm transition ${audienceType === 'all'
                  ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
                Todos los contactos
              </button>
              <button onClick={() => setAudienceType('segment')}
                className={`w-full text-left p-3 rounded-xl border text-sm transition ${audienceType === 'segment'
                  ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
                Por segmentos
              </button>
            </div>
            {audienceType === 'segment' && segments.length > 0 && (
              <div className="mt-3 ml-4 space-y-1">
                {segments.map(seg => (
                  <label key={seg.id} className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer py-1">
                    <input type="checkbox" checked={selectedSegments.includes(seg.id)}
                      onChange={e => {
                        setSelectedSegments(e.target.checked
                          ? [...selectedSegments, seg.id]
                          : selectedSegments.filter(id => id !== seg.id));
                      }} />
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: seg.color }} />
                    {seg.name} <span className="text-xs text-gray-500">({seg.contact_count})</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Summary + Send */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
            <h2 className="text-sm font-medium text-white mb-3">Resumen</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Plantilla:</span>
                <span className="text-white">{template?.name || 'Sin seleccionar'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Audiencia:</span>
                <span className="text-white">
                  {audienceType === 'all' ? 'Todos' : `${selectedSegments.length} segmentos`}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Destinatarios (est.):</span>
                <span className="text-white">~{totalContacts}</span>
              </div>
            </div>
            <button onClick={handleSend} disabled={sending || !selectedTemplate}
              className="w-full mt-4 py-2.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 disabled:opacity-50 font-medium transition">
              {sending ? 'Enviando...' : 'Enviar broadcast'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BroadcastPage;
