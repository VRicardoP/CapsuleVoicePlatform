import React, { useState, useEffect, useCallback } from 'react';
import type { WASurvey, WASurveyAnswer } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';

const TYPES = [
  { value: 'csat', label: 'CSAT (Satisfaccion)' },
  { value: 'nps', label: 'NPS (Recomendacion)' },
  { value: 'custom', label: 'Personalizada' },
];

const TRIGGERS = [
  { value: 'conversation_closed', label: 'Al cerrar conversacion' },
  { value: 'manual', label: 'Envio manual' },
  { value: 'after_purchase', label: 'Tras compra' },
  { value: 'scheduled', label: 'Programada' },
];

const SurveysPage: React.FC = () => {
  const { toast } = useToast();
  const [surveys, setSurveys] = useState<WASurvey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [responsesFor, setResponsesFor] = useState<string | null>(null);
  const [responses, setResponses] = useState<WASurveyAnswer[]>([]);
  const [form, setForm] = useState({ name: '', survey_type: 'csat', trigger: 'conversation_closed' });

  const fetchSurveys = useCallback(async () => {
    setLoading(true);
    try {
      const res = await whatsappApi.getSurveys();
      setSurveys(res.items);
    } catch { toast('Error cargando encuestas', 'error'); }
    setLoading(false);
  }, [toast]);

  useEffect(() => { fetchSurveys(); }, [fetchSurveys]);

  const openCreate = () => {
    setEditId(null);
    setForm({ name: '', survey_type: 'csat', trigger: 'conversation_closed' });
    setShowModal(true);
  };

  const openEdit = (s: WASurvey) => {
    setEditId(s.id);
    setForm({ name: s.name, survey_type: s.survey_type, trigger: s.trigger });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name) return;
    try {
      if (editId) {
        await whatsappApi.updateSurvey(editId, form);
        toast('Encuesta actualizada');
      } else {
        await whatsappApi.createSurvey(form);
        toast('Encuesta creada');
      }
      setShowModal(false);
      fetchSurveys();
    } catch { toast('Error guardando encuesta', 'error'); }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await whatsappApi.deleteSurvey(deleteId);
      toast('Encuesta eliminada');
      fetchSurveys();
    } catch { toast('Error eliminando', 'error'); }
    setDeleteId(null);
  };

  const handleToggle = async (s: WASurvey) => {
    try {
      await whatsappApi.updateSurvey(s.id, { is_active: !s.is_active });
      fetchSurveys();
    } catch { toast('Error', 'error'); }
  };

  const openResponses = async (surveyId: string) => {
    setResponsesFor(surveyId);
    try {
      const res = await whatsappApi.getSurveyResponses(surveyId);
      setResponses(res.items);
    } catch { toast('Error cargando respuestas', 'error'); }
  };

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Encuestas</h1>
          <p className="text-gray-400 text-sm">CSAT, NPS y encuestas personalizadas</p>
        </div>
        <button onClick={openCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nueva encuesta</button>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[480px] border border-gray-700">
            <h2 className="text-white font-bold mb-4">{editId ? 'Editar' : 'Nueva'} encuesta</h2>
            <div className="space-y-3">
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Nombre de la encuesta" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-gray-500 mb-1 block">Tipo</label>
                  <select value={form.survey_type} onChange={e => setForm({ ...form, survey_type: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500">
                    {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-gray-500 mb-1 block">Disparador</label>
                  <select value={form.trigger} onChange={e => setForm({ ...form, trigger: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500">
                    {TRIGGERS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
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

      {responsesFor && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && setResponsesFor(null)}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[520px] border border-gray-700 max-h-[80vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-bold">Respuestas</h2>
              <button onClick={() => setResponsesFor(null)} className="text-gray-400 hover:text-white text-sm font-medium transition">Cerrar</button>
            </div>
            {responses.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-8">No hay respuestas aun</p>
            ) : (
              <div className="space-y-2">
                {responses.map(r => (
                  <div key={r.id} className="bg-gray-900/50 rounded-xl p-3 border border-gray-700/50">
                    <div className="flex items-center justify-between mb-1">
                      {r.score !== null && <span className="text-sm font-bold text-amber-400">{r.score}/5</span>}
                      <span className="text-[10px] text-gray-500">{new Date(r.created_at).toLocaleString('es-ES')}</span>
                    </div>
                    {r.feedback && <p className="text-xs text-gray-300">{r.feedback}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Eliminar encuesta"
        message="¿Seguro que quieres eliminar esta encuesta?" confirmLabel="Eliminar"
        onConfirm={handleDelete} onCancel={() => setDeleteId(null)} />

      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : surveys.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500 text-sm">No hay encuestas</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {surveys.map(s => (
                <div key={s.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-4 hover:border-green-500/30 transition">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-sm font-medium text-white">{s.name}</h3>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${s.is_active ? 'bg-green-600/20 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                      {s.is_active ? 'Activa' : 'Inactiva'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mb-3 text-[10px] text-gray-500">
                    <span className="px-1.5 py-0.5 bg-gray-700 rounded">{s.survey_type.toUpperCase()}</span>
                    <span>{TRIGGERS.find(t => t.value === s.trigger)?.label || s.trigger}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-400 mb-3">
                    <span>{s.response_count} respuestas</span>
                    {s.avg_score !== null && <span>Promedio: <strong className="text-amber-400">{s.avg_score}</strong></span>}
                  </div>
                  <div className="flex items-center gap-2 text-xs border-t border-gray-700 pt-2">
                    <button onClick={() => handleToggle(s)} className="text-amber-400 hover:text-amber-300">{s.is_active ? 'Desactivar' : 'Activar'}</button>
                    <button onClick={() => openEdit(s)} className="text-blue-400 hover:text-blue-300">Editar</button>
                    <button onClick={() => openResponses(s.id)} className="text-purple-400 hover:text-purple-300">Respuestas</button>
                    <button onClick={() => setDeleteId(s.id)} className="text-gray-600 hover:text-red-400 ml-auto">Eliminar</button>
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

export default SurveysPage;
