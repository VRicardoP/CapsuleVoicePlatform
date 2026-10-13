import { useTemplateList } from './useTemplateList';
import { useTemplateForm } from './useTemplateForm';

/* ========================================================================== */
/*  Constants                                                                  */
/* ========================================================================== */

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-600', pending: 'bg-yellow-600', approved: 'bg-green-600',
  rejected: 'bg-red-600', paused: 'bg-orange-600', disabled: 'bg-gray-700',
};

const STATUS_LABELS: Record<string, string> = {
  '': 'Todas', draft: 'Borrador', pending: 'Pendiente',
  approved: 'Aprobada', rejected: 'Rechazada',
};

const CATEGORY_LABELS: Record<string, string> = {
  MARKETING: 'Marketing', UTILITY: 'Utilidad', AUTHENTICATION: 'Autenticacion',
};

const LANGUAGE_OPTIONS = [
  { value: 'es', label: 'Espanol' },
  { value: 'en', label: 'English' },
  { value: 'ca', label: 'Catala' },
  { value: 'pt_BR', label: 'Portugues' },
  { value: 'fr', label: 'Francais' },
  { value: 'de', label: 'Deutsch' },
  { value: 'it', label: 'Italiano' },
];

const HEADER_TYPES = [
  { value: '', label: 'Sin cabecera' },
  { value: 'TEXT', label: 'Texto' },
  { value: 'IMAGE', label: 'Imagen' },
];

/* ========================================================================== */
/*  Shared types                                                               */
/* ========================================================================== */

export interface TemplateButton {
  type: 'QUICK_REPLY' | 'URL' | 'PHONE_NUMBER';
  text: string;
  url?: string;
  phone_number?: string;
}

export interface FormState {
  name: string;
  body_text: string;
  category: string;
  language: string;
  footer: string;
  header_type: string;
  header_content: string;
}

/* ========================================================================== */
/*  Helpers                                                                    */
/* ========================================================================== */

/** Auto-format template name: lowercase, underscores, no special chars */
function formatTemplateName(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/\s+/g, '_')
    .replace(/[^a-z0-9_]/g, '')
    .slice(0, 512);
}

/** Count {{N}} variables in text */
function countVariables(text: string): number {
  return (text.match(/\{\{\d+\}\}/g) || []).length;
}

/* ========================================================================== */
/*  Combined hook                                                              */
/* ========================================================================== */

export function useTemplates() {
  const list = useTemplateList();
  const form = useTemplateForm(list.fetchTemplates);

  return {
    // List state & actions
    templates: list.templates,
    total: list.total,
    loading: list.loading,
    statusFilter: list.statusFilter,
    setStatusFilter: list.setStatusFilter,
    page: list.page,
    setPage: list.setPage,
    deleteId: list.deleteId,
    setDeleteId: list.setDeleteId,
    syncing: list.syncing,
    submitting: list.submitting,
    hasPending: list.hasPending,
    totalPages: list.totalPages,
    fetchTemplates: list.fetchTemplates,
    handleDeleteConfirmed: list.handleDeleteConfirmed,
    handleSubmit: list.handleSubmit,
    handleSync: list.handleSync,

    // Form state & actions
    showCreate: form.showCreate,
    setShowCreate: form.setShowCreate,
    form: form.form,
    setForm: form.setForm,
    buttons: form.buttons,
    setButtons: form.setButtons,
    bodyExamples: form.bodyExamples,
    setBodyExamples: form.setBodyExamples,
    editId: form.editId,
    saving: form.saving,
    bodyRef: form.bodyRef,
    variableNums: form.variableNums,
    handleCreate: form.handleCreate,
    closeModal: form.closeModal,
    handleEdit: form.handleEdit,
    openCreate: form.openCreate,
    addButton: form.addButton,
    updateButton: form.updateButton,
    removeButton: form.removeButton,
    insertVariable: form.insertVariable,
    previewBody: form.previewBody,

    // Constants & helpers
    STATUS_COLORS,
    STATUS_LABELS,
    CATEGORY_LABELS,
    LANGUAGE_OPTIONS,
    HEADER_TYPES,
    formatTemplateName,
    countVariables,
  };
}

export { STATUS_COLORS, STATUS_LABELS, CATEGORY_LABELS, LANGUAGE_OPTIONS, HEADER_TYPES };
