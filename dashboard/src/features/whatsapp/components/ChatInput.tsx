import React, { useState, useRef, useEffect, useMemo } from 'react';
import type { WATemplate, WAMacro } from '../types';
import { whatsappApi } from '../services/whatsappApi';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
  disabledReason?: string;
  onCreateNote?: (content: string) => void;
  conversationId?: string;
  isWindowExpired?: boolean;
  onTemplateSent?: (templateId: string) => Promise<void>;
}

const ACCEPT_TYPES: Record<string, string> = {
  image: 'image/jpeg,image/png,image/webp',
  video: 'video/mp4,video/3gpp',
  audio: 'audio/aac,audio/mp4,audio/mpeg,audio/amr,audio/ogg',
  document: '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt',
};

const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled,
  disabledReason,
  onCreateNote,
  conversationId,
  isWindowExpired,
  onTemplateSent,
}) => {
  const [text, setText] = useState('');
  const [isNoteMode, setIsNoteMode] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Template selector state
  const [showTemplates, setShowTemplates] = useState(false);
  const [templates, setTemplates] = useState<WATemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [sendingTemplate, setSendingTemplate] = useState<string | null>(null);

  // Attachment state
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [attachedFile, setAttachedFile] = useState<{ file: File; type: string; preview?: string } | null>(null);

  // Macro command palette state
  const [macros, setMacros] = useState<WAMacro[]>([]);
  const [showMacros, setShowMacros] = useState(false);
  const [macroFilter, setMacroFilter] = useState('');
  const [selectedMacroIdx, setSelectedMacroIdx] = useState(0);

  const filteredMacros = useMemo(() => {
    if (!macroFilter) return macros;
    const q = macroFilter.toLowerCase();
    return macros.filter(m =>
      m.name.toLowerCase().includes(q) ||
      (m.shortcut && m.shortcut.toLowerCase().includes(q)) ||
      m.text.toLowerCase().includes(q)
    );
  }, [macros, macroFilter]);

  useEffect(() => {
    // Load macros once
    (async () => {
      try {
        const res = await whatsappApi.getMacros();
        setMacros(res);
      } catch { /* empty */ }
    })();
  }, []);

  const fetchTemplates = async () => {
    if (templates.length > 0) { setShowTemplates(true); return; }
    setLoadingTemplates(true);
    try {
      const res = await whatsappApi.getTemplates({ status: 'approved', limit: 50 });
      setTemplates(res.items);
      setShowTemplates(true);
    } catch { /* empty */ }
    setLoadingTemplates(false);
  };

  const handleSendTemplate = async (template: WATemplate) => {
    if (!conversationId || sendingTemplate) return;
    setSendingTemplate(template.id);
    try {
      await onTemplateSent?.(template.id);
      setShowTemplates(false);
    } catch { /* error handled by context */ }
    setSendingTemplate(null);
  };

  // Close template picker and attach menu on conversation change
  useEffect(() => {
    setShowTemplates(false);
    setShowAttachMenu(false);
    setAttachedFile(null);
  }, [conversationId]);

  const handleFileSelect = (type: string) => {
    setShowAttachMenu(false);
    if (fileInputRef.current) {
      fileInputRef.current.accept = ACCEPT_TYPES[type] || '*/*';
      fileInputRef.current.dataset.mediaType = type;
      fileInputRef.current.click();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const type = e.target.dataset.mediaType || 'document';
    const preview = type === 'image' ? URL.createObjectURL(file) : undefined;
    setAttachedFile({ file, type, preview });
    e.target.value = '';
  };

  const removeAttachment = () => {
    if (attachedFile?.preview) URL.revokeObjectURL(attachedFile.preview);
    setAttachedFile(null);
  };

  const handleSubmit = () => {
    const trimmed = text.trim();

    if (isNoteMode && onCreateNote && trimmed) {
      onCreateNote(trimmed);
    } else if (!disabled && (trimmed || attachedFile)) {
      // If there's an attachment, include file info in the message
      if (attachedFile) {
        const caption = trimmed || '';
        onSend(caption ? `[${attachedFile.type}: ${attachedFile.file.name}] ${caption}` : `[${attachedFile.type}: ${attachedFile.file.name}]`);
        removeAttachment();
      } else if (trimmed) {
        onSend(trimmed);
      }
    } else {
      return;
    }

    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Macro palette navigation
    if (showMacros) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedMacroIdx(i => Math.min(i + 1, filteredMacros.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedMacroIdx(i => Math.max(i - 1, 0));
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (filteredMacros[selectedMacroIdx]) {
          setText(filteredMacros[selectedMacroIdx].text);
          setShowMacros(false);
          setMacroFilter('');
        }
        return;
      }
      if (e.key === 'Escape') {
        setShowMacros(false);
        setMacroFilter('');
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  };

  const inputDisabled = isNoteMode ? false : disabled;

  return (
    <div className="border-t border-gray-700 bg-gray-800 px-4 py-3">
      <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileChange} />

      {/* Macro command palette */}
      {showMacros && filteredMacros.length > 0 && (
        <div className="mb-2 bg-gray-700 border border-gray-600 rounded-lg max-h-48 overflow-auto">
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-600">
            <span className="text-[10px] text-gray-400">Macros — escribe para filtrar</span>
            <button onClick={() => { setShowMacros(false); setMacroFilter(''); setText(''); }} className="text-gray-500 hover:text-white text-[10px]">Esc</button>
          </div>
          {filteredMacros.map((m, idx) => (
            <button
              key={m.id}
              onClick={() => { setText(m.text); setShowMacros(false); setMacroFilter(''); }}
              className={`w-full text-left px-3 py-2 border-b border-gray-600/30 last:border-0 transition ${
                idx === selectedMacroIdx ? 'bg-gray-600' : 'hover:bg-gray-600/50'
              }`}
            >
              <div className="flex items-center gap-2">
                {m.shortcut && (
                  <span className="text-[10px] text-green-400 bg-green-900/30 px-1.5 py-0.5 rounded font-mono">/{m.shortcut}</span>
                )}
                <span className="text-xs text-white font-medium">{m.name}</span>
              </div>
              <p className="text-[11px] text-gray-400 mt-0.5 line-clamp-1">{m.text}</p>
            </button>
          ))}
        </div>
      )}

      {/* Template picker dropdown */}
      {showTemplates && (
        <div className="mb-3 bg-gray-700 border border-gray-600 rounded-lg max-h-60 overflow-auto">
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-600">
            <span className="text-xs font-medium text-white">Seleccionar plantilla</span>
            <button onClick={() => setShowTemplates(false)} className="text-gray-400 hover:text-white text-xs">Cerrar</button>
          </div>
          {templates.length === 0 ? (
            <div className="px-3 py-4 text-center text-xs text-gray-500">No hay plantillas aprobadas</div>
          ) : (
            templates.map(t => (
              <button
                key={t.id}
                onClick={() => handleSendTemplate(t)}
                disabled={!!sendingTemplate}
                className="w-full text-left px-3 py-2.5 hover:bg-gray-600 border-b border-gray-600/50 last:border-0 transition disabled:opacity-50"
              >
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-sm text-white font-medium">{t.name}</span>
                  <span className="text-[10px] text-gray-500">{t.language.toUpperCase()} · {t.category}</span>
                </div>
                <p className="text-xs text-gray-400 line-clamp-2">{t.body_text}</p>
                {sendingTemplate === t.id && (
                  <span className="text-[10px] text-green-400 mt-1 block">Enviando...</span>
                )}
              </button>
            ))
          )}
        </div>
      )}

      {/* Attachment preview */}
      {attachedFile && (
        <div className="mb-2 flex items-center gap-2 bg-gray-700/50 rounded-lg px-3 py-2">
          {attachedFile.preview ? (
            <img src={attachedFile.preview} alt="" className="w-10 h-10 rounded object-cover" />
          ) : (
            <div className="w-10 h-10 bg-gray-600 rounded flex items-center justify-center">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-xs text-white truncate">{attachedFile.file.name}</p>
            <p className="text-[10px] text-gray-500">{(attachedFile.file.size / 1024).toFixed(0)} KB · {attachedFile.type}</p>
          </div>
          <button onClick={removeAttachment} className="text-gray-500 hover:text-red-400 flex-shrink-0">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Conversation closed banner */}
      {disabled && disabledReason && !isNoteMode && (
        <div className="text-xs text-amber-400 mb-2 flex items-center gap-2">
          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
          <span className="flex-1">{disabledReason}</span>
        </div>
      )}

      {/* Window expired info banner — input still enabled */}
      {!disabled && isWindowExpired && !isNoteMode && (
        <div className="text-xs text-orange-400 mb-2 flex items-center gap-2">
          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
          </svg>
          <span className="flex-1">Sin ventana de 24h — usa una plantilla para iniciar conversacion</span>
          {conversationId && (
            <button
              onClick={fetchTemplates}
              disabled={loadingTemplates}
              className="px-2 py-0.5 bg-green-600 hover:bg-green-500 text-white rounded text-[11px] font-medium flex-shrink-0 disabled:opacity-50"
            >
              {loadingTemplates ? 'Cargando...' : 'Enviar plantilla'}
            </button>
          )}
        </div>
      )}

      {isNoteMode && (
        <div className="text-xs text-green-400 mb-2 flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
          </svg>
          Modo nota interna - Solo visible para agentes
        </div>
      )}
      <div className="flex items-end gap-2">
        {onCreateNote && (
          <button
            onClick={() => setIsNoteMode(!isNoteMode)}
            className={`p-2 rounded-lg transition-colors flex-shrink-0 ${
              isNoteMode
                ? 'bg-green-600/20 text-green-400 border border-green-500/30'
                : 'text-gray-500 hover:text-gray-300 hover:bg-gray-700'
            }`}
            title={isNoteMode ? 'Cambiar a mensaje' : 'Escribir nota interna'}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
        )}

        {/* Attachment button */}
        {!isNoteMode && !disabled && (
          <div className="relative flex-shrink-0">
            <button
              onClick={() => setShowAttachMenu(!showAttachMenu)}
              className="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-gray-700 transition-colors"
              title="Adjuntar archivo"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            </button>
            {showAttachMenu && (
              <div className="absolute bottom-10 left-0 bg-gray-700 border border-gray-600 rounded-lg shadow-lg py-1 min-w-[140px] z-10">
                <button onClick={() => handleFileSelect('image')} className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600 flex items-center gap-2">
                  <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                  Imagen
                </button>
                <button onClick={() => handleFileSelect('video')} className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600 flex items-center gap-2">
                  <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                  Video
                </button>
                <button onClick={() => handleFileSelect('audio')} className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600 flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" /></svg>
                  Audio
                </button>
                <button onClick={() => handleFileSelect('document')} className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600 flex items-center gap-2">
                  <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                  Documento
                </button>
              </div>
            )}
          </div>
        )}

        {/* Template button — always accessible */}
        {!isNoteMode && conversationId && (
          <button
            onClick={fetchTemplates}
            disabled={loadingTemplates}
            className="p-2 rounded-lg text-gray-500 hover:text-green-400 hover:bg-gray-700 transition-colors flex-shrink-0 disabled:opacity-50"
            title="Enviar plantilla"
          >
            {loadingTemplates ? (
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            )}
          </button>
        )}

        <textarea
          ref={textareaRef}
          aria-label={isNoteMode ? 'Escribir nota interna' : 'Escribir mensaje'}
          value={text}
          onChange={(e) => {
            const val = e.target.value;
            setText(val);
            // Detect "/" at the beginning to open macro command palette
            if (val.startsWith('/')) {
              setShowMacros(true);
              setMacroFilter(val.slice(1));
              setSelectedMacroIdx(0);
            } else {
              setShowMacros(false);
              setMacroFilter('');
            }
          }}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={inputDisabled}
          placeholder={
            isNoteMode
              ? 'Escribir nota interna...'
              : attachedFile
                ? 'Añadir texto (opcional)...'
                : disabled
                  ? 'No puedes enviar mensajes'
                  : 'Escribe un mensaje...'
          }
          rows={1}
          className={`flex-1 resize-none rounded-lg border text-sm px-3 py-2 placeholder-gray-500 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed ${
            isNoteMode
              ? 'bg-green-900/10 border-green-600/30 text-green-100 focus:border-green-500'
              : 'bg-gray-700 border-gray-600 text-white focus:border-green-500'
          }`}
        />
        <button
          onClick={handleSubmit}
          disabled={inputDisabled || (!text.trim() && !attachedFile)}
          className={`p-2 rounded-lg text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
            isNoteMode
              ? 'bg-green-700 hover:bg-green-600'
              : 'bg-green-600 hover:bg-green-500'
          }`}
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default ChatInput;
