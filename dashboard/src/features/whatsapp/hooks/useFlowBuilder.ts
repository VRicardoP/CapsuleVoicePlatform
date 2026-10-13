import { useState, useEffect, useCallback } from 'react';
import type { WAFlow } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';

export interface FlowStep {
  type: string;
  params: Record<string, string | number>;
}

export function useFlowBuilder() {
  const { toast } = useToast();
  const [flows, setFlows] = useState<WAFlow[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', description: '', trigger_type: 'message_received' });
  const [triggerConfig, setTriggerConfig] = useState<Record<string, string>>({});
  const [steps, setSteps] = useState<FlowStep[]>([]);
  const [editingFlow, setEditingFlow] = useState<string | null>(null);

  const fetchFlows = useCallback(async () => {
    setLoading(true);
    try {
      const res = await whatsappApi.getFlows();
      setFlows(res.items);
    } catch { toast('Error cargando flows', 'error'); }
    setLoading(false);
  }, [toast]);

  useEffect(() => { fetchFlows(); }, [fetchFlows]);

  const openCreate = () => {
    setEditId(null);
    setForm({ name: '', description: '', trigger_type: 'message_received' });
    setTriggerConfig({});
    setSteps([]);
    setShowModal(true);
  };

  const openEdit = (f: WAFlow) => {
    setEditId(f.id);
    setForm({ name: f.name, description: f.description || '', trigger_type: f.trigger_type });
    setTriggerConfig((f.trigger_config || {}) as Record<string, string>);
    const flowSteps = f.steps ? (Array.isArray(f.steps) ? f.steps : f.steps.nodes || []) : [];
    setSteps(flowSteps as FlowStep[]);
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name) return;
    const data = {
      ...form,
      description: form.description || undefined,
      trigger_config: Object.keys(triggerConfig).length > 0 ? triggerConfig : undefined,
      steps: steps.length > 0 ? { nodes: steps } : { nodes: [] },
    };
    try {
      if (editId) {
        await whatsappApi.updateFlow(editId, data);
        toast('Flow actualizado');
      } else {
        await whatsappApi.createFlow(data);
        toast('Flow creado');
      }
      setShowModal(false);
      fetchFlows();
    } catch { toast('Error guardando flow', 'error'); }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await whatsappApi.deleteFlow(deleteId);
      toast('Flow eliminado');
      fetchFlows();
    } catch { toast('Error eliminando', 'error'); }
    setDeleteId(null);
  };

  const handleToggle = async (f: WAFlow) => {
    try {
      await whatsappApi.activateFlow(f.id);
      fetchFlows();
      toast(f.is_active ? 'Flow desactivado' : 'Flow activado');
    } catch { toast('Error', 'error'); }
  };

  const openStepEditor = (f: WAFlow) => {
    const flowSteps = f.steps ? (Array.isArray(f.steps) ? f.steps : f.steps.nodes || []) : [];
    setSteps(flowSteps as FlowStep[]);
    setEditingFlow(f.id);
  };

  const saveSteps = async () => {
    if (!editingFlow) return;
    try {
      await whatsappApi.updateFlow(editingFlow, { steps: { nodes: steps } });
      toast('Pasos guardados');
      fetchFlows();
    } catch { toast('Error guardando pasos', 'error'); }
    setEditingFlow(null);
  };

  const addStep = () => {
    setSteps([...steps, { type: 'send_message', params: {} }]);
  };

  const updateStep = (idx: number, step: FlowStep) => {
    const newSteps = [...steps];
    newSteps[idx] = step;
    setSteps(newSteps);
  };

  const removeStep = (idx: number) => {
    setSteps(steps.filter((_, i) => i !== idx));
  };

  const moveStep = (idx: number, direction: -1 | 1) => {
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= steps.length) return;
    const newSteps = [...steps];
    [newSteps[idx], newSteps[newIdx]] = [newSteps[newIdx], newSteps[idx]];
    setSteps(newSteps);
  };

  return {
    flows,
    loading,
    showModal,
    setShowModal,
    editId,
    deleteId,
    setDeleteId,
    form,
    setForm,
    triggerConfig,
    setTriggerConfig,
    steps,
    editingFlow,
    setEditingFlow,
    openCreate,
    openEdit,
    handleSave,
    handleDelete,
    handleToggle,
    openStepEditor,
    saveSteps,
    addStep,
    updateStep,
    removeStep,
    moveStep,
  };
}
