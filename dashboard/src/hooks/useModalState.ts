import { useState, useCallback } from 'react';

interface UseModalStateResult {
  /** ID of item being edited (null = closed) */
  editId: string | null;
  /** ID of item pending delete confirmation (null = closed) */
  deleteId: string | null;
  /** Whether the create/edit modal is open */
  showModal: boolean;
  /** Open modal for creating a new item */
  openCreate: () => void;
  /** Open modal for editing an existing item */
  openEdit: (id: string) => void;
  /** Close the create/edit modal */
  closeModal: () => void;
  /** Open delete confirmation for an item */
  confirmDelete: (id: string) => void;
  /** Close delete confirmation */
  cancelDelete: () => void;
}

/**
 * Shared hook for modal + delete confirmation state.
 *
 * Replaces the repeated pattern of:
 *   const [showModal, setShowModal] = useState(false);
 *   const [editId, setEditId] = useState<string | null>(null);
 *   const [deleteId, setDeleteId] = useState<string | null>(null);
 *
 * @example
 * const { showModal, editId, deleteId, openCreate, openEdit, closeModal, confirmDelete, cancelDelete } = useModalState();
 */
export function useModalState(): UseModalStateResult {
  const [editId, setEditId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const openCreate = useCallback(() => {
    setEditId(null);
    setShowModal(true);
  }, []);

  const openEdit = useCallback((id: string) => {
    setEditId(id);
    setShowModal(true);
  }, []);

  const closeModal = useCallback(() => {
    setEditId(null);
    setShowModal(false);
  }, []);

  const confirmDelete = useCallback((id: string) => {
    setDeleteId(id);
  }, []);

  const cancelDelete = useCallback(() => {
    setDeleteId(null);
  }, []);

  return {
    editId,
    deleteId,
    showModal,
    openCreate,
    openEdit,
    closeModal,
    confirmDelete,
    cancelDelete,
  };
}
