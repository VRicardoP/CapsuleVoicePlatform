import { useState, useCallback, useRef } from 'react';
import type { WAInternalNote } from '../types';
import { whatsappApi } from '../services/whatsappApi';

export function useNotes(conversationId: string | null) {
  const [notes, setNotes] = useState<WAInternalNote[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const fetchNotes = useCallback(async (convId: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    try {
      const data = await whatsappApi.getNotes(convId, controller.signal);
      if (controller.signal.aborted) return;
      setNotes(data.items);
    } catch {
      if (controller.signal.aborted) return;
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  const createNote = useCallback(async (content: string) => {
    if (!conversationId) return;
    const note = await whatsappApi.createNote(conversationId, content);
    setNotes(prev => {
      if (prev.some(n => n.id === note.id)) return prev;
      return [...prev, note];
    });
    return note;
  }, [conversationId]);

  const updateNote = useCallback(async (noteId: string, content: string) => {
    if (!conversationId) return;
    const updated = await whatsappApi.updateNote(conversationId, noteId, content);
    setNotes(prev => prev.map(n => n.id === noteId ? updated : n));
    return updated;
  }, [conversationId]);

  const deleteNote = useCallback(async (noteId: string) => {
    if (!conversationId) return;
    await whatsappApi.deleteNote(conversationId, noteId);
    setNotes(prev => prev.filter(n => n.id !== noteId));
  }, [conversationId]);

  const addNoteFromSSE = useCallback((note: WAInternalNote) => {
    setNotes(prev => {
      if (prev.some(n => n.id === note.id)) return prev;
      return [...prev, note];
    });
  }, []);

  return { notes, loading, fetchNotes, createNote, updateNote, deleteNote, addNoteFromSSE };
}
