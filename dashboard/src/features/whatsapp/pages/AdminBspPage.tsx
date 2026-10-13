import React, { useState, useEffect } from 'react';
import type { WAAdminOverview } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';

const USAGE_LABELS: Record<string, string> = {
  contacts: 'Contactos',
  conversations: 'Conversaciones',
  messages: 'Mensajes',
  templates: 'Plantillas',
  campaigns: 'Campañas',
  flows: 'Flows',
  macros: 'Macros',
  surveys: 'Encuestas',
  integrations: 'Integraciones',
};

const AdminBspPage: React.FC = () => {
  const { toast } = useToast();
  const [data, setData] = useState<WAAdminOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const d = await whatsappApi.getAdminOverview();
        setData(d);
      } catch { toast('Error cargando datos admin', 'error'); }
      setLoading(false);
    })();
  }, [toast]);

  if (loading) return (
    <div className="flex items-center justify-center h-full bg-gray-900">
      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
    </div>
  );
  if (!data) return <div className="flex items-center justify-center h-full bg-gray-900 text-gray-500 text-sm">Sin datos</div>;

  const s = data.settings;

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div>
        <h1 className="text-2xl font-bold text-white">Admin BSP</h1>
        <p className="text-gray-400 text-sm">Administración del Business Service Provider de WhatsApp</p>
      </div>

      <div className="flex-1 overflow-auto space-y-6">
        {/* Connection Status */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-white">Estado de conexión</h2>
            <span className={`px-2 py-0.5 rounded text-xs ${s.is_configured ? 'bg-green-600/20 text-green-400' : 'bg-red-600/20 text-red-400'}`}>
              {s.is_configured ? 'Configurado' : 'No configurado'}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Phone Number ID</label>
              <div className="bg-gray-900 rounded-lg px-3 py-2 text-sm font-mono text-gray-300">
                {s.phone_number_id || <span className="text-gray-600">No configurado</span>}
              </div>
            </div>
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Business Account ID</label>
              <div className="bg-gray-900 rounded-lg px-3 py-2 text-sm font-mono text-gray-300">
                {s.business_account_id || <span className="text-gray-600">No configurado</span>}
              </div>
            </div>
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Número de teléfono</label>
              <div className="bg-gray-900 rounded-lg px-3 py-2 text-sm font-mono text-gray-300">
                {s.display_phone || <span className="text-gray-600">No configurado</span>}
              </div>
            </div>
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Webhook Verify Token</label>
              <div className="bg-gray-900 rounded-lg px-3 py-2 text-sm font-mono text-gray-300">
                {s.webhook_verify_token ? '••••••••' : <span className="text-gray-600">No configurado</span>}
              </div>
            </div>
          </div>
          {!s.is_configured && (
            <div className="mt-4 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
              <p className="text-xs text-amber-400">
                Para activar WhatsApp, necesitas configurar las credenciales de Meta Business API.
                Contacta con el administrador para obtener el Phone Number ID, Business Account ID y API Token.
              </p>
            </div>
          )}
        </div>

        {/* Tenant Info */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
          <h2 className="text-sm font-bold text-white mb-3">Información del tenant</h2>
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">Tenant ID</label>
            <div className="bg-gray-900 rounded-lg px-3 py-2 text-sm font-mono text-gray-300">{data.tenant_id}</div>
          </div>
        </div>

        {/* Usage Stats */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
          <h2 className="text-sm font-bold text-white mb-4">Uso del módulo</h2>
          <div className="grid grid-cols-3 md:grid-cols-5 gap-4">
            {Object.entries(data.usage).map(([key, count]) => (
              <div key={key} className="text-center bg-gray-800 rounded-xl p-4 border border-gray-700">
                <p className="text-2xl font-bold text-white">{count}</p>
                <p className="text-[10px] text-gray-500">{USAGE_LABELS[key] || key}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminBspPage;
