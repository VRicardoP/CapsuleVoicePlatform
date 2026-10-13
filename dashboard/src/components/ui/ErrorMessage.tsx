import React from 'react';

type AccentColor = 'blue' | 'green' | 'orange' | 'purple' | 'cyan' | 'red';

const accentBtn: Record<AccentColor, string> = {
  blue: 'bg-blue-600 hover:bg-blue-700',
  green: 'bg-green-600 hover:bg-green-700',
  orange: 'bg-orange-600 hover:bg-orange-700',
  purple: 'bg-purple-600 hover:bg-purple-700',
  cyan: 'bg-cyan-600 hover:bg-cyan-700',
  red: 'bg-red-600 hover:bg-red-700',
};

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
  accent?: AccentColor;
}

const ErrorMessage: React.FC<ErrorMessageProps> = ({ message, onRetry, accent = 'blue' }) => {
  return (
    <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-6 text-center">
      <div className="text-4xl mb-4">⚠️</div>
      <h3 className="text-xl font-bold text-red-400 mb-2">Error</h3>
      <p className="text-gray-300 mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className={`px-6 py-2 text-white rounded-lg transition ${accentBtn[accent]}`}
        >
          Reintentar
        </button>
      )}
    </div>
  );
};

export default ErrorMessage;
