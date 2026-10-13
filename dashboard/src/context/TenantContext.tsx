import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { User, TenantFeatures } from '../types';
import { secureHttpClient } from '../services/api/httpClient';

interface TenantContextType {
  features: TenantFeatures;
  hasFeature: (key: keyof TenantFeatures) => boolean;
  loading: boolean;
}

const DEFAULT_FEATURES: TenantFeatures = {
  whatsapp: false,
  calendar: false,
  recordings: false,
  sentiment: false,
  robinson: false,
  outbound: false,
  newsletter: false,
  captacion: false,
  whatsapp_emoji_filters: false,
  avisos: false,
  trips: false,
};

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export const useTenant = () => {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within TenantProvider');
  }
  return context;
};

interface TenantProviderProps {
  children: ReactNode;
  user: User;
}

export const TenantProvider: React.FC<TenantProviderProps> = ({ children, user }) => {
  const [features, setFeatures] = useState<TenantFeatures>(DEFAULT_FEATURES);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFeatures = async () => {
      try {
        const response = await secureHttpClient<{ features: Partial<TenantFeatures> }>('/users/me/features');
        if (response.success && response.data?.features) {
          setFeatures({ ...DEFAULT_FEATURES, ...response.data.features });
        }
      } catch (error) {
        console.error('Failed to fetch tenant features:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchFeatures();
  }, [user.id]);

  const hasFeature = (key: keyof TenantFeatures): boolean => features[key];

  return (
    <TenantContext.Provider value={{ features, hasFeature, loading }}>
      {children}
    </TenantContext.Provider>
  );
};
