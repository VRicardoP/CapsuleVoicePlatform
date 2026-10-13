import { useState, useEffect, useCallback, useRef } from 'react';
import type { WACampaign, WACatalogItem, WATemplate, WASegment } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import { useSmartPolling } from '../../../hooks/useSmartPolling';

export const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: 'Borrador', color: 'bg-gray-600' },
  scheduled: { label: 'Programada', color: 'bg-blue-600' },
  sending: { label: 'Enviando', color: 'bg-yellow-600' },
  paused: { label: 'Pausada', color: 'bg-orange-600' },
  completed: { label: 'Completada', color: 'bg-green-600' },
  cancelled: { label: 'Cancelada', color: 'bg-red-600' },
};

export type WizardStep = 'name' | 'template' | 'product' | 'audience' | 'schedule' | 'review';
export const STEPS: WizardStep[] = ['name', 'template', 'product', 'audience', 'schedule', 'review'];
export const STEP_LABELS: Record<WizardStep, string> = {
  name: 'Nombre', template: 'Plantilla', product: 'Producto', audience: 'Audiencia', schedule: 'Programar', review: 'Revisar',
};

const INITIAL_WIZARD_FORM = {
  name: '', template_id: '', ab_template_id: '', is_ab_test: false,
  catalog_item_id: '',
  audience_type: 'all' as 'all' | 'segment',
  segment_ids: [] as string[], schedule_type: 'now' as 'now' | 'later', scheduled_at: '',
};

export function useCampaigns() {
  const { toast } = useToast();
  const [campaigns, setCampaigns] = useState<WACampaign[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const limit = 15;

  // Wizard
  const [showWizard, setShowWizard] = useState(false);
  const [step, setStep] = useState<WizardStep>('name');
  const [wizardForm, setWizardForm] = useState(INITIAL_WIZARD_FORM);
  const [templates, setTemplates] = useState<WATemplate[]>([]);
  const [segments, setSegments] = useState<WASegment[]>([]);
  const [catalogItems, setCatalogItems] = useState<WACatalogItem[]>([]);
  const [catalogSearch, setCatalogSearch] = useState('');

  // Relaunch
  const [relaunchId, setRelaunchId] = useState<string | null>(null);
  const [relaunching, setRelaunching] = useState(false);

  // SSE for real-time progress
  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const sse = new EventSource('/api/v1/whatsapp/events', { withCredentials: true });
    sseRef.current = sse;

    sse.addEventListener('campaign.progress', (event) => {
      const data = JSON.parse(event.data);
      setCampaigns(prev => prev.map(c =>
        c.id === data.campaignId
          ? { ...c, sent_count: data.sent, failed_count: data.failed, total_recipients: data.total }
          : c
      ));
    });

    sse.addEventListener('campaign.delivery', (event) => {
      const data = JSON.parse(event.data);
      setCampaigns(prev => prev.map(c =>
        c.id === data.campaignId
          ? { ...c, delivered_count: data.delivered, read_count: data.read }
          : c
      ));
    });

    sse.addEventListener('campaign.completed', (event) => {
      const data = JSON.parse(event.data);
      setCampaigns(prev => prev.map(c =>
        c.id === data.campaignId ? { ...c, status: 'completed' as const } : c
      ));
      toast('Campaña completada');
    });

    return () => { sse.close(); };
  }, [toast]);

  const fetchCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await whatsappApi.getCampaigns({ status: statusFilter || undefined, skip: page * limit, limit });
      setCampaigns(res.items);
      setTotal(res.total);
    } catch { toast('Error cargando campañas', 'error'); }
    setLoading(false);
  }, [statusFilter, page, toast]);

  useEffect(() => { fetchCampaigns(); }, [fetchCampaigns]);

  // Silent polling: 15s when sending campaigns exist, 30s otherwise
  const hasSending = campaigns.some(c => c.status === 'sending');
  const pollInterval = hasSending ? 15_000 : 30_000;

  const silentFetch = useCallback(async () => {
    try {
      const res = await whatsappApi.getCampaigns({ status: statusFilter || undefined, skip: page * limit, limit });
      setCampaigns(res.items);
      setTotal(res.total);
    } catch { /* silent */ }
  }, [statusFilter, page]);

  useSmartPolling(silentFetch, { interval: pollInterval });

  const loadWizardData = async () => {
    try {
      const [tRes, sRes, cRes] = await Promise.all([
        whatsappApi.getTemplates({ status: 'approved', limit: 100 }),
        whatsappApi.getSegments(),
        whatsappApi.getCatalogItems({ status: 'active', limit: 100 }),
      ]);
      setTemplates(tRes.items);
      setSegments(sRes.items);
      setCatalogItems(cRes.items);
    } catch { /* empty */ }
  };

  const openWizard = async () => {
    setWizardForm({ ...INITIAL_WIZARD_FORM, segment_ids: [], audience_type: 'all', schedule_type: 'now' });
    setStep('name');
    setCatalogSearch('');
    setShowWizard(true);
    await loadWizardData();
  };

  const handleWizardFinish = async () => {
    try {
      const audienceFilter = wizardForm.audience_type === 'segment'
        ? { segment_ids: wizardForm.segment_ids } : undefined;
      const campaign = await whatsappApi.createCampaign({
        name: wizardForm.name,
        template_id: wizardForm.template_id || undefined,
        catalog_item_id: wizardForm.catalog_item_id || undefined,
        audience_filter: audienceFilter,
        scheduled_at: wizardForm.schedule_type === 'later' ? wizardForm.scheduled_at : undefined,
        is_ab_test: wizardForm.is_ab_test,
      });
      if (wizardForm.schedule_type === 'now') {
        await whatsappApi.startCampaign(campaign.id);
        toast('Campaña creada e iniciada');
      } else {
        toast('Campaña programada');
      }
      setShowWizard(false);
      fetchCampaigns();
    } catch { toast('Error creando campaña', 'error'); }
  };

  const handleAction = async (id: string, action: 'start' | 'pause' | 'cancel') => {
    try {
      if (action === 'start') { await whatsappApi.startCampaign(id); toast('Campaña iniciada'); }
      else if (action === 'pause') { await whatsappApi.pauseCampaign(id); toast('Campaña pausada'); }
      else if (action === 'cancel') { await whatsappApi.cancelCampaign(id); toast('Campaña cancelada'); }
      fetchCampaigns();
    } catch { toast('Error en acción', 'error'); }
  };

  const handleDeleteConfirmed = async () => {
    if (!deleteId) return;
    try { await whatsappApi.deleteCampaign(deleteId); toast('Campaña eliminada'); fetchCampaigns(); }
    catch { toast('Error eliminando', 'error'); }
    setDeleteId(null);
  };

  const handleRelaunchConfirmed = async () => {
    if (!relaunchId) return;
    setRelaunching(true);
    try {
      await whatsappApi.relaunchCampaign(relaunchId);
      toast('Campaña relanzada');
      fetchCampaigns();
    } catch { toast('Error relanzando campaña', 'error'); }
    setRelaunching(false);
    setRelaunchId(null);
  };

  const handleDuplicate = async (campaign: WACampaign) => {
    const segIds = (campaign.audience_filter as { segment_ids?: string[] } | null)?.segment_ids || [];
    setWizardForm({
      name: `${campaign.name} (copia)`,
      template_id: campaign.template_id || '',
      ab_template_id: '',
      is_ab_test: false,
      catalog_item_id: campaign.catalog_item_id || '',
      audience_type: segIds.length > 0 ? 'segment' : 'all',
      segment_ids: segIds,
      schedule_type: 'now',
      scheduled_at: '',
    });
    setStep('name');
    setCatalogSearch('');
    setShowWizard(true);
    await loadWizardData();
  };

  // Computed values
  const stepIdx = STEPS.indexOf(step);
  const canNext = (() => {
    if (step === 'name') return wizardForm.name.length > 0;
    if (step === 'template') return true;
    if (step === 'product') return true;
    if (step === 'audience') return wizardForm.audience_type === 'all' || wizardForm.segment_ids.length > 0;
    if (step === 'schedule') return wizardForm.schedule_type === 'now' || wizardForm.scheduled_at.length > 0;
    return true;
  })();

  const selectedTemplate = templates.find(t => t.id === wizardForm.template_id);
  const selectedAbTemplate = templates.find(t => t.id === wizardForm.ab_template_id);
  const selectedCatalogItem = catalogItems.find(p => p.id === wizardForm.catalog_item_id);
  const filteredCatalogItems = catalogItems.filter(p =>
    !catalogSearch || p.name.toLowerCase().includes(catalogSearch.toLowerCase())
  );
  const totalPages = Math.ceil(total / limit);

  return {
    campaigns, total, loading, page, setPage, statusFilter, setStatusFilter,
    deleteId, setDeleteId, relaunchId, setRelaunchId, relaunching,
    showWizard, setShowWizard, step, setStep, wizardForm, setWizardForm,
    templates, segments, catalogItems, catalogSearch, setCatalogSearch,
    stepIdx, canNext, selectedTemplate, selectedAbTemplate, selectedCatalogItem,
    filteredCatalogItems, totalPages,
    openWizard, handleWizardFinish, handleAction,
    handleDeleteConfirmed, handleRelaunchConfirmed, handleDuplicate,
  };
}
