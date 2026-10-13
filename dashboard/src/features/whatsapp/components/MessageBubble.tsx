import React from 'react';
import type { WAMessage } from '../types';

interface MessageBubbleProps {
  message: WAMessage;
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}

function DeliveryTicks({ status }: { status: string }) {
  if (status === 'pending') return <span className="text-gray-500">&#10003;</span>;
  if (status === 'sent') return <span className="text-gray-400">&#10003;</span>;
  if (status === 'delivered') return <span className="text-gray-400">&#10003;&#10003;</span>;
  if (status === 'read') return <span className="text-blue-400">&#10003;&#10003;</span>;
  if (status === 'failed') return <span className="text-red-400">!</span>;
  return null;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isOutbound = message.direction === 'outbound';

  return (
    <div className={`flex ${isOutbound ? 'justify-end' : 'justify-start'} mb-2`}>
      <div
        className={`max-w-[70%] rounded-xl px-4 py-2 ${
          isOutbound
            ? 'bg-green-700/30 border border-green-600/30 rounded-br-sm'
            : 'bg-gray-700 border border-gray-600 rounded-bl-sm'
        }`}
      >
        {message.text_body && (
          <p className="text-sm text-white whitespace-pre-wrap break-words">{message.text_body}</p>
        )}
        {message.msg_type !== 'text' && !message.text_body && (
          <p className="text-sm text-gray-400 italic">[{message.msg_type}]</p>
        )}
        {message.media_caption && (
          <p className="text-sm text-gray-300 mt-1">{message.media_caption}</p>
        )}
        <div className={`flex items-center gap-1 mt-1 ${isOutbound ? 'justify-end' : 'justify-start'}`}>
          <span className="text-[10px] text-gray-500">{formatTime(message.created_at)}</span>
          {isOutbound && <DeliveryTicks status={message.delivery_status} />}
          {message.is_from_ai && (
            <span className="text-[10px] text-purple-400 ml-1">AI</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
