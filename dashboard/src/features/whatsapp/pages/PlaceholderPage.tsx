import React from 'react';

interface PlaceholderPageProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
}

const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, description, icon }) => (
  <div className="flex items-center justify-center h-full bg-gray-900">
    <div className="text-center max-w-md">
      {icon && <div className="mb-4 text-gray-600">{icon}</div>}
      <h2 className="text-xl font-bold text-white mb-2">{title}</h2>
      <p className="text-gray-400 text-sm mb-4">{description || 'Esta funcionalidad estará disponible próximamente.'}</p>
      <span className="inline-block px-3 py-1 bg-gray-800 border border-gray-700 rounded-full text-xs text-gray-500">
        Próximamente
      </span>
    </div>
  </div>
);

export default PlaceholderPage;
