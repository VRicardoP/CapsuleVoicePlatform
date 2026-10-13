// src/context/DashboardContext.tsx
import React, { createContext, useContext, useState, useMemo, type ReactNode } from 'react';
import type { User, DashboardContextType } from '../types';
import { apiService } from '../services/api';
import { AVAILABLE_MODULES } from '../config/modulesConfig';

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export const useDashboard = () => {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboard must be used within DashboardProvider');
  }
  return context;
};

interface DashboardProviderProps {
  children: ReactNode;
  user: User;
}

/**
 * Get initial visible modules from saved preferences.
 * If the user has saved preferences, honor them exactly.
 * Only use defaults when there are no saved preferences at all.
 */
const getInitialVisibleModules = (savedModules: string[] | undefined): string[] => {
  if (!savedModules || savedModules.length === 0) {
    // No saved preferences - use all default visible modules
    return AVAILABLE_MODULES
      .filter(m => m.defaultVisible)
      .map(m => m.id);
  }

  // User has saved preferences - use exactly what they saved.
  // Filter out IDs for modules that no longer exist (removed from codebase).
  const availableIds = new Set(AVAILABLE_MODULES.map(m => m.id));
  return savedModules.filter(id => availableIds.has(id));
};

export const DashboardProvider: React.FC<DashboardProviderProps> = ({ children, user }) => {
  const [visibleModules, setVisibleModules] = useState<string[]>(
    getInitialVisibleModules(user.preferences?.visibleModules)
  );
  const savePreferences = (modules: string[]) => {
    apiService.saveUserPreferences(user.id, { visibleModules: modules })
      .then(res => {
        if (!res.success) {
          console.error('Failed to save module preferences:', res.error);
        }
      })
      .catch(err => console.error('Failed to save module preferences:', err));
  };

  const toggleModule = (moduleId: string) => {
    setVisibleModules(prev => {
      const newModules = prev.includes(moduleId)
        ? prev.filter(id => id !== moduleId)
        : [...prev, moduleId];

      savePreferences(newModules);
      return newModules;
    });
  };

  // Set multiple modules at once (for activate/deactivate all)
  const setModules = (moduleIds: string[]) => {
    setVisibleModules(moduleIds);
    savePreferences(moduleIds);
  };

  const contextValue: DashboardContextType = useMemo(() => ({
    user,
    visibleModules,
    toggleModule,
    setModules,
  }), [user, visibleModules]);

  return (
    <DashboardContext.Provider value={contextValue}>
      {children}
    </DashboardContext.Provider>
  );
};