import React, { useState, useEffect, useCallback } from 'react';
import type { WAWebhookConfig, WAWebhookLog } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';

const EVENT_TYPES = [
  'message.received', 'message.sent', 'message.delivered', 'message.read',
  'conversation.opened', 'conversation.closed', 'contact.created', 'contact.updated',
];

const WebhooksPage: React.FC = () => {
  const { toast } = useToast();
  const [webhooks, setWebhooks] = useState<WAWebhookConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [logsWebhookId, setLogsWebhookId] = useState<string | null>(null);
  const [logs, setLogs] = useState<WAWebhookLog[]>([]);
  const [form, setForm] = useState({ name: '', url: '', events: [] as string[], secret: '' });

  const fetchWebhooks = useCallback(async () => {
    setLoading(true);
    try {
      const items = await whatsappApi.getWebhookConfigs();
      setWebhooks(items);
    } catch { toast('Error cargando webhooks', 'error'); }
    setLoading(false);
  }, [toast]);

  useEffect(() => { fetchWebhooks(); }, [fetchWebhooks]);

  const openCreate = () => {
    setEditId(null);
    setForm({ name: '', url: '', events: [], secret: '' });
    setShowModal(true);
  };

  const openEdit = (w: WAWebhookConfig) => {
    setEditId(w.id);
    setForm({ name: w.name, url: w.url, events: [...w.events], secret: '' });
    setShowModal(true);
  };

  const toggleEvent = (ev: string) => {
    setForm(prev => ({
      ...prev,
      events: prev.events.includes(ev)
        ? prev.events.filter(e => e !== ev)
        : [...prev.events, ev],
    }));
  };

  const handleSave = async () => {
    if (!form.name || !form.url || form.events.length === 0) {
      toast('Completa nombre, URL y al menos un evento', 'warning');
      return;
    }
    try {
      const data = { name: form.name, url: form.url, events: form.events, secret: form.secret || undefined };
      if (editId) {
        await whatsappApi.updateWebhookConfig(editId, data);
        toast('Webhook actualizado');
      } else {
        await whatsappApi.createWebhookConfig(data);
        toast('Webhook creado');
      }
      setShowModal(false);
      fetchWebhooks();
    } catch { toast('Error guardando webhook', 'error'); }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await whatsappApi.deleteWebhookConfig(deleteId);
      toast('Webhook eliminado');
      fetchWebhooks();
    } catch { toast('Error eliminando', 'error'); }
    setDeleteId(null);
  };

  const handleToggle = async (w: WAWebhookConfig) => {
    try {
      await whatsappApi.updateWebhookConfig(w.id, { is_active: !w.is_active });
      fetchWebhooks();
    } catch { toast('Error', 'error'); }
  };

  const handleTest = async (w: WAWebhookConfig) => {
    try {
      const res = await whatsappApi.testWebhook(w.id);
      if (res.success) toast('Test exitoso');
      else toast(`Test fallido: ${res.error || `HTTP ${res.status_code}`}`, 'error');
    } catch { toast('Error enviando test', 'error'); }
  };

  const openLogs = async (webhookId: string) => {
    setLogsWebhookId(webhookId);
    try {
      const res = await whatsappApi.getWebhookLogs(webhookId);
      setLogs(res.items);
    } catch { toast('Error cargando logs', 'error'); }
  };

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Webhooks</h1>
          <p className="text-gray-400 text-sm">Notifica eventos de WhatsApp a servicios externos</p>
        </div>
        <button onClick={openCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nuevo webhook</button>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[520px] border border-gray-700 max-h-[80vh] overflow-auto">
            <h2 className="text-white font-bold mb-4">{editId ? 'Editar' : 'Nuevo'} webhook</h2>
            <div className="space-y-3">
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Nombre del webhook" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <input type="url" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })}
                placeholder="https://tu-servidor.com/webhook" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <input type="text" value={form.secret} onChange={e => setForm({ ...form, secret: e.target.value })}
                placeholder="Secret (opcional)" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <div>
                <p className="text-xs text-gray-400 mb-2">Eventos ({form.events.length})</p>
                <div className="grid grid-cols-2 gap-1">
                  {EVENT_TYPES.map(ev => (
                    <label key={ev} className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer py-1 px-2 rounded hover:bg-gray-900/30">
                      <input type="checkbox" checked={form.events.includes(ev)} onChange={() => toggleEvent(ev)} />
                      {ev}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
              <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">{editId ? 'Guardar' : 'Crear'}</button>
            </div>
          </div>
        </div>
      )}

      {logsWebhookId && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && setLogsWebhookId(null)}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[520px] border border-gray-700 max-h-[80vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-bold">Logs de entrega</h2>
              <button onClick={() => setLogsWebhookId(null)} className="text-gray-400 hover:text-white text-sm font-medium transition">Cerrar</button>
            </div>
            {logs.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-8">No hay logs aun</p>
            ) : (
              <div className="space-y-2">
                {logs.map(log => (
                  <div key={log.id} className="bg-gray-900/50 rounded-xl p-3 border border-gray-700/50 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${log.success ? 'bg-green-500' : 'bg-red-500'}`} />
                      <span className="text-sm text-white">{log.event_type}</span>
                    </div>
                    <div className="text-right">
                      {log.response_code && <span className="text-xs text-gray-400 mr-2">HTTP {log.response_code}</span>}
                      <span className="text-[10px] text-gray-500">{new Date(log.sent_at).toLocaleString('es-ES')}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Eliminar webhook"
        message="¿Seguro que quieres eliminar este webhook?" confirmLabel="Eliminar"
        onConfirm={handleDelete} onCancel={() => setDeleteId(null)} />

      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : webhooks.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500 text-sm">No hay webhooks configurados</div>
          ) : (
            <div className="space-y-3">
              {webhooks.map(w => (
                <div key={w.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-4 hover:border-green-500/30 transition">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-medium text-white">{w.name}</h3>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${w.is_active ? 'bg-green-600/20 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                        {w.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                      {w.failure_count > 0 && <span className="px-1.5 py-0.5 bg-red-600/20 text-red-400 rounded text-[10px]">{w.failure_count} fallos</span>}
                    </div>
                    <div className="flex gap-2 text-xs">
                      <button onClick={() => handleTest(w)} className="text-purple-400 hover:text-purple-300">Test</button>
                      <button onClick={() => openLogs(w.id)} className="text-gray-400 hover:text-gray-300">Logs</button>
                      <button onClick={() => handleToggle(w)} className="text-amber-400 hover:text-amber-300">{w.is_active ? 'Desactivar' : 'Activar'}</button>
                      <button onClick={() => openEdit(w)} className="text-blue-400 hover:text-blue-300">Editar</button>
                      <button onClick={() => setDeleteId(w.id)} className="text-gray-600 hover:text-red-400">Eliminar</button>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 font-mono mb-1">{w.url}</p>
                  <div className="flex flex-wrap gap-1">
                    {w.events.map(ev => (
                      <span key={ev} className="px-1.5 py-0.5 bg-gray-700 rounded text-[10px] text-gray-400">{ev}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WebhooksPage;
