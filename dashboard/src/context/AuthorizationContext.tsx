import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { SECURITY_CONFIG } from '../services/api/config';
import { notifySessionExpired } from '../services/api/httpClient';

interface AuthorizationContextValue {
  role: string;
  features: Record<string, boolean>;
  permissions: Set<string>;
  hasFeature: (key: string) => boolean;
  hasPermission: (key: string) => boolean;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

const AuthorizationContext = createContext<AuthorizationContextValue | null>(null);

export const useAuthorization = () => {
  const ctx = useContext(AuthorizationContext);
  if (!ctx) throw new Error('useAuthorization must be within AuthorizationProvider');
  return ctx;
};

// hasPermission with hierarchy: "whatsapp" grants "whatsapp.inbox.view"
function checkPermission(permissions: Set<string>, key: string): boolean {
  if (permissions.has('*')) return true;
  const parts = key.split('.');
  for (let i = 1; i <= parts.length; i++) {
    if (permissions.has(parts.slice(0, i).join('.'))) return true;
  }
  return false;
}

export const AuthorizationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRole] = useState('user');
  const [features, setFeatures] = useState<Record<string, boolean>>({});
  const [permissions, setPermissions] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAuth = useCallback(async () => {
    try {
      setError(null);
      const res = await fetch(`${SECURITY_CONFIG.BASE_URL}/permissions/me`, { credentials: 'include' });
      if (res.status === 401) {
        // Session expired in the background — surface it via the global
        // handler so App.tsx routes back to login. Without this the
        // dashboard would render with an empty permissions set, looking
        // broken instead of asking the user to re-auth.
        notifySessionExpired();
        setLoading(false);
        return;
      }
      if (!res.ok) { setLoading(false); return; }
      const data = await res.json();
      setRole(data.user.role);
      setFeatures(data.features);
      setPermissions(new Set(data.permissions));
    } catch {
      setError('Error cargando permisos');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAuth(); }, [fetchAuth]);

  const hasFeature = useCallback((key: string) => {
    if (role === 'superadmin') return true;
    return features[key] === true;
  }, [role, features]);

  const hasPermission = useCallback((key: string) => checkPermission(permissions, key), [permissions]);

  return (
    <AuthorizationContext.Provider value={{ role, features, permissions, hasFeature, hasPermission, loading, error, refresh: fetchAuth }}>
      {children}
    </AuthorizationContext.Provider>
  );
};
