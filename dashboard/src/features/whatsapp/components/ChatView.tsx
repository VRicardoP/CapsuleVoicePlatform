import React, { useEffect, useRef, useState } from 'react';
import type { WAConversation, WAMessage, WAInternalNote } from '../types';
import ConversationHeader from './ConversationHeader';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';

interface ChatViewProps {
  conversation: WAConversation;
  messages: WAMessage[];
  loading: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
  onSend: (text: string) => void;
  onClose: () => void;
  onMarkRead: () => void;
  notes?: WAInternalNote[];
  onCreateNote?: (content: string) => void;
  onUpdateNote?: (noteId: string, content: string) => void;
  onDeleteNote?: (noteId: string) => void;
  onTemplateSent?: (templateId: string) => Promise<void>;
}

const ChatView: React.FC<ChatViewProps> = ({
  conversation,
  messages,
  loading,
  hasMore,
  onLoadMore,
  onSend,
  onClose,
  onMarkRead,
  notes = [],
  onCreateNote,
  onUpdateNote,
  onDeleteNote,
  onTemplateSent,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevMessagesLength = useRef(messages.length);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingNoteContent, setEditingNoteContent] = useState('');

  // Auto-scroll when new messages arrive
  useEffect(() => {
    if (messages.length > prevMessagesLength.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    prevMessagesLength.current = messages.length;
  }, [messages.length]);

  // Scroll to bottom on conversation change
  useEffect(() => {
    bottomRef.current?.scrollIntoView();
  }, [conversation.id]);

  // Infinite scroll up for older messages
  const handleScroll = () => {
    const el = containerRef.current;
    if (!el || !hasMore || loading) return;
    if (el.scrollTop < 100) {
      onLoadMore();
    }
  };

  const isWindowExpired = conversation.window_expires_at
    ? new Date(conversation.window_expires_at).getTime() < Date.now()
    : true;

  // 24h window indicator
  const getWindowInfo = () => {
    if (!conversation.window_expires_at) {
      return { color: 'orange' as const, label: 'Sin ventana activa', hoursLeft: 0 };
    }
    const expiresAt = new Date(conversation.window_expires_at).getTime();
    const msLeft = expiresAt - Date.now();
    const hoursLeft = msLeft / (1000 * 60 * 60);

    if (hoursLeft <= 0) {
      return { color: 'orange' as const, label: 'Ventana expirada', hoursLeft: 0 };
    }
    if (hoursLeft <= 1) {
      return { color: 'red' as const, label: `${Math.round(hoursLeft * 60)}min restantes`, hoursLeft };
    }
    if (hoursLeft <= 4) {
      return { color: 'orange' as const, label: `${hoursLeft.toFixed(1)}h restantes`, hoursLeft };
    }
    return { color: 'green' as const, label: `${hoursLeft.toFixed(1)}h restantes`, hoursLeft };
  };

  const windowInfo = getWindowInfo();

  const inputDisabled = conversation.status === 'closed';
  const disabledReason = conversation.status === 'closed'
    ? 'Conversacion cerrada'
    : undefined;

  // Merge messages and notes into a single timeline
  type TimelineItem = { type: 'message'; data: WAMessage } | { type: 'note'; data: WAInternalNote };
  const timeline: TimelineItem[] = [
    ...messages.map(m => ({ type: 'message' as const, data: m })),
    ...notes.map(n => ({ type: 'note' as const, data: n })),
  ].sort((a, b) => a.data.created_at.localeCompare(b.data.created_at));

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-900 via-black to-gray-900">
      <ConversationHeader
        conversation={conversation}
        onClose={onClose}
        onMarkRead={onMarkRead}
      />

      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-3 space-y-1"
      >
        {loading && timeline.length === 0 && (
          <div className="flex items-center justify-center py-10">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
          </div>
        )}
        {hasMore && (
          <div className="text-center py-2">
            <button
              onClick={onLoadMore}
              disabled={loading}
              className="text-xs text-green-400 hover:text-green-300 px-3 py-1 rounded-lg hover:bg-green-900/20 transition-colors"
            >
              {loading ? 'Cargando...' : 'Cargar anteriores'}
            </button>
          </div>
        )}
        {timeline.map((item) => {
          if (item.type === 'message') {
            return <MessageBubble key={`msg-${item.data.id}`} message={item.data} />;
          }
          // Internal note - green card centered
          const note = item.data;
          const isEditing = editingNoteId === note.id;
          return (
            <div key={`note-${note.id}`} className="flex justify-center my-2">
              <div className="max-w-[80%] bg-green-900/20 border border-green-700/30 rounded-lg px-3 py-2 group">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-medium text-green-400">{note.author_name}</span>
                  <span className="text-[10px] text-gray-600">
                    {new Date(note.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <span className="text-[10px] text-green-600 bg-green-900/40 px-1.5 rounded">Nota interna</span>
                  <div className="flex items-center gap-1 ml-auto opacity-0 group-hover:opacity-100 transition-opacity">
                    {onUpdateNote && !isEditing && (
                      <button
                        onClick={() => { setEditingNoteId(note.id); setEditingNoteContent(note.content); }}
                        className="text-gray-600 hover:text-blue-400 text-[10px]"
                      >
                        editar
                      </button>
                    )}
                    {onDeleteNote && !isEditing && (
                      <button
                        onClick={() => onDeleteNote(note.id)}
                        className="text-gray-600 hover:text-red-400 text-xs"
                      >
                        x
                      </button>
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
                        if (e.key === 'Enter' && editingNoteContent.trim()) {
                          onUpdateNote?.(note.id, editingNoteContent.trim());
                          setEditingNoteId(null);
                        }
                        if (e.key === 'Escape') setEditingNoteId(null);
                      }}
                      autoFocus
                      className="flex-1 px-2 py-1 bg-gray-900 border border-gray-700 rounded text-xs text-white focus:outline-none focus:border-green-500"
                    />
                    <button
                      onClick={() => {
                        if (editingNoteContent.trim()) {
                          onUpdateNote?.(note.id, editingNoteContent.trim());
                          setEditingNoteId(null);
                        }
                      }}
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
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* 24h window indicator */}
      {conversation.status !== 'closed' && (
        <div className="px-4 py-1.5 flex items-center gap-2 border-t border-gray-700/50">
          <div
            className={`w-2 h-2 rounded-full ${
              windowInfo.color === 'green' ? 'bg-green-500' :
              windowInfo.color === 'orange' ? 'bg-orange-500' :
              'bg-red-500'
            }`}
            title={conversation.window_expires_at
              ? `Expira: ${new Date(conversation.window_expires_at).toLocaleString('es-ES')}`
              : 'Sin ventana de mensajeria activa'}
          />
          <span className={`text-[10px] ${
            windowInfo.color === 'green' ? 'text-green-400' :
            windowInfo.color === 'orange' ? 'text-orange-400' :
            'text-red-400'
          }`}>
            {windowInfo.label}
          </span>
        </div>
      )}

      <ChatInput
        onSend={onSend}
        disabled={inputDisabled}
        disabledReason={disabledReason}
        onCreateNote={onCreateNote}
        conversationId={conversation.id}
        isWindowExpired={isWindowExpired}
        onTemplateSent={onTemplateSent}
      />
    </div>
  );
};

export default ChatView;
