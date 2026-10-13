import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { WATemplate } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import type { TemplateButton, FormState } from './useTemplates';

const EMPTY_FORM: FormState = {
  name: '', body_text: '', category: 'MARKETING', language: 'es',
  footer: '', header_type: '', header_content: '',
};

/** Extract unique sorted variable numbers from body text */
function extractVariableNumbers(text: string): number[] {
  const matches = text.match(/\{\{(\d+)\}\}/g) || [];
  const nums = [...new Set(matches.map(m => parseInt(m.replace(/\{|\}/g, ''))))];
  return nums.sort((a, b) => a - b);
}

export function useTemplateForm(fetchTemplates: () => void) {
  const { toast } = useToast();

  // Modal state
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<FormState>({ ...EMPTY_FORM });
  const [buttons, setButtons] = useState<TemplateButton[]>([]);
  const [bodyExamples, setBodyExamples] = useState<string[]>([]);
  const [editId, setEditId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Body textarea ref for cursor-based variable insertion
  const bodyRef = useRef<HTMLTextAreaElement>(null);

  /* ======================================================================== */
  /*  Variable helpers                                                         */
  /* ======================================================================== */

  const variableNums = useMemo(() => extractVariableNumbers(form.body_text), [form.body_text]);

  // Keep bodyExamples array in sync with variable count
  useEffect(() => {
    setBodyExamples(prev => {
      const needed = variableNums.length;
      if (prev.length === needed) return prev;
      const next = [...prev];
      while (next.length < needed) next.push('');
      return next.slice(0, needed);
    });
  }, [variableNums.length]);

  const insertVariable = useCallback(() => {
    const nextNum = variableNums.length > 0 ? Math.max(...variableNums) + 1 : 1;
    const tag = `{{${nextNum}}}`;
    const el = bodyRef.current;
    if (el) {
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const text = form.body_text;
      const newText = text.slice(0, start) + tag + text.slice(end);
      setForm(f => ({ ...f, body_text: newText }));
      // Restore cursor after React re-render
      setTimeout(() => {
        el.selectionStart = el.selectionEnd = start + tag.length;
        el.focus();
      }, 0);
    } else {
      setForm(f => ({ ...f, body_text: f.body_text + tag }));
    }
  }, [variableNums, form.body_text]);

  /* ======================================================================== */
  /*  Form handlers                                                            */
  /* ======================================================================== */

  const handleCreate = async () => {
    if (!form.name || !form.body_text) {
      toast('Nombre y cuerpo del mensaje son obligatorios', 'error');
      return;
    }
    // Validate variable examples
    if (variableNums.length > 0 && bodyExamples.some(e => !e.trim())) {
      toast('Rellena todos los ejemplos de variables \u2014 Meta los requiere para aprobar la plantilla', 'error');
      return;
    }
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        body_text: form.body_text,
        category: form.category,
        language: form.language,
        footer: form.footer || undefined,
        header_type: form.header_type || undefined,
        header_content: form.header_content || undefined,
      };
      if (buttons.length > 0) {
        payload.buttons = { buttons };
      }
      if (variableNums.length > 0 && bodyExamples.length > 0) {
        payload.variables = { body_examples: bodyExamples };
      }
      if (editId) {
        await whatsappApi.updateTemplate(editId, payload as Parameters<typeof whatsappApi.updateTemplate>[1]);
        toast('Plantilla actualizada');
      } else {
        await whatsappApi.createTemplate(payload as Parameters<typeof whatsappApi.createTemplate>[0]);
        toast('Plantilla creada como borrador');
      }
      closeModal();
      fetchTemplates();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Error guardando plantilla', 'error');
    }
    setSaving(false);
  };

  const closeModal = useCallback(() => {
    setShowCreate(false);
    setEditId(null);
    setForm({ ...EMPTY_FORM });
    setButtons([]);
    setBodyExamples([]);
  }, []);

  const handleEdit = useCallback((t: WATemplate) => {
    setForm({
      name: t.name,
      body_text: t.body_text,
      category: t.category,
      language: t.language,
      footer: t.footer || '',
      header_type: t.header_type || '',
      header_content: t.header_content || '',
    });
    const existingButtons = (t.buttons as { buttons?: TemplateButton[] } | null)?.buttons || [];
    setButtons(existingButtons);
    const vars = t.variables as { body_examples?: string[] } | null;
    setBodyExamples(vars?.body_examples || []);
    setEditId(t.id);
    setShowCreate(true);
  }, []);

  const openCreate = useCallback(() => {
    setEditId(null);
    setForm({ ...EMPTY_FORM });
    setButtons([]);
    setBodyExamples([]);
    setShowCreate(true);
  }, []);

  /* ======================================================================== */
  /*  Button editor                                                            */
  /* ======================================================================== */

  const addButton = useCallback((type: TemplateButton['type']) => {
    if (buttons.length >= 3) return;
    setButtons(prev => [...prev, { type, text: '' }]);
  }, [buttons.length]);

  const updateButton = useCallback((index: number, field: keyof TemplateButton, value: string) => {
    setButtons(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  }, []);

  const removeButton = useCallback((index: number) => {
    setButtons(prev => prev.filter((_, i) => i !== index));
  }, []);

  /* ======================================================================== */
  /*  Preview with variable substitution                                       */
  /* ======================================================================== */

  const previewBody = useMemo(() => {
    let text = form.body_text || 'Escribe el cuerpo del mensaje...';
    variableNums.forEach((num, idx) => {
      const example = bodyExamples[idx];
      const replacement = example ? `*${example}*` : `[Variable ${num}]`;
      text = text.replace(`{{${num}}}`, replacement);
    });
    return text;
  }, [form.body_text, variableNums, bodyExamples]);

  return {
    showCreate, setShowCreate, form, setForm, buttons, setButtons,
    bodyExamples, setBodyExamples, editId, saving, bodyRef, variableNums,
    handleCreate, closeModal, handleEdit, openCreate,
    addButton, updateButton, removeButton, insertVariable,
    previewBody,
  };
}
