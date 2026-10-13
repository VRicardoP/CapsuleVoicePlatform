import React from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'default';
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

const VARIANT_COLORS = {
  danger: 'bg-red-600 hover:bg-red-500',
  warning: 'bg-amber-600 hover:bg-amber-500',
  default: 'bg-green-600 hover:bg-green-500',
};

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  variant = 'danger',
  loading = false,
  onConfirm,
  onCancel,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]" onClick={e => { if (e.target === e.currentTarget && !loading) onCancel(); }}>
      <div className="bg-gray-800 rounded-xl p-6 w-96 border border-gray-700">
        <h3 className="text-white font-bold mb-2">{title}</h3>
        <p className="text-sm text-gray-400 mb-4">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} disabled={loading} className="px-3 py-1.5 text-sm text-gray-400 hover:text-white disabled:opacity-50">
            {cancelLabel}
          </button>
          <button onClick={onConfirm} disabled={loading} className={`px-3 py-1.5 text-sm text-white rounded-lg disabled:opacity-50 ${VARIANT_COLORS[variant]}`}>
            {loading ? 'Procesando...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
