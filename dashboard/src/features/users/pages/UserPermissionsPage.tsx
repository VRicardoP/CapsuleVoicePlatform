import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { usersAdminApi } from '../services/usersAdminApi';
import type { CatalogModule } from '../types';

const UserPermissionsPage: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();

  const [catalog, setCatalog] = useState<CatalogModule[]>([]);
  const [userRole, setUserRole] = useState<string>('');
  // All keys the role template grants (whether or not they're denied for this user).
  const [rolePermissions, setRolePermissions] = useState<Set<string>>(new Set());
  // Effective checked set: role perms not denied + additive overrides.
  const [selectedPerms, setSelectedPerms] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const initialSelected = useRef<Set<string>>(new Set());

  const fetchData = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const [catalogRes, permsRes] = await Promise.all([
        usersAdminApi.getPermissionCatalog(),
        usersAdminApi.getPermissions(userId),
      ]);
      setCatalog(catalogRes.modules);
      setUserRole(permsRes.role);

      // Derive: role template keys (all role perms, denied or not) and the
      // effective selected set (checked checkboxes).
      const roleKeys = new Set<string>();
      const effective = new Set<string>();
      for (const p of permsRes.permissions) {
        if (p.source === 'role_template' || p.source === 'user_deny') {
          roleKeys.add(p.key);
        }
        if (p.granted) {
          effective.add(p.key);
        }
      }
      setRolePermissions(roleKeys);
      setSelectedPerms(effective);
      initialSelected.current = new Set(effective);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error cargando datos');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  // Toggle any permission, including role-template ones (unchecking a role
  // permission becomes a deny override when saving).
  const togglePermission = useCallback((key: string) => {
    setSelectedPerms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleModule = useCallback((mod: CatalogModule) => {
    const permKeys = mod.permissions.map((p) => p.key);
    const allChecked = permKeys.every((k) => selectedPerms.has(k));
    setSelectedPerms((prev) => {
      const next = new Set(prev);
      for (const k of permKeys) {
        if (allChecked) next.delete(k);
        else next.add(k);
      }
      return next;
    });
  }, [selectedPerms]);

  const hasChanges = useMemo(() => {
    if (selectedPerms.size !== initialSelected.current.size) return true;
    for (const k of selectedPerms) {
      if (!initialSelected.current.has(k)) return true;
    }
    return false;
  }, [selectedPerms]);

  const handleSave = async () => {
    if (!userId) return;
    setSaving(true);
    setError(null);
    try {
      // Split the effective set into additive grants (not in the role) and
      // denies (role perms that are now unchecked).
      const grants: string[] = [];
      const denies: string[] = [];
      for (const k of selectedPerms) {
        if (!rolePermissions.has(k)) grants.push(k);
      }
      for (const k of rolePermissions) {
        if (!selectedPerms.has(k)) denies.push(k);
      }
      const result = await usersAdminApi.setPermissions(userId, grants, denies);
      setToast({ type: 'success', message: `Permisos actualizados: +${result.granted} -${result.revoked}` });
      initialSelected.current = new Set(selectedPerms);
    } catch (err) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : 'Error al guardar' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto mb-3"></div>
          <p className="text-gray-400 text-sm">Cargando permisos...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl">
      {/* Toast notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg border text-sm ${
          toast.type === 'success'
            ? 'bg-green-900/80 border-green-600/50 text-green-300'
            : 'bg-red-900/80 border-red-600/50 text-red-300'
        }`}>
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/users')}
          className="text-gray-400 hover:text-white transition">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">Permisos de usuario</h1>
          <p className="text-sm text-gray-400 mt-1">
            Rol: <span className="text-gray-300 font-medium">{userRole}</span>
            {' '} &middot; ID: <span className="text-gray-500 font-mono text-xs">{userId?.slice(0, 8)}...</span>
          </p>
        </div>
      </div>

      {error && <div className="mb-4 p-3 bg-red-900/30 border border-red-600/40 rounded text-red-400 text-sm">{error}</div>}

      <p className="text-xs text-gray-500 mb-4">
        Los permisos del rol base aparecen marcados. Puedes desmarcarlos para
        revocarlos solo para este usuario, o marcar permisos adicionales.
      </p>

      {/* Permission modules — only show modules contracted by this tenant */}
      <div className="space-y-4">
        {catalog.filter((mod) => mod.available).map((mod) => {
          const permKeys = mod.permissions.map((p) => p.key);
          const checkedCount = permKeys.filter((k) => selectedPerms.has(k)).length;
          const allChecked = checkedCount === permKeys.length;
          const isIndeterminate = checkedCount > 0 && !allChecked;

          return (
            <div key={mod.key} className="rounded-lg border border-gray-700 bg-gray-800/50">
              {/* Module header */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-700/50">
                <input
                  type="checkbox"
                  checked={allChecked}
                  ref={(el) => { if (el) el.indeterminate = isIndeterminate; }}
                  onChange={() => toggleModule(mod)}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                />
                <span className="text-sm font-semibold text-white">{mod.label}</span>
                <span className="ml-auto text-xs text-gray-500">{checkedCount}/{permKeys.length}</span>
              </div>
              {/* Permissions list */}
              <div className="px-4 py-2 space-y-1">
                {mod.permissions.map((perm) => {
                  const isFromRole = rolePermissions.has(perm.key);
                  const isChecked = selectedPerms.has(perm.key);
                  const isRevoked = isFromRole && !isChecked;
                  return (
                    <label key={perm.key}
                      className="flex items-center gap-3 py-1.5 px-2 rounded cursor-pointer hover:bg-gray-700/30 transition">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => togglePermission(perm.key)}
                        className="w-3.5 h-3.5 rounded border-gray-600 bg-gray-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                      />
                      <div className="flex-1 min-w-0">
                        <span className="text-sm text-gray-200">{perm.label}</span>
                        {perm.description && (
                          <span className="ml-2 text-xs text-gray-500">{perm.description}</span>
                        )}
                      </div>
                      {isFromRole && !isRevoked && (
                        <span className="text-[10px] text-gray-500 bg-gray-700/50 px-1.5 py-0.5 rounded">rol</span>
                      )}
                      {isRevoked && (
                        <span className="text-[10px] text-red-400 bg-red-900/30 border border-red-700/40 px-1.5 py-0.5 rounded">revocado</span>
                      )}
                    </label>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {catalog.length === 0 && !error && (
        <p className="text-gray-500 text-sm text-center py-8">No hay permisos en el catalogo.</p>
      )}

      {/* Save bar */}
      <div className="sticky bottom-0 bg-gray-900/95 border-t border-gray-700 mt-6 -mx-6 px-6 py-4 flex items-center justify-between">
        <button onClick={() => navigate('/users')} className="text-sm text-gray-400 hover:text-white transition">
          Volver a usuarios
        </button>
        <button onClick={handleSave} disabled={saving || !hasChanges}
          className="px-6 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition">
          {saving ? 'Guardando...' : 'Guardar permisos'}
        </button>
      </div>
    </div>
  );
};

export default UserPermissionsPage;
