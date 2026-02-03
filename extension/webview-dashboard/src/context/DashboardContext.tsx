import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { DashboardData, WebviewMessage, ProjectConfig, SetupReadiness, DocumentInfo, IngestionResult, ResearchPrompt } from '../types';
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
  sendMessage: (msg: WebviewMessage) => void;
  agentFilter: string | null;
  setAgentFilter: (agent: string | null) => void;
  governanceFilter: string | null;
  setGovernanceFilter: (ref: string | null) => void;
  typeFilter: string | null;
  setTypeFilter: (type: string | null) => void;
  // Wizard and settings state
  showWizard: boolean;
  setShowWizard: (show: boolean) => void;
  showSettings: boolean;
  setShowSettings: (show: boolean) => void;
  projectConfig: ProjectConfig | null;
  setupReadiness: SetupReadiness | null;
  visionDocs: DocumentInfo[];
  architectureDocs: DocumentInfo[];
  lastIngestionResult: IngestionResult | null;
  // Research prompts
  showResearchPrompts: boolean;
  setShowResearchPrompts: (show: boolean) => void;
  researchPrompts: ResearchPrompt[];
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

  // Wizard and settings state
  const [showWizard, setShowWizard] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [projectConfig, setProjectConfig] = useState<ProjectConfig | null>(null);
  const [setupReadiness, setSetupReadiness] = useState<SetupReadiness | null>(null);
  const [visionDocs, setVisionDocs] = useState<DocumentInfo[]>([]);
  const [architectureDocs, setArchitectureDocs] = useState<DocumentInfo[]>([]);
  const [lastIngestionResult, setLastIngestionResult] = useState<IngestionResult | null>(null);

  // Research prompts state
  const [showResearchPrompts, setShowResearchPrompts] = useState(false);
  const [researchPrompts, setResearchPrompts] = useState<ResearchPrompt[]>([]);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      switch (msg.type) {
        case 'update':
          setData(msg.data);
          // Extract setup readiness and config from update if present
          if (msg.data.setupReadiness) {
            setSetupReadiness(msg.data.setupReadiness);
          }
          if (msg.data.projectConfig) {
            setProjectConfig(msg.data.projectConfig);
          }
          if (msg.data.visionDocs) {
            setVisionDocs(msg.data.visionDocs);
          }
          if (msg.data.architectureDocs) {
            setArchitectureDocs(msg.data.architectureDocs);
          }
          if (msg.data.researchPrompts) {
            setResearchPrompts(msg.data.researchPrompts);
          }
          break;
        case 'activityAdd':
          setData(prev => ({
            ...prev,
            activities: [msg.entry, ...prev.activities],
          }));
          break;
        case 'setupReadiness':
          setSetupReadiness(msg.readiness);
          break;
        case 'projectConfig':
          setProjectConfig(msg.config);
          break;
        case 'visionDocs':
          setVisionDocs(msg.docs);
          break;
        case 'architectureDocs':
          setArchitectureDocs(msg.docs);
          break;
        case 'ingestionResult':
          setLastIngestionResult(msg.result);
          break;
        case 'documentCreated':
          if (msg.docType === 'vision') {
            setVisionDocs(prev => [...prev, msg.doc]);
          } else {
            setArchitectureDocs(prev => [...prev, msg.doc]);
          }
          break;
        case 'researchPrompts':
          setResearchPrompts(msg.prompts);
          break;
        case 'researchPromptUpdated':
          setResearchPrompts(prev => {
            const idx = prev.findIndex(p => p.id === msg.prompt.id);
            if (idx >= 0) {
              const updated = [...prev];
              updated[idx] = msg.prompt;
              return updated;
            }
            return [...prev, msg.prompt];
          });
          break;
        case 'researchPromptDeleted':
          setResearchPrompts(prev => prev.filter(p => p.id !== msg.id));
          break;
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  // Auto-show wizard when setup is incomplete
  useEffect(() => {
    if (setupReadiness && !setupReadiness.isComplete && !showWizard) {
      // Auto-show wizard if setup is incomplete
      // Only auto-show once on initial load
      const hasSeenWizard = sessionStorage.getItem('avt-wizard-dismissed');
      if (!hasSeenWizard) {
        setShowWizard(true);
      }
    }
  }, [setupReadiness, showWizard]);

  const sendCommand = useCallback((type: WebviewMessage['type']) => {
    vscodeApi.postMessage({ type });
  }, [vscodeApi]);

  const sendMessage = useCallback((msg: WebviewMessage) => {
    vscodeApi.postMessage(msg);
  }, [vscodeApi]);

  return (
    <DashboardContext.Provider value={{
      data,
      sendCommand,
      sendMessage,
      agentFilter, setAgentFilter,
      governanceFilter, setGovernanceFilter,
      typeFilter, setTypeFilter,
      showWizard, setShowWizard,
      showSettings, setShowSettings,
      projectConfig,
      setupReadiness,
      visionDocs,
      architectureDocs,
      lastIngestionResult,
      showResearchPrompts, setShowResearchPrompts,
      researchPrompts,
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
