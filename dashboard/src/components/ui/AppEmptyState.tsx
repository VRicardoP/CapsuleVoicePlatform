import React from 'react';

type AccentColor = 'blue' | 'green' | 'orange' | 'purple' | 'cyan';

interface AppEmptyStateProps {
  title: string;
  description?: string;
  icon?: string;
  accent?: AccentColor;
  action?: { label: string; onClick: () => void };
}

const accentBtn: Record<AccentColor, string> = {
  blue: 'bg-blue-600 hover:bg-blue-500',
  green: 'bg-green-600 hover:bg-green-500',
  orange: 'bg-orange-600 hover:bg-orange-500',
  purple: 'bg-purple-600 hover:bg-purple-500',
  cyan: 'bg-cyan-600 hover:bg-cyan-500',
};

const AppEmptyState: React.FC<AppEmptyStateProps> = ({ title, description, icon = '📭', accent = 'blue', action }) => (
  <div className="flex flex-col items-center justify-center p-12 text-center">
    <span className="text-4xl mb-4">{icon}</span>
    <h3 className="text-lg font-semibold text-white mb-1">{title}</h3>
    {description && <p className="text-sm text-gray-400 mb-4">{description}</p>}
    {action && (
      <button onClick={action.onClick} className={`px-4 py-2 text-white text-sm rounded-lg font-medium transition ${accentBtn[accent]}`}>
        {action.label}
      </button>
    )}
  </div>
);

export default AppEmptyState;
