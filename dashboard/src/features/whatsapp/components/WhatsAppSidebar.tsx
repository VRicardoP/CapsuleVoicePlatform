import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import type { WASegment } from '../types';

interface WhatsAppSidebarProps {
  segments: WASegment[];
  activeSegmentId: string | null;
  onSegmentClick: (id: string | null) => void;
}

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
}

const InboxIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-2.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
  </svg>
);

const TemplateIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const CampaignIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
  </svg>
);

const ContactsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const AnalyticsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

const CatalogIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
  </svg>
);

const SlaIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const SurveyIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
  </svg>
);

const DashboardIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
  </svg>
);

const SegmentsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
  </svg>
);

const segmentIcons: Record<string, string> = {
  'inbox': '\u{1F4E5}',
  'check-circle': '\u2705',
  'clock': '\u{1F551}',
  'phone': '\u{1F4DE}',
  'star': '\u2B50',
  'x-circle': '\u274C',
  'message-circle': '\u{1F4AC}',
};

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors ${
    isActive
      ? 'bg-green-600/20 text-green-400'
      : 'text-gray-400 hover:bg-gray-700/50 hover:text-gray-200'
  }`;

const WhatsAppSidebar: React.FC<WhatsAppSidebarProps> = ({ segments, activeSegmentId, onSegmentClick }) => {
  const navigate = useNavigate();

  const handleSegmentClick = (id: string | null) => {
    onSegmentClick(id);
    navigate('/whatsapp');
  };
  const mainNav: NavItem[] = [
    { to: '/whatsapp', label: 'Inbox', icon: <InboxIcon /> },
    { to: '/whatsapp/templates', label: 'Plantillas', icon: <TemplateIcon /> },
    { to: '/whatsapp/campaigns', label: 'Campañas', icon: <CampaignIcon /> },
    { to: '/whatsapp/contacts', label: 'Contactos', icon: <ContactsIcon /> },
    { to: '/whatsapp/segments', label: 'Segmentos', icon: <SegmentsIcon /> },
  ];

  const crmNav: NavItem[] = [
    { to: '/whatsapp/analytics', label: 'Analytics', icon: <AnalyticsIcon /> },
  ];

  const commerceNav: NavItem[] = [
    { to: '/whatsapp/catalog', label: 'Catálogo', icon: <CatalogIcon /> },
  ];

  const automationNav: NavItem[] = [
    { to: '/whatsapp/sla', label: 'SLA', icon: <SlaIcon /> },
    { to: '/whatsapp/surveys', label: 'Encuestas', icon: <SurveyIcon /> },
  ];

  const analyticsNav: NavItem[] = [
    { to: '/whatsapp/dashboard', label: 'Dashboard', icon: <DashboardIcon /> },
  ];

  // Filter out "Todos" from segments (it's represented by clicking Inbox with no segment filter)
  const displaySegments = segments.filter(s => s.slug !== 'todos');

  return (
    <div className="w-52 flex-shrink-0 border-r border-gray-700 flex flex-col h-full overflow-y-auto"
         style={{ backgroundColor: '#131720' }}>
      {/* Header */}
      <div className="px-3 py-3 border-b border-gray-700">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <span className="w-5 h-5 bg-green-600 rounded flex items-center justify-center text-xs">W</span>
          WhatsApp
        </h2>
      </div>

      {/* Principal */}
      <div className="px-2 py-2">
        <p className="px-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Principal</p>
        {mainNav.map(item => (
          <NavLink key={item.to} to={item.to} end={item.to === '/whatsapp'} className={navLinkClass}>
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      {/* Segments */}
      <div className="px-2 py-2 border-t border-gray-700/50">
        <p className="px-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Segmentos</p>
        <button
          onClick={() => handleSegmentClick(null)}
          className={`w-full flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors ${
            !activeSegmentId ? 'bg-green-600/20 text-green-400' : 'text-gray-400 hover:bg-gray-700/50'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-gray-500" />
          <span>Todos</span>
          <span className="ml-auto text-[10px] text-gray-600">
            {segments.reduce((sum, s) => sum + s.contact_count, 0)}
          </span>
        </button>
        {displaySegments.map(seg => (
          <button
            key={seg.id}
            onClick={() => handleSegmentClick(seg.id)}
            className={`w-full flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors ${
              activeSegmentId === seg.id
                ? 'bg-green-600/20 text-green-400'
                : 'text-gray-400 hover:bg-gray-700/50'
            }`}
          >
            <span className="text-xs">{segmentIcons[seg.icon || ''] || '\u{1F3F7}'}</span>
            <span className="truncate">{seg.name}</span>
            {seg.contact_count > 0 && (
              <span className="ml-auto text-[10px] text-gray-600">{seg.contact_count}</span>
            )}
          </button>
        ))}
      </div>

      {/* CRM */}
      <div className="px-2 py-2 border-t border-gray-700/50">
        <p className="px-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">CRM</p>
        {crmNav.map(item => (
          <NavLink key={item.to} to={item.to} className={navLinkClass}>
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      {/* Commerce */}
      <div className="px-2 py-2 border-t border-gray-700/50">
        <p className="px-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Comercio</p>
        {commerceNav.map(item => (
          <NavLink key={item.to} to={item.to} className={navLinkClass}>
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      {/* Automation */}
      <div className="px-2 py-2 border-t border-gray-700/50">
        <p className="px-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Automatización</p>
        {automationNav.map(item => (
          <NavLink key={item.to} to={item.to} className={navLinkClass}>
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      {/* Analytics */}
      <div className="px-2 py-2 border-t border-gray-700/50">
        <p className="px-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Analítica</p>
        {analyticsNav.map(item => (
          <NavLink key={item.to} to={item.to} className={navLinkClass}>
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

    </div>
  );
};

export default WhatsAppSidebar;
