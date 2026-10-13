import React from 'react';
import type { WAFlow } from '../types';
import type { FlowStep } from '../hooks/useFlowBuilder';

const TRIGGER_LABELS: Record<string, string> = {
  message_received: 'Mensaje recibido',
  keyword: 'Palabra clave',
  conversation_opened: 'Conversacion abierta',
  conversation_closed: 'Conversacion cerrada',
  contact_created: 'Contacto creado',
  tag_added: 'Tag anadido',
  manual: 'Manual',
};

const STEP_TYPES = [
  { value: 'send_message', label: 'Enviar mensaje', icon: '\ud83d\udcac', color: 'green' },
  { value: 'send_template', label: 'Enviar plantilla', icon: '\ud83d\udccb', color: 'blue' },
  { value: 'wait', label: 'Esperar', icon: '\u23f1', color: 'amber' },
  { value: 'condition', label: 'Condicion', icon: '\ud83d\udd00', color: 'purple' },
  { value: 'assign_agent', label: 'Asignar agente', icon: '\ud83d\udc64', color: 'cyan' },
  { value: 'add_tag', label: 'Anadir tag', icon: '\ud83c\udff7', color: 'orange' },
  { value: 'close', label: 'Cerrar conversacion', icon: '\u2713', color: 'red' },
];

interface FlowListProps {
  flows: WAFlow[];
  loading: boolean;
  openCreate: () => void;
  openEdit: (flow: WAFlow) => void;
  openStepEditor: (flow: WAFlow) => void;
  handleToggle: (flow: WAFlow) => void;
  setDeleteId: (id: string) => void;
}

const FlowList: React.FC<FlowListProps> = ({
  flows,
  loading,
  openCreate,
  openEdit,
  openStepEditor,
  handleToggle,
  setDeleteId,
}) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
      </div>
    );
  }

  if (flows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center">
        <div className="bg-gray-900/50 border border-dashed border-gray-700 rounded-xl px-8 py-6">
          <p className="text-gray-400 text-sm mb-2">No hay flows de automatizacion</p>
          <p className="text-gray-600 text-xs mb-4">Crea tu primer flow para automatizar respuestas y acciones basadas en eventos.</p>
          <button onClick={openCreate} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">Crear primer flow</button>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {flows.map(f => {
        const flowSteps = f.steps ? (Array.isArray(f.steps) ? f.steps : (f.steps as { nodes?: FlowStep[] }).nodes || []) : [];
        return (
          <div key={f.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-4 hover:border-green-500/30 transition">
            <div className="flex items-start justify-between mb-2">
              <h3 className="text-sm font-medium text-white">{f.name}</h3>
              <span className={`px-1.5 py-0.5 rounded text-[10px] ${f.is_active ? 'bg-green-600/20 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                {f.is_active ? 'Activo' : 'Inactivo'}
              </span>
            </div>
            {f.description && <p className="text-xs text-gray-500 mb-2 line-clamp-2">{f.description}</p>}
            <div className="flex items-center gap-2 mb-2">
              <span className="px-1.5 py-0.5 bg-purple-600/15 border border-purple-600/20 rounded text-[10px] text-purple-400">
                {TRIGGER_LABELS[f.trigger_type] || f.trigger_type}
              </span>
              {f.execution_count > 0 && <span className="text-[10px] text-gray-500">{f.execution_count} ejecuciones</span>}
            </div>
            {/* Step preview */}
            {flowSteps.length > 0 && (
              <div className="flex items-center gap-1 mb-2 overflow-hidden">
                {(flowSteps as FlowStep[]).slice(0, 5).map((s, i) => {
                  const meta = STEP_TYPES.find(st => st.value === s.type);
                  return (
                    <span key={i} className="px-1.5 py-0.5 bg-gray-700 rounded text-[10px] text-gray-400" title={meta?.label}>
                      {meta?.icon || '?'}
                    </span>
                  );
                })}
                {flowSteps.length > 5 && <span className="text-[10px] text-gray-600">+{flowSteps.length - 5}</span>}
              </div>
            )}
            <div className="flex items-center gap-2 text-xs border-t border-gray-700 pt-2">
              <button onClick={() => handleToggle(f)} className={`${f.is_active ? 'text-amber-400 hover:text-amber-300' : 'text-green-400 hover:text-green-300'}`}>
                {f.is_active ? 'Desactivar' : 'Activar'}
              </button>
              <button onClick={() => openStepEditor(f)} className="text-purple-400 hover:text-purple-300">Pasos</button>
              <button onClick={() => openEdit(f)} className="text-blue-400 hover:text-blue-300">Editar</button>
              <button onClick={() => setDeleteId(f.id)} className="text-gray-600 hover:text-red-400 ml-auto">Eliminar</button>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default FlowList;
