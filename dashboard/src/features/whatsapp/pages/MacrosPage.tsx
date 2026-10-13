import React, { useState, useEffect, useCallback } from 'react';
import type { WAMacro } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';

const CATEGORIES = ['general', 'greeting', 'closing', 'faq', 'sales'];

const MacrosPage: React.FC = () => {
  const { toast } = useToast();
  const [macros, setMacros] = useState<WAMacro[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCat, setFilterCat] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', shortcut: '', text: '', category: 'general' });

  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const items = await whatsappApi.getMacros(filterCat || undefined);
      setMacros(items);
    } catch { toast('Error cargando macros', 'error'); }
    setLoading(false);
  }, [filterCat, toast]);

  useEffect(() => { fetch_(); }, [fetch_]);

  const openCreate = () => {
    setEditId(null);
    setForm({ name: '', shortcut: '', text: '', category: 'general' });
    setShowModal(true);
  };

  const openEdit = (m: WAMacro) => {
    setEditId(m.id);
    setForm({ name: m.name, shortcut: m.shortcut || '', text: m.text, category: m.category });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name || !form.text) return;
    try {
      if (editId) {
        await whatsappApi.updateMacro(editId, { ...form, shortcut: form.shortcut || undefined });
        toast('Macro actualizada');
      } else {
        await whatsappApi.createMacro({ ...form, shortcut: form.shortcut || undefined });
        toast('Macro creada');
      }
      setShowModal(false);
      fetch_();
    } catch { toast('Error guardando macro', 'error'); }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await whatsappApi.deleteMacro(deleteId);
      toast('Macro eliminada');
      fetch_();
    } catch { toast('Error eliminando macro', 'error'); }
    setDeleteId(null);
  };

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Macros</h1>
            <p className="text-gray-400 text-sm">Respuestas rapidas y textos predefinidos para agentes</p>
          </div>
          <button onClick={openCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nueva macro</button>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[480px] border border-gray-700">
            <h2 className="text-white font-bold mb-4">{editId ? 'Editar' : 'Nueva'} macro</h2>
            <div className="space-y-3">
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Nombre de la macro" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <div className="flex gap-2">
                <input type="text" value={form.shortcut} onChange={e => setForm({ ...form, shortcut: e.target.value })}
                  placeholder="Atajo (ej: /saludo)" className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
                <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500">
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <textarea value={form.text} onChange={e => setForm({ ...form, text: e.target.value })}
                placeholder="Texto de la macro..." rows={5}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-green-500" />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
              <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">{editId ? 'Guardar' : 'Crear'}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Eliminar macro"
        message="¿Seguro que quieres eliminar esta macro?" confirmLabel="Eliminar"
        onConfirm={handleDelete} onCancel={() => setDeleteId(null)} />

      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="flex gap-2">
            {['', ...CATEGORIES].map(c => (
              <button key={c} onClick={() => setFilterCat(c)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium ${filterCat === c ? 'bg-green-600/20 text-green-400 border border-green-500/30' : 'border border-gray-600 text-gray-400'}`}>
                {c || 'Todas'}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : macros.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500 text-sm">No hay macros</div>
          ) : (
            <div className="space-y-2">
              {macros.map(m => (
                <div key={m.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-4 hover:border-green-500/30 transition">
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-medium text-white">{m.name}</h3>
                      {m.shortcut && <span className="px-1.5 py-0.5 bg-gray-700 rounded text-[10px] text-gray-400 font-mono">{m.shortcut}</span>}
                      <span className="px-1.5 py-0.5 bg-gray-700 rounded text-[10px] text-gray-500">{m.category}</span>
                    </div>
                    <div className="flex gap-2 text-xs">
                      <button onClick={() => openEdit(m)} className="text-blue-400 hover:text-blue-300">Editar</button>
                      <button onClick={() => setDeleteId(m.id)} className="text-gray-600 hover:text-red-400">Eliminar</button>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 whitespace-pre-wrap line-clamp-3">{m.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MacrosPage;
