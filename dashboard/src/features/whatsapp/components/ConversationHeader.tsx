import React from 'react';
import type { WAConversation } from '../types';
import { formatPhone } from '../utils';

interface ConversationHeaderProps {
  conversation: WAConversation;
  onClose: () => void;
  onMarkRead: () => void;
}

function windowStatus(expiresAt: string | null): { label: string; color: string } {
  if (!expiresAt) return { label: 'Sin ventana', color: 'text-gray-500' };
  const remaining = new Date(expiresAt).getTime() - Date.now();
  if (remaining <= 0) return { label: 'Ventana expirada', color: 'text-red-400' };
  const hours = Math.floor(remaining / 3_600_000);
  const mins = Math.floor((remaining % 3_600_000) / 60_000);
  if (hours > 0) return { label: `Ventana: ${hours}h ${mins}m`, color: 'text-green-400' };
  return { label: `Ventana: ${mins}m`, color: 'text-amber-400' };
}

const ConversationHeader: React.FC<ConversationHeaderProps> = ({ conversation, onClose, onMarkRead }) => {
  const contact = conversation.contact;
  const window = windowStatus(conversation.window_expires_at);

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-600 to-green-800 flex items-center justify-center flex-shrink-0">
          <span className="text-white font-semibold text-sm">
            {(contact.display_name || formatPhone(contact.phone_e164)).charAt(0).toUpperCase()}
          </span>
        </div>
        <div className="min-w-0">
          <h3 className="text-white font-medium text-sm truncate">
            {contact.display_name || formatPhone(contact.phone_e164)}
          </h3>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-400">{formatPhone(contact.phone_e164)}</span>
            <span className={`${window.color} text-[11px]`}>{window.label}</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {conversation.unread_count > 0 && (
          <button
            onClick={onMarkRead}
            className="text-xs text-gray-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-gray-700 transition-colors border border-transparent hover:border-gray-600"
          >
            Marcar leido
          </button>
        )}
        {conversation.status !== 'closed' && (
          <button
            onClick={onClose}
            className="text-xs text-gray-400 hover:text-red-400 px-3 py-1.5 rounded-lg hover:bg-red-900/20 transition-colors border border-transparent hover:border-red-500/30"
          >
            Cerrar
          </button>
        )}
      </div>
    </div>
  );
};

export default ConversationHeader;
