import React from 'react';
import type { ConsentInfo } from '../../../types';

/* ========================================================================== */
/*  Static data                                                                */
/* ========================================================================== */

const MOCK_CONSENTS: ConsentInfo[] = [
  { id: 'consent-001', purpose: 'Grabacion de llamadas telefonicas',       given: true,  obtainedAt: '2025-01-10T10:00:00Z', expiresAt: '2026-01-10T10:00:00Z', canRevoke: true },
  { id: 'consent-002', purpose: 'Procesamiento de transcripciones',        given: true,  obtainedAt: '2025-01-10T10:00:00Z', expiresAt: '2026-01-10T10:00:00Z', canRevoke: true },
  { id: 'consent-003', purpose: 'Analisis de sentimiento de conversaciones', given: true, obtainedAt: '2025-01-10T10:00:00Z', canRevoke: true },
  { id: 'consent-004', purpose: 'Comunicaciones de marketing',             given: false, obtainedAt: '2025-01-10T10:00:00Z', revokedAt: '2025-01-12T15:30:00Z', canRevoke: false },
];

/* ========================================================================== */
/*  Helpers                                                                    */
/* ========================================================================== */

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function getDaysUntilExpiry(expiresAt?: string): number | null {
  if (!expiresAt) return null;
  const diffTime = new Date(expiresAt).getTime() - Date.now();
  return Math.max(0, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
}

/* ========================================================================== */
/*  Component                                                                  */
/* ========================================================================== */

interface ConsentTabProps {
  canManageConsents: () => boolean;
  handleRevokeConsent: (consentId: string) => void;
}

const ConsentTab: React.FC<ConsentTabProps> = ({ canManageConsents, handleRevokeConsent }) => (
  <div className="space-y-4">
    <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 text-sm text-blue-300">
      <strong>Art. 7 RGPD:</strong> Puedes revocar tu consentimiento en cualquier momento.
      La retirada del consentimiento no afectara a la licitud del tratamiento basada en el consentimiento previo.
    </div>

    {MOCK_CONSENTS.map((consent) => (
      <div
        key={consent.id}
        className={`bg-gray-900 rounded-lg p-4 border ${
          consent.given ? 'border-green-500/30' : 'border-gray-700'
        }`}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="text-white font-semibold flex items-center gap-2">
              {consent.given ? '\u2705' : '\u274C'}
              {consent.purpose}
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Otorgado: {formatDate(consent.obtainedAt)}
            </p>
            {consent.expiresAt && (
              <p className="text-xs text-gray-500">
                Expira en {getDaysUntilExpiry(consent.expiresAt)} dias ({formatDate(consent.expiresAt)})
              </p>
            )}
            {consent.revokedAt && (
              <p className="text-xs text-yellow-400">
                Revocado: {formatDate(consent.revokedAt)}
              </p>
            )}
          </div>

          {consent.given && consent.canRevoke && canManageConsents() && (
            <button
              onClick={() => handleRevokeConsent(consent.id)}
              className="px-3 py-1 bg-red-900/30 border border-red-500/30 text-red-400 rounded text-sm hover:bg-red-900/50 transition"
            >
              Revocar
            </button>
          )}
        </div>

        <div className="text-xs text-gray-400 bg-gray-800 rounded p-2">
          ID: {consent.id}
        </div>
      </div>
    ))}
  </div>
);

export default ConsentTab;
