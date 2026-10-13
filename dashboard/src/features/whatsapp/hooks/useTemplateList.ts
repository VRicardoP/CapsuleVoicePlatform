import { useState, useEffect, useCallback, useMemo } from 'react';
import type { WATemplate } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import { useSmartPolling } from '../../../hooks/useSmartPolling';

export function useTemplateList() {
  const { toast } = useToast();

  // List state
  const [templates, setTemplates] = useState<WATemplate[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(0);
  const limit = 12;

  // Delete
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Sync
  const [syncing, setSyncing] = useState(false);

  // Submit
  const [submitting, setSubmitting] = useState<string | null>(null);

  /* ======================================================================== */
  /*  Fetching                                                                 */
  /* ======================================================================== */

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const res = await whatsappApi.getTemplates({ status: statusFilter || undefined, skip: page * limit, limit });
      setTemplates(res.items);
      setTotal(res.total);
    } catch { toast('Error cargando plantillas', 'error'); }
    setLoading(false);
  }, [statusFilter, page, toast]);

  // Initial fetch
  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);

  const hasPending = useMemo(() => templates.some(t => t.status === 'pending'), [templates]);

  // Silent 30s polling — syncs from Meta first if there are pending templates
  const silentRefresh = useCallback(async () => {
    try {
      if (hasPending) await whatsappApi.syncTemplates();
      const res = await whatsappApi.getTemplates({ status: statusFilter || undefined, skip: page * limit, limit });
      setTemplates(prev => {
        const changed = res.items.some((u, i) => prev[i]?.status !== u.status);
        if (changed) toast('Estado de plantillas actualizado', 'info');
        return changed ? res.items : prev;
      });
      setTotal(res.total);
    } catch { /* silent */ }
  }, [hasPending, statusFilter, page, toast]);

  useSmartPolling(silentRefresh, { interval: 30_000 });

  /* ======================================================================== */
  /*  Actions                                                                  */
  /* ======================================================================== */

  const handleDeleteConfirmed = async () => {
    if (!deleteId) return;
    try {
      await whatsappApi.deleteTemplate(deleteId);
      toast('Plantilla eliminada');
      fetchTemplates();
    } catch (err) { toast(err instanceof Error ? err.message : 'Error eliminando plantilla', 'error'); }
    setDeleteId(null);
  };

  const handleSubmit = async (id: string) => {
    setSubmitting(id);
    try {
      await whatsappApi.submitTemplate(id);
      toast('Plantilla enviada a Meta \u2014 se comprobara el estado automaticamente');
      fetchTemplates();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Error enviando a Meta', 'error');
    }
    setSubmitting(null);
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await whatsappApi.syncTemplates();
      toast(`Sincronizado: ${res.created} nuevas, ${res.updated} actualizadas (${res.synced} total)`);
      fetchTemplates();
    } catch (err) { toast(err instanceof Error ? err.message : 'Error sincronizando desde Meta', 'error'); }
    setSyncing(false);
  };

  const totalPages = Math.ceil(total / limit);

  return {
    templates, total, loading, statusFilter, setStatusFilter, page, setPage,
    deleteId, setDeleteId, syncing, submitting, hasPending, totalPages,
    fetchTemplates, handleDeleteConfirmed, handleSubmit, handleSync,
  };
}
