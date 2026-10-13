import React, { useState, useEffect } from 'react';
import type { WAWidgetConfig } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';

const WidgetPage: React.FC = () => {
  const { toast } = useToast();
  const [, setConfig] = useState<WAWidgetConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [embedCode, setEmbedCode] = useState('');
  const [form, setForm] = useState({
    is_active: false,
    primary_color: '#25D366',
    welcome_message: '¡Hola! ¿En qué podemos ayudarte?',
    position: 'bottom-right',
    auto_open_seconds: 0,
    business_name: '',
    offline_message: 'Estamos fuera de horario. Te responderemos pronto.',
    allowed_domains: '',
  });

  useEffect(() => {
    (async () => {
      try {
        const c = await whatsappApi.getWidgetConfig();
        setConfig(c);
        setForm({
          is_active: c.is_active,
          primary_color: c.primary_color,
          welcome_message: c.welcome_message,
          position: c.position,
          auto_open_seconds: c.auto_open_seconds,
          business_name: c.business_name || '',
          offline_message: c.offline_message,
          allowed_domains: (c.allowed_domains || []).join(', '),
        });
      } catch { /* new tenant, form defaults */ }
      setLoading(false);
    })();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const domains = form.allowed_domains
        .split(',')
        .map(d => d.trim())
        .filter(Boolean);
      const updated = await whatsappApi.updateWidgetConfig({
        is_active: form.is_active,
        primary_color: form.primary_color,
        welcome_message: form.welcome_message,
        position: form.position,
        auto_open_seconds: form.auto_open_seconds,
        business_name: form.business_name || undefined,
        offline_message: form.offline_message,
        allowed_domains: domains.length > 0 ? domains : undefined,
      });
      setConfig(updated);
      toast('Configuración guardada');
    } catch { toast('Error guardando', 'error'); }
    setSaving(false);
  };

  const fetchEmbed = async () => {
    try {
      const res = await whatsappApi.getWidgetEmbedCode();
      setEmbedCode(res.embed_code);
    } catch { toast('Error obteniendo código', 'error'); }
  };

  const copyEmbed = () => {
    navigator.clipboard.writeText(embedCode);
    toast('Código copiado');
  };

  if (loading) return (
    <div className="flex items-center justify-center h-full bg-gray-900">
      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
    </div>
  );

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div>
        <h1 className="text-2xl font-bold text-white">Widget Web</h1>
        <p className="text-gray-400 text-sm">Integra un botón de WhatsApp en tu sitio web para que los clientes inicien conversaciones.</p>
      </div>

      <div className="flex-1 overflow-auto space-y-6">
        <div className="max-w-2xl space-y-6">
          {/* Toggle */}
          <div className="flex items-center justify-between bg-gray-800 rounded-xl border border-gray-700 p-4">
            <div>
              <p className="text-sm text-white font-medium">Widget activo</p>
              <p className="text-[10px] text-gray-500">Muestra el botón de WhatsApp en tu web</p>
            </div>
            <button
              onClick={() => setForm({ ...form, is_active: !form.is_active })}
              className={`w-11 h-6 rounded-full relative transition-colors ${form.is_active ? 'bg-green-600' : 'bg-gray-600'}`}
            >
              <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${form.is_active ? 'left-5.5 translate-x-0' : 'left-0.5'}`}
                style={{ left: form.is_active ? '22px' : '2px' }} />
            </button>
          </div>

          {/* Appearance */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 space-y-3">
            <h2 className="text-sm font-medium text-white">Apariencia</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Color principal</label>
                <div className="flex items-center gap-2">
                  <input type="color" value={form.primary_color} onChange={e => setForm({ ...form, primary_color: e.target.value })}
                    className="w-8 h-8 rounded cursor-pointer border-0" />
                  <input type="text" value={form.primary_color} onChange={e => setForm({ ...form, primary_color: e.target.value })}
                    className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-green-500" maxLength={7} />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Posición</label>
                <select value={form.position} onChange={e => setForm({ ...form, position: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500">
                  <option value="bottom-right">Abajo derecha</option>
                  <option value="bottom-left">Abajo izquierda</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Nombre del negocio</label>
              <input type="text" value={form.business_name} onChange={e => setForm({ ...form, business_name: e.target.value })}
                placeholder="Tu empresa" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Auto-abrir después de (segundos, 0 = desactivado)</label>
              <input type="number" value={form.auto_open_seconds} onChange={e => setForm({ ...form, auto_open_seconds: parseInt(e.target.value) || 0 })}
                className="w-32 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" min={0} />
            </div>
          </div>

          {/* Messages */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 space-y-3">
            <h2 className="text-sm font-medium text-white">Mensajes</h2>
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Mensaje de bienvenida</label>
              <textarea value={form.welcome_message} onChange={e => setForm({ ...form, welcome_message: e.target.value })}
                rows={2} className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white resize-none focus:outline-none focus:border-green-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Mensaje fuera de horario</label>
              <textarea value={form.offline_message} onChange={e => setForm({ ...form, offline_message: e.target.value })}
                rows={2} className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white resize-none focus:outline-none focus:border-green-500" />
            </div>
          </div>

          {/* Domains */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 space-y-3">
            <h2 className="text-sm font-medium text-white">Dominios permitidos</h2>
            <p className="text-[10px] text-gray-500">Separa con comas. Vacío = todos los dominios.</p>
            <input type="text" value={form.allowed_domains} onChange={e => setForm({ ...form, allowed_domains: e.target.value })}
              placeholder="ejemplo.com, mitienda.es" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
          </div>

          {/* Preview */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
            <h2 className="text-sm font-medium text-white mb-3">Vista previa</h2>
            <div className="relative bg-gray-900 rounded-lg p-8 flex items-end" style={{ minHeight: 200, justifyContent: form.position === 'bottom-right' ? 'flex-end' : 'flex-start' }}>
              <div className="flex flex-col items-end gap-2" style={{ alignItems: form.position === 'bottom-right' ? 'flex-end' : 'flex-start' }}>
                <div className="bg-white rounded-lg p-3 shadow-lg max-w-[200px]">
                  {form.business_name && <p className="text-xs font-bold text-gray-900 mb-0.5">{form.business_name}</p>}
                  <p className="text-xs text-gray-600">{form.welcome_message}</p>
                </div>
                <div className="w-14 h-14 rounded-full flex items-center justify-center shadow-lg cursor-pointer"
                  style={{ backgroundColor: form.primary_color }}>
                  <svg className="w-7 h-7 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          {/* Embed Code */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-white">Código de instalación</h2>
              <button onClick={fetchEmbed} className="text-xs text-green-400 hover:text-green-300 font-medium transition">Generar código</button>
            </div>
            {embedCode ? (
              <div className="relative">
                <pre className="bg-gray-900 rounded-lg p-3 text-xs text-gray-300 font-mono overflow-auto">{embedCode}</pre>
                <button onClick={copyEmbed} className="absolute top-2 right-2 px-2 py-1 bg-gray-700 text-[10px] text-gray-300 rounded hover:bg-gray-600 transition">Copiar</button>
              </div>
            ) : (
              <p className="text-xs text-gray-500">Guarda la configuración y pulsa "Generar código" para obtener el snippet.</p>
            )}
          </div>

          {/* Save */}
          <button onClick={handleSave} disabled={saving}
            className="w-full py-2.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 disabled:opacity-50 font-medium transition">
            {saving ? 'Guardando...' : 'Guardar configuración'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default WidgetPage;
