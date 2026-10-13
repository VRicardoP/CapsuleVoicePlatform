import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { WhatsAppProvider } from './context/WhatsAppContext';
import { ToastProvider } from './components/Toast';
import InboxPage from './pages/InboxPage';
import TemplatesPage from './pages/TemplatesPage';
import CampaignsPage from './pages/CampaignsPage';
import ContactsPage from './pages/ContactsPage';
import PipelinePage from './pages/PipelinePage';
import CrmAnalyticsPage from './pages/CrmAnalyticsPage';
import BroadcastPage from './pages/BroadcastPage';
import CatalogPage from './pages/CatalogPage';
import OrdersPage from './pages/OrdersPage';
import FlowBuilderPage from './pages/FlowBuilderPage';
import WebhooksPage from './pages/WebhooksPage';
import MacrosPage from './pages/MacrosPage';
import SlaPage from './pages/SlaPage';
import SurveysPage from './pages/SurveysPage';
import IntegrationsPage from './pages/IntegrationsPage';
import WidgetPage from './pages/WidgetPage';
import DashboardWAPage from './pages/DashboardWAPage';
import AuditPage from './pages/AuditPage';
import AdminBspPage from './pages/AdminBspPage';
import SegmentsPage from './pages/SegmentsPage';
import TagsPage from './pages/TagsPage';

const WhatsAppInbox: React.FC = () => (
  <ToastProvider>
    <WhatsAppProvider>
      <div className="h-full">
        <Routes>
          <Route index element={<InboxPage />} />
          <Route path="templates" element={<TemplatesPage />} />
          <Route path="campaigns" element={<CampaignsPage />} />
          <Route path="contacts" element={<ContactsPage />} />
          <Route path="pipeline" element={<PipelinePage />} />
          <Route path="analytics" element={<CrmAnalyticsPage />} />
          <Route path="broadcast" element={<BroadcastPage />} />
          <Route path="catalog" element={<CatalogPage />} />
          <Route path="orders" element={<OrdersPage />} />
          <Route path="flows" element={<FlowBuilderPage />} />
          <Route path="webhooks" element={<WebhooksPage />} />
          <Route path="macros" element={<MacrosPage />} />
          <Route path="sla" element={<SlaPage />} />
          <Route path="surveys" element={<SurveysPage />} />
          <Route path="integrations" element={<IntegrationsPage />} />
          <Route path="widget" element={<WidgetPage />} />
          <Route path="dashboard" element={<DashboardWAPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="segments" element={<SegmentsPage />} />
          <Route path="tags" element={<TagsPage />} />
          <Route path="admin" element={<AdminBspPage />} />
        </Routes>
      </div>
    </WhatsAppProvider>
  </ToastProvider>
);

export default WhatsAppInbox;
