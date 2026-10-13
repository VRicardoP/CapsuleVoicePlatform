import React, { useState, useEffect } from 'react';


interface MarketplaceModule {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  available?: boolean;
}

interface MarketplaceModalProps {
  onClose: () => void;
  onRequestModules: (modules: MarketplaceModule[]) => void;
}

const MarketplaceModal: React.FC<MarketplaceModalProps> = ({ onClose, onRequestModules }) => {
  const [modules, setModules] = useState<MarketplaceModule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModules, setSelectedModules] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch('/api/v1/marketplace/modules', { credentials: 'include' })
      .then(res => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json(); })
      .then((data) => {
        setModules(data as MarketplaceModule[]);
        setLoading(false);
      })
      .catch(() => {
        setError('Error cargando modulos');
        setLoading(false);
      });
  }, []);

  const toggleModule = (moduleId: string) => {
    setSelectedModules(prev => {
      const newSet = new Set(prev);
      if (newSet.has(moduleId)) {
        newSet.delete(moduleId);
      } else {
        newSet.add(moduleId);
      }
      return newSet;
    });
  };

  const handleRequest = () => {
    const selected = modules.filter(m => selectedModules.has(m.id));
    onRequestModules(selected);
  };

  const selectedCount = selectedModules.size;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl max-w-3xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <span>🛍️</span>
              <span>Tienda de Integraciones</span>
            </h2>
            <p className="text-gray-400 text-sm mt-1">Amplía las capacidades de tu asistente virtual</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl transition"
            aria-label="Cerrar"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400" />
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-12">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {modules.map(module => {
                const isSelected = selectedModules.has(module.id);
                return (
                  <div
                    key={module.id}
                    role="checkbox"
                    aria-checked={isSelected}
                    aria-label={`Seleccionar modulo ${module.name}`}
                    tabIndex={0}
                    onClick={() => toggleModule(module.id)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleModule(module.id); } }}
                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-blue-900/30 border-blue-500'
                        : 'bg-gray-900 border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0">
                        <div
                          className={`w-6 h-6 rounded border-2 flex items-center justify-center transition ${
                            isSelected
                              ? 'bg-blue-600 border-blue-600'
                              : 'border-gray-600 hover:border-gray-500'
                          }`}
                        >
                          {isSelected && (
                            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-2xl">{module.icon}</span>
                          <h3 className="text-white font-semibold truncate">{module.name}</h3>
                        </div>
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span className="inline-block text-xs px-2 py-0.5 bg-gray-700 text-gray-300 rounded">
                            {module.category}
                          </span>
                          {module.available ? (
                            <span className="inline-block text-xs px-2 py-0.5 bg-green-600/30 text-green-400 border border-green-500/30 rounded">
                              Disponible
                            </span>
                          ) : (
                            <span className="inline-block text-xs px-2 py-0.5 bg-amber-600/30 text-amber-400 border border-amber-500/30 rounded">
                              Próximamente
                            </span>
                          )}
                        </div>
                        <p className="text-gray-400 text-sm leading-relaxed">{module.description}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 bg-gray-900/50">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-gray-400">
              {selectedCount === 0 ? (
                'Selecciona los módulos que te interesen'
              ) : (
                <span className="text-blue-400 font-medium">
                  {selectedCount} módulo{selectedCount !== 1 ? 's' : ''} seleccionado{selectedCount !== 1 ? 's' : ''}
                </span>
              )}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleRequest}
                disabled={selectedCount === 0}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                Solicitar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketplaceModal;
