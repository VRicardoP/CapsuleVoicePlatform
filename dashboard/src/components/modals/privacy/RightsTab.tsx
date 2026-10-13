import React from 'react';
import type { PrivacyRequest } from '../../../types';

/* ========================================================================== */
/*  Static data                                                                */
/* ========================================================================== */

const ARCO_RIGHTS: { type: PrivacyRequest['type']; icon: string; title: string; subtitle: string }[] = [
  { type: 'access',        icon: '\ud83d\udce5', title: 'Derecho de Acceso (Art. 15)',       subtitle: 'Solicitar una copia de todos mis datos personales' },
  { type: 'rectification', icon: '\u270f\ufe0f', title: 'Derecho de Rectificacion (Art. 16)', subtitle: 'Corregir datos personales inexactos o incompletos' },
  { type: 'erasure',       icon: '\ud83d\uddd1\ufe0f', title: 'Derecho al Olvido (Art. 17)',       subtitle: 'Solicitar la eliminacion completa de mis datos' },
  { type: 'restriction',   icon: '\u23f8\ufe0f', title: 'Derecho de Limitacion (Art. 18)',   subtitle: 'Limitar el tratamiento de mis datos personales' },
  { type: 'portability',   icon: '\ud83d\udce4', title: 'Derecho de Portabilidad (Art. 20)', subtitle: 'Recibir mis datos en formato estructurado y legible' },
  { type: 'objection',     icon: '\ud83d\udeab', title: 'Derecho de Oposicion (Art. 21)',    subtitle: 'Oponerme al tratamiento de mis datos personales' },
];

/* ========================================================================== */
/*  Component                                                                  */
/* ========================================================================== */

interface RightsTabProps {
  selectedRequest: PrivacyRequest['type'] | null;
  setSelectedRequest: (type: PrivacyRequest['type']) => void;
  requestReason: string;
  setRequestReason: (value: string) => void;
  requestDetails: string;
  setRequestDetails: (value: string) => void;
  showSuccess: boolean;
  handlePrivacyRequest: () => void;
  resetRequestForm: () => void;
}

const RightsTab: React.FC<RightsTabProps> = ({
  selectedRequest,
  setSelectedRequest,
  requestReason,
  setRequestReason,
  requestDetails,
  setRequestDetails,
  showSuccess,
  handlePrivacyRequest,
  resetRequestForm,
}) => (
  <div className="space-y-4">
    <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4 text-sm text-green-300">
      <strong>Derechos ARCO (Art. 15-21 RGPD):</strong> Tienes derecho a acceder, rectificar, suprimir,
      limitar el tratamiento, portabilidad y oposicion al tratamiento de tus datos personales.
    </div>

    {showSuccess && (
      <div className="bg-green-900/30 border border-green-500/40 rounded-lg p-4 text-green-300 flex items-center gap-3">
        <span className="text-2xl">{'\u2713'}</span>
        <div>
          <p className="font-semibold">Solicitud enviada correctamente</p>
          <p className="text-xs text-green-400">Procesaremos tu solicitud en un plazo maximo de 30 dias</p>
        </div>
      </div>
    )}

    <div className="space-y-3">
      <h3 className="text-white font-semibold mb-3">Selecciona el tipo de solicitud:</h3>

      {ARCO_RIGHTS.map(right => (
        <button
          key={right.type}
          onClick={() => setSelectedRequest(right.type)}
          className={`w-full text-left p-4 rounded-lg border transition ${
            selectedRequest === right.type
              ? 'bg-blue-900/30 border-blue-500/50'
              : 'bg-gray-900 border-gray-700 hover:border-gray-600'
          }`}
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">{right.icon}</span>
            <div>
              <p className="text-white font-semibold">{right.title}</p>
              <p className="text-xs text-gray-400">{right.subtitle}</p>
            </div>
          </div>
        </button>
      ))}
    </div>

    {selectedRequest && (
      <div className="mt-6 p-4 bg-gray-900 rounded-lg border border-gray-700">
        <h4 className="text-white font-semibold mb-3">Detalles de la solicitud</h4>

        <div className="space-y-3">
          <div>
            <label className="text-sm text-gray-400 block mb-1">Motivo de la solicitud</label>
            <input
              type="text"
              value={requestReason}
              onChange={(e) => setRequestReason(e.target.value)}
              placeholder="Breve descripcion del motivo"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 block mb-1">Informacion adicional (opcional)</label>
            <textarea
              value={requestDetails}
              onChange={(e) => setRequestDetails(e.target.value)}
              placeholder="Proporciona detalles adicionales si es necesario"
              rows={3}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm focus:border-blue-500 focus:outline-none resize-none"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={handlePrivacyRequest}
              disabled={!requestReason}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Enviar Solicitud
            </button>
            <button
              onClick={resetRequestForm}
              className="px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 transition"
            >
              Cancelar
            </button>
          </div>

          <p className="text-xs text-gray-500">
            Procesaremos tu solicitud en un plazo maximo de 30 dias segun el Art. 12.3 RGPD.
          </p>
        </div>
      </div>
    )}
  </div>
);

export default RightsTab;
