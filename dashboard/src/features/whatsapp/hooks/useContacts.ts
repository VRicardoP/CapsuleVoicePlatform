import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { WAContactDetail, WASegment, WATag } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useWhatsApp } from '../context/WhatsAppContext';
import { useToast } from '../components/Toast';

const LIMIT = 25;

export function useContacts() {
  const { toast } = useToast();
  const { selectConversation, refetchConversations } = useWhatsApp();
  const navigate = useNavigate();
  const [contacts, setContacts] = useState<WAContactDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [createForm, setCreateForm] = useState({ phone_e164: '', display_name: '', email: '', notes: '' });
  const [editId, setEditId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmDelete, setConfirmDelete] = useState<{ type: 'single' | 'bulk'; id?: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Segments for bulk assign
  const [segments, setSegments] = useState<WASegment[]>([]);
  const [showBulkSegment, setShowBulkSegment] = useState(false);
  const [bulkSegmentIds, setBulkSegmentIds] = useState<string[]>([]);

  // Tags
  const [tags, setTags] = useState<WATag[]>([]);

  // CSV import state
  const fileRef = useRef<HTMLInputElement>(null);
  const [csvRows, setCsvRows] = useState<{ phone: string; name: string; email: string }[]>([]);
  const [csvParsed, setCsvParsed] = useState(false);
  const [importing, setImporting] = useState(false);

  const fetchContacts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await whatsappApi.getContacts({ search: search || undefined, skip: page * LIMIT, limit: LIMIT });
      setContacts(res.items);
      setTotal(res.total);
    } catch { toast('Error cargando contactos', 'error'); }
    setLoading(false);
  }, [search, page, toast]);

  useEffect(() => { fetchContacts(); }, [fetchContacts]);

  // Load segments and tags once
  useEffect(() => {
    whatsappApi.getSegments().then(res => setSegments(res.items)).catch(() => {});
    whatsappApi.getTags().then(res => setTags(res.items)).catch(() => {});
  }, []);

  const openCreate = () => {
    setEditId(null);
    setCreateForm({ phone_e164: '', display_name: '', email: '', notes: '' });
    setShowCreate(true);
  };

  const openEdit = (c: WAContactDetail) => {
    setEditId(c.id);
    setCreateForm({
      phone_e164: c.phone_e164,
      display_name: c.display_name || '',
      email: c.email || '',
      notes: c.notes || '',
    });
    setShowCreate(true);
  };

  const handleSave = async () => {
    try {
      if (editId) {
        await whatsappApi.updateContact(editId, {
          display_name: createForm.display_name || undefined,
          email: createForm.email || undefined,
          notes: createForm.notes || undefined,
        });
        toast('Contacto actualizado');
      } else {
        if (!createForm.phone_e164) return;
        await whatsappApi.createContact(createForm);
        toast('Contacto creado');
      }
      setShowCreate(false);
      setEditId(null);
      setCreateForm({ phone_e164: '', display_name: '', email: '', notes: '' });
      fetchContacts();
    } catch { toast('Error guardando contacto', 'error'); }
  };

  const handleDeleteConfirmed = async () => {
    if (!confirmDelete) return;
    setDeleting(true);
    try {
      if (confirmDelete.type === 'single' && confirmDelete.id) {
        await whatsappApi.deleteContact(confirmDelete.id);
        toast('Contacto eliminado');
      } else if (confirmDelete.type === 'bulk') {
        for (const id of selected) await whatsappApi.deleteContact(id);
        toast(`${selected.size} contactos eliminados`);
        setSelected(new Set());
      }
      fetchContacts();
      refetchConversations();
    } catch { toast('Error eliminando contacto', 'error'); }
    setDeleting(false);
    setConfirmDelete(null);
  };

  const handleBulkSegmentAssign = async () => {
    if (bulkSegmentIds.length === 0 || selected.size === 0) return;
    try {
      await whatsappApi.bulkAssignSegments(Array.from(selected), bulkSegmentIds);
      toast(`Segmentos asignados a ${selected.size} contactos`);
      setShowBulkSegment(false);
      setBulkSegmentIds([]);
      setSelected(new Set());
      fetchContacts();
    } catch { toast('Error asignando segmentos', 'error'); }
  };

  const handleExport = () => {
    window.open(whatsappApi.exportContactsCsvUrl(), '_blank');
  };

  const openChat = async (contactId: string) => {
    try {
      const conv = await whatsappApi.startConversation(contactId);
      await refetchConversations();
      selectConversation(conv.id);
      navigate('/whatsapp');
    } catch { toast('Error abriendo conversacion', 'error'); }
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const toggleAll = () => {
    setSelected(selected.size === contacts.length ? new Set() : new Set(contacts.map(c => c.id)));
  };

  // CSV parsing
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const lines = text.split('\n').filter(l => l.trim());
      if (lines.length < 2) { toast('El CSV debe tener al menos una fila de datos', 'warning'); return; }
      const header = lines[0].toLowerCase();
      const sep = header.includes('\t') ? '\t' : header.includes(';') ? ';' : ',';
      const cols = header.split(sep).map(c => c.trim().replace(/"/g, ''));
      const phoneIdx = cols.findIndex(c => ['phone', 'telefono', 'phone_e164', 'movil'].includes(c));
      const nameIdx = cols.findIndex(c => ['name', 'nombre', 'display_name'].includes(c));
      const emailIdx = cols.findIndex(c => ['email', 'correo', 'e-mail'].includes(c));
      if (phoneIdx === -1) { toast('No se encontro columna de telefono', 'error'); return; }
      const rows: { phone: string; name: string; email: string }[] = [];
      for (let i = 1; i < lines.length; i++) {
        const vals = lines[i].split(sep).map(v => v.trim().replace(/^"|"$/g, ''));
        const phone = vals[phoneIdx];
        if (!phone) continue;
        rows.push({
          phone: phone.startsWith('+') ? phone : `+${phone}`,
          name: nameIdx >= 0 ? vals[nameIdx] || '' : '',
          email: emailIdx >= 0 ? vals[emailIdx] || '' : '',
        });
      }
      setCsvRows(rows);
      setCsvParsed(true);
    };
    reader.readAsText(file);
  };

  const handleImport = async () => {
    setImporting(true);
    let imported = 0;
    let failed = 0;
    for (const row of csvRows) {
      try {
        await whatsappApi.createContact({
          phone_e164: row.phone,
          display_name: row.name || undefined,
          email: row.email || undefined,
        });
        imported++;
      } catch { failed++; }
    }
    toast(`Importados: ${imported}, fallidos: ${failed}`, imported > 0 ? 'success' : 'warning');
    setImporting(false);
    setShowImport(false);
    setCsvRows([]);
    setCsvParsed(false);
    fetchContacts();
  };

  // Per-contact segment picker
  const [segPickerContact, setSegPickerContact] = useState<string | null>(null);

  // Per-contact tag picker
  const [tagPickerContact, setTagPickerContact] = useState<string | null>(null);

  // Single-select: clicking another tag replaces the previous one;
  // clicking the active tag clears it.
  const toggleContactTag = async (contact: WAContactDetail, tagId: string) => {
    const currentIds = contact.tags.map(t => t.id);
    const newIds = currentIds.includes(tagId) ? [] : [tagId];
    try {
      await whatsappApi.updateContact(contact.id, { tag_ids: newIds });
      fetchContacts();
    } catch { toast('Error asignando etiqueta', 'error'); }
  };

  const createTagAndAssign = async (contact: WAContactDetail, name: string, color: string) => {
    try {
      const tag = await whatsappApi.createTag({ name, color });
      setTags(prev => [...prev, tag]);
      // Single-select: the new tag replaces any previous one
      await whatsappApi.updateContact(contact.id, { tag_ids: [tag.id] });
      fetchContacts();
    } catch { toast('Error creando etiqueta', 'error'); }
  };

  // Single-select segment: same behaviour as tags.
  const toggleContactSegment = async (contact: WAContactDetail, segId: string) => {
    const currentIds = contact.segments.map(s => s.id);
    const newIds = currentIds.includes(segId) ? [] : [segId];
    try {
      await whatsappApi.assignContactSegments(contact.id, newIds);
      fetchContacts();
    } catch { toast('Error asignando segmento', 'error'); }
  };

  const totalPages = Math.ceil(total / LIMIT);

  return {
    contacts,
    total,
    loading,
    search,
    setSearch,
    page,
    setPage,
    showCreate,
    setShowCreate,
    showImport,
    setShowImport,
    createForm,
    setCreateForm,
    editId,
    setEditId,
    selected,
    confirmDelete,
    setConfirmDelete,
    deleting,
    segments,
    showBulkSegment,
    setShowBulkSegment,
    bulkSegmentIds,
    setBulkSegmentIds,
    fileRef,
    csvRows,
    setCsvRows,
    csvParsed,
    setCsvParsed,
    importing,
    segPickerContact,
    setSegPickerContact,
    tags,
    tagPickerContact,
    setTagPickerContact,
    toggleContactTag,
    createTagAndAssign,
    totalPages,
    limit: LIMIT,
    openCreate,
    openEdit,
    handleSave,
    handleDeleteConfirmed,
    handleBulkSegmentAssign,
    handleExport,
    openChat,
    toggleSelect,
    toggleAll,
    handleFileChange,
    handleImport,
    toggleContactSegment,
  };
}
