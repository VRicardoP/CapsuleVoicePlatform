import React, { createContext, useContext, useState, useCallback } from 'react';

export interface SidebarSegment {
  id: string;
  name: string;
  slug: string;
  icon?: string;
  contact_count: number;
}

interface SidebarState {
  whatsAppSegments: SidebarSegment[];
  activeSegmentId: string | null;
}

interface SidebarContextValue extends SidebarState {
  setWhatsAppSegments: (segments: SidebarSegment[]) => void;
  setActiveSegmentId: (id: string | null) => void;
}

const SidebarContext = createContext<SidebarContextValue | null>(null);

export const SidebarProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<SidebarState>({
    whatsAppSegments: [],
    activeSegmentId: null,
  });

  const setWhatsAppSegments = useCallback((segments: SidebarSegment[]) => {
    setState(prev => ({ ...prev, whatsAppSegments: segments }));
  }, []);

  const setActiveSegmentId = useCallback((id: string | null) => {
    setState(prev => ({ ...prev, activeSegmentId: id }));
  }, []);

  return (
    <SidebarContext.Provider value={{ ...state, setWhatsAppSegments, setActiveSegmentId }}>
      {children}
    </SidebarContext.Provider>
  );
};

export const useSidebar = () => {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error('useSidebar must be used within SidebarProvider');
  return ctx;
};
