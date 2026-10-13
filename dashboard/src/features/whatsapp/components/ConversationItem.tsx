import React from 'react';
import type { WAConversation } from '../types';
import { formatPhone } from '../utils';

interface ConversationItemProps {
  conversation: WAConversation;
  isActive: boolean;
  /** Just replied to in this session — kept visible with a "respondida" mark. */
  isPinned?: boolean;
  onClick: () => void;
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  if (isToday) {
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  }

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Ayer';
  }

  return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
}

function getInitials(name: string | null, phone: string): string {
  if (name) {
    return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
  }
  return phone.slice(-2);
}

const ConversationItem: React.FC<ConversationItemProps> = ({ conversation, isActive, isPinned, onClick }) => {
  const { contact } = conversation;
  const displayName = contact.display_name || formatPhone(contact.phone_e164);
  const initials = getInitials(contact.display_name, formatPhone(contact.phone_e164));

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 flex items-center gap-3 transition-colors border-l-2 ${
        isActive
          ? 'bg-green-600/10 border-green-500'
          : 'hover:bg-gray-700/30 border-transparent'
      }`}
    >
      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-600 to-green-800 text-white flex items-center justify-center text-sm font-semibold flex-shrink-0">
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium truncate ${isActive ? 'text-white' : 'text-gray-200'}`}>{displayName}</span>
          <span className="text-[11px] text-gray-500 flex-shrink-0 ml-2 flex items-center gap-1">
            {isPinned && (
              <span className="text-green-500" title="Respondida — se mantiene en la lista">✓</span>
            )}
            {formatTime(conversation.last_message_at)}
          </span>
        </div>
        <div className="flex items-center justify-between mt-0.5">
          <span className="text-xs text-gray-500 truncate">
            {conversation.last_message_text || 'Sin mensajes'}
          </span>
          {conversation.unread_count > 0 && (
            <span className="bg-green-500 text-white text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0 ml-2">
              {conversation.unread_count > 9 ? '9+' : conversation.unread_count}
            </span>
          )}
        </div>
        {conversation.contact_tags && conversation.contact_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {conversation.contact_tags.map(tag => (
              <span
                key={tag.id}
                className="px-1.5 py-0 rounded text-[9px] leading-[16px]"
                style={{ backgroundColor: tag.color + '25', color: tag.color }}
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </button>
  );
};

export default ConversationItem;
