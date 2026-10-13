import React, { useState, useEffect, useCallback } from 'react';
import type { WAIntegration } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';

const INTEGRATION_TYPES = [
  { value: 'crm', label: 'CRM', icon: '🏢' },
  { value: 'helpdesk', label: 'Helpdesk', icon: '🎧' },
  { value: 'ecommerce', label: 'E-commerce', icon: '🛒' },
  { value: 'email', label: 'Email', icon: '📧' },
  { value: 'calendar', label: 'Calendario', icon: '📅' },
  { value: 'custom_api', label: 'API personalizada', icon: '🔌' },
];

const IntegrationsPage: React.FC = () => {
  const { toast } = useToast();
  const [integrations, setIntegrations] = useState<WAIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [form, setForm] = useState({ integration_type: 'crm', name: '', api_url: '', api_key: '' });

  const fetchIntegrations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await whatsappApi.getIntegrations();
      setIntegrations(res.items);
    } catch { toast('Error cargando integraciones', 'error'); }
    setLoading(false);
  }, [toast]);

  useEffect(() => { fetchIntegrations(); }, [fetchIntegrations]);

  const openCreate = () => {
    setEditId(null);
    setForm({ integration_type: 'crm', name: '', api_url: '', api_key: '' });
    setShowModal(true);
  };

  const openEdit = (i: WAIntegration) => {
    setEditId(i.id);
    const config = i.config || {};
    setForm({
      integration_type: i.integration_type,
      name: i.name,
      api_url: (config.url || config.api_url || '') as string,
      api_key: (config.api_key || '') as string,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name) return;
    try {
      const config: Record<string, unknown> = {};
      if (form.api_url) config.url = form.api_url;
      if (form.api_key) config.api_key = form.api_key;
      if (editId) {
        await whatsappApi.updateIntegration(editId, { name: form.name, config });
        toast('Integración actualizada');
      } else {
        await whatsappApi.createIntegration({ integration_type: form.integration_type, name: form.name, config });
        toast('Integración creada');
      }
      setShowModal(false);
      fetchIntegrations();
    } catch { toast('Error guardando integración', 'error'); }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await whatsappApi.deleteIntegration(deleteId);
      toast('Integración eliminada');
      fetchIntegrations();
    } catch { toast('Error eliminando', 'error'); }
    setDeleteId(null);
  };

  const handleToggle = async (i: WAIntegration) => {
    try {
      await whatsappApi.updateIntegration(i.id, { is_active: !i.is_active });
      fetchIntegrations();
    } catch { toast('Error', 'error'); }
  };

  const handleTest = async (i: WAIntegration) => {
    setTesting(i.id);
    try {
      const res = await whatsappApi.testIntegration(i.id);
      if (res.success) toast('Conexión exitosa');
      else toast(`Fallo: ${res.error || res.message}`, 'error');
      fetchIntegrations();
    } catch { toast('Error en test', 'error'); }
    setTesting(null);
  };

  const getTypeInfo = (type: string) => INTEGRATION_TYPES.find(t => t.value === type) || { icon: '🔌', label: type };

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Integraciones</h1>
          <p className="text-gray-400 text-sm">Conecta con CRM, helpdesk, e-commerce y más</p>
        </div>
        <button onClick={openCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nueva integración</button>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[480px] border border-gray-700">
            <h2 className="text-white font-bold mb-4">{editId ? 'Editar' : 'Nueva'} integración</h2>
            <div className="space-y-3">
              {!editId && (
                <div>
                  <label className="text-[10px] text-gray-500 mb-1 block">Tipo</label>
                  <div className="grid grid-cols-3 gap-2">
                    {INTEGRATION_TYPES.map(t => (
                      <button key={t.value} onClick={() => setForm({ ...form, integration_type: t.value })}
                        className={`p-2 rounded-lg border text-center text-xs transition ${form.integration_type === t.value
                          ? 'border-green-500/30 bg-green-600/20 text-green-400'
                          : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
                        <span className="text-lg block mb-0.5">{t.icon}</span>
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Nombre" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <input type="url" value={form.api_url} onChange={e => setForm({ ...form, api_url: e.target.value })}
                placeholder="URL del API (opcional)" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <input type="password" value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })}
                placeholder="API Key (opcional)" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
              <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">{editId ? 'Guardar' : 'Crear'}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Eliminar integración"
        message="¿Seguro que quieres eliminar esta integración?" confirmLabel="Eliminar"
        onConfirm={handleDelete} onCancel={() => setDeleteId(null)} />

      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : integrations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center">
              <p className="text-gray-400 text-sm mb-2">No hay integraciones configuradas</p>
              <p className="text-gray-600 text-xs mb-4">Conecta WhatsApp con tus herramientas favoritas.</p>
              <button onClick={openCreate} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">Añadir integración</button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {integrations.map(i => {
                const typeInfo = getTypeInfo(i.integration_type);
                return (
                  <div key={i.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-4 hover:border-green-500/30 transition">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{typeInfo.icon}</span>
                        <div>
                          <h3 className="text-sm font-medium text-white">{i.name}</h3>
                          <p className="text-[10px] text-gray-500">{typeInfo.label}</p>
                        </div>
                      </div>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${i.is_active ? 'bg-green-600/20 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                        {i.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </div>
                    {i.status_message && <p className="text-[10px] text-gray-500 mb-2">{i.status_message}</p>}
                    {i.last_sync_at && <p className="text-[10px] text-gray-600 mb-2">Último sync: {new Date(i.last_sync_at).toLocaleString('es-ES')}</p>}
                    <div className="flex items-center gap-2 text-xs border-t border-gray-700 pt-2">
                      <button onClick={() => handleTest(i)} disabled={testing === i.id}
                        className="text-purple-400 hover:text-purple-300 disabled:opacity-50">
                        {testing === i.id ? 'Probando...' : 'Probar'}
                      </button>
                      <button onClick={() => handleToggle(i)} className="text-amber-400 hover:text-amber-300">{i.is_active ? 'Desactivar' : 'Activar'}</button>
                      <button onClick={() => openEdit(i)} className="text-blue-400 hover:text-blue-300">Editar</button>
                      <button onClick={() => setDeleteId(i.id)} className="text-gray-600 hover:text-red-400 ml-auto">Eliminar</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default IntegrationsPage;
