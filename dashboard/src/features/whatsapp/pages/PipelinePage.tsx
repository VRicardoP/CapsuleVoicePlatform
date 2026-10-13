import React, { useState, useEffect, useCallback } from 'react';
import type { WAPipelineStage, WADeal, WAContactDetail } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';

const PipelinePage: React.FC = () => {
  const { toast } = useToast();
  const [stages, setStages] = useState<WAPipelineStage[]>([]);
  const [deals, setDeals] = useState<WADeal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', stage_id: '', value: '', contact_id: '', notes: '', expected_close_date: '' });
  const [dragDealId, setDragDealId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editDeal, setEditDeal] = useState<WADeal | null>(null);
  const [contacts, setContacts] = useState<WAContactDetail[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [stagesRes, dealsRes] = await Promise.all([
        whatsappApi.getPipelineStages(),
        whatsappApi.getDeals({ limit: 200 }),
      ]);
      setStages(stagesRes);
      setDeals(dealsRes.items);
    } catch { toast('Error cargando pipeline', 'error'); }
    setLoading(false);
  }, [toast]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const fetchContacts = async () => {
    try { const res = await whatsappApi.getContacts({ limit: 100 }); setContacts(res.items); } catch { /* empty */ }
  };

  const openCreate = () => {
    setForm({ title: '', stage_id: stages[0]?.id || '', value: '', contact_id: '', notes: '', expected_close_date: '' });
    setEditDeal(null);
    setShowCreate(true);
    fetchContacts();
  };

  const openEdit = (deal: WADeal) => {
    setForm({
      title: deal.title, stage_id: deal.stage_id, value: deal.value ? String(deal.value) : '',
      contact_id: deal.contact_id || '', notes: deal.notes || '', expected_close_date: deal.expected_close_date || '',
    });
    setEditDeal(deal);
    setShowCreate(true);
    fetchContacts();
  };

  const handleSave = async () => {
    if (!form.title || !form.stage_id) return;
    try {
      if (editDeal) {
        await whatsappApi.updateDeal(editDeal.id, {
          title: form.title, stage_id: form.stage_id,
          value: form.value ? parseFloat(form.value) : undefined,
          notes: form.notes || undefined, expected_close_date: form.expected_close_date || undefined,
        });
        toast('Deal actualizado');
      } else {
        await whatsappApi.createDeal({
          title: form.title, stage_id: form.stage_id,
          value: form.value ? parseFloat(form.value) : 0,
          contact_id: form.contact_id || undefined,
          notes: form.notes || undefined, expected_close_date: form.expected_close_date || undefined,
        });
        toast('Deal creado');
      }
      setShowCreate(false);
      setEditDeal(null);
      fetchData();
    } catch { toast('Error guardando deal', 'error'); }
  };

  const handleDrop = async (stageId: string) => {
    if (!dragDealId) return;
    const deal = deals.find(d => d.id === dragDealId);
    if (deal && deal.stage_id !== stageId) {
      try { await whatsappApi.moveDeal(dragDealId, stageId); toast('Deal movido'); fetchData(); }
      catch { toast('Error moviendo deal', 'error'); }
    }
    setDragDealId(null);
  };

  const handleDeleteConfirmed = async () => {
    if (!deleteId) return;
    try { await whatsappApi.deleteDeal(deleteId); toast('Deal eliminado'); fetchData(); }
    catch { toast('Error eliminando deal', 'error'); }
    setDeleteId(null);
  };

  if (loading) return (
    <div className="flex items-center justify-center h-32">
      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
    </div>
  );

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white">Pipeline CRM</h1>
        </div>
        <button onClick={openCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nuevo deal</button>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && (() => { setShowCreate(false); setEditDeal(null); })()}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[460px] border border-gray-700 max-h-[80vh] overflow-auto">
            <h2 className="text-white font-bold mb-4">{editDeal ? 'Editar deal' : 'Nuevo deal'}</h2>
            <div className="space-y-3">
              <input type="text" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Título del deal"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" autoFocus />
              <select value={form.stage_id} onChange={e => setForm({ ...form, stage_id: e.target.value })}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500">
                {stages.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <input type="number" value={form.value} onChange={e => setForm({ ...form, value: e.target.value })} placeholder="Valor (EUR)"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <select value={form.contact_id} onChange={e => setForm({ ...form, contact_id: e.target.value })}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500">
                <option value="">Sin contacto</option>
                {contacts.map(c => <option key={c.id} value={c.id}>{c.display_name || c.phone_e164}</option>)}
              </select>
              <input type="date" value={form.expected_close_date} onChange={e => setForm({ ...form, expected_close_date: e.target.value })}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" />
              <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="Notas (opcional)"
                rows={3} className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-green-500" />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => { setShowCreate(false); setEditDeal(null); }} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
              <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">{editDeal ? 'Guardar' : 'Crear'}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Eliminar deal"
        message="¿Seguro que quieres eliminar este deal?" confirmLabel="Eliminar"
        onConfirm={handleDeleteConfirmed} onCancel={() => setDeleteId(null)} />

      <div className="flex-1 min-h-64 overflow-hidden">
        <div className="flex gap-4 h-full overflow-x-auto min-w-max">
          {stages.map(stage => {
            const stageDeals = deals.filter(d => d.stage_id === stage.id);
            const stageValue = stageDeals.reduce((sum, d) => sum + Number(d.value), 0);
            return (
              <div key={stage.id} className="w-72 flex-shrink-0 flex flex-col bg-gray-800/50 rounded-xl"
                onDragOver={e => e.preventDefault()} onDrop={() => handleDrop(stage.id)}>
                <div className="px-3 py-2 border-b border-gray-700">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: stage.color }} />
                    <span className="text-sm font-medium text-white">{stage.name}</span>
                    <span className="text-[10px] text-gray-500 ml-auto">{stageDeals.length}</span>
                  </div>
                  {stageValue > 0 && <p className="text-[10px] text-gray-500 mt-0.5">{stageValue.toLocaleString('es-ES')} EUR</p>}
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                  {stageDeals.map(deal => (
                    <div key={deal.id} draggable onDragStart={() => setDragDealId(deal.id)}
                      className="bg-gray-900/50 rounded-xl p-3 border border-gray-700 cursor-grab hover:border-green-500/30 transition active:cursor-grabbing group">
                      <div className="flex items-start justify-between">
                        <button onClick={() => openEdit(deal)} className="text-xs font-medium text-white hover:text-green-400 text-left">{deal.title}</button>
                        <button onClick={() => setDeleteId(deal.id)} className="text-gray-700 hover:text-red-400 text-[10px] opacity-0 group-hover:opacity-100">x</button>
                      </div>
                      {deal.contact_name && <p className="text-[10px] text-gray-400 mt-1">{deal.contact_name}</p>}
                      {Number(deal.value) > 0 && <p className="text-xs text-green-400 font-medium mt-1">{Number(deal.value).toLocaleString('es-ES')} {deal.currency}</p>}
                      {deal.expected_close_date && <p className="text-[10px] text-gray-600 mt-1">Cierre: {deal.expected_close_date}</p>}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default PipelinePage;
