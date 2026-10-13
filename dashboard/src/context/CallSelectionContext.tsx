import { createContext, useContext } from 'react';
import type { CallRecord } from '../types';

interface CallSelectionContextType {
  setSelectedCall: (call: CallRecord | null) => void;
}

const CallSelectionContext = createContext<CallSelectionContextType | undefined>(undefined);

export const useCallSelection = () => {
  const ctx = useContext(CallSelectionContext);
  if (!ctx) throw new Error('useCallSelection must be used within DashboardView');
  return ctx;
};

export default CallSelectionContext;
