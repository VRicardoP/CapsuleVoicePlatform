import React, { useState } from 'react';
import { useContacts } from '../hooks/useContacts';
import ConfirmDialog from '../components/ConfirmDialog';
import { formatPhone } from '../utils';
import type { WATag } from '../types';

const TAG_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316'];

function TagPicker({ tags, contactTags, onToggle, onCreate }: {
  tags: WATag[];
  contactTags: WATag[];
  onToggle: (tagId: string) => void;
  onCreate: (name: string, color: string) => void;
}) {
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [color, setColor] = useState(TAG_COLORS[0]);
  const contactTagIds = new Set(contactTags.map(t => t.id));

  return (
    <div className="absolute top-full left-0 mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-20 p-2 min-w-[200px]">
      {tags.length === 0 && !showCreate ? (
        <p className="text-xs text-gray-400 p-1">No hay etiquetas</p>
      ) : tags.map(tag => (
        <label key={tag.id} className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer p-1.5 rounded hover:bg-gray-700">
          <input type="checkbox" checked={contactTagIds.has(tag.id)} onChange={() => onToggle(tag.id)} />
          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: tag.color }} />
          {tag.name}
        </label>
      ))}
      {showCreate ? (
        <div className="border-t border-gray-700 mt-1 pt-2">
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && name.trim()) { onCreate(name.trim(), color); setShowCreate(false); setName(''); }
              if (e.key === 'Escape') setShowCreate(false);
            }}
            placeholder="Nombre"
            autoFocus
            className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500 mb-1.5"
          />
          <div className="flex gap-1 mb-2">
            {TAG_COLORS.map(c => (
              <button key={c} onClick={() => setColor(c)}
                className={`w-4 h-4 rounded-full ${color === c ? 'ring-2 ring-white ring-offset-1 ring-offset-gray-900' : ''}`}
                style={{ backgroundColor: c }} />
            ))}
          </div>
          <div className="flex gap-1.5">
            <button onClick={() => setShowCreate(false)} className="flex-1 text-[10px] text-gray-400 hover:text-white py-1">Cancelar</button>
            <button onClick={() => { if (name.trim()) { onCreate(name.trim(), color); setShowCreate(false); setName(''); } }}
              disabled={!name.trim()}
              className="flex-1 text-[10px] bg-green-600 text-white py-1 rounded hover:bg-green-500 disabled:opacity-50">Crear</button>
          </div>
        </div>
      ) : (
        <button onClick={() => setShowCreate(true)}
          className="w-full text-left text-[10px] text-green-400 hover:text-green-300 p-1.5 border-t border-gray-700 mt-1 pt-2">
          + Nueva etiqueta
        </button>
      )}
    </div>
  );
}

const ContactsPage: React.FC = () => {
  const {
    contacts,
    total,
    loading,
    search,
    setSearch,
    page,
    setPage,
    showCreate,
    setShowCreate,
    showImport,
    setShowImport,
    createForm,
    setCreateForm,
    editId,
    setEditId,
    selected,
    confirmDelete,
    setConfirmDelete,
    deleting,
    segments,
    showBulkSegment,
    setShowBulkSegment,
    bulkSegmentIds,
    setBulkSegmentIds,
    fileRef,
    csvRows,
    setCsvRows,
    csvParsed,
    setCsvParsed,
    importing,
    segPickerContact,
    setSegPickerContact,
    tags,
    tagPickerContact,
    setTagPickerContact,
    toggleContactTag,
    createTagAndAssign,
    totalPages,
    openCreate,
    openEdit,
    handleSave,
    handleDeleteConfirmed,
    handleBulkSegmentAssign,
    handleExport,
    openChat,
    toggleSelect,
    toggleAll,
    handleFileChange,
    handleImport,
    toggleContactSegment,
  } = useContacts();

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <h1 className="text-2xl font-bold text-white">Contactos</h1>
        <div className="flex gap-2">
          <button onClick={handleExport} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg font-medium transition flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            Exportar CSV
          </button>
          <button onClick={() => setShowImport(true)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg font-medium transition">Importar CSV</button>
          <button onClick={openCreate} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nuevo contacto</button>
        </div>
      </div>

      {/* Main Card */}
      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        {/* Filter Bar */}
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <input type="text" value={search} onChange={e => { setSearch(e.target.value); setPage(0); }}
              placeholder="Buscar por nombre, telefono o email..."
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
            {selected.size > 0 && (
              <div className="flex gap-2">
                <button onClick={() => { setShowBulkSegment(true); setBulkSegmentIds([]); }}
                  className="px-3 py-1.5 bg-blue-600/20 text-blue-400 border border-blue-600/30 text-sm rounded-lg hover:bg-blue-600/30 font-medium transition">
                  Asignar segmentos ({selected.size})
                </button>
                <button onClick={() => setConfirmDelete({ type: 'bulk' })}
                  className="px-3 py-1.5 bg-red-600/20 text-red-400 border border-red-600/30 text-sm rounded-lg hover:bg-red-600/30 font-medium transition">
                  Eliminar ({selected.size})
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Create / Edit Modal */}
        {showCreate && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => { if (e.target === e.currentTarget) { setShowCreate(false); setEditId(null); } }}>
            <div className="bg-gray-800 rounded-2xl p-6 w-96 border border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-white font-bold">{editId ? 'Editar' : 'Nuevo'} contacto</h2>
                <button onClick={() => { setShowCreate(false); setEditId(null); }} className="text-gray-400 hover:text-white text-lg leading-none">&times;</button>
              </div>
              <div className="space-y-3">
                <input type="text" value={createForm.phone_e164} onChange={e => setCreateForm({ ...createForm, phone_e164: e.target.value })}
                  placeholder="Telefono (ej: +34612345678)" disabled={!!editId}
                  className={`w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500 ${editId ? 'opacity-60' : ''}`} />
                <input type="text" value={createForm.display_name} onChange={e => setCreateForm({ ...createForm, display_name: e.target.value })}
                  placeholder="Nombre" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
                <input type="email" value={createForm.email} onChange={e => setCreateForm({ ...createForm, email: e.target.value })}
                  placeholder="Email" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
                <textarea value={createForm.notes} onChange={e => setCreateForm({ ...createForm, notes: e.target.value })}
                  placeholder="Notas (opcional)" rows={3}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500 resize-none" />
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <button onClick={() => { setShowCreate(false); setEditId(null); }} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
                <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">{editId ? 'Guardar' : 'Crear'}</button>
              </div>
            </div>
          </div>
        )}

        {/* Bulk Segment Assign Modal */}
        {showBulkSegment && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && setShowBulkSegment(false)}>
            <div className="bg-gray-800 rounded-2xl p-6 w-96 border border-gray-700">
              <h2 className="text-white font-bold mb-4">Asignar segmentos a {selected.size} contactos</h2>
              {segments.length === 0 ? (
                <p className="text-gray-400 text-sm">No hay segmentos disponibles</p>
              ) : (
                <div className="space-y-2 max-h-60 overflow-auto">
                  {segments.map(seg => (
                    <label key={seg.id} className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer p-2 rounded hover:bg-gray-700">
                      <input type="checkbox" checked={bulkSegmentIds.includes(seg.id)}
                        onChange={e => {
                          setBulkSegmentIds(e.target.checked
                            ? [...bulkSegmentIds, seg.id]
                            : bulkSegmentIds.filter(id => id !== seg.id));
                        }} />
                      <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: seg.color }} />
                      {seg.name}
                      <span className="text-xs text-gray-400 ml-auto">{seg.contact_count} contactos</span>
                    </label>
                  ))}
                </div>
              )}
              <div className="flex justify-end gap-2 mt-4">
                <button onClick={() => setShowBulkSegment(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
                <button onClick={handleBulkSegmentAssign} disabled={bulkSegmentIds.length === 0}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-500 disabled:opacity-50 font-medium transition">
                  Asignar
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Import CSV Modal */}
        {showImport && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => { if (e.target === e.currentTarget) { setShowImport(false); setCsvRows([]); setCsvParsed(false); } }}>
            <div className="bg-gray-800 rounded-2xl p-6 w-[500px] border border-gray-700 max-h-[80vh] overflow-auto">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-white font-bold">Importar contactos desde CSV</h2>
                <button onClick={() => { setShowImport(false); setCsvRows([]); setCsvParsed(false); }} className="text-gray-400 hover:text-white text-lg leading-none">&times;</button>
              </div>
              {!csvParsed ? (
                <>
                  <p className="text-sm text-gray-400 mb-3">
                    El archivo debe tener cabecera con al menos una columna de telefono
                    (<span className="text-gray-300">phone</span>, <span className="text-gray-300">telefono</span> o <span className="text-gray-300">movil</span>).
                    Opcionalmente: <span className="text-gray-300">name/nombre</span> y <span className="text-gray-300">email/correo</span>.
                  </p>
                  <p className="text-xs text-gray-400 mb-4">Separadores soportados: coma, punto y coma, tabulacion.</p>
                  <input ref={fileRef} type="file" accept=".csv,.tsv,.txt" onChange={handleFileChange}
                    className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-gray-700 file:text-white hover:file:bg-gray-600" />
                </>
              ) : (
                <>
                  <p className="text-sm text-green-400 mb-3">{csvRows.length} contactos encontrados</p>
                  <div className="max-h-60 overflow-auto bg-gray-900/50 rounded-lg mb-4">
                    <table className="w-full text-xs">
                      <thead className="text-gray-400 sticky top-0 bg-gray-900/50">
                        <tr><th className="px-2 py-1 text-left">Telefono</th><th className="px-2 py-1 text-left">Nombre</th><th className="px-2 py-1 text-left">Email</th></tr>
                      </thead>
                      <tbody className="text-gray-300">
                        {csvRows.slice(0, 50).map((r, i) => (
                          <tr key={i} className="border-t border-gray-700/50">
                            <td className="px-2 py-1 font-mono">{r.phone}</td>
                            <td className="px-2 py-1">{r.name || '-'}</td>
                            <td className="px-2 py-1">{r.email || '-'}</td>
                          </tr>
                        ))}
                        {csvRows.length > 50 && <tr><td colSpan={3} className="px-2 py-1 text-gray-400 text-center">...y {csvRows.length - 50} mas</td></tr>}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
              <div className="flex justify-end gap-2 mt-4">
                <button onClick={() => { setShowImport(false); setCsvRows([]); setCsvParsed(false); }} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
                {csvParsed && (
                  <button onClick={handleImport} disabled={importing} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 disabled:opacity-50 font-medium transition">
                    {importing ? 'Importando...' : `Importar ${csvRows.length} contactos`}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        <ConfirmDialog
          open={!!confirmDelete}
          title={confirmDelete?.type === 'bulk' ? `Eliminar ${selected.size} contactos` : 'Eliminar contacto'}
          message={confirmDelete?.type === 'bulk'
            ? `Seguro que quieres eliminar ${selected.size} contactos? Esta accion no se puede deshacer.`
            : 'Seguro que quieres eliminar este contacto? Esta accion no se puede deshacer.'}
          confirmLabel="Eliminar"
          loading={deleting}
          onConfirm={handleDeleteConfirmed}
          onCancel={() => setConfirmDelete(null)}
        />

        {/* Table content */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : contacts.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-400 text-sm">No hay contactos</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-900/50 text-gray-400 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left w-8"><input type="checkbox" checked={selected.size === contacts.length && contacts.length > 0} onChange={toggleAll} /></th>
                  <th className="px-4 py-2 text-left">Nombre</th>
                  <th className="px-4 py-2 text-left">Telefono</th>
                  <th className="px-4 py-2 text-left">Email</th>
                  <th className="px-4 py-2 text-left">Segmentos</th>
                  <th className="px-4 py-2 text-left">Etiquetas</th>
                  <th className="px-4 py-2 text-left">Origen</th>
                  <th className="px-4 py-2 text-left">Fecha</th>
                  <th className="px-4 py-2 w-28"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {contacts.map(c => (
                  <tr key={c.id} className="hover:bg-gray-900/30 transition">
                    <td className="px-4 py-2"><input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleSelect(c.id)} /></td>
                    <td className="px-4 py-2 text-white">{c.display_name || '-'}</td>
                    <td className="px-4 py-2 text-gray-300 font-mono text-xs">{formatPhone(c.phone_e164)}</td>
                    <td className="px-4 py-2 text-gray-400">{c.email || '-'}</td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1 items-center relative">
                        {c.segments.map(s => (<span key={s.id} className="px-1.5 py-0.5 rounded text-[10px]" style={{ backgroundColor: s.color + '33', color: s.color }}>{s.name}</span>))}
                        <button
                          onClick={() => setSegPickerContact(segPickerContact === c.id ? null : c.id)}
                          className="w-5 h-5 rounded bg-gray-700 hover:bg-gray-600 text-gray-400 hover:text-white text-xs flex items-center justify-center transition"
                          title="Gestionar segmentos"
                        >+</button>
                        {segPickerContact === c.id && (
                          <div className="absolute top-full left-0 mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-20 p-2 min-w-[180px]">
                            {segments.length === 0 ? (
                              <p className="text-xs text-gray-400 p-1">No hay segmentos</p>
                            ) : segments.map(seg => (
                              <label key={seg.id} className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer p-1.5 rounded hover:bg-gray-700">
                                <input type="checkbox" checked={c.segments.some(cs => cs.id === seg.id)} onChange={() => toggleContactSegment(c, seg.id)} />
                                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: seg.color }} />
                                {seg.name}
                              </label>
                            ))}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1 items-center relative">
                        {c.tags.map(t => (<span key={t.id} className="px-1.5 py-0.5 rounded text-[10px]" style={{ backgroundColor: t.color + '33', color: t.color }}>{t.name}</span>))}
                        <button
                          onClick={() => setTagPickerContact(tagPickerContact === c.id ? null : c.id)}
                          className="w-5 h-5 rounded bg-gray-700 hover:bg-gray-600 text-gray-400 hover:text-white text-xs flex items-center justify-center transition"
                          title="Gestionar etiquetas"
                        >+</button>
                        {tagPickerContact === c.id && (
                          <TagPicker
                            tags={tags}
                            contactTags={c.tags}
                            onToggle={(tagId) => toggleContactTag(c, tagId)}
                            onCreate={(name, color) => createTagAndAssign(c, name, color)}
                          />
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-gray-400 text-xs">{c.source}</td>
                    <td className="px-4 py-2 text-gray-400 text-xs">{new Date(c.created_at).toLocaleDateString('es-ES')}</td>
                    <td className="px-4 py-2 text-right">
                      <button onClick={() => openChat(c.id)} className="text-green-400 hover:text-green-300 text-xs mr-2 transition" title="Abrir conversacion">
                        <svg className="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
                        {' '}Chat
                      </button>
                      <button onClick={() => openEdit(c)} className="text-blue-400 hover:text-blue-300 text-xs mr-2 transition">Editar</button>
                      <button onClick={() => setConfirmDelete({ type: 'single', id: c.id })} className="text-gray-600 hover:text-red-400 text-xs transition">Eliminar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between text-sm text-gray-400">
            <span>{total} contactos</span>
            <div className="flex gap-2">
              <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 transition disabled:opacity-50 font-medium">Anterior</button>
              <span className="px-3 py-1.5">{page + 1} / {totalPages}</span>
              <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 transition disabled:opacity-50 font-medium">Siguiente</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContactsPage;
