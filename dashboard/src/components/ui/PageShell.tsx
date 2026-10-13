import React from 'react';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';

type AccentColor = 'blue' | 'green' | 'orange' | 'purple' | 'cyan' | 'red';

interface PageShellProps {
  title: string;
  subtitle?: string;
  accent?: AccentColor;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

const PageShell: React.FC<PageShellProps> = ({
  title, subtitle, accent = 'blue', loading, error, onRetry, actions, children
}) => {
  if (loading) return <div className="flex items-center justify-center h-full"><LoadingSpinner accent={accent} /></div>;
  if (error) return <div className="flex items-center justify-center h-full"><ErrorMessage message={error} onRetry={onRetry} accent={accent} /></div>;

  return (
    <div className="flex flex-col min-h-full p-6 gap-6 overflow-y-auto">
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white">{title}</h1>
          {subtitle && <p className="text-sm text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
};

export default PageShell;
