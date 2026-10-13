import React, { createContext, useContext, useCallback, useEffect, useRef, useState } from 'react';
import type { WAConversation, WAMessage, WASegment, WATag, WAInternalNote, WAContactDetail } from '../types';
import { useConversations } from '../hooks/useConversations';
import { useMessages } from '../hooks/useMessages';
import { useSSE } from '../hooks/useSSE';
import { useSegments } from '../hooks/useSegments';
import { useNotes } from '../hooks/useNotes';
import { useContact } from '../hooks/useContact';
import { useToast } from '../components/Toast';
import { whatsappApi } from '../services/whatsappApi';

interface WhatsAppState {
  // Conversations
  conversations: WAConversation[];
  conversationsLoading: boolean;
  // Pagination for large inboxes (500+ conversations)
  conversationsTotal: number;
  hasMoreConversations: boolean;
  loadingMoreConversations: boolean;
  loadMoreConversations: () => Promise<void>;
  // IDs of conversations just replied to, kept visible until the view changes
  pinnedConversationIds: Set<string>;
  activeConversation: WAConversation | null;
  messages: WAMessage[];
  messagesLoading: boolean;
  hasMoreMessages: boolean;
  selectConversation: (id: string) => void;
  sendMessage: (text: string) => Promise<void>;
  sendTemplate: (templateId: string) => Promise<void>;
  closeConversation: () => Promise<void>;
  markAsRead: () => Promise<void>;
  loadMoreMessages: () => void;
  refetchConversations: () => Promise<void>;
  // Phase A: Segments
  segments: WASegment[];
  activeSegmentId: string | null;
  setActiveSegmentId: (id: string | null) => void;
  // Unanswered (no respondidos) filter
  unansweredFilter: boolean;
  setUnansweredFilter: (v: boolean) => void;
  refreshActiveConversation: () => Promise<void>;
  // Phase A: Contact
  contact: WAContactDetail | null;
  contactLoading: boolean;
  assignContactSegments: (contactId: string, segmentIds: string[]) => Promise<void>;
  // Phase A: Notes
  notes: WAInternalNote[];
  createNote: (content: string) => Promise<void>;
  updateNote: (noteId: string, content: string) => Promise<void>;
  deleteNote: (noteId: string) => Promise<void>;
  // Phase A: Create segment from contact panel
  createSegment: (data: { name: string; color?: string }) => Promise<WASegment>;
  refetchSegments: () => Promise<void>;
  // Tags
  tags: WATag[];
  assignContactTags: (contactId: string, tagIds: string[]) => Promise<void>;
  createTag: (data: { name: string; color?: string }) => Promise<WATag>;
}

const WhatsAppContext = createContext<WhatsAppState | null>(null);

export function useWhatsApp(): WhatsAppState {
  const ctx = useContext(WhatsAppContext);
  if (!ctx) throw new Error('useWhatsApp must be used within WhatsAppProvider');
  return ctx;
}

export const WhatsAppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { toast } = useToast();
  // Phase A: Segments (before useConversations so activeSegmentId is available)
  const {
    segments,
    activeSegmentId,
    setActiveSegmentId,
    createSegment: createSegmentRaw,
    refetch: refetchSegments,
  } = useSegments();

  const [unansweredFilter, setUnansweredFilter] = useState<boolean>(false);
  const [activeId, setActiveId] = useState<string | null>(null);

  const {
    conversations,
    loading: conversationsLoading,
    loadingMore: loadingMoreConversations,
    total: conversationsTotal,
    hasMore: hasMoreConversations,
    loadMore: loadMoreConversations,
    updateConversationFromSSE,
    addOrUpdateMessagePreview,
    refetch: refetchConversations,
    pinnedIds: pinnedConversationIds,
    pinConversation,
  } = useConversations(activeSegmentId, unansweredFilter, activeId);


  // Clear active conversation when segment filter changes
  const prevSegmentRef = React.useRef(activeSegmentId);
  useEffect(() => {
    if (prevSegmentRef.current !== activeSegmentId) {
      setActiveId(null);
      prevSegmentRef.current = activeSegmentId;
    }
  }, [activeSegmentId]);

  const {
    messages,
    loading: messagesLoading,
    hasMore: hasMoreMessages,
    fetchMessages,
    loadMore,
    addMessage,
    updateMessageStatus,
  } = useMessages(activeId);

  // Phase A: Contact detail
  const {
    contact,
    loading: contactLoading,
    fetchContact,
    assignSegments: assignContactSegments,
  } = useContact();

  // Phase A: Internal notes
  const {
    notes,
    fetchNotes,
    createNote: createNoteRaw,
    updateNote: updateNoteRaw,
    deleteNote: deleteNoteRaw,
    addNoteFromSSE,
  } = useNotes(activeId);

  const activeConversation = conversations.find(c => c.id === activeId) || null;

  // Ref to access conversations without adding it as a useEffect dependency.
  // Without this, every SSE event that updates conversations would re-trigger
  // fetchMessages/fetchContact/fetchNotes, creating race conditions.
  const conversationsRef = useRef(conversations);
  conversationsRef.current = conversations;

  // Fetch messages + contact + notes ONLY when the selected conversation changes
  useEffect(() => {
    if (activeId) {
      fetchMessages(activeId);
      const conv = conversationsRef.current.find(c => c.id === activeId);
      if (conv) {
        fetchContact(conv.contact.id);
        fetchNotes(activeId);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, fetchMessages, fetchContact, fetchNotes]);

  // SSE handlers — field names match backend camelCase convention
  useSSE('/api/v1/whatsapp/events', {
    'message.new': (data: { conversationId: string; message: WAMessage }) => {
      const existsInList = conversationsRef.current.some(c => c.id === data.conversationId);

      if (existsInList) {
        addOrUpdateMessagePreview(
          data.conversationId,
          data.message.text_body,
          data.message.created_at,
          data.message.direction,
          data.message.is_from_ai === true,
        );
      } else {
        // New conversation created by inbound message — refetch list
        refetchConversations();
      }

      if (data.conversationId === activeId) {
        addMessage(data.message);
      }

      if (data.conversationId !== activeId && data.message.direction === 'inbound' && existsInList) {
        updateConversationFromSSE(data.conversationId, {
          unread_count: (conversationsRef.current.find(c => c.id === data.conversationId)?.unread_count || 0) + 1,
        });
      }
    },
    'message.status': (data: { conversationId: string; messageId: string; status: string; timestamp: string }) => {
      if (data.conversationId === activeId) {
        updateMessageStatus(data.messageId, data.status, data.timestamp);
      }
    },
    'conversation.updated': (data: { conversationId: string; changes: Partial<WAConversation> }) => {
      updateConversationFromSSE(data.conversationId, data.changes);
      if (!conversationsRef.current.find(c => c.id === data.conversationId)) {
        refetchConversations();
      }
    },
    'note.new': (data: { conversationId: string; note: { id: string; authorUserId: string; authorName: string; content: string; createdAt: string } }) => {
      if (data.conversationId === activeId) {
        addNoteFromSSE({
          id: data.note.id,
          author_user_id: data.note.authorUserId,
          author_name: data.note.authorName,
          content: data.note.content,
          created_at: data.note.createdAt,
        });
      }
    },
  });

  const selectConversation = useCallback((id: string) => {
    setActiveId(id);
    // Auto-mark as read: reset badge immediately, then sync with backend
    updateConversationFromSSE(id, { unread_count: 0 });
    whatsappApi.markAsRead(id).catch(() => {});
  }, [updateConversationFromSSE]);

  const sendMessage = useCallback(async (text: string) => {
    if (!activeId) return;
    try {
      const msg = await whatsappApi.sendMessage(activeId, text);
      addMessage(msg);
      addOrUpdateMessagePreview(activeId, text, msg.created_at, 'outbound');
      pinConversation(activeId);  // keep visible after it stops being "unanswered"
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Error enviando mensaje';
      toast(typeof detail === 'string' ? detail : 'Error enviando mensaje', 'error');
    }
  }, [activeId, addMessage, addOrUpdateMessagePreview, pinConversation, toast]);

  const sendTemplate = useCallback(async (templateId: string) => {
    if (!activeId) return;
    try {
      const msg = await whatsappApi.sendTemplate(activeId, templateId);
      addMessage(msg);
      addOrUpdateMessagePreview(activeId, msg.text_body || '[Plantilla]', msg.created_at, 'outbound');
      pinConversation(activeId);  // same as sendMessage: optimistic + keep visible, no forced refetch
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Error enviando plantilla';
      toast(typeof detail === 'string' ? detail : 'Error enviando plantilla', 'error');
      throw err;
    }
  }, [activeId, addMessage, addOrUpdateMessagePreview, pinConversation, toast]);

  const closeConversation = useCallback(async () => {
    if (!activeId) return;
    await whatsappApi.closeConversation(activeId);
    updateConversationFromSSE(activeId, { status: 'closed' });
  }, [activeId, updateConversationFromSSE]);

  const markAsRead = useCallback(async () => {
    if (!activeId) return;
    await whatsappApi.markAsRead(activeId);
    updateConversationFromSSE(activeId, { unread_count: 0 });
  }, [activeId, updateConversationFromSSE]);

  const refreshActiveConversation = useCallback(async () => {
    if (!activeId) return;
    refetchConversations();
    fetchMessages(activeId);
  }, [activeId, refetchConversations, fetchMessages]);

  const createNote = useCallback(async (content: string) => {
    await createNoteRaw(content);
  }, [createNoteRaw]);

  const updateNote = useCallback(async (noteId: string, content: string) => {
    await updateNoteRaw(noteId, content);
  }, [updateNoteRaw]);

  const deleteNote = useCallback(async (noteId: string) => {
    await deleteNoteRaw(noteId);
  }, [deleteNoteRaw]);

  const createSegment = useCallback(async (data: { name: string; color?: string }) => {
    return await createSegmentRaw(data);
  }, [createSegmentRaw]);

  // Tags
  const [tags, setTags] = useState<WATag[]>([]);
  useEffect(() => {
    whatsappApi.getTags().then(res => setTags(res.items)).catch(() => {});
  }, []);

  const assignContactTags = useCallback(async (contactId: string, tagIds: string[]) => {
    await whatsappApi.updateContact(contactId, { tag_ids: tagIds });
    await fetchContact(contactId);
    await refetchConversations();
  }, [fetchContact, refetchConversations]);

  const createTag = useCallback(async (data: { name: string; color?: string }) => {
    const tag = await whatsappApi.createTag(data);
    setTags(prev => [...prev, tag]);
    return tag;
  }, []);

  return (
    <WhatsAppContext.Provider
      value={{
        conversations,
        conversationsLoading,
        conversationsTotal,
        hasMoreConversations,
        loadingMoreConversations,
        loadMoreConversations,
        pinnedConversationIds,
        activeConversation,
        messages,
        messagesLoading,
        hasMoreMessages,
        selectConversation,
        sendMessage,
        sendTemplate,
        closeConversation,
        markAsRead,
        loadMoreMessages: loadMore,
        refetchConversations,
        refreshActiveConversation,
        // Phase A
        segments,
        activeSegmentId,
        setActiveSegmentId,
        unansweredFilter,
        setUnansweredFilter,
        contact,
        contactLoading,
        assignContactSegments,
        notes,
        createNote,
        updateNote,
        deleteNote,
        createSegment,
        refetchSegments,
        tags,
        assignContactTags,
        createTag,
      }}
    >
      {children}
    </WhatsAppContext.Provider>
  );
};
