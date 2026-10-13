import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { usersAdminApi } from '../services/usersAdminApi';
import { useSmartPolling } from '../../../hooks/useSmartPolling';
import { useAuthorization } from '../../../context/AuthorizationContext';
import type { UserItem, CreateUserPayload } from '../types';

const ROLE_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  superadmin: { bg: 'bg-red-600/20', text: 'text-red-400', label: 'Superadmin' },
  client_admin: { bg: 'bg-blue-600/20', text: 'text-blue-400', label: 'Admin' },
  admin: { bg: 'bg-blue-600/20', text: 'text-blue-400', label: 'Admin' },
  user: { bg: 'bg-gray-600/20', text: 'text-gray-400', label: 'Usuario' },
};

function RoleBadge({ role }: { role: string }) {
  const cfg = ROLE_BADGE[role] ?? ROLE_BADGE.user;
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  try {
    return new Date(iso).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return '-'; }
}

/** Modal for creating a new user. */
function CreateUserModal({
  onClose,
  onCreated,
  callerRole,
}: {
  onClose: () => void;
  onCreated: () => void;
  callerRole: string;
}) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Backend allows superadmin and client_admin to create client_admin users
  // (the latter scoped to their own org). Mirror that here.
  const canCreateClientAdmin =
    callerRole === 'superadmin' || callerRole === 'client_admin' || callerRole === 'admin';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload: CreateUserPayload = { email, password, role };
      if (name.trim()) payload.name = name.trim();
      await usersAdminApi.createUser(payload);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear usuario');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6 border border-gray-700" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-white mb-4">Nuevo usuario</h2>
        {error && <div className="mb-3 p-2 bg-red-900/30 border border-red-600/40 rounded text-red-400 text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email *</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Nombre</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)}
              className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Contrasena *</label>
            <input type="password" required minLength={12} value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              placeholder="Minimo 12 caracteres" />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Rol *</label>
            <select value={role} onChange={(e) => setRole(e.target.value)}
              className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
              <option value="user">Usuario</option>
              {canCreateClientAdmin && <option value="client_admin">Admin</option>}
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition">
              Cancelar
            </button>
            <button type="submit" disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-500 disabled:opacity-50 transition">
              {saving ? 'Creando...' : 'Crear usuario'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const UsersPage: React.FC = () => {
  const navigate = useNavigate();
  const { role: callerRole } = useAuthorization();
  const [showCreate, setShowCreate] = useState(false);
  const [deactivating, setDeactivating] = useState<string | null>(null);

  const fetcher = useCallback(() => usersAdminApi.listUsers(), []);
  const { data, loading, error, refetch } = useSmartPolling(fetcher, { interval: 30_000 });

  const users: UserItem[] = data?.items ?? [];
  const total = data?.total ?? 0;

  const handleCreated = () => {
    setShowCreate(false);
    refetch();
  };

  const handleDeactivate = async (userId: string, userName: string | null) => {
    const label = userName || userId.slice(0, 8);
    if (!window.confirm(`Desactivar al usuario "${label}"? Esta accion no se puede deshacer.`)) return;
    setDeactivating(userId);
    try {
      await usersAdminApi.deactivateUser(userId);
      refetch();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Error al desactivar usuario');
    } finally {
      setDeactivating(null);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Usuarios</h1>
          <p className="text-sm text-gray-400 mt-1">{total} usuario{total !== 1 ? 's' : ''} registrado{total !== 1 ? 's' : ''}</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-500 transition">
          + Nuevo usuario
        </button>
      </div>

      {error && <div className="mb-4 p-3 bg-red-900/30 border border-red-600/40 rounded text-red-400 text-sm">{error}</div>}

      <div className="overflow-x-auto rounded-lg border border-gray-700">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Nombre</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Email</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Rol</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Ultimo acceso</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Estado</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="bg-gray-900 divide-y divide-gray-800">
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">Cargando...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No hay usuarios</td></tr>
            ) : users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-800/50 transition-colors">
                <td className="px-4 py-3 text-sm text-white">{u.name || '-'}</td>
                <td className="px-4 py-3 text-sm text-gray-300">{u.email || '-'}</td>
                <td className="px-4 py-3"><RoleBadge role={u.role} /></td>
                <td className="px-4 py-3 text-sm text-gray-400">{formatDate(u.last_login_at)}</td>
                <td className="px-4 py-3">
                  {u.is_active ? (
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-600/20 text-green-400">Activo</span>
                  ) : (
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-600/20 text-gray-500">Inactivo</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => navigate(`/users/${u.id}/permissions`)}
                    className="text-xs text-blue-400 hover:text-blue-300 transition">
                    Permisos
                  </button>
                  {u.is_active && (
                    <button onClick={() => handleDeactivate(u.id, u.name)}
                      disabled={deactivating === u.id}
                      className="text-xs text-red-400 hover:text-red-300 transition disabled:opacity-50">
                      {deactivating === u.id ? 'Desactivando...' : 'Desactivar'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
          callerRole={callerRole}
        />
      )}
    </div>
  );
};

export default UsersPage;
