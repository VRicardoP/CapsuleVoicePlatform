import { useCallback, useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { useAuthorization } from '../../context/AuthorizationContext';
import { apiService } from '../../services/api';
import type { PrivacyRequest } from '../../types';

type TabId = 'consents' | 'rights' | 'privacy';

// Roles allowed to manage RGPD consents — the new permission system uses
// `client_admin` / `superadmin` as the admin-tier roles, and `admin` is
// kept for back-compat with any cached sessions on the legacy schema.
const CONSENT_MANAGER_ROLES = new Set(['admin', 'client_admin', 'superadmin']);

export function usePrivacySettings() {
  useDashboard();
  const { role } = useAuthorization();
  const canManageConsents = useCallback(
    (): boolean => CONSENT_MANAGER_ROLES.has(role),
    [role],
  );
  const [activeTab, setActiveTab] = useState<TabId>('consents');
  const [selectedRequest, setSelectedRequest] = useState<PrivacyRequest['type'] | null>(null);
  const [requestReason, setRequestReason] = useState('');
  const [requestDetails, setRequestDetails] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  const handleDownloadComplianceReport = async () => {
    setIsDownloadingPdf(true);
    try {
      const response = await apiService.downloadComplianceReportPdf(30);
      if (response.success && response.data) {
        const url = window.URL.createObjectURL(response.data);
        const a = document.createElement('a');
        a.href = url;
        a.download = `informe_cumplimiento_aepd_${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } else {
        console.error('Error downloading report:', response.error);
        alert(`Error al descargar el informe: ${response.error}`);
      }
    } catch (error) {
      console.error('Error downloading compliance report:', error);
      alert('Error al descargar el informe. Por favor, intentelo de nuevo.');
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const handlePrivacyRequest = async () => {
    if (!selectedRequest) return;

    try {
      let response;
      switch (selectedRequest) {
        case 'access':
          response = await apiService.exportUserData();
          break;
        case 'rectification':
          response = await apiService.requestRectification({
            field: requestDetails || 'general',
            new_value: '',
            reason: requestReason,
          });
          break;
        case 'erasure':
          response = await apiService.requestDataDeletion(requestReason);
          break;
        case 'restriction':
          response = await apiService.requestRestriction({
            reason: requestReason,
            scope: requestDetails,
          });
          break;
        case 'portability':
          response = await apiService.exportUserData();
          break;
        case 'objection':
          response = await apiService.requestObjection({
            processing_type: requestDetails || 'general',
            reason: requestReason,
          });
          break;
        default:
          console.error('Unknown request type:', selectedRequest);
          return;
      }

      if (response.success) {
        setShowSuccess(true);
        setTimeout(() => {
          setShowSuccess(false);
          setSelectedRequest(null);
          setRequestReason('');
          setRequestDetails('');
        }, 3000);
      } else {
        console.error('Error submitting request:', response.error);
        alert(`Error: ${response.error}`);
      }
    } catch (error) {
      console.error('Error submitting privacy request:', error);
      alert('Error al enviar la solicitud. Por favor, inténtelo de nuevo.');
    }
  };

  const handleRevokeConsent = (consentId: string) => {
    alert(`Consentimiento ${consentId} revocado correctamente`);
  };

  const resetRequestForm = () => {
    setSelectedRequest(null);
    setRequestReason('');
    setRequestDetails('');
  };

  return {
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
  };
}
