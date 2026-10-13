import React from 'react';
import ConfirmDialog from '../components/ConfirmDialog';
import { useCampaigns, STATUS_LABELS, STEPS, STEP_LABELS } from '../hooks/useCampaigns';
import { formatDateTime } from '../../../utils/dateFormat';

const CampaignsPage: React.FC = () => {
  const {
    campaigns, total, loading, page, setPage, statusFilter, setStatusFilter,
    deleteId, setDeleteId, relaunchId, setRelaunchId, relaunching,
    showWizard, setShowWizard, step, setStep, wizardForm, setWizardForm,
    templates, segments, catalogSearch, setCatalogSearch,
    stepIdx, canNext, selectedTemplate, selectedAbTemplate, selectedCatalogItem,
    filteredCatalogItems, totalPages,
    openWizard, handleWizardFinish, handleAction,
    handleDeleteConfirmed, handleRelaunchConfirmed, handleDuplicate,
  } = useCampaigns();

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white">Campañas</h1>
          <p className="text-sm text-gray-400 mt-0.5">{total} campañas en total</p>
        </div>
        <button id="wa-campaigns-new" onClick={openWizard} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nueva campaña</button>
      </div>

      {/* Wizard Modal */}
      {showWizard && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowWizard(false)}>
          <div className="bg-gray-800 rounded-2xl w-[560px] border border-gray-700 max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-700">
              <h2 className="text-white font-bold">Nueva campaña</h2>
            </div>
            <div className="px-6 py-4 flex-1 overflow-auto">
              <div className="flex items-center gap-1 mb-6">
                {STEPS.map((s, i) => (
                  <React.Fragment key={s}>
                    <div className={`flex items-center gap-1.5 ${i <= stepIdx ? 'text-green-400' : 'text-gray-600'}`}>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold
                        ${i < stepIdx ? 'bg-green-600 text-white' : i === stepIdx ? 'bg-green-600/20 border border-green-500 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                        {i < stepIdx ? '✓' : i + 1}
                      </div>
                      <span className="text-xs hidden sm:inline">{STEP_LABELS[s]}</span>
                    </div>
                    {i < STEPS.length - 1 && <div className={`flex-1 h-px ${i < stepIdx ? 'bg-green-600' : 'bg-gray-700'}`} />}
                  </React.Fragment>
                ))}
              </div>

              {step === 'name' && (
                <div className="space-y-3">
                  <label className="text-sm text-gray-400">Nombre de la campaña</label>
                  <input type="text" value={wizardForm.name} onChange={e => setWizardForm({ ...wizardForm, name: e.target.value })}
                    placeholder="Ej: Promo Verano 2026" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" autoFocus />
                  <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer mt-2">
                    <input type="checkbox" checked={wizardForm.is_ab_test}
                      onChange={e => setWizardForm({ ...wizardForm, is_ab_test: e.target.checked, ab_template_id: '' })}
                      className="rounded" />
                    Prueba A/B (enviar dos variantes)
                  </label>
                </div>
              )}
              {step === 'template' && (
                <div className="space-y-3">
                  <label className="text-sm text-gray-400">
                    {wizardForm.is_ab_test ? 'Variante A - Plantilla principal' : 'Selecciona plantilla aprobada (opcional)'}
                  </label>
                  {templates.length === 0 ? (
                    <p className="text-xs text-gray-500">No hay plantillas aprobadas.</p>
                  ) : (
                    <div className="space-y-2 max-h-48 overflow-auto">
                      {!wizardForm.is_ab_test && (
                        <button onClick={() => setWizardForm({ ...wizardForm, template_id: '' })}
                          className={`w-full text-left p-3 rounded-lg border text-sm ${!wizardForm.template_id ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
                          Sin plantilla
                        </button>
                      )}
                      {templates.map(t => (
                        <button key={t.id} onClick={() => setWizardForm({ ...wizardForm, template_id: t.id })}
                          className={`w-full text-left p-3 rounded-lg border ${wizardForm.template_id === t.id ? 'border-green-500 bg-green-500/10' : 'border-gray-700 hover:border-gray-600'}`}>
                          <p className="text-sm text-white font-medium">{t.name}</p>
                          <p className="text-xs text-gray-400 line-clamp-2 mt-1">{t.body_text}</p>
                        </button>
                      ))}
                    </div>
                  )}
                  {wizardForm.is_ab_test && (
                    <>
                      <label className="text-sm text-gray-400 block mt-4">Variante B - Plantilla alternativa</label>
                      <div className="space-y-2 max-h-48 overflow-auto">
                        {templates.filter(t => t.id !== wizardForm.template_id).map(t => (
                          <button key={t.id} onClick={() => setWizardForm({ ...wizardForm, ab_template_id: t.id })}
                            className={`w-full text-left p-3 rounded-lg border ${wizardForm.ab_template_id === t.id ? 'border-purple-500 bg-purple-500/10' : 'border-gray-700 hover:border-gray-600'}`}>
                            <p className="text-sm text-white font-medium">{t.name}</p>
                            <p className="text-xs text-gray-400 line-clamp-2 mt-1">{t.body_text}</p>
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
              {step === 'product' && (
                <div className="space-y-3">
                  <label className="text-sm text-gray-400">Adjuntar producto del catálogo (opcional)</label>
                  <input type="text" value={catalogSearch} onChange={e => setCatalogSearch(e.target.value)}
                    placeholder="Buscar producto..." className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
                  <div className="space-y-2 max-h-56 overflow-auto">
                    <button onClick={() => setWizardForm({ ...wizardForm, catalog_item_id: '' })}
                      className={`w-full text-left p-3 rounded-lg border text-sm ${!wizardForm.catalog_item_id ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
                      Sin producto
                    </button>
                    {filteredCatalogItems.map(p => (
                      <button key={p.id} onClick={() => setWizardForm({ ...wizardForm, catalog_item_id: p.id })}
                        className={`w-full text-left p-3 rounded-lg border flex items-center gap-3 ${wizardForm.catalog_item_id === p.id ? 'border-green-500 bg-green-500/10' : 'border-gray-700 hover:border-gray-600'}`}>
                        {p.image_url ? (
                          <img src={p.image_url} alt={p.name} className="w-10 h-10 rounded object-cover flex-shrink-0" />
                        ) : (
                          <div className="w-10 h-10 rounded bg-gray-700 flex items-center justify-center flex-shrink-0 text-gray-500 text-lg">&#128230;</div>
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-white font-medium truncate">{p.name}</p>
                          <p className="text-xs text-green-400">{Number(p.price).toLocaleString('es-ES', { minimumFractionDigits: 2 })} {p.currency}</p>
                        </div>
                        {p.category && <span className="text-[10px] text-gray-500 flex-shrink-0">{p.category}</span>}
                      </button>
                    ))}
                    {filteredCatalogItems.length === 0 && catalogSearch && (
                      <p className="text-xs text-gray-500 text-center py-2">No se encontraron productos</p>
                    )}
                  </div>
                  {selectedCatalogItem && wizardForm.template_id && (
                    <div className="bg-gray-900/50 rounded-lg border border-gray-700 p-3 mt-2">
                      <p className="text-[10px] text-gray-500 mb-1">Vista previa de variables del template:</p>
                      <p className="text-xs text-gray-300">{'{{1}}'} → <span className="text-white">{selectedCatalogItem.name}</span></p>
                      <p className="text-xs text-gray-300">{'{{2}}'} → <span className="text-white">{Number(selectedCatalogItem.price).toFixed(2)} {selectedCatalogItem.currency}</span></p>
                      {selectedCatalogItem.description && <p className="text-xs text-gray-300">{'{{3}}'} → <span className="text-white">{selectedCatalogItem.description}</span></p>}
                      {selectedCatalogItem.image_url && <p className="text-xs text-gray-300">Header imagen → <span className="text-green-400">imagen del producto</span></p>}
                      {selectedCatalogItem.product_url && <p className="text-xs text-gray-300">Botón URL → <span className="text-blue-400">{selectedCatalogItem.product_url}</span></p>}
                    </div>
                  )}
                </div>
              )}
              {step === 'audience' && (
                <div className="space-y-3">
                  <label className="text-sm text-gray-400">Audiencia</label>
                  <div className="space-y-2">
                    <button onClick={() => setWizardForm({ ...wizardForm, audience_type: 'all', segment_ids: [] })}
                      className={`w-full text-left p-3 rounded-lg border text-sm ${wizardForm.audience_type === 'all' ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
                      Todos los contactos
                    </button>
                    <button onClick={() => setWizardForm({ ...wizardForm, audience_type: 'segment' })}
                      className={`w-full text-left p-3 rounded-lg border text-sm ${wizardForm.audience_type === 'segment' ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
                      Por segmentos
                    </button>
                  </div>
                  {wizardForm.audience_type === 'segment' && segments.length > 0 && (
                    <div className="space-y-1 ml-4">
                      {segments.map(seg => (
                        <label key={seg.id} className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                          <input type="checkbox" checked={wizardForm.segment_ids.includes(seg.id)}
                            onChange={e => {
                              const ids = e.target.checked ? [...wizardForm.segment_ids, seg.id] : wizardForm.segment_ids.filter(id => id !== seg.id);
                              setWizardForm({ ...wizardForm, segment_ids: ids });
                            }} />
                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: seg.color }} />
                          {seg.name} <span className="text-xs text-gray-500">({seg.contact_count})</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {step === 'schedule' && (
                <div className="space-y-3">
                  <label className="text-sm text-gray-400">Programación</label>
                  <div className="space-y-2">
                    <button onClick={() => setWizardForm({ ...wizardForm, schedule_type: 'now' })}
                      className={`w-full text-left p-3 rounded-lg border text-sm ${wizardForm.schedule_type === 'now' ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
                      Enviar ahora
                    </button>
                    <button onClick={() => setWizardForm({ ...wizardForm, schedule_type: 'later' })}
                      className={`w-full text-left p-3 rounded-lg border text-sm ${wizardForm.schedule_type === 'later' ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
                      Programar
                    </button>
                  </div>
                  {wizardForm.schedule_type === 'later' && (
                    <input type="datetime-local" value={wizardForm.scheduled_at} onChange={e => setWizardForm({ ...wizardForm, scheduled_at: e.target.value })}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" />
                  )}
                </div>
              )}
              {step === 'review' && (
                <div className="bg-gray-900/50 rounded-xl p-4 space-y-2 text-sm border border-gray-700">
                  <div className="flex justify-between"><span className="text-gray-500">Nombre:</span><span className="text-white">{wizardForm.name}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Plantilla:</span><span className="text-white">{selectedTemplate?.name || 'Ninguna'}</span></div>
                  {wizardForm.is_ab_test && (
                    <div className="flex justify-between"><span className="text-gray-500">Variante B:</span><span className="text-purple-400">{selectedAbTemplate?.name || 'Ninguna'}</span></div>
                  )}
                  <div className="flex justify-between"><span className="text-gray-500">Producto:</span><span className="text-white">{selectedCatalogItem ? `${selectedCatalogItem.name} (${Number(selectedCatalogItem.price).toFixed(2)} ${selectedCatalogItem.currency})` : 'Ninguno'}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Tipo:</span><span className="text-white">{wizardForm.is_ab_test ? 'Prueba A/B' : 'Estándar'}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Audiencia:</span><span className="text-white">{wizardForm.audience_type === 'all' ? 'Todos' : `${wizardForm.segment_ids.length} segmentos`}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Envío:</span><span className="text-white">{wizardForm.schedule_type === 'now' ? 'Inmediato' : wizardForm.scheduled_at}</span></div>
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t border-gray-700 flex justify-between">
              <button onClick={() => stepIdx === 0 ? setShowWizard(false) : setStep(STEPS[stepIdx - 1])}
                className="px-3 py-1.5 text-sm text-gray-400 hover:text-white">
                {stepIdx === 0 ? 'Cancelar' : 'Anterior'}
              </button>
              {step === 'review' ? (
                <button onClick={handleWizardFinish} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium">
                  {wizardForm.schedule_type === 'now' ? 'Crear e iniciar' : 'Programar'}
                </button>
              ) : (
                <button onClick={() => setStep(STEPS[stepIdx + 1])} disabled={!canNext}
                  className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 disabled:opacity-50 font-medium">Siguiente</button>
              )}
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Eliminar campaña"
        message="¿Seguro que quieres eliminar esta campaña?" confirmLabel="Eliminar"
        onConfirm={handleDeleteConfirmed} onCancel={() => setDeleteId(null)} />

      <ConfirmDialog open={!!relaunchId} title="Relanzar campaña"
        message="Se resetearán los destinatarios y se volverá a enviar la misma campaña. ¿Continuar?"
        confirmLabel={relaunching ? 'Enviando...' : 'Relanzar'}
        onConfirm={handleRelaunchConfirmed} onCancel={() => setRelaunchId(null)} />

      {/* Main Card */}
      <div id="wa-campaigns-list" className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        {/* Filters */}
        <div className="px-4 py-3 border-b border-gray-700 flex gap-2">
          {['', 'draft', 'scheduled', 'sending', 'completed', 'cancelled'].map(s => (
            <button key={s} onClick={() => { setStatusFilter(s); setPage(0); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${statusFilter === s ? 'bg-green-600/20 text-green-400 border border-green-500/30' : 'text-gray-400 hover:text-white border border-transparent'}`}>
              {s ? (STATUS_LABELS[s]?.label || s) : 'Todas'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : campaigns.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500 text-sm">No hay campañas</div>
          ) : (
            <div className="space-y-3">
              {campaigns.map(c => {
                const st = STATUS_LABELS[c.status] || { label: c.status, color: 'bg-gray-600' };
                const deliveryRate = c.total_recipients > 0 ? Math.round(c.delivered_count / c.total_recipients * 100) : 0;
                const readRate = c.delivered_count > 0 ? Math.round(c.read_count / c.delivered_count * 100) : 0;
                const sentProgress = c.total_recipients > 0 ? Math.round((c.sent_count + c.failed_count) / c.total_recipients * 100) : 0;
                return (
                  <div key={c.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-4 hover:border-green-500/30 transition">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <h3 className="text-sm font-medium text-white">{c.name}</h3>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] text-white ${st.color}`}>{st.label}</span>
                        {c.is_ab_test && <span className="px-1.5 py-0.5 rounded text-[10px] text-purple-300 bg-purple-600/30">A/B</span>}
                        {c.template_name && <span className="text-[10px] text-gray-500">Plantilla: {c.template_name}</span>}
                        {c.catalog_item && <span className="text-[10px] text-green-500">Producto: {c.catalog_item.name}</span>}
                        {c.scheduled_at && c.status === 'scheduled' && (
                          <span className="text-[10px] text-blue-400">Programada: {formatDateTime(c.scheduled_at)}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        {(c.status === 'draft' || c.status === 'scheduled') && <button onClick={() => handleAction(c.id, 'start')} className="text-green-400 hover:text-green-300">Iniciar</button>}
                        {c.status === 'sending' && <button onClick={() => handleAction(c.id, 'pause')} className="text-yellow-400 hover:text-yellow-300">Pausar</button>}
                        {!['completed', 'cancelled'].includes(c.status) && <button onClick={() => handleAction(c.id, 'cancel')} className="text-orange-400 hover:text-orange-300">Cancelar</button>}
                        {['completed', 'cancelled'].includes(c.status) && <button onClick={() => setRelaunchId(c.id)} className="text-green-400 hover:text-green-300">Relanzar</button>}
                        {['completed', 'cancelled'].includes(c.status) && <button onClick={() => handleDuplicate(c)} className="text-blue-400 hover:text-blue-300">Duplicar</button>}
                        {['draft', 'cancelled', 'completed'].includes(c.status) && <button onClick={() => setDeleteId(c.id)} className="text-gray-600 hover:text-red-400">Eliminar</button>}
                      </div>
                    </div>
                    {c.total_recipients > 0 && (
                      <div className="flex items-center gap-6 text-[11px] text-gray-400">
                        <span>Destinatarios: <span className="text-white">{c.total_recipients}</span></span>
                        <span>Enviados: <span className="text-green-400">{c.sent_count}</span></span>
                        <span>Entregados: <span className="text-blue-400">{c.delivered_count}</span> ({deliveryRate}%)</span>
                        <span>Leídos: <span className="text-purple-400">{c.read_count}</span> ({readRate}%)</span>
                        <span>Fallos: <span className={c.failed_count > 0 ? 'text-red-400' : 'text-gray-600'}>{c.failed_count}</span></span>
                      </div>
                    )}
                    {c.total_recipients > 0 && (
                      <div className="mt-2 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all ${c.status === 'sending' ? 'bg-yellow-500' : 'bg-green-500'}`}
                          style={{ width: `${c.status === 'sending' ? sentProgress : deliveryRate}%` }} />
                      </div>
                    )}
                    {c.status === 'sending' && c.total_recipients > 0 && (
                      <p className="text-[10px] text-yellow-400 mt-1 animate-pulse">Enviando... {sentProgress}% ({c.sent_count + c.failed_count}/{c.total_recipients})</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between text-sm text-gray-400">
            <span>{total} campañas</span>
            <div className="flex gap-2">
              <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 disabled:opacity-50 transition">Anterior</button>
              <span className="px-3 py-1.5">{page + 1} / {totalPages}</span>
              <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 disabled:opacity-50 transition">Siguiente</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CampaignsPage;
