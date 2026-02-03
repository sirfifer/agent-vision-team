import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { DashboardData, WebviewMessage } from '../types';
import { useVsCodeApi } from '../hooks/useVsCodeApi';

const defaultData: DashboardData = {
  connectionStatus: 'disconnected',
  serverPorts: { kg: 3101, quality: 3102, governance: 3103 },
  agents: [],
  visionStandards: [],
  architecturalElements: [],
  activities: [],
  tasks: { active: 0, total: 0 },
  sessionPhase: 'inactive',
};

interface DashboardContextValue {
  data: DashboardData;
  sendCommand: (type: WebviewMessage['type']) => void;
  agentFilter: string | null;
  setAgentFilter: (agent: string | null) => void;
  governanceFilter: string | null;
  setGovernanceFilter: (ref: string | null) => void;
  typeFilter: string | null;
  setTypeFilter: (type: string | null) => void;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

declare global {
  interface Window {
    __INITIAL_DATA__?: DashboardData;
  }
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const vscodeApi = useVsCodeApi();
  const [data, setData] = useState<DashboardData>(
    () => window.__INITIAL_DATA__ ?? defaultData
  );
  const [agentFilter, setAgentFilter] = useState<string | null>(null);
  const [governanceFilter, setGovernanceFilter] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      if (msg.type === 'update') {
        setData(msg.data);
      } else if (msg.type === 'activityAdd') {
        setData(prev => ({
          ...prev,
          activities: [msg.entry, ...prev.activities],
        }));
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  const sendCommand = useCallback((type: WebviewMessage['type']) => {
    vscodeApi.postMessage({ type });
  }, [vscodeApi]);

  return (
    <DashboardContext.Provider value={{
      data,
      sendCommand,
      agentFilter, setAgentFilter,
      governanceFilter, setGovernanceFilter,
      typeFilter, setTypeFilter,
    }}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard(): DashboardContextValue {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error('useDashboard must be used within DashboardProvider');
  return ctx;
}
