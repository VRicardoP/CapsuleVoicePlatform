import React, { useState, useEffect, useCallback } from 'react';
import type { WATag } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
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

const TagsPage: React.FC = () => {
  const { toast } = useToast();
  const [tags, setTags] = useState<WATag[]>([]);
  const [loading, setLoading] = useState(true);
  const { showModal, editId, deleteId, openCreate, openEdit, closeModal, confirmDelete, cancelDelete } = useModalState();
  const [form, setForm] = useState({ name: '', color: '#3B82F6' });

  const fetchTags = useCallback(async () => {
    setLoading(true);
    try {
      const data = await whatsappApi.getTags();
      setTags(data.items);
    } catch { toast('Error cargando etiquetas', 'error'); }
    setLoading(false);
  }, [toast]);

  useEffect(() => { fetchTags(); }, [fetchTags]);

  const handleOpenCreate = () => {
    setForm({ name: '', color: '#3B82F6' });
    openCreate();
  };

  const handleOpenEdit = (t: WATag) => {
    setForm({ name: t.name, color: t.color });
    openEdit(t.id);
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    try {
      if (editId) {
        await whatsappApi.updateTag(editId, { name: form.name, color: form.color });
        toast('Etiqueta actualizada');
      } else {
        await whatsappApi.createTag({ name: form.name, color: form.color });
        toast('Etiqueta creada');
      }
      closeModal();
      fetchTags();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error guardando etiqueta';
      toast(msg, 'error');
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await whatsappApi.deleteTag(deleteId);
      toast('Etiqueta eliminada');
      fetchTags();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error eliminando etiqueta';
      toast(msg, 'error');
    }
    cancelDelete();
  };

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white">Etiquetas</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Clasifica contactos con etiquetas para organizar tu inbox
          </p>
        </div>
        <button onClick={handleOpenCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">
          + Nueva etiqueta
        </button>
      </div>

      {/* Modal crear/editar */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && closeModal()}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[420px] border border-gray-700">
            <h2 className="text-white font-bold mb-4">{editId ? 'Editar' : 'Nueva'} etiqueta</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Nombre</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  onKeyDown={e => { if (e.key === 'Enter') handleSave(); }}
                  placeholder="Ej: Urgente, VIP, Nuevo"
                  autoFocus
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
                />
              </div>
              <div>
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
        title="Eliminar etiqueta"
        message="Los contactos con esta etiqueta no se eliminaran, solo se desvincularan."
        confirmLabel="Eliminar"
        onConfirm={handleDelete}
        onCancel={() => cancelDelete()}
      />

      {/* Main Card */}
      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : tags.length === 0 ? (
            <div className="bg-gray-900/50 rounded-xl border border-dashed border-gray-700 p-8 text-center">
              <p className="text-gray-400 text-sm mb-2">No hay etiquetas</p>
              <p className="text-gray-400 text-xs mb-4">Crea etiquetas para clasificar tus contactos</p>
              <button onClick={handleOpenCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">
                + Crear primera etiqueta
              </button>
            </div>
          ) : (
            <div className="grid gap-2">
              {tags.map(t => (
                <div key={t.id} className="bg-gray-900/50 rounded-xl border border-gray-700 hover:border-green-500/30 transition p-4 flex items-center gap-4">
                  <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: t.color }} />
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-white">{t.name}</h3>
                  </div>
                  <div className="flex gap-2 text-xs flex-shrink-0">
                    <button onClick={() => handleOpenEdit(t)} className="text-blue-400 hover:text-blue-300 transition">Editar</button>
                    <button onClick={() => confirmDelete(t.id)} className="text-gray-600 hover:text-red-400 transition">Eliminar</button>
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

export default TagsPage;
