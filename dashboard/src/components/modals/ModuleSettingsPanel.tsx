import React from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { AVAILABLE_MODULES } from '../../config/modulesConfig';

interface ModuleSettingsPanelProps {
  onClose: () => void;
}

const ModuleSettingsPanel: React.FC<ModuleSettingsPanelProps> = ({ onClose }) => {
  const { visibleModules, toggleModule, setModules } = useDashboard();
  const categories = ['metrics', 'charts', 'tables', 'analytics', 'advanced', 'gdpr'] as const;

  const categoryNames: Record<string, string> = {
    metrics: '📊 Métricas',
    charts: '📈 Gráficos',
    tables: '📋 Tablas',
    analytics: '🔍 Analíticas',
    advanced: '⚡ Avanzado',
    gdpr: '🛡️ GDPR/RGPD'
  };

  const activateAll = () => {
    // Set all modules at once instead of toggling one by one
    const allModuleIds = AVAILABLE_MODULES.map(m => m.id);
    setModules(allModuleIds);
  };

  const deactivateAll = () => {
    // Clear all modules at once
    setModules([]);
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-white">⚙️ Configurar Módulos</h2>
            <p className="text-gray-400">Personaliza tu dashboard activando o desactivando módulos</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">×</button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {categories.map(category => {
            const modulesInCategory = AVAILABLE_MODULES.filter(m => m.category === category);
            if (modulesInCategory.length === 0) return null;

            return (
              <div key={category}>
                <h3 className="text-lg font-bold text-white mb-4">{categoryNames[category]}</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {modulesInCategory.map(module => {
                    const isVisible = visibleModules.includes(module.id);
                    return (
                      <div
                        key={module.id}
                        onClick={() => toggleModule(module.id)}
                        className={`p-4 rounded-lg border-2 cursor-pointer transition ${
                          isVisible
                            ? 'bg-blue-900/30 border-blue-500'
                            : 'bg-gray-900 border-gray-700 hover:border-gray-600'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-2xl">{module.icon}</span>
                            <h4 className="font-semibold text-white">{module.name}</h4>
                          </div>
                          <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                            isVisible ? 'bg-blue-600 border-blue-600' : 'border-gray-600'
                          }`}>
                            {isVisible && <span className="text-white text-xs">✓</span>}
                          </div>
                        </div>
                        <p className="text-sm text-gray-400">{module.description}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        <div className="p-6 border-t border-gray-700 flex justify-between">
          <div className="space-x-2">
            <button
              onClick={activateAll}
              className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
            >
              Activar Todos
            </button>
            <button
              onClick={deactivateAll}
              className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
            >
              Desactivar Todos
            </button>
          </div>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Guardar Cambios
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModuleSettingsPanel;