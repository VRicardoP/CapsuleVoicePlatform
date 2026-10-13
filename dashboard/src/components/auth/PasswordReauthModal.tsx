/**
 * Password re-authentication modal.
 *
 * Shown when the backend rejects a sensitive operation with
 * X-Reauth-Code: REAUTH_REQUIRED. The user types their current password,
 * we hit /auth/login again (which refreshes recent_auth_at on the active
 * session), and the caller retries the original action.
 */
import React, { useState } from 'react';
import { authApi } from '../../services/api/authApi';

interface Props {
  /** Email of the currently authenticated user (prefilled, read-only). */
  email: string;
  /** Called when the user successfully re-authenticated. The caller should retry the operation. */
  onSuccess: () => void;
  /** Called when the user dismisses the modal without re-authenticating. */
  onCancel: () => void;
}

const PasswordReauthModal: React.FC<Props> = ({ email, onSuccess, onCancel }) => {
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const res = await authApi.login(email, password);
    if (res.success) {
      onSuccess();
    } else {
      setError(res.error || 'Contraseña incorrecta');
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onCancel}
    >
      <div
        className="bg-gray-800 rounded-lg shadow-xl w-full max-w-sm p-6 border border-gray-700"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-white mb-2">
          Confirmar identidad
        </h2>
        <p className="text-sm text-gray-400 mb-4">
          Esta acción requiere reintroducir tu contraseña por seguridad.
        </p>
        {error && (
          <div className="mb-3 p-2 bg-red-900/30 border border-red-600/40 rounded text-red-400 text-sm">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email</label>
            <input
              type="email"
              value={email}
              disabled
              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-400 text-sm cursor-not-allowed"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Contraseña *</label>
            <input
              type="password"
              required
              autoFocus
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting || !password}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-500 disabled:opacity-50 transition"
            >
              {submitting ? 'Confirmando...' : 'Confirmar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PasswordReauthModal;
