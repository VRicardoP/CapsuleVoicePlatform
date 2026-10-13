import React from 'react';
import type { FlowStep } from '../hooks/useFlowBuilder';

const STEP_TYPES = [
  { value: 'send_message', label: 'Enviar mensaje', icon: '\ud83d\udcac', color: 'green' },
  { value: 'send_template', label: 'Enviar plantilla', icon: '\ud83d\udccb', color: 'blue' },
  { value: 'wait', label: 'Esperar', icon: '\u23f1', color: 'amber' },
  { value: 'condition', label: 'Condicion', icon: '\ud83d\udd00', color: 'purple' },
  { value: 'assign_agent', label: 'Asignar agente', icon: '\ud83d\udc64', color: 'cyan' },
  { value: 'add_tag', label: 'Anadir tag', icon: '\ud83c\udff7', color: 'orange' },
  { value: 'close', label: 'Cerrar conversacion', icon: '\u2713', color: 'red' },
];

interface FlowStepEditorProps {
  step: FlowStep;
  index: number;
  total: number;
  onChange: (step: FlowStep) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

const FlowStepEditor: React.FC<FlowStepEditorProps> = ({ step, index, total, onChange, onRemove, onMoveUp, onMoveDown }) => {
  const stepMeta = STEP_TYPES.find(s => s.value === step.type);
  const colorClass = stepMeta?.color || 'gray';

  return (
    <div className="relative">
      {/* Connector line */}
      {index > 0 && (
        <div className="absolute -top-4 left-8 w-0.5 h-4 bg-gray-600" />
      )}

      <div className={`bg-gray-900/50 rounded-xl border border-gray-700 p-3 hover:border-${colorClass}-600/40 transition group`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">{stepMeta?.icon || '?'}</span>
          <select
            value={step.type}
            onChange={(e) => onChange({ type: e.target.value, params: {} })}
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-white flex-1 focus:outline-none focus:border-green-500"
          >
            {STEP_TYPES.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          <span className="text-[10px] text-gray-600 font-mono">#{index + 1}</span>
          <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition">
            <button onClick={onMoveUp} disabled={index === 0} className="text-gray-500 hover:text-white disabled:opacity-20 p-0.5" title="Subir">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" /></svg>
            </button>
            <button onClick={onMoveDown} disabled={index === total - 1} className="text-gray-500 hover:text-white disabled:opacity-20 p-0.5" title="Bajar">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
            </button>
            <button onClick={onRemove} className="text-gray-500 hover:text-red-400 p-0.5" title="Eliminar">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        {/* Step-specific params */}
        {step.type === 'send_message' && (
          <textarea
            value={(step.params.text as string) || ''}
            onChange={(e) => onChange({ ...step, params: { ...step.params, text: e.target.value } })}
            placeholder="Texto del mensaje (soporta {{contact.name}})"
            rows={2}
            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-white resize-none placeholder-gray-500 focus:outline-none focus:border-green-500"
          />
        )}

        {step.type === 'send_template' && (
          <div className="grid grid-cols-2 gap-2">
            <input
              value={(step.params.template_name as string) || ''}
              onChange={(e) => onChange({ ...step, params: { ...step.params, template_name: e.target.value } })}
              placeholder="Nombre de la plantilla"
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
            />
            <input
              value={(step.params.language as string) || 'es'}
              onChange={(e) => onChange({ ...step, params: { ...step.params, language: e.target.value } })}
              placeholder="Idioma"
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
            />
          </div>
        )}

        {step.type === 'wait' && (
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={(step.params.minutes as number) || 0}
              onChange={(e) => onChange({ ...step, params: { ...step.params, minutes: parseInt(e.target.value) || 0 } })}
              min={0}
              className="w-20 bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-green-500"
            />
            <span className="text-xs text-gray-500">minutos</span>
          </div>
        )}

        {step.type === 'condition' && (
          <div className="grid grid-cols-3 gap-2">
            <select
              value={(step.params.field as string) || ''}
              onChange={(e) => onChange({ ...step, params: { ...step.params, field: e.target.value } })}
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-green-500"
            >
              <option value="">Campo...</option>
              <option value="contact.opt_in_status">Opt-in status</option>
              <option value="conversation.status">Estado conv.</option>
              <option value="conversation.priority">Prioridad</option>
              <option value="contact.source">Origen contacto</option>
            </select>
            <select
              value={(step.params.operator as string) || 'equals'}
              onChange={(e) => onChange({ ...step, params: { ...step.params, operator: e.target.value } })}
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-green-500"
            >
              <option value="equals">es igual a</option>
              <option value="not_equals">no es igual a</option>
              <option value="contains">contiene</option>
            </select>
            <input
              value={(step.params.value as string) || ''}
              onChange={(e) => onChange({ ...step, params: { ...step.params, value: e.target.value } })}
              placeholder="Valor"
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
            />
          </div>
        )}

        {step.type === 'assign_agent' && (
          <input
            value={(step.params.agent_id as string) || ''}
            onChange={(e) => onChange({ ...step, params: { ...step.params, agent_id: e.target.value } })}
            placeholder="ID del agente (UUID)"
            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
          />
        )}

        {step.type === 'add_tag' && (
          <input
            value={(step.params.tag as string) || ''}
            onChange={(e) => onChange({ ...step, params: { ...step.params, tag: e.target.value } })}
            placeholder="Nombre del tag"
            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
          />
        )}

        {step.type === 'close' && (
          <p className="text-[10px] text-gray-500">Cierra la conversacion automaticamente.</p>
        )}
      </div>
    </div>
  );
};

export default FlowStepEditor;
