import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import type { User } from '../../types';
import Sidebar from './Sidebar';
import PrivacySettingsPanel from '../modals/PrivacySettingsPanel';
import ContactModal from '../modals/ContactModal';
import MarketplaceModal from '../modals/MarketplaceModal';
import { useOnboarding } from '../../hooks/useOnboarding';
import { useSidebar } from '../../context/SidebarContext';

interface AppLayoutProps {
  user: User;
  onLogout: () => void;
}

interface ContactInitialData {
  subject: string;
  message: string;
}

const AppLayout: React.FC<AppLayoutProps> = ({ user, onLogout }) => {
  const [showPrivacy, setShowPrivacy] = useState(false);
  const [showContact, setShowContact] = useState(false);
  const [showMarketplace, setShowMarketplace] = useState(false);
  const [contactInitialData, setContactInitialData] = useState<ContactInitialData | null>(null);
  const { startTour } = useOnboarding();
  const { whatsAppSegments, activeSegmentId, setActiveSegmentId } = useSidebar();

  const handleMarketplaceRequest = (modules: { id: string; name: string; icon: string }[]) => {
    const modulesList = modules.map(m => `  - ${m.icon} ${m.name}`).join('\n');
    const message = `Estimado equipo de Capsule Corp,

Me gustaría solicitar información sobre los siguientes módulos del Marketplace de Integraciones:

${modulesList}

Por favor, pónganse en contacto conmigo para recibir más detalles sobre precios, implementación y plazos.

Quedo a la espera de su respuesta.

Un saludo.`;

    setContactInitialData({
      subject: 'Solicitud de módulos',
      message,
    });
    setShowMarketplace(false);
    setShowContact(true);
  };

  const handleCloseContact = () => {
    setShowContact(false);
    setContactInitialData(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900">
      <Sidebar
        user={user}
        onLogout={onLogout}
        onOpenPrivacy={() => setShowPrivacy(true)}
        onOpenContact={() => setShowContact(true)}
        onOpenMarketplace={() => setShowMarketplace(true)}
        onStartTour={startTour}
        whatsAppSegments={whatsAppSegments}
        activeSegmentId={activeSegmentId}
        onSegmentClick={setActiveSegmentId}
      />

      <main className="ml-64 h-screen overflow-auto">
        <Outlet />
      </main>

      {showPrivacy && <PrivacySettingsPanel onClose={() => setShowPrivacy(false)} />}
      {showContact && (
        <ContactModal
          onClose={handleCloseContact}
          initialSubject={contactInitialData?.subject}
          initialMessage={contactInitialData?.message}
        />
      )}
      {showMarketplace && (
        <MarketplaceModal
          onClose={() => setShowMarketplace(false)}
          onRequestModules={handleMarketplaceRequest}
        />
      )}
    </div>
  );
};

export default AppLayout;
