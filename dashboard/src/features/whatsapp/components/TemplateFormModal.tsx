import React from 'react';
import type { TemplateButton } from '../hooks/useTemplates';

interface TemplateFormModalProps {
  form: {
    name: string;
    category: string;
    language: string;
    header_type: string;
    header_content: string;
    body_text: string;
    footer: string;
  };
  setForm: (f: TemplateFormModalProps['form'] | ((prev: TemplateFormModalProps['form']) => TemplateFormModalProps['form'])) => void;
  buttons: TemplateButton[];
  bodyExamples: string[];
  setBodyExamples: (v: string[]) => void;
  editId: string | null;
  saving: boolean;
  bodyRef: React.RefObject<HTMLTextAreaElement | null>;
  variableNums: number[];
  previewBody: string;
  onSave: () => void;
  onClose: () => void;
  addButton: (type: TemplateButton['type']) => void;
  updateButton: (i: number, field: keyof TemplateButton, value: string) => void;
  removeButton: (i: number) => void;
  insertVariable: () => void;
  formatTemplateName: (v: string) => string;
  LANGUAGE_OPTIONS: { value: string; label: string }[];
  HEADER_TYPES: { value: string; label: string }[];
}

const TemplateFormModal: React.FC<TemplateFormModalProps> = ({
  form, setForm, buttons, bodyExamples, setBodyExamples,
  editId, saving, bodyRef, variableNums, previewBody,
  onSave, onClose, addButton, updateButton, removeButton,
  insertVariable, formatTemplateName, LANGUAGE_OPTIONS, HEADER_TYPES,
}) => {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-gray-800 border border-gray-700 rounded-2xl w-full max-w-4xl overflow-hidden flex flex-col max-h-[95vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div>
            <h2 className="text-xl font-bold text-white">{editId ? 'Editar' : 'Nueva'} plantilla</h2>
            <p className="text-gray-500 text-xs mt-1">Las plantillas deben ser aprobadas por Meta antes de poder usarse</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl leading-none transition-colors">&times;</button>
        </div>

        {/* Modal content: two columns */}
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col lg:flex-row">
            {/* Left: Form */}
            <div className="flex-1 p-6 space-y-5 lg:border-r lg:border-gray-700">
              {/* Basic info */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Nombre de la plantilla</label>
                <input type="text" value={form.name}
                  onChange={e => setForm({ ...form, name: formatTemplateName(e.target.value) })}
                  placeholder="ej: bienvenida_nuevo_cliente"
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-500 focus:border-green-500 focus:outline-none transition font-mono" />
                <p className="text-[11px] text-gray-600 mt-1">Solo letras minusculas, numeros y guion bajo (_).</p>
              </div>

              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">Categoria</label>
                  <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm focus:border-green-500 focus:outline-none transition">
                    <option value="MARKETING">Marketing</option>
                    <option value="UTILITY">Utilidad</option>
                    <option value="AUTHENTICATION">Autenticacion</option>
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">Idioma</label>
                  <select value={form.language} onChange={e => setForm({ ...form, language: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm focus:border-green-500 focus:outline-none transition">
                    {LANGUAGE_OPTIONS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
                  </select>
                </div>
              </div>

              {/* Header */}
              <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4">
                <label className="block text-sm font-medium text-gray-300 mb-3">Cabecera (opcional)</label>
                <div className="flex gap-2 mb-3">
                  {HEADER_TYPES.map(ht => (
                    <button key={ht.value} onClick={() => setForm({ ...form, header_type: ht.value, header_content: '' })}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${form.header_type === ht.value ? 'bg-green-600/20 text-green-400 border border-green-500/30' : 'text-gray-400 hover:bg-gray-700 border border-gray-700'}`}>
                      {ht.label}
                    </button>
                  ))}
                </div>
                {form.header_type === 'TEXT' && (
                  <div>
                    <input type="text" value={form.header_content} onChange={e => setForm({ ...form, header_content: e.target.value })}
                      placeholder="Texto de la cabecera" maxLength={60}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-500 focus:border-green-500 focus:outline-none transition" />
                    <p className="text-[11px] text-gray-600 mt-1">{form.header_content.length}/60</p>
                  </div>
                )}
                {form.header_type === 'IMAGE' && (
                  <div>
                    <input type="url" value={form.header_content} onChange={e => setForm({ ...form, header_content: e.target.value })}
                      placeholder="URL publica de la imagen (JPG o PNG)"
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-500 focus:border-green-500 focus:outline-none transition" />
                    {form.header_content && form.header_content.startsWith('http') && (
                      <div className="mt-2 rounded-lg overflow-hidden border border-gray-700 max-w-[200px]">
                        <img src={form.header_content} alt="Preview" className="w-full h-auto"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Body */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-sm font-medium text-gray-300">Cuerpo del mensaje</label>
                  <button onClick={insertVariable}
                    className="flex items-center gap-1 px-2.5 py-1 text-[11px] bg-purple-600/20 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-600/30 transition-colors">
                    + Variable {`{{${variableNums.length > 0 ? Math.max(...variableNums) + 1 : 1}}}`}
                  </button>
                </div>
                <textarea ref={bodyRef} value={form.body_text} onChange={e => setForm({ ...form, body_text: e.target.value })}
                  placeholder="Escribe el mensaje..." rows={6} maxLength={1024}
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-500 focus:border-green-500 focus:outline-none transition resize-none" />
                <div className="flex justify-between mt-1">
                  <p className="text-[11px] text-gray-600">Variables {'{{1}}'}, {'{{2}}'} se sustituyen al enviar</p>
                  <span className="text-[11px] text-gray-600">{form.body_text.length}/1024</span>
                </div>
              </div>

              {/* Variable examples */}
              {variableNums.length > 0 && (
                <div className="bg-purple-900/10 border border-purple-700/20 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-sm font-medium text-purple-300">Ejemplos de variables</span>
                    <span className="text-[11px] text-purple-500 bg-purple-900/30 px-2 py-0.5 rounded">Obligatorio para Meta</span>
                  </div>
                  <div className="space-y-2">
                    {variableNums.map((num, idx) => (
                      <div key={num} className="flex items-center gap-3">
                        <span className="text-xs text-purple-400 font-mono w-10 flex-shrink-0">{`{{${num}}}`}</span>
                        <input type="text" value={bodyExamples[idx] || ''}
                          onChange={e => { const next = [...bodyExamples]; next[idx] = e.target.value; setBodyExamples(next); }}
                          placeholder={idx === 0 ? 'ej: Maria Garcia' : idx === 1 ? 'ej: 20% de descuento' : `Ejemplo para variable ${num}`}
                          className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none transition" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Footer */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Pie de pagina (opcional)</label>
                <input type="text" value={form.footer} onChange={e => setForm({ ...form, footer: e.target.value })}
                  placeholder="ej: Responde STOP para darte de baja" maxLength={60}
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-500 focus:border-green-500 focus:outline-none transition" />
              </div>

              {/* Buttons */}
              <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-300">Botones ({buttons.length}/3)</span>
                  {buttons.length < 3 && (
                    <div className="flex gap-1.5">
                      <button onClick={() => addButton('QUICK_REPLY')} className="px-2.5 py-1 text-[11px] bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors">+ Respuesta</button>
                      <button onClick={() => addButton('URL')} className="px-2.5 py-1 text-[11px] bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors">+ Enlace</button>
                      <button onClick={() => addButton('PHONE_NUMBER')} className="px-2.5 py-1 text-[11px] bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors">+ Telefono</button>
                    </div>
                  )}
                </div>
                {buttons.length === 0 ? (
                  <p className="text-xs text-gray-600">Sin botones.</p>
                ) : (
                  <div className="space-y-2">
                    {buttons.map((btn, i) => (
                      <div key={i} className="bg-gray-800 rounded-lg p-3 space-y-2 border border-gray-700">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-gray-400 font-medium">
                            {btn.type === 'QUICK_REPLY' ? 'Respuesta rapida' : btn.type === 'URL' ? 'Enlace web' : 'Llamada'}
                          </span>
                          <button onClick={() => removeButton(i)} className="text-gray-600 hover:text-red-400 text-[11px] transition-colors">Eliminar</button>
                        </div>
                        <input type="text" value={btn.text} onChange={e => updateButton(i, 'text', e.target.value)}
                          placeholder="Texto del boton" maxLength={25}
                          className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:border-green-500 focus:outline-none transition" />
                        {btn.type === 'URL' && (
                          <input type="url" value={btn.url || ''} onChange={e => updateButton(i, 'url', e.target.value)}
                            placeholder="https://tu-web.com/oferta"
                            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:border-green-500 focus:outline-none transition" />
                        )}
                        {btn.type === 'PHONE_NUMBER' && (
                          <input type="tel" value={btn.phone_number || ''} onChange={e => updateButton(i, 'phone_number', e.target.value)}
                            placeholder="+34612345678"
                            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:border-green-500 focus:outline-none transition" />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right: Preview */}
            <div className="lg:w-[360px] p-6 space-y-5 bg-gray-900/30">
              <div>
                <p className="text-xs font-medium text-green-400 mb-3">Vista previa</p>
                <div className="bg-[#0b141a] rounded-xl p-4 max-w-[300px] mx-auto">
                  <div className="bg-[#202c33] rounded-lg overflow-hidden shadow-lg">
                    {form.header_type === 'IMAGE' && (
                      <div className="bg-gray-700/50 h-[140px] flex items-center justify-center">
                        {form.header_content ? (
                          <img src={form.header_content} alt="" className="w-full h-full object-cover"
                            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                        ) : <span className="text-gray-500 text-xs">Imagen</span>}
                      </div>
                    )}
                    {form.header_type === 'TEXT' && form.header_content && (
                      <div className="px-3 pt-3"><p className="text-sm font-bold text-white">{form.header_content}</p></div>
                    )}
                    <div className="px-3 py-2"><p className="text-[13px] text-gray-200 whitespace-pre-wrap leading-relaxed">{previewBody}</p></div>
                    {form.footer && <div className="px-3 pb-2"><p className="text-[11px] text-gray-500">{form.footer}</p></div>}
                    {buttons.length > 0 && (
                      <div className="border-t border-gray-600/50">
                        {buttons.map((btn, i) => (
                          <div key={i} className="text-center py-2 text-[13px] text-[#53bdeb] border-b border-gray-600/30 last:border-b-0">
                            {btn.type === 'URL' && '🔗 '}{btn.type === 'PHONE_NUMBER' && '📞 '}{btn.type === 'QUICK_REPLY' && '↩ '}
                            {btn.text || 'Boton'}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="bg-yellow-900/10 border border-yellow-700/20 rounded-xl p-4">
                <p className="text-xs font-medium text-yellow-400 mb-2">Consejos para la aprobacion</p>
                <ul className="space-y-1.5 text-[11px] text-gray-400 leading-relaxed">
                  <li className="flex items-start gap-1.5"><span className="text-yellow-500 mt-0.5">&#x2022;</span><span>No escribas todo en MAYUSCULAS</span></li>
                  <li className="flex items-start gap-1.5"><span className="text-yellow-500 mt-0.5">&#x2022;</span><span>Evita enlaces acortados (bit.ly)</span></li>
                  <li className="flex items-start gap-1.5"><span className="text-yellow-500 mt-0.5">&#x2022;</span><span>El nombre debe describir el proposito</span></li>
                  <li className="flex items-start gap-1.5"><span className="text-yellow-500 mt-0.5">&#x2022;</span><span>Imagenes: JPG o PNG, min 600x340px</span></li>
                  <li className="flex items-start gap-1.5"><span className="text-yellow-500 mt-0.5">&#x2022;</span><span>Marketing: incluye opcion de baja</span></li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Modal footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-700 bg-gray-900/50">
          <div className="text-[11px] text-gray-600">
            {editId ? 'Los cambios se guardan como borrador' : 'Se creara como borrador'}
          </div>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="px-4 py-2.5 bg-gray-700 text-white text-sm rounded-lg hover:bg-gray-600 transition-colors">Cancelar</button>
            <button onClick={onSave} disabled={saving || !form.name || !form.body_text}
              className="px-4 py-2.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-500 disabled:opacity-50 transition-colors">
              {saving ? 'Guardando...' : editId ? 'Guardar cambios' : 'Crear borrador'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TemplateFormModal;
