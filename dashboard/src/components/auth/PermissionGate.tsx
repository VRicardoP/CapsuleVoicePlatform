import React from 'react';
import { useAuthorization } from '../../context/AuthorizationContext';

interface PermissionGateProps {
  permission: string;
  feature?: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

const PermissionGate: React.FC<PermissionGateProps> = ({ permission, feature, children, fallback = null }) => {
  const { hasPermission, hasFeature, loading } = useAuthorization();
  if (loading) return null;
  if (feature && !hasFeature(feature)) return <>{fallback}</>;
  if (!hasPermission(permission)) return <>{fallback}</>;
  return <>{children}</>;
};

export default PermissionGate;
