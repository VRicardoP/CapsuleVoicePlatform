import React from 'react';

type AccentColor = 'blue' | 'green' | 'orange' | 'purple' | 'cyan' | 'red';

const accentClasses: Record<AccentColor, string> = {
  blue: 'border-blue-500',
  green: 'border-green-500',
  orange: 'border-orange-500',
  purple: 'border-purple-500',
  cyan: 'border-cyan-500',
  red: 'border-red-500',
};

const LoadingSpinner: React.FC<{ message?: string; accent?: AccentColor }> = ({ message = 'Cargando...', accent = 'blue' }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12" role="status" aria-busy="true">
      <div className={`animate-spin rounded-full h-12 w-12 border-b-2 ${accentClasses[accent]} mb-4`}></div>
      <p className="text-gray-400">{message}</p>
    </div>
  );
};

export default LoadingSpinner;
