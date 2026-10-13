import React, { useState } from 'react';
import type { WAContactDetail, WASegment, WATag, WAInternalNote } from '../types';
import { formatPhone } from '../utils';

const SEGMENT_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
  '#EC4899', '#06B6D4', '#F97316',
];

interface ContactPanelProps {
  contact: WAContactDetail | null;
  loading: boolean;
  allSegments: WASegment[];
  allTags: WATag[];
  notes: WAInternalNote[];
  windowExpiresAt: string | null;
  onAssignSegments: (segmentIds: string[]) => void;
  onAssignTags: (tagIds: string[]) => void;
  onCreateNote: (content: string) => void;
  onUpdateNote: (noteId: string, content: string) => void;
  onDeleteNote: (noteId: string) => void;
  onCreateSegment: (data: { name: string; color?: string }) => Promise<WASegment>;
  onCreateTag: (data: { name: string; color?: string }) => Promise<WATag>;
}

function WindowProgressBar({ expiresAt }: { expiresAt: string | null }) {
  if (!expiresAt) return <div className="text-xs text-gray-500">Sin ventana activa</div>;

  const expires = new Date(expiresAt).getTime();
  const now = Date.now();
  const total = 24 * 60 * 60 * 1000; // 24h in ms
  const remaining = Math.max(0, expires - now);
  const percent = Math.min(100, (remaining / total) * 100);

  let color = 'bg-green-500';
  let textColor = 'text-green-400';
  if (remaining < 3600000) {
    color = 'bg-amber-500';
    textColor = 'text-amber-400';
  }
  if (remaining <= 0) {
    color = 'bg-red-500';
    textColor = 'text-red-400';
  }

  const hours = Math.floor(remaining / 3600000);
  const mins = Math.floor((remaining % 3600000) / 60000);
  const label = remaining <= 0 ? 'Expirada' : `${hours}h ${mins}m restantes`;

  return (
    <div>
      <div className="flex justify-between text-[10px] mb-1">
        <span className="text-gray-500">Ventana 24h</span>
        <span className={textColor}>{label}</span>
      </div>
      <div className="h-1.5 bg-gray-900 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

const ContactPanel: React.FC<ContactPanelProps> = ({
  contact,
  loading,
  allSegments,
  allTags,
  notes,
  windowExpiresAt,
  onAssignSegments,
  onAssignTags,
  onCreateNote,
  onUpdateNote,
  onDeleteNote,
  onCreateSegment,
  onCreateTag,
}) => {
  const [noteInput, setNoteInput] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingNoteContent, setEditingNoteContent] = useState('');
  const [showNewSegment, setShowNewSegment] = useState(false);
  const [newSegmentName, setNewSegmentName] = useState('');
  const [newSegmentColor, setNewSegmentColor] = useState(SEGMENT_COLORS[0]);
  const [creatingSegment, setCreatingSegment] = useState(false);
  const [showNewTag, setShowNewTag] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [newTagColor, setNewTagColor] = useState(SEGMENT_COLORS[0]);
  const [creatingTag, setCreatingTag] = useState(false);

  if (loading) {
    return (
      <div className="w-80 flex-shrink-0 border-l border-gray-700 flex items-center justify-center">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
      </div>
    );
  }

  if (!contact) return null;

  const contactSegmentIds = new Set(contact.segments.map(s => s.id));
  const assignableSegments = allSegments.filter(s => s.slug !== 'todos');
  const contactTagIds = new Set(contact.tags.map(t => t.id));

  // Single-select: clicking a segment replaces any previous selection.
  // Clicking the active one clears it.
  const handleSegmentToggle = (segmentId: string) => {
    const newIds = contactSegmentIds.has(segmentId) ? [] : [segmentId];
    onAssignSegments(newIds);
  };

  const handleCreateSegment = async () => {
    if (!newSegmentName.trim() || creatingSegment) return;
    setCreatingSegment(true);
    try {
      const seg = await onCreateSegment({ name: newSegmentName.trim(), color: newSegmentColor });
      // Auto-assign new segment to current contact (single-select replaces previous)
      onAssignSegments([seg.id]);
      setShowNewSegment(false);
      setNewSegmentName('');
      setNewSegmentColor(SEGMENT_COLORS[0]);
    } catch {
      // Error handled by parent
    }
    setCreatingSegment(false);
  };

  // Single-select tag: same behaviour as segments.
  const handleTagToggle = (tagId: string) => {
    const newIds = contactTagIds.has(tagId) ? [] : [tagId];
    onAssignTags(newIds);
  };

  const handleCreateTag = async () => {
    if (!newTagName.trim() || creatingTag) return;
    setCreatingTag(true);
    try {
      const tag = await onCreateTag({ name: newTagName.trim(), color: newTagColor });
      onAssignTags([...contactTagIds, tag.id]);
      setShowNewTag(false);
      setNewTagName('');
      setNewTagColor(SEGMENT_COLORS[0]);
    } catch {
      // Error handled by parent
    }
    setCreatingTag(false);
  };

  const handleNoteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteInput.trim()) return;
    onCreateNote(noteInput.trim());
    setNoteInput('');
  };

  const handleNoteEdit = (noteId: string) => {
    if (!editingNoteContent.trim()) return;
    onUpdateNote(noteId, editingNoteContent.trim());
    setEditingNoteId(null);
  };

  return (
    <div className="w-80 flex-shrink-0 border-l border-gray-700 flex flex-col h-full overflow-y-auto">
      {/* Contact info */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-600 to-green-800 flex items-center justify-center">
            <span className="text-white font-semibold text-lg">
              {(contact.display_name || formatPhone(contact.phone_e164)).charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-white font-medium text-sm truncate">
              {contact.display_name || formatPhone(contact.phone_e164)}
            </h3>
            <p className="text-gray-400 text-xs">{formatPhone(contact.phone_e164)}</p>
            {contact.email && <p className="text-gray-500 text-xs truncate">{contact.email}</p>}
          </div>
        </div>
        <WindowProgressBar expiresAt={windowExpiresAt} />
      </div>

      {/* Segments */}
      <div className="p-4 border-b border-gray-700 relative">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Segmentos</h4>
          <button
            onClick={() => setShowNewSegment(!showNewSegment)}
            className="w-5 h-5 flex items-center justify-center rounded bg-green-600/20 text-green-400 hover:bg-green-600/30 text-xs font-bold transition"
            title="Crear segmento"
          >
            +
          </button>
        </div>

        {/* New segment overlay */}
        {showNewSegment && (
          <div className="absolute right-4 left-4 top-10 z-20 bg-gray-800 border border-gray-600 rounded-xl p-3 shadow-xl">
            <p className="text-[10px] text-gray-400 mb-2 font-medium">Nuevo segmento</p>
            <input
              type="text"
              value={newSegmentName}
              onChange={e => setNewSegmentName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleCreateSegment(); if (e.key === 'Escape') setShowNewSegment(false); }}
              placeholder="Nombre del segmento"
              autoFocus
              className="w-full px-2.5 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500 mb-2"
            />
            <div className="flex gap-1.5 mb-3">
              {SEGMENT_COLORS.map(c => (
                <button
                  key={c}
                  onClick={() => setNewSegmentColor(c)}
                  className={`w-5 h-5 rounded-full transition ${newSegmentColor === c ? 'ring-2 ring-white ring-offset-1 ring-offset-gray-800' : 'hover:opacity-80'}`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowNewSegment(false)}
                className="flex-1 px-2 py-1.5 text-xs text-gray-400 hover:text-white transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreateSegment}
                disabled={!newSegmentName.trim() || creatingSegment}
                className="flex-1 px-2 py-1.5 bg-green-600 text-white text-xs rounded-lg hover:bg-green-500 disabled:opacity-50 transition"
              >
                {creatingSegment ? '...' : 'Crear'}
              </button>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-1.5">
          {assignableSegments.map(seg => (
            <button
              key={seg.id}
              onClick={() => handleSegmentToggle(seg.id)}
              className={`px-2.5 py-0.5 rounded-full text-[11px] border transition-colors ${
                contactSegmentIds.has(seg.id)
                  ? 'border-green-500/50 bg-green-600/20 text-green-400'
                  : 'border-gray-600 text-gray-500 hover:border-gray-500 hover:text-gray-400'
              }`}
              style={contactSegmentIds.has(seg.id) ? { borderColor: seg.color + '80', backgroundColor: seg.color + '20', color: seg.color } : undefined}
            >
              {seg.name}
            </button>
          ))}
        </div>
      </div>

      {/* Tags */}
      <div className="p-4 border-b border-gray-700 relative">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Etiquetas</h4>
          <button
            onClick={() => setShowNewTag(!showNewTag)}
            className="w-5 h-5 flex items-center justify-center rounded bg-green-600/20 text-green-400 hover:bg-green-600/30 text-xs font-bold transition"
            title="Crear etiqueta"
          >
            +
          </button>
        </div>

        {/* New tag overlay */}
        {showNewTag && (
          <div className="absolute right-4 left-4 top-10 z-20 bg-gray-800 border border-gray-600 rounded-xl p-3 shadow-xl">
            <p className="text-[10px] text-gray-400 mb-2 font-medium">Nueva etiqueta</p>
            <input
              type="text"
              value={newTagName}
              onChange={e => setNewTagName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleCreateTag(); if (e.key === 'Escape') setShowNewTag(false); }}
              placeholder="Nombre de la etiqueta"
              autoFocus
              className="w-full px-2.5 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500 mb-2"
            />
            <div className="flex gap-1.5 mb-3">
              {SEGMENT_COLORS.map(c => (
                <button
                  key={c}
                  onClick={() => setNewTagColor(c)}
                  className={`w-5 h-5 rounded-full transition ${newTagColor === c ? 'ring-2 ring-white ring-offset-1 ring-offset-gray-800' : 'hover:opacity-80'}`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowNewTag(false)}
                className="flex-1 px-2 py-1.5 text-xs text-gray-400 hover:text-white transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreateTag}
                disabled={!newTagName.trim() || creatingTag}
                className="flex-1 px-2 py-1.5 bg-green-600 text-white text-xs rounded-lg hover:bg-green-500 disabled:opacity-50 transition"
              >
                {creatingTag ? '...' : 'Crear'}
              </button>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-1.5">
          {allTags.map(tag => (
            <button
              key={tag.id}
              onClick={() => handleTagToggle(tag.id)}
              className={`px-2.5 py-0.5 rounded-full text-[11px] border transition-colors ${
                contactTagIds.has(tag.id)
                  ? ''
                  : 'border-gray-600 text-gray-500 hover:border-gray-500 hover:text-gray-400'
              }`}
              style={contactTagIds.has(tag.id) ? { borderColor: tag.color + '80', backgroundColor: tag.color + '20', color: tag.color } : undefined}
            >
              {tag.name}
            </button>
          ))}
          {allTags.length === 0 && <p className="text-xs text-gray-600">Sin etiquetas</p>}
        </div>
      </div>

      {/* Internal Notes */}
      <div className="p-4 flex-1 flex flex-col min-h-0">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Notas internas</h4>
        <div className="flex-1 overflow-y-auto space-y-2 mb-3">
          {notes.length === 0 ? (
            <p className="text-xs text-gray-600">Sin notas</p>
          ) : (
            notes.map(note => {
              const isEditing = editingNoteId === note.id;
              return (
                <div key={note.id} className="bg-green-900/20 border border-green-700/30 rounded-lg p-2 group">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-green-400 font-medium">{note.author_name}</span>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-gray-600">
                        {new Date(note.created_at).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                      </span>
                      {!isEditing && (
                        <>
                          <button
                            onClick={() => { setEditingNoteId(note.id); setEditingNoteContent(note.content); }}
                            className="text-gray-600 hover:text-blue-400 text-[10px] opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            editar
                          </button>
                          <button
                            onClick={() => onDeleteNote(note.id)}
                            className="text-gray-600 hover:text-red-400 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            x
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  {isEditing ? (
                    <div className="flex gap-1.5 mt-1">
                      <input
                        type="text"
                        value={editingNoteContent}
                        onChange={e => setEditingNoteContent(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter') handleNoteEdit(note.id);
                          if (e.key === 'Escape') setEditingNoteId(null);
                        }}
                        autoFocus
                        className="flex-1 px-2 py-1 bg-gray-900 border border-gray-700 rounded text-xs text-white focus:outline-none focus:border-green-500"
                      />
                      <button
                        onClick={() => handleNoteEdit(note.id)}
                        className="px-2 py-1 bg-green-600 text-white text-[10px] rounded hover:bg-green-500 transition"
                      >
                        OK
                      </button>
                      <button
                        onClick={() => setEditingNoteId(null)}
                        className="px-2 py-1 text-gray-500 text-[10px] hover:text-white transition"
                      >
                        Esc
                      </button>
                    </div>
                  ) : (
                    <p className="text-xs text-gray-300">{note.content}</p>
                  )}
                </div>
              );
            })
          )}
        </div>
        <form onSubmit={handleNoteSubmit} className="flex gap-2">
          <input
            type="text"
            value={noteInput}
            onChange={e => setNoteInput(e.target.value)}
            placeholder="Escribir nota..."
            className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500 transition"
          />
          <button
            type="submit"
            disabled={!noteInput.trim()}
            className="px-3 py-2 bg-green-600 text-white text-xs rounded-lg hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            +
          </button>
        </form>
      </div>

      {/* Contact metadata */}
      <div className="p-4 border-t border-gray-700 text-[10px] text-gray-600 space-y-0.5">
        <div className="flex justify-between"><span>Origen</span><span className="text-gray-400">{contact.source}</span></div>
        <div className="flex justify-between"><span>Opt-in</span><span className="text-gray-400">{contact.opt_in_status}</span></div>
        <div className="flex justify-between"><span>Creado</span><span className="text-gray-400">{new Date(contact.created_at).toLocaleDateString('es-ES')}</span></div>
      </div>
    </div>
  );
};

export default ContactPanel;
