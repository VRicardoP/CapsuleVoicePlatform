import React, { useState, useEffect, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import type { User } from './types';
import LoginScreen from './components/auth/LoginScreen';
import AppLayout from './components/layout/AppLayout';
import { apiService } from './services/api';
import { setSessionExpiredHandler } from './services/api/httpClient';
import { TenantProvider, useTenant } from './context/TenantContext';
import { AuthorizationProvider, useAuthorization } from './context/AuthorizationContext';
import { DashboardProvider } from './context/DashboardContext';
import { DataProvider } from './context/DataContext';
import { SidebarProvider } from './context/SidebarContext';
import PermissionGate from './components/auth/PermissionGate';
import { firstAccessibleRoute } from './config/navigationConfig';

const DashboardView = lazy(() => import('./components/layout/DashboardView'));
const WhatsAppInbox = lazy(() => import('./features/whatsapp/WhatsAppInbox'));
const UsersModule = lazy(() => import('./features/users/UsersModule'));

const LoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
      <p className="text-gray-400">Cargando...</p>
    </div>
  </div>
);

const FeatureGate: React.FC<{ feature: keyof import('./types').TenantFeatures; children: React.ReactNode }> = ({ feature, children }) => {
  const { hasFeature, loading } = useTenant();
  if (loading) return <LoadingFallback />;
  if (!hasFeature(feature)) return <AccessDeniedRedirect />;
  return <>{children}</>;
};

/**
 * Redirect the user to the best route they actually have access to.
 * Used as the fallback for FeatureGate/PermissionGate and as the main
 * dashboard gate — if a user has no `dashboard` permission we send them
 * to their first accessible module instead of showing a blank page.
 */
const AccessDeniedRedirect: React.FC = () => {
  const { hasPermission, loading: permsLoading } = useAuthorization();
  const { hasFeature, loading: tenantLoading } = useTenant();
  if (permsLoading || tenantLoading) return <LoadingFallback />;
  const dest = firstAccessibleRoute(
    (k: string) => hasFeature(k as keyof import('./types').TenantFeatures),
    hasPermission,
  );
  if (dest === null) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
        <div className="max-w-md text-center">
          <div className="text-5xl mb-4">🔒</div>
          <h1 className="text-xl font-semibold text-white mb-2">Sin permisos asignados</h1>
          <p className="text-gray-400 text-sm">
            Tu administrador aún no te ha concedido acceso a ningún módulo.
            Contacta con él para que te asigne los permisos necesarios.
          </p>
        </div>
      </div>
    );
  }
  return <Navigate to={dest} replace />;
};

/**
 * Wrapper around the dashboard landing page: require the `dashboard`
 * permission and otherwise route to the first accessible destination.
 */
const DashboardGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { hasPermission, loading } = useAuthorization();
  if (loading) return <LoadingFallback />;
  if (!hasPermission('dashboard')) return <AccessDeniedRedirect />;
  return <>{children}</>;
};

const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Redirect to login on session expiration
  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
    return () => setSessionExpiredHandler(null);
  }, []);

  // Check for existing session on mount
  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await apiService.getCurrentUser();
        if (response.success && response.data) {
          setUser(response.data);
        }
      } catch {
        // No valid session, user will need to login
      } finally {
        setLoading(false);
      }
    };

    checkSession();
  }, []);

  const handleLogin = (loggedUser: User) => {
    setUser(loggedUser);
  };

  const handleLogout = async () => {
    try {
      await apiService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
    setUser(null);
  };

  // Show loading spinner while checking session
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Verificando sesión...</p>
        </div>
      </div>
    );
  }

  // Public routes (no auth required) — must check before login gate
  if (!user) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <BrowserRouter>
      <SidebarProvider>
      <TenantProvider user={user}>
        <AuthorizationProvider>
        <DashboardProvider user={user}>
          <Routes>
            <Route element={<AppLayout user={user} onLogout={handleLogout} />}>
              <Route index element={
                <DashboardGate>
                  <DataProvider>
                    <Suspense fallback={<LoadingFallback />}>
                      <DashboardView />
                    </Suspense>
                  </DataProvider>
                </DashboardGate>
              } />
              <Route path="whatsapp/*" element={
                <FeatureGate feature="whatsapp">
                  <PermissionGate permission="whatsapp" fallback={<AccessDeniedRedirect />}>
                    <Suspense fallback={<LoadingFallback />}>
                      <WhatsAppInbox />
                    </Suspense>
                  </PermissionGate>
                </FeatureGate>
              } />
              <Route path="users/*" element={
                <PermissionGate permission="users.view" fallback={<AccessDeniedRedirect />}>
                  <Suspense fallback={<LoadingFallback />}>
                    <UsersModule />
                  </Suspense>
                </PermissionGate>
              } />
            </Route>
          </Routes>
        </DashboardProvider>
        </AuthorizationProvider>
      </TenantProvider>
      </SidebarProvider>
    </BrowserRouter>
  );
};

export default App;
