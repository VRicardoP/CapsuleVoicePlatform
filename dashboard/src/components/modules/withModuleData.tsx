import React from 'react';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';

interface DataHookResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * HOC that wraps a dashboard module component with standard loading/error
 * handling.  Eliminates the repeated if-loading/if-error/if-!data guard
 * present in every module.
 *
 * Usage:
 *   const MyModule = withModuleData(useMyData, 'Cargando...', ({ data }) => (
 *     <div>{data.value}</div>
 *   ));
 */
export function withModuleData<T>(
  useData: () => DataHookResult<T>,
  loadingMessage: string,
  Component: React.FC<{ data: T }>,
): React.FC {
  const Wrapped: React.FC = () => {
    const { data, loading, error, refetch } = useData();

    if (loading) return <LoadingSpinner message={loadingMessage} />;
    if (error) return <ErrorMessage message={error} onRetry={refetch} />;
    if (!data) return null;

    return <Component data={data} />;
  };

  Wrapped.displayName = `withModuleData(${Component.displayName || Component.name || 'Component'})`;
  return React.memo(Wrapped);
}
