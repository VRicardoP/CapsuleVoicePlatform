import React, { useState, useEffect, useCallback } from 'react';
import type { WASlaPolicy, WASlaBreach } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import { useModalState } from '../../../hooks/useModalState';

const SlaPage: React.FC = () => {
  const { toast } = useToast();
  const [policies, setPolicies] = useState<WASlaPolicy[]>([]);
  const [breaches, setBreaches] = useState<WASlaBreach[]>([]);
  const [breachTotal, setBreachTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'policies' | 'breaches'>('policies');
  const { showModal, editId, deleteId, openCreate, openEdit, closeModal, confirmDelete, cancelDelete } = useModalState();
  const [form, setForm] = useState({
    name: '', first_response_minutes: '5', resolution_minutes: '60',
    priority: 'normal', escalation_email: '', business_hours_only: true,
  });

  const fetchPolicies = useCallback(async () => {
    try {
      const items = await whatsappApi.getSlaPolicies();
      setPolicies(items);
    } catch { toast('Error cargando politicas SLA', 'error'); }
  }, [toast]);

  const fetchBreaches = useCallback(async () => {
    try {
      const res = await whatsappApi.getSlaBreaches({ limit: 100 });
      setBreaches(res.items);
      setBreachTotal(res.total);
    } catch { toast('Error cargando brechas SLA', 'error'); }
  }, [toast]);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchPolicies(), fetchBreaches()]).finally(() => setLoading(false));
  }, [fetchPolicies, fetchBreaches]);

  const handleOpenCreate = () => {
    setForm({ name: '', first_response_minutes: '5', resolution_minutes: '60', priority: 'normal', escalation_email: '', business_hours_only: true });
    openCreate();
  };

  const handleOpenEdit = (p: WASlaPolicy) => {
    setForm({
      name: p.name,
      first_response_minutes: String(p.first_response_minutes),
      resolution_minutes: String(p.resolution_minutes),
      priority: p.priority,
      escalation_email: p.escalation_email || '',
      business_hours_only: p.business_hours_only,
    });
    openEdit(p.id);
  };

  const handleSave = async () => {
    if (!form.name) return;
    try {
      const data = {
        name: form.name,
        first_response_minutes: parseInt(form.first_response_minutes) || 5,
        resolution_minutes: parseInt(form.resolution_minutes) || 60,
        priority: form.priority,
        escalation_email: form.escalation_email || undefined,
        business_hours_only: form.business_hours_only,
      };
      if (editId) {
        await whatsappApi.updateSlaPolicy(editId, data);
        toast('Politica actualizada');
      } else {
        await whatsappApi.createSlaPolicy(data);
        toast('Politica creada');
      }
      closeModal();
      fetchPolicies();
    } catch { toast('Error guardando politica', 'error'); }
  };

  const handleToggle = async (p: WASlaPolicy) => {
    try {
      await whatsappApi.updateSlaPolicy(p.id, { is_active: !p.is_active });
      fetchPolicies();
    } catch { toast('Error actualizando', 'error'); }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await whatsappApi.deleteSlaPolicy(deleteId);
      toast('Politica eliminada');
      fetchPolicies();
    } catch { toast('Error eliminando', 'error'); }
    cancelDelete();
  };

  if (loading) return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div>
        <h1 className="text-2xl font-bold text-white">SLA</h1>
        <p className="text-gray-400 text-sm">Acuerdos de nivel de servicio para tiempos de respuesta</p>
      </div>
      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">SLA</h1>
          <p className="text-gray-400 text-sm">Acuerdos de nivel de servicio para tiempos de respuesta</p>
        </div>
        <button onClick={handleOpenCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nueva politica</button>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && closeModal()}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[480px] border border-gray-700">
            <h2 className="text-white font-bold mb-4">{editId ? 'Editar' : 'Nueva'} politica SLA</h2>
            <div className="space-y-3">
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Nombre" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-gray-500 mb-1 block">1a respuesta (min)</label>
                  <input type="number" value={form.first_response_minutes} onChange={e => setForm({ ...form, first_response_minutes: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" min={1} />
                </div>
                <div>
                  <label className="text-[10px] text-gray-500 mb-1 block">Resolucion (min)</label>
                  <input type="number" value={form.resolution_minutes} onChange={e => setForm({ ...form, resolution_minutes: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" min={1} />
                </div>
              </div>
              <div className="flex gap-2">
                <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500">
                  <option value="low">Baja</option><option value="normal">Normal</option>
                  <option value="high">Alta</option><option value="urgent">Urgente</option>
                </select>
                <input type="email" value={form.escalation_email} onChange={e => setForm({ ...form, escalation_email: e.target.value })}
                  placeholder="Email escalado (opcional)" className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input type="checkbox" checked={form.business_hours_only} onChange={e => setForm({ ...form, business_hours_only: e.target.checked })} />
                Solo horario laboral
              </label>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => closeModal()} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
              <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">{editId ? 'Guardar' : 'Crear'}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Eliminar politica SLA"
        message="¿Seguro que quieres eliminar esta politica?" confirmLabel="Eliminar"
        onConfirm={handleDelete} onCancel={() => cancelDelete()} />

      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="flex gap-2">
            <button onClick={() => setTab('policies')} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${tab === 'policies' ? 'bg-green-600/20 text-green-400 border border-green-500/30' : 'border border-gray-600 text-gray-400'}`}>
              Politicas ({policies.length})
            </button>
            <button onClick={() => setTab('breaches')} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${tab === 'breaches' ? 'bg-red-600/20 text-red-400 border border-red-500/30' : 'border border-gray-600 text-gray-400'}`}>
              Brechas ({breachTotal})
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-auto p-6">
          {tab === 'policies' ? (
            policies.length === 0 ? (
              <div className="flex items-center justify-center h-32 text-gray-500 text-sm">No hay politicas SLA configuradas</div>
            ) : (
              <div className="space-y-3">
                {policies.map(p => (
                  <div key={p.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-4 hover:border-green-500/30 transition">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-medium text-white">{p.name}</h3>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${p.is_active ? 'bg-green-600/20 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                          {p.is_active ? 'Activa' : 'Inactiva'}
                        </span>
                        <span className="px-1.5 py-0.5 bg-gray-700 rounded text-[10px] text-gray-400">{p.priority}</span>
                      </div>
                      <div className="flex gap-2 text-xs">
                        <button onClick={() => handleToggle(p)} className="text-amber-400 hover:text-amber-300">{p.is_active ? 'Desactivar' : 'Activar'}</button>
                        <button onClick={() => handleOpenEdit(p)} className="text-blue-400 hover:text-blue-300">Editar</button>
                        <button onClick={() => confirmDelete(p.id)} className="text-gray-600 hover:text-red-400">Eliminar</button>
                      </div>
                    </div>
                    <div className="flex gap-6 text-xs text-gray-400">
                      <span>1a respuesta: <strong className="text-white">{p.first_response_minutes} min</strong></span>
                      <span>Resolucion: <strong className="text-white">{p.resolution_minutes} min</strong></span>
                      {p.business_hours_only && <span className="text-gray-500">Solo horario laboral</span>}
                      {p.escalation_email && <span className="text-gray-500">Escalado: {p.escalation_email}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            breaches.length === 0 ? (
              <div className="flex items-center justify-center h-32 text-gray-500 text-sm">No hay brechas SLA registradas</div>
            ) : (
              <div className="space-y-2">
                {breaches.map(b => (
                  <div key={b.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-3 hover:border-green-500/30 transition flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`w-2 h-2 rounded-full ${b.resolved_at ? 'bg-green-500' : 'bg-red-500'}`} />
                      <div>
                        <span className="text-sm text-white">{b.breach_type === 'first_response' ? '1a respuesta' : 'Resolucion'}</span>
                        <p className="text-[10px] text-gray-500">Conv: {b.conversation_id.slice(0, 8)}...</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-400">{new Date(b.breached_at).toLocaleString('es-ES')}</p>
                      {b.resolved_at && <p className="text-[10px] text-green-500">Resuelto</p>}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
};

export default SlaPage;
