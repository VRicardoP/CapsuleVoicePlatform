import React from 'react';

const EmptyState: React.FC = () => (
  <div className="flex items-center justify-center h-full">
    <div className="text-center max-w-sm">
      <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-green-600 to-green-800 rounded-2xl flex items-center justify-center">
        <span className="text-3xl">💬</span>
      </div>
      <h3 className="text-lg font-bold text-white mb-2">Selecciona una conversación</h3>
      <p className="text-gray-500 text-sm">Elige una conversación de la lista para ver los mensajes o inicia una nueva.</p>
    </div>
  </div>
);

export default EmptyState;
