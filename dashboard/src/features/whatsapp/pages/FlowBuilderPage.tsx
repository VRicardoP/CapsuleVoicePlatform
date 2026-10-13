import React from 'react';
import { useFlowBuilder } from '../hooks/useFlowBuilder';
import ConfirmDialog from '../components/ConfirmDialog';
import FlowList from '../components/FlowList';
import FlowStepEditor from '../components/FlowStepEditor';

const TRIGGER_LABELS: Record<string, string> = {
  message_received: 'Mensaje recibido',
  keyword: 'Palabra clave',
  conversation_opened: 'Conversacion abierta',
  conversation_closed: 'Conversacion cerrada',
  contact_created: 'Contacto creado',
  tag_added: 'Tag anadido',
  manual: 'Manual',
};

const FlowBuilderPage: React.FC = () => {
  const {
    flows,
    loading,
    showModal,
    setShowModal,
    editId,
    deleteId,
    setDeleteId,
    form,
    setForm,
    triggerConfig,
    setTriggerConfig,
    steps,
    editingFlow,
    setEditingFlow,
    openCreate,
    openEdit,
    handleSave,
    handleDelete,
    handleToggle,
    openStepEditor,
    saveSteps,
    addStep,
    updateStep,
    removeStep,
    moveStep,
  } = useFlowBuilder();

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div>
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-2xl font-bold text-white">Flow Builder</h1>
          <button onClick={openCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nuevo flow</button>
        </div>
        <p className="text-gray-400 text-sm">Automatizaciones basadas en triggers y acciones</p>
      </div>

      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        {/* Inline step editor panel */}
        {editingFlow && (
          <div className="border-b border-gray-700 px-6 py-4 bg-gray-800/50 rounded-xl">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-white">Editando pasos del flow</h2>
              <div className="flex gap-2">
                <button onClick={addStep} className="text-xs text-green-400 hover:text-green-300">+ Paso</button>
                <button onClick={saveSteps} className="px-4 py-2 bg-green-600 text-white text-xs rounded-lg hover:bg-green-500 font-medium transition">Guardar pasos</button>
                <button onClick={() => setEditingFlow(null)} className="text-xs text-gray-500 hover:text-white">Cancelar</button>
              </div>
            </div>
            <div className="space-y-3 max-h-72 overflow-auto">
              {steps.length === 0 ? (
                <div className="bg-gray-900/50 border border-dashed border-gray-700 rounded-xl text-center py-4">
                  <p className="text-xs text-gray-600">Sin pasos. Pulsa "+ Paso" para anadir.</p>
                </div>
              ) : (
                steps.map((step, idx) => (
                  <FlowStepEditor
                    key={idx}
                    step={step}
                    index={idx}
                    total={steps.length}
                    onChange={(s) => updateStep(idx, s)}
                    onRemove={() => removeStep(idx)}
                    onMoveUp={() => moveStep(idx, -1)}
                    onMoveDown={() => moveStep(idx, 1)}
                  />
                ))
              )}
            </div>
          </div>
        )}

        <div className="flex-1 overflow-auto p-6">
          <FlowList
            flows={flows}
            loading={loading}
            openCreate={openCreate}
            openEdit={openEdit}
            openStepEditor={openStepEditor}
            handleToggle={handleToggle}
            setDeleteId={setDeleteId}
          />
        </div>
      </div>

      {/* Create/Edit modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[600px] max-h-[85vh] overflow-auto border border-gray-700">
            <h2 className="text-white font-bold mb-4">{editId ? 'Editar' : 'Nuevo'} flow</h2>
            <div className="space-y-3">
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Nombre del flow" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                placeholder="Descripcion (opcional)" rows={2}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-green-500" />

              {/* Trigger */}
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Trigger</label>
                <select value={form.trigger_type} onChange={e => setForm({ ...form, trigger_type: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500">
                  {Object.entries(TRIGGER_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>

              {/* Trigger config for keyword type */}
              {(form.trigger_type === 'keyword' || form.trigger_type === 'message_received') && (
                <div>
                  <label className="text-[10px] text-gray-500 mb-1 block">Palabras clave (separadas por coma)</label>
                  <input
                    type="text"
                    value={triggerConfig.keywords || ''}
                    onChange={(e) => setTriggerConfig({ ...triggerConfig, keywords: e.target.value })}
                    placeholder="hola, info, precio"
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
                  />
                </div>
              )}

              {/* Steps editor */}
              <div className="border-t border-gray-600 pt-3 mt-3">
                <div className="flex items-center justify-between mb-3">
                  <label className="text-xs text-gray-400 font-medium">Pasos del flow</label>
                  <button onClick={addStep} className="text-xs text-green-400 hover:text-green-300">+ Anadir paso</button>
                </div>
                {steps.length === 0 ? (
                  <div className="bg-gray-900/50 border border-dashed border-gray-700 rounded-xl text-center py-4">
                    <p className="text-xs text-gray-600">No hay pasos. Anade acciones que se ejecutaran en orden.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {steps.map((step, idx) => (
                      <FlowStepEditor
                        key={idx}
                        step={step}
                        index={idx}
                        total={steps.length}
                        onChange={(s) => updateStep(idx, s)}
                        onRemove={() => removeStep(idx)}
                        onMoveUp={() => moveStep(idx, -1)}
                        onMoveDown={() => moveStep(idx, 1)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
              <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">{editId ? 'Guardar' : 'Crear'}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Eliminar flow"
        message="Seguro que quieres eliminar este flow?" confirmLabel="Eliminar"
        onConfirm={handleDelete} onCancel={() => setDeleteId(null)} />
    </div>
  );
};

export default FlowBuilderPage;
