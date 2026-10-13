import React, { useState } from 'react';
import { useWhatsApp } from '../context/WhatsAppContext';
import ConversationList from '../components/ConversationList';
import ChatView from '../components/ChatView';
import ContactPanel from '../components/ContactPanel';
import EmptyState from '../components/EmptyState';
import NewConversationModal from '../components/NewConversationModal';

const InboxPage: React.FC = () => {
  const {
    conversations,
    conversationsLoading,
    activeConversation,
    messages,
    messagesLoading,
    hasMoreMessages,
    selectConversation,
    sendMessage,
    sendTemplate,
    closeConversation,
    markAsRead,
    loadMoreMessages,
    // Phase A
    segments,
    activeSegmentId,
    setActiveSegmentId,
    contact,
    contactLoading,
    notes,
    assignContactSegments,
    createNote,
    updateNote,
    deleteNote,
    createSegment,
    refetchConversations,
    tags,
    assignContactTags,
    createTag,
  } = useWhatsApp();

  const activeSegment = activeSegmentId
    ? segments.find(s => s.id === activeSegmentId)
    : null;

  const [showNewModal, setShowNewModal] = useState(false);

  const handleConversationCreated = async (conversationId: string) => {
    await refetchConversations();
    selectConversation(conversationId);
    setShowNewModal(false);
  };

  const activeCount = conversations.filter(c => c.status !== 'closed').length;

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Page header - dashboard style */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white">
              {activeSegment ? activeSegment.name : 'Inbox'}
            </h1>
            {activeSegment && (
              <button
                onClick={() => setActiveSegmentId(null)}
                className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
                title="Quitar filtro"
              >
                x
              </button>
            )}
          </div>
          <p className="text-gray-400 text-sm">
            {activeCount} conversaciones{activeSegment ? ` en ${activeSegment.name}` : ' activas'}
          </p>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="px-4 py-2.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-500 transition-colors flex items-center gap-2"
        >
          <span className="text-lg leading-none">+</span>
          Nueva conversación
        </button>
      </div>

      {/* Main content card - dashboard style */}
      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex">
        {/* Conversation list */}
        <div id="wa-inbox-conversations" className="w-80 flex-shrink-0 border-r border-gray-700">
          <ConversationList
            conversations={conversations}
            loading={conversationsLoading}
            activeId={activeConversation?.id || null}
            segments={segments}
            tags={tags}
            onSelect={selectConversation}
            onRefetch={refetchConversations}
          />
        </div>

        {/* Chat view */}
        <div id="wa-inbox-chat" className="flex-1 min-w-0">
          {activeConversation ? (
            <ChatView
              conversation={activeConversation}
              messages={messages}
              loading={messagesLoading}
              hasMore={hasMoreMessages}
              onLoadMore={loadMoreMessages}
              onSend={sendMessage}
              onClose={closeConversation}
              onMarkRead={markAsRead}
              notes={notes}
              onCreateNote={createNote}
              onUpdateNote={updateNote}
              onDeleteNote={deleteNote}
              onTemplateSent={sendTemplate}
            />
          ) : (
            <EmptyState />
          )}
        </div>

        {/* Contact panel (only when conversation selected) */}
        {activeConversation && (
          <div id="wa-inbox-contact">
          <ContactPanel
            contact={contact}
            loading={contactLoading}
            allSegments={segments}
            allTags={tags}
            notes={notes}
            windowExpiresAt={activeConversation.window_expires_at}
            onAssignSegments={async (ids) => {
              if (contact) { await assignContactSegments(contact.id, ids); await refetchConversations(); }
            }}
            onAssignTags={(ids) => {
              if (contact) assignContactTags(contact.id, ids);
            }}
            onCreateNote={createNote}
            onUpdateNote={updateNote}
            onDeleteNote={deleteNote}
            onCreateSegment={createSegment}
            onCreateTag={createTag}
          />
          </div>
        )}
      </div>

      {/* New conversation modal */}
      <NewConversationModal
        open={showNewModal}
        onClose={() => setShowNewModal(false)}
        onCreated={handleConversationCreated}
      />
    </div>
  );
};

export default InboxPage;
