import React, { useState, useMemo } from 'react';
import type { WAConversation, WASegment, WATag } from '../types';
import ConversationItem from './ConversationItem';
import { useWhatsApp } from '../context/WhatsAppContext';
import { isUnanswered } from '../hooks/useConversations';
import { useTenant } from '../../../context/TenantContext';

// Segment icon → emoji mapping (mirrors SegmentsPage)
const SEGMENT_ICON_EMOJI: Record<string, string> = {
  inbox: '\u{1F4E5}',
  star: '\u2B50',
  phone: '\u{1F4DE}',
  'check-circle': '\u2705',
  clock: '\u{1F551}',
  'x-circle': '\u274C',
  'message-circle': '\u{1F4AC}',
};

/** Extrae todos los emojis de un nombre como grapheme clusters completos (soporta ZWJ sequences). */
function extractAllEmojis(name: string): string[] {
  const seg = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
  return [...seg.segment(name)]
    .map(s => s.segment)
    .filter(s => /\p{Extended_Pictographic}/u.test(s));
}

/**
 * Para cada nombre de la lista, asigna el emoji más distintivo (el que aparece
 * en el menor número de otros nombres). Usa asignación greedy para evitar
 * colisiones: si dos nombres tienen el mismo emoji óptimo, el primero en ser
 * procesado lo conserva y el segundo escoge el siguiente candidato disponible.
 * Devuelve un Map de nombre → emoji (null si el nombre no tiene emojis).
 */
function assignDistinctiveEmojis(names: string[]): Map<string, string | null> {
  const result = new Map<string, string | null>();
  const usedEmojis = new Set<string>();

  const withCandidates = names.map(name => {
    const emojis = extractAllEmojis(name);
    const otherNames = names.filter(n => n !== name);
    const scored = emojis
      .map((emoji, idx) => ({
        emoji,
        count: otherNames.filter(n => n.includes(emoji)).length,
        idx,
      }))
      .sort((a, b) => a.count - b.count || b.idx - a.idx);
    return { name, candidates: scored };
  });

  // Procesar primero los más restringidos (menos candidatos disponibles)
  withCandidates.sort((a, b) => a.candidates.length - b.candidates.length);

  for (const { name, candidates } of withCandidates) {
    if (candidates.length === 0) { result.set(name, null); continue; }
    const pick = candidates.find(c => !usedEmojis.has(c.emoji)) ?? candidates[0];
    result.set(name, pick.emoji);
    usedEmojis.add(pick.emoji);
  }
  return result;
}

interface ConversationListProps {
  conversations: WAConversation[];
  activeId: string | null;
  loading: boolean;
  segments: WASegment[];
  tags: WATag[];
  onSelect: (id: string) => void;
  onRefetch: () => Promise<void>;
}

const ConversationList: React.FC<ConversationListProps> = ({ conversations, activeId, loading, segments, tags, onSelect }) => {
  const {
    unansweredFilter,
    setUnansweredFilter,
    pinnedConversationIds,
    conversationsTotal,
    hasMoreConversations,
    loadingMoreConversations,
    loadMoreConversations,
  } = useWhatsApp();
  const { hasFeature } = useTenant();
  const emojiFiltersEnabled = hasFeature('whatsapp_emoji_filters');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  // Single-select filters: at most one segment and one tag at a time.
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);
  const [selectedTagId, setSelectedTagId] = useState<string | null>(null);

  const unansweredCount = conversations.filter(isUnanswered).length;

  const filtered = conversations.filter(c => {
    const matchesSearch = !search ||
      (c.contact.display_name || '').toLowerCase().includes(search.toLowerCase()) ||
      c.contact.phone_e164.includes(search);

    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;

    const matchesSegment = !selectedSegmentId ||
      (c.contact_segments || []).some(s => s.id === selectedSegmentId);

    const matchesTag = !selectedTagId ||
      (c.contact_tags || []).some(t => t.id === selectedTagId);

    return matchesSearch && matchesStatus && matchesSegment && matchesTag;
  });

  const statusOptions = [
    { key: 'all', label: 'Todas' },
    { key: 'open', label: 'Abiertas' },
    { key: 'assigned', label: 'Asignadas' },
    { key: 'closed', label: 'Cerradas' },
  ];

  const assignableSegments = segments.filter(s => s.slug !== 'todos');

  // Calcular emojis distintivos una sola vez cuando cambian segmentos o etiquetas
  const emojiMap = useMemo(() => {
    if (!emojiFiltersEnabled) return new Map<string, string | null>();
    const allNames = [
      ...assignableSegments.map(s => s.name),
      ...tags.map(t => t.name),
    ];
    return assignDistinctiveEmojis(allNames);
  }, [emojiFiltersEnabled, assignableSegments, tags]);

  return (
    <div className="flex flex-col h-full">
      {/* Search and filters */}
      <div className="p-4 space-y-3 border-b border-gray-700">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Buscar conversación..."
          className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-500 focus:border-green-500 focus:outline-none transition"
        />

        {/* Inline filter chips: segmentos + etiquetas como emoji del nombre.
            Solo visibles si el tenant tiene whatsapp_emoji_filters activado. */}
        {emojiFiltersEnabled && assignableSegments.length > 0 && (
          <div className="flex flex-wrap gap-1.5 items-center">
            {assignableSegments.map(seg => {
              const isActive = selectedSegmentId === seg.id;
              const emoji = emojiMap.get(seg.name)
                ?? SEGMENT_ICON_EMOJI[seg.icon || '']
                ?? '\u{1F516}';
              return (
                <button
                  key={seg.id}
                  onClick={() => setSelectedSegmentId(isActive ? null : seg.id)}
                  title={seg.name}
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-sm transition ${
                    isActive ? 'ring-2 ring-white ring-offset-1 ring-offset-gray-800' : 'opacity-70 hover:opacity-100'
                  }`}
                  style={{ backgroundColor: seg.color + '40' }}
                >
                  {emoji}
                </button>
              );
            })}
            {selectedSegmentId && (
              <button
                onClick={() => setSelectedSegmentId(null)}
                className="text-[10px] text-gray-500 hover:text-gray-300 px-1"
                title="Limpiar filtro de segmento"
              >
                Limpiar
              </button>
            )}
          </div>
        )}
        {emojiFiltersEnabled && tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 items-center">
            {tags.map(tag => {
              const isActive = selectedTagId === tag.id;
              const emoji = emojiMap.get(tag.name) ?? null;
              return (
                <button
                  key={tag.id}
                  onClick={() => setSelectedTagId(isActive ? null : tag.id)}
                  title={tag.name}
                  className={`w-7 h-7 rounded-full flex items-center justify-center transition ${
                    isActive ? 'ring-2 ring-white ring-offset-1 ring-offset-gray-800' : 'opacity-70 hover:opacity-100'
                  }`}
                  style={{ backgroundColor: tag.color }}
                >
                  {emoji
                    ? <span className="text-sm">{emoji}</span>
                    : <span className="w-3 h-3 rounded-full bg-white/30" />
                  }
                </button>
              );
            })}
            {selectedTagId && (
              <button
                onClick={() => setSelectedTagId(null)}
                className="text-[10px] text-gray-500 hover:text-gray-300 px-1"
                title="Limpiar filtro de etiqueta"
              >
                Limpiar
              </button>
            )}
          </div>
        )}

        <div className="flex flex-wrap gap-1.5">
          {statusOptions.map(s => (
            <button
              key={s.key}
              onClick={() => setStatusFilter(s.key)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === s.key
                  ? 'bg-green-600/20 text-green-400 border border-green-500/30'
                  : 'text-gray-400 hover:bg-gray-700 hover:text-gray-300 border border-transparent'
              }`}
            >
              {s.label}
              {s.key === 'all' && ` (${conversations.length})`}
            </button>
          ))}
          <button
            onClick={() => setUnansweredFilter(!unansweredFilter)}
            title="Mostrar solo conversaciones sin responder"
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
              unansweredFilter
                ? 'bg-orange-600/20 text-orange-300 border border-orange-500/40'
                : 'text-gray-400 hover:bg-gray-700 hover:text-gray-300 border border-transparent'
            }`}
          >
            Sin responder{unansweredCount > 0 && ` (${unansweredCount})`}
          </button>
        </div>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500"></div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="text-4xl mb-3">{search ? '🔍' : '💬'}</div>
            <p className="text-gray-500 text-sm">
              {search ? 'Sin resultados para tu búsqueda' : 'No hay conversaciones'}
            </p>
          </div>
        ) : (
          <>
            {filtered.map(c => (
              <ConversationItem
                key={c.id}
                conversation={c}
                isActive={c.id === activeId}
                isPinned={pinnedConversationIds.has(c.id)}
                onClick={() => onSelect(c.id)}
              />
            ))}
            {hasMoreConversations && !search && (
              <button
                onClick={() => loadMoreConversations()}
                disabled={loadingMoreConversations}
                className="w-full py-3 text-sm text-green-400 hover:bg-gray-700/30 disabled:opacity-50 transition-colors"
              >
                {loadingMoreConversations
                  ? 'Cargando…'
                  : `Cargar más (${conversations.length} de ${conversationsTotal})`}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ConversationList;
