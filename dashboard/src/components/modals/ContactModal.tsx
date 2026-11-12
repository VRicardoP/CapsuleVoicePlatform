import React, { useState } from 'react';
import { apiService } from '../../services/api';

interface ContactModalProps {
  onClose: () => void;
  initialSubject?: string;
  initialMessage?: string;
}

const ContactModal: React.FC<ContactModalProps> = ({ onClose, initialSubject = '', initialMessage = '' }) => {
  const [subject, setSubject] = useState(initialSubject);
  const [message, setMessage] = useState(initialMessage);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!subject.trim() || !message.trim()) {
      setError('Por favor, completa todos los campos.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await apiService.sendContactEmail({
        subject: subject.trim(),
        message: message.trim(),
      });

      if (response.success) {
        setShowSuccess(true);
        setSubject('');
        setMessage('');
        setTimeout(() => {
          setShowSuccess(false);
          onClose();
        }, 3000);
      } else {
        setError(response.error || 'Error al enviar el mensaje. Por favor, inténtalo de nuevo.');
      }
    } catch {
      setError('Error al enviar el mensaje. Por favor, inténtalo de nuevo.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl max-w-lg w-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex justify-between items-start">
          <div>
            <h2 className="text-2xl font-bold text-white">Contacto</h2>
            <p className="text-gray-400 text-sm mt-1">Ponte en contacto con nosotros</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl transition"
            aria-label="Cerrar"
          >
            ×
          </button>
        </div>

        {/* Company Info */}
        <div className="px-6 pt-6 pb-4 flex items-center gap-6">
          <img
            src="/icono.png"
            alt="Capsule Corp"
            className="h-24 w-auto flex-shrink-0"
          />
          <div className="text-white text-base font-bold leading-relaxed">
            <p>Carrer Isaac Albéniz 48</p>
            <p>Malgrat de Mar, C.P. 08380</p>
            <p>Barcelona</p>
            <p className="mt-2">Telf: 900 009 099</p>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 pt-2 overflow-y-auto">

          {/* Success Message */}
          {showSuccess && (
            <div className="bg-green-900/30 border border-green-500/40 rounded-lg p-4 text-green-300 flex items-center gap-3 mb-4">
              <svg className="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <div>
                <p className="font-semibold">Mensaje enviado correctamente</p>
                <p className="text-xs text-green-400">Nos pondremos en contacto contigo lo antes posible</p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-900/30 border border-red-500/40 rounded-lg p-4 text-red-300 flex items-center gap-3 mb-4">
              <svg className="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p>{error}</p>
            </div>
          )}

          {/* Contact Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="contact-subject" className="text-sm text-gray-400 block mb-1">
                Asunto <span className="text-red-400">*</span>
              </label>
              <input
                id="contact-subject"
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Escribe el asunto de tu mensaje"
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none transition"
                disabled={isSubmitting}
                required
              />
            </div>

            <div>
              <label htmlFor="contact-message" className="text-sm text-gray-400 block mb-1">
                Mensaje <span className="text-red-400">*</span>
              </label>
              <textarea
                id="contact-message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Escribe tu mensaje aquí..."
                rows={5}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none resize-none transition"
                disabled={isSubmitting}
                required
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={isSubmitting || !subject.trim() || !message.trim()}
                className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isSubmitting ? 'Enviando...' : 'Enviar Mensaje'}
              </button>
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition disabled:opacity-50"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 bg-gray-900/50">
          <p className="text-xs text-gray-500 text-center">
            Tu mensaje será enviado al equipo de Capsule Corp
          </p>
        </div>
      </div>
    </div>
  );
};

export default ContactModal;
