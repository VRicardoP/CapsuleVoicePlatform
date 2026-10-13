import React, { useState } from 'react';
import { whatsappApi } from '../services/whatsappApi';

interface NewConversationModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (conversationId: string) => void;
}

const NewConversationModal: React.FC<NewConversationModalProps> = ({ open, onClose, onCreated }) => {
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState('');

  if (!open) return null;

  const handleCreate = async () => {
    const trimmed = phone.trim();
    if (!trimmed.startsWith('+') || trimmed.length < 8) {
      setFormError('Formato requerido: +34612345678');
      return;
    }
    setCreating(true);
    setFormError('');
    try {
      let contactId: string;
      try {
        const contact = await whatsappApi.createContact({
          phone_e164: trimmed,
          display_name: name.trim() || undefined,
        });
        contactId = contact.id;
      } catch (err) {
        if (err instanceof Error && err.message.includes('already exists')) {
          const res = await whatsappApi.getContacts({ search: trimmed, limit: 1 });
          if (!res.items.length) { setFormError('Contacto no encontrado'); setCreating(false); return; }
          contactId = res.items[0].id;
        } else {
          throw err;
        }
      }
      const conv = await whatsappApi.startConversation(contactId);
      setPhone('');
      setName('');
      setFormError('');
      onCreated(conv.id);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Error al crear conversación');
    }
    setCreating(false);
  };

  const handleClose = () => {
    setPhone('');
    setName('');
    setFormError('');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={handleClose}>
      <div
        className="bg-gray-800 border border-gray-700 rounded-2xl w-full max-w-md overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white">Nueva conversación</h2>
          <button onClick={handleClose} className="text-gray-400 hover:text-white text-2xl leading-none transition-colors">&times;</button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Teléfono</label>
            <input
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="+34612345678"
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-500 focus:border-green-500 focus:outline-none transition"
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Nombre (opcional)</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Nombre del contacto"
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-500 focus:border-green-500 focus:outline-none transition"
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
            />
          </div>
          {formError && (
            <p className="text-red-400 text-sm bg-red-900/20 border border-red-500/30 rounded-lg px-3 py-2">{formError}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-700 bg-gray-900/50">
          <button
            onClick={handleClose}
            className="px-4 py-2.5 bg-gray-700 text-white text-sm rounded-lg hover:bg-gray-600 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleCreate}
            disabled={creating || !phone.trim()}
            className="px-4 py-2.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {creating ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                Creando...
              </span>
            ) : 'Crear conversación'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default NewConversationModal;
