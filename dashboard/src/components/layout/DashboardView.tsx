import React, { useState, useMemo } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { useAuthorization } from '../../context/AuthorizationContext';
import CallSelectionContext from '../../context/CallSelectionContext';
import { AVAILABLE_MODULES } from '../../config/modulesConfig';
import ModuleSettingsPanel from '../modals/ModuleSettingsPanel';
import CallDetailModal from '../modals/CallDetailModal';
import type { CallRecord } from '../../types';

const DashboardView: React.FC = () => {
  const [showSettings, setShowSettings] = useState(false);
  const [selectedCall, setSelectedCall] = useState<CallRecord | null>(null);
  const { visibleModules } = useDashboard();
  const { hasPermission } = useAuthorization();

  // Effective modules = saved preferences intersection permissions
  const effectiveModules = useMemo(() => {
    return visibleModules.filter(moduleId => {
      const module = AVAILABLE_MODULES.find(m => m.id === moduleId);
      if (!module) return false;
      if (!module.requiredPermission) return true;
      return hasPermission(module.requiredPermission);
    });
  }, [visibleModules, hasPermission]);

  const renderModule = (moduleId: string) => {
    const module = AVAILABLE_MODULES.find(m => m.id === moduleId);
    if (!module) return null;
    const Component = module.component;
    return (
      <div key={moduleId} id={`module-${moduleId}`}>
        <Component />
      </div>
    );
  };

  return (
    <CallSelectionContext.Provider value={{ setSelectedCall }}>
      <div className="p-8">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h2 className="text-3xl font-bold text-white mb-2">Panel de Control</h2>
            <p className="text-gray-400">Vista personalizada de tu asistente virtual</p>
          </div>
          <button
            id="module-settings-button"
            onClick={() => setShowSettings(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-lg hover:bg-gray-700 hover:text-white transition text-sm"
            title="Configurar módulos visibles"
          >
            <span>⚙️</span>
            <span>Configurar Módulos</span>
          </button>
        </div>

        {effectiveModules.length === 0 ? (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center">
            <div className="text-6xl mb-4">📊</div>
            <h3 className="text-2xl font-bold text-white mb-2">No hay módulos activos</h3>
            <p className="text-gray-400 mb-6">Activa algunos módulos para comenzar a ver tus estadísticas</p>
            <button
              onClick={() => setShowSettings(true)}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Configurar Módulos
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {effectiveModules.map(moduleId => renderModule(moduleId))}
          </div>
        )}

        {showSettings && <ModuleSettingsPanel onClose={() => setShowSettings(false)} />}
        {selectedCall && <CallDetailModal call={selectedCall} onClose={() => setSelectedCall(null)} />}
      </div>
    </CallSelectionContext.Provider>
  );
};

export default DashboardView;
