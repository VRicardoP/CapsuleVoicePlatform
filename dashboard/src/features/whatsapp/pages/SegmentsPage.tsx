import React, { useState, useEffect, useCallback } from 'react';
import type { WASegment, WAContactDetail } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useWhatsApp } from '../context/WhatsAppContext';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import { formatPhone } from '../utils';
import { useModalState } from '../../../hooks/useModalState';

const COLORS = [
  { value: '#10B981', label: 'Verde' },
  { value: '#3B82F6', label: 'Azul' },
  { value: '#F59E0B', label: 'Amarillo' },
  { value: '#EF4444', label: 'Rojo' },
  { value: '#8B5CF6', label: 'Morado' },
  { value: '#EC4899', label: 'Rosa' },
  { value: '#6B7280', label: 'Gris' },
  { value: '#F97316', label: 'Naranja' },
];

const ICONS = [
  { value: 'inbox', emoji: '\u{1F4E5}' },
  { value: 'star', emoji: '\u2B50' },
  { value: 'phone', emoji: '\u{1F4DE}' },
  { value: 'check-circle', emoji: '\u2705' },
  { value: 'clock', emoji: '\u{1F551}' },
  { value: 'x-circle', emoji: '\u274C' },
  { value: 'message-circle', emoji: '\u{1F4AC}' },
];

const SegmentsPage: React.FC = () => {
  const { toast } = useToast();
  const { refetchSegments } = useWhatsApp();
  const [segments, setSegments] = useState<WASegment[]>([]);
  const [loading, setLoading] = useState(true);
  const { showModal, editId, deleteId, openCreate, openEdit, closeModal, confirmDelete, cancelDelete } = useModalState();
  const [form, setForm] = useState({ name: '', description: '', color: '#10B981', icon: 'star' });
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [segContacts, setSegContacts] = useState<WAContactDetail[]>([]);
  const [segContactsLoading, setSegContactsLoading] = useState(false);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const data = await whatsappApi.getSegments();
      setSegments(data.items);
    } catch { toast('Error cargando segmentos', 'error'); }
    setLoading(false);
  }, [toast]);

  useEffect(() => { fetch_(); }, [fetch_]);

  const handleOpenCreate = () => {
    setForm({ name: '', description: '', color: '#10B981', icon: 'star' });
    openCreate();
  };

  const handleOpenEdit = (s: WASegment) => {
    setForm({ name: s.name, description: s.description || '', color: s.color, icon: s.icon || 'star' });
    openEdit(s.id);
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    try {
      if (editId) {
        await whatsappApi.updateSegment(editId, { name: form.name, color: form.color });
        toast('Segmento actualizado');
      } else {
        await whatsappApi.createSegment({
          name: form.name,
          color: form.color,
          icon: form.icon || undefined,
          description: form.description || undefined,
        });
        toast('Segmento creado');
      }
      closeModal();
      fetch_();
      refetchSegments();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error guardando segmento';
      toast(msg, 'error');
    }
  };

  const toggleExpand = async (segId: string) => {
    if (expandedId === segId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(segId);
    setSegContactsLoading(true);
    try {
      const res = await whatsappApi.getContacts({ segment: segId, limit: 100 });
      setSegContacts(res.items);
    } catch { toast('Error cargando contactos del segmento', 'error'); }
    setSegContactsLoading(false);
  };

  const removeContactFromSegment = async (contact: WAContactDetail, segId: string) => {
    const remainingIds = contact.segments.filter(s => s.id !== segId).map(s => s.id);
    try {
      await whatsappApi.assignContactSegments(contact.id, remainingIds);
      setSegContacts(prev => prev.filter(c => c.id !== contact.id));
      // Update count locally
      setSegments(prev => prev.map(s => s.id === segId ? { ...s, contact_count: Math.max(0, s.contact_count - 1) } : s));
      toast('Contacto quitado del segmento');
      refetchSegments();
    } catch { toast('Error quitando contacto', 'error'); }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await whatsappApi.deleteSegment(deleteId);
      toast('Segmento eliminado');
      fetch_();
      refetchSegments();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error eliminando segmento';
      toast(msg, 'error');
    }
    cancelDelete();
  };

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white">Segmentos</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Agrupa contactos para filtrar conversaciones y segmentar campanas
          </p>
        </div>
        <button onClick={handleOpenCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">
          + Nuevo segmento
        </button>
      </div>

      {/* Modal crear/editar */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && closeModal()}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[480px] border border-gray-700">
            <h2 className="text-white font-bold mb-4">{editId ? 'Editar' : 'Nuevo'} segmento</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Nombre</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="Ej: Clientes VIP"
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Descripcion (opcional)</label>
                <textarea
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  placeholder="Describe para que sirve este segmento..."
                  rows={2}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500 resize-none"
                />
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-xs text-gray-400 mb-1">Color</label>
                  <div className="flex gap-1.5 flex-wrap">
                    {COLORS.map(c => (
                      <button
                        key={c.value}
                        onClick={() => setForm({ ...form, color: c.value })}
                        className={`w-7 h-7 rounded-full border-2 transition ${
                          form.color === c.value ? 'border-white scale-110' : 'border-transparent opacity-60 hover:opacity-100'
                        }`}
                        style={{ backgroundColor: c.value }}
                        title={c.label}
                      />
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Icono</label>
                  <div className="flex gap-1.5">
                    {ICONS.map(i => (
                      <button
                        key={i.value}
                        onClick={() => setForm({ ...form, icon: i.value })}
                        className={`w-7 h-7 rounded flex items-center justify-center text-sm transition ${
                          form.icon === i.value ? 'bg-gray-600 ring-1 ring-white' : 'bg-gray-700 hover:bg-gray-600'
                        }`}
                      >
                        {i.emoji}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => closeModal()} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
              <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">
                {editId ? 'Guardar' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm delete */}
      <ConfirmDialog
        open={!!deleteId}
        title="Eliminar segmento"
        message="Los contactos asignados a este segmento no se eliminaran, solo se desvincularan."
        confirmLabel="Eliminar"
        onConfirm={handleDelete}
        onCancel={() => cancelDelete()}
      />

      {/* Main Card */}
      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : segments.length === 0 ? (
            <div className="bg-gray-900/50 rounded-xl border border-dashed border-gray-700 p-8 text-center">
              <p className="text-gray-400 text-sm mb-2">No hay segmentos</p>
              <p className="text-gray-400 text-xs mb-4">Crea segmentos para agrupar contactos y filtrar conversaciones</p>
              <button onClick={handleOpenCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">
                + Crear primer segmento
              </button>
            </div>
          ) : (
            <div className="grid gap-2">
              {segments.map(s => (
                <div key={s.id} className="bg-gray-900/50 rounded-xl border border-gray-700 hover:border-green-500/30 transition">
                  <div className="p-4 flex items-center gap-4">
                    <button onClick={() => toggleExpand(s.id)} className="w-3 h-3 rounded-full flex-shrink-0 cursor-pointer" style={{ backgroundColor: s.color }} title="Ver contactos" />
                    <div className="flex-1 min-w-0 cursor-pointer" onClick={() => toggleExpand(s.id)}>
                      <h3 className="text-sm font-medium text-white">{s.name}</h3>
                      {s.description && <p className="text-xs text-gray-400 mt-0.5">{s.description}</p>}
                    </div>
                    <button onClick={() => toggleExpand(s.id)} className="text-right flex-shrink-0 cursor-pointer hover:opacity-80">
                      <span className="text-sm font-semibold text-white">{s.contact_count}</span>
                      <span className="text-xs text-gray-400 ml-1">contactos</span>
                      <span className="text-xs text-gray-400 ml-1">{expandedId === s.id ? '\u25B2' : '\u25BC'}</span>
                    </button>
                    <div className="flex gap-2 text-xs flex-shrink-0">
                      <button onClick={() => handleOpenEdit(s)} className="text-blue-400 hover:text-blue-300 transition">Editar</button>
                      <button onClick={() => confirmDelete(s.id)} className="text-gray-600 hover:text-red-400 transition">Eliminar</button>
                    </div>
                  </div>
                  {expandedId === s.id && (
                    <div className="border-t border-gray-700 px-4 py-3">
                      {segContactsLoading ? (
                        <div className="flex items-center justify-center py-3"><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-500" /></div>
                      ) : segContacts.length === 0 ? (
                        <p className="text-xs text-gray-400">No hay contactos en este segmento</p>
                      ) : (
                        <div className="space-y-1 max-h-60 overflow-auto">
                          {segContacts.map(c => (
                            <div key={c.id} className="flex items-center gap-3 py-1.5 px-2 rounded hover:bg-gray-700/50 text-sm transition">
                              <span className="text-white flex-1 min-w-0 truncate">{c.display_name || formatPhone(c.phone_e164)}</span>
                              <span className="text-gray-400 text-xs font-mono flex-shrink-0">{formatPhone(c.phone_e164)}</span>
                              <button onClick={() => removeContactFromSegment(c, s.id)} className="text-xs text-gray-500 hover:text-red-400 flex-shrink-0 transition">Quitar</button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SegmentsPage;
