import React from 'react';
import ConfirmDialog from '../components/ConfirmDialog';
import TemplateFormModal from '../components/TemplateFormModal';
import { useTemplates } from '../hooks/useTemplates';
import type { TemplateButton } from '../hooks/useTemplates';

const TemplatesPage: React.FC = () => {
  const {
    templates, total, loading, statusFilter, setStatusFilter, page, setPage,
    showCreate, form, setForm, buttons,
    bodyExamples, setBodyExamples, editId, deleteId, setDeleteId,
    saving, submitting, syncing, bodyRef, variableNums, hasPending,
    handleCreate, closeModal, handleEdit, openCreate,
    handleDeleteConfirmed, handleSubmit, handleSync,
    addButton, updateButton, removeButton, insertVariable,
    previewBody, totalPages, countVariables,
    STATUS_COLORS, STATUS_LABELS, CATEGORY_LABELS, LANGUAGE_OPTIONS, HEADER_TYPES,
    formatTemplateName,
  } = useTemplates();


  // All state, effects, and handlers are in useTemplates hook

  /*  Render                                                                   */
  /* ======================================================================== */

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Page header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white">Plantillas</h1>
          <p className="text-gray-400 text-sm">
            {total} plantilla{total !== 1 ? 's' : ''} en total
            {hasPending && <span className="ml-2 text-yellow-500 animate-pulse">● Comprobando aprobación...</span>}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            id="wa-templates-sync"
            onClick={handleSync}
            disabled={syncing}
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            {syncing ? (
              <><span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Sincronizando...</>
            ) : (
              'Sincronizar Meta'
            )}
          </button>
          <button
            onClick={openCreate}
            className="px-4 py-2.5 bg-green-600 hover:bg-green-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            <span className="text-lg leading-none">+</span> Nueva plantilla
          </button>
        </div>
      </div>

      {/* Main content card */}
      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        {/* Status filters */}
        <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between">
          <div className="flex gap-2">
            {['', 'draft', 'pending', 'approved', 'rejected'].map(s => (
              <button
                key={s}
                onClick={() => { setStatusFilter(s); setPage(0); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  statusFilter === s
                    ? 'bg-green-600/20 text-green-400 border border-green-500/30'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-gray-300 border border-transparent'
                }`}
              >
                {STATUS_LABELS[s] || s}
              </button>
            ))}
          </div>
          <span className="text-xs text-gray-500">{templates.length} de {total}</span>
        </div>

        {/* Template grid */}
        <div id="wa-templates-grid" className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
            </div>
          ) : templates.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-center">
                <p className="text-gray-500 text-sm">No hay plantillas{statusFilter ? ` con estado "${STATUS_LABELS[statusFilter]}"` : ''}</p>
                {!statusFilter && (
                  <button onClick={openCreate} className="mt-3 text-green-400 hover:text-green-300 text-sm">
                    Crear tu primera plantilla
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {templates.map(t => {
                const tButtons = (t.buttons as { buttons?: TemplateButton[] } | null)?.buttons || [];
                const varCount = countVariables(t.body_text);
                return (
                  <div key={t.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-5 hover:border-green-500/30 transition group">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-sm font-semibold text-white truncate">{t.name}</h3>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium text-white flex-shrink-0 ml-2 ${STATUS_COLORS[t.status] || 'bg-gray-600'}`}>
                        {STATUS_LABELS[t.status] || t.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mb-3 text-[11px] text-gray-500 flex-wrap">
                      <span className="px-1.5 py-0.5 rounded bg-gray-700/50">{CATEGORY_LABELS[t.category] || t.category}</span>
                      <span>{t.language.toUpperCase()}</span>
                      {t.header_type && (
                        <span className="px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-400">
                          {t.header_type === 'TEXT' ? 'Texto' : t.header_type === 'IMAGE' ? 'Imagen' : t.header_type}
                        </span>
                      )}
                      {varCount > 0 && <span>{varCount} variable{varCount > 1 ? 's' : ''}</span>}
                      {tButtons.length > 0 && <span>{tButtons.length} botone{tButtons.length > 1 ? 's' : ''}</span>}
                    </div>
                    <p className="text-xs text-gray-400 line-clamp-3 mb-3 leading-relaxed">{t.body_text}</p>
                    {t.footer && <p className="text-[10px] text-gray-600 mb-3">{t.footer}</p>}
                    {t.meta_rejected_reason && (
                      <div className="bg-red-900/20 border border-red-700/30 rounded-lg px-3 py-2 mb-3">
                        <p className="text-[11px] text-red-400">Motivo rechazo: {t.meta_rejected_reason}</p>
                      </div>
                    )}
                    {tButtons.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-3">
                        {tButtons.map((btn, i) => (
                          <span key={i} className="px-2 py-0.5 rounded-full text-[10px] bg-blue-600/10 text-blue-400 border border-blue-500/20">
                            {btn.type === 'URL' && '🔗 '}{btn.type === 'PHONE_NUMBER' && '📞 '}{btn.text || 'Botón'}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-xs pt-2 border-t border-gray-700/50">
                      {t.status === 'draft' && (
                        <>
                          <button onClick={() => handleEdit(t)} className="text-blue-400 hover:text-blue-300 transition-colors">Editar</button>
                          <button
                            onClick={() => handleSubmit(t.id)}
                            disabled={submitting === t.id}
                            className="text-green-400 hover:text-green-300 transition-colors disabled:opacity-50"
                          >
                            {submitting === t.id ? 'Enviando...' : 'Enviar a Meta'}
                          </button>
                        </>
                      )}
                      {t.status === 'pending' && (
                        <span className="text-yellow-500 text-[11px] animate-pulse">Esperando revisión de Meta...</span>
                      )}
                      {t.status !== 'pending' && (
                        <button onClick={() => setDeleteId(t.id)} className="text-gray-600 hover:text-red-400 ml-auto transition-colors">Eliminar</button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-3 border-t border-gray-700 flex items-center justify-between text-sm text-gray-400">
            <span>{total} plantillas</span>
            <div className="flex gap-2 items-center">
              <button
                disabled={page === 0}
                onClick={() => setPage(p => p - 1)}
                className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 disabled:opacity-50 transition-colors text-xs"
              >
                Anterior
              </button>
              <span className="px-2 py-1 text-xs">{page + 1} / {totalPages}</span>
              <button
                disabled={page >= totalPages - 1}
                onClick={() => setPage(p => p + 1)}
                className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 disabled:opacity-50 transition-colors text-xs"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>

      {showCreate && (
        <TemplateFormModal
          form={form} setForm={setForm} buttons={buttons}
          bodyExamples={bodyExamples} setBodyExamples={setBodyExamples}
          editId={editId} saving={saving} bodyRef={bodyRef}
          variableNums={variableNums} previewBody={previewBody}
          onSave={handleCreate} onClose={closeModal}
          addButton={addButton} updateButton={updateButton} removeButton={removeButton}
          insertVariable={insertVariable} formatTemplateName={formatTemplateName}
          LANGUAGE_OPTIONS={LANGUAGE_OPTIONS} HEADER_TYPES={HEADER_TYPES}
        />
      )}

      <ConfirmDialog
        open={!!deleteId}
        title="Eliminar plantilla"
        message="¿Seguro que quieres eliminar esta plantilla? Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        onConfirm={handleDeleteConfirmed}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
};

export default TemplatesPage;
