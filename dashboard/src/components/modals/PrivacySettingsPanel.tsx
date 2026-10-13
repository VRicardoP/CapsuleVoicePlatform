import React from 'react';
import { usePrivacySettings } from './usePrivacySettings';
import ConsentTab from './privacy/ConsentTab';
import RightsTab from './privacy/RightsTab';
import DataExportTab from './privacy/DataExportTab';

const FileDownIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
    <polyline points="14 2 14 8 20 8" />
    <path d="M12 18v-6" />
    <path d="M9 15l3 3 3-3" />
  </svg>
);

const TABS: { id: 'consents' | 'rights' | 'privacy'; icon: string; label: string }[] = [
  { id: 'consents', icon: '\ud83d\udccb', label: 'Mis Consentimientos' },
  { id: 'rights',   icon: '\u2696\ufe0f', label: 'Derechos ARCO' },
  { id: 'privacy',  icon: '\ud83d\udcc4', label: 'Informacion Legal' },
];

interface PrivacySettingsPanelProps {
  onClose: () => void;
}

const PrivacySettingsPanel: React.FC<PrivacySettingsPanelProps> = ({ onClose }) => {
  const {
    canManageConsents,
    activeTab,
    setActiveTab,
    selectedRequest,
    setSelectedRequest,
    requestReason,
    setRequestReason,
    requestDetails,
    setRequestDetails,
    showSuccess,
    isDownloadingPdf,
    handleDownloadComplianceReport,
    handlePrivacyRequest,
    handleRevokeConsent,
    resetRequestForm,
  } = usePrivacySettings();

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <span>{'\ud83d\udd12'}</span>
              <span>Configuracion de Privacidad</span>
            </h2>
            <p className="text-gray-400 text-sm mt-1">Gestiona tus datos personales y consentimientos (RGPD)</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">{'\u00d7'}</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-6 py-3 text-sm font-semibold transition ${
                activeTab === tab.id
                  ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-900/20'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'consents' && (
            <ConsentTab
              canManageConsents={canManageConsents}
              handleRevokeConsent={handleRevokeConsent}
            />
          )}

          {activeTab === 'rights' && (
            <RightsTab
              selectedRequest={selectedRequest}
              setSelectedRequest={setSelectedRequest}
              requestReason={requestReason}
              setRequestReason={setRequestReason}
              requestDetails={requestDetails}
              setRequestDetails={setRequestDetails}
              showSuccess={showSuccess}
              handlePrivacyRequest={handlePrivacyRequest}
              resetRequestForm={resetRequestForm}
            />
          )}

          {activeTab === 'privacy' && <DataExportTab />}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 bg-gray-900/50 flex justify-between items-center">
          <p className="text-xs text-gray-500">
            Cumplimiento RGPD (UE) 2016/679 y LOPDGDD 3/2018
          </p>
          <div className="flex gap-3">
            <button
              onClick={handleDownloadComplianceReport}
              disabled={isDownloadingPdf}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              title="Descargar informe de cumplimiento para AEPD"
            >
              {isDownloadingPdf ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Generando...</span>
                </>
              ) : (
                <>
                  <FileDownIcon className="w-4 h-4" />
                  <span>Informe AEPD</span>
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 transition"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PrivacySettingsPanel;
