import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import type { DashboardData, WebviewMessage, ProjectConfig, SetupReadiness, DocumentInfo, IngestionResult, ResearchPrompt, ResearchBriefInfo, BootstrapScaleProfile, BootstrapActivity } from '../types';
import { useTransport } from '../hooks/useTransport';
import { DEMO_DATA } from '../data/demoData';

const defaultData: DashboardData = {
  connectionStatus: 'disconnected',
  serverPorts: { kg: 3101, quality: 3102, governance: 3103 },
  agents: [],
  visionStandards: [],
  architecturalElements: [],
  activities: [],
  tasks: { active: 0, total: 0 },
  sessionPhase: 'inactive',
  governedTasks: [],
  governanceStats: { totalDecisions: 0, approved: 0, blocked: 0, pending: 0, pendingReviews: 0, totalGovernedTasks: 0, needsHumanReview: 0 },
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
  // Document formatting
  lastFormatResult: FormatDocResult | null;
  // Research prompts
  showResearchPrompts: boolean;
  setShowResearchPrompts: (show: boolean) => void;
  researchPrompts: ResearchPrompt[];
  // Research briefs
  researchBriefs: ResearchBriefInfo[];
  researchBriefContent: { briefPath: string; content: string; error?: string } | null;
  // Tutorial
  showTutorial: boolean;
  setShowTutorial: (show: boolean) => void;
  // Bootstrap
  showBootstrap: boolean;
  setShowBootstrap: (show: boolean) => void;
  bootstrapScaleProfile: BootstrapScaleProfile | null;
  bootstrapRunning: boolean;
  bootstrapProgress: { phase: string; detail: string; percent?: number; activities?: BootstrapActivity[] } | null;
  bootstrapResult: { success: boolean; reportPath?: string; error?: string } | null;
  // Demo mode
  demoMode: boolean;
}

export interface FormatDocResult {
  requestId: string;
  success: boolean;
  formattedContent?: string;
  error?: string;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

declare global {
  interface Window {
    __INITIAL_DATA__?: DashboardData;
  }
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const vscodeApi = useTransport();
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
  const [lastFormatResult, setLastFormatResult] = useState<FormatDocResult | null>(null);

  // Research prompts state
  const [showResearchPrompts, setShowResearchPrompts] = useState(false);
  const [researchPrompts, setResearchPrompts] = useState<ResearchPrompt[]>([]);

  // Research briefs state
  const [researchBriefs, setResearchBriefs] = useState<ResearchBriefInfo[]>([]);
  const [researchBriefContent, setResearchBriefContent] = useState<{ briefPath: string; content: string; error?: string } | null>(null);

  // Tutorial state
  const [showTutorial, setShowTutorial] = useState(false);

  // Bootstrap state
  const [showBootstrap, setShowBootstrap] = useState(false);
  const [bootstrapScaleProfile, setBootstrapScaleProfile] = useState<BootstrapScaleProfile | null>(null);
  const [bootstrapRunning, setBootstrapRunning] = useState(false);
  const [bootstrapProgress, setBootstrapProgress] = useState<{ phase: string; detail: string; percent?: number; activities?: BootstrapActivity[] } | null>(null);
  const [bootstrapResult, setBootstrapResult] = useState<{ success: boolean; reportPath?: string; error?: string } | null>(null);

  // Demo mode state
  const [demoMode, setDemoMode] = useState(false);
  const savedDataRef = useRef<DashboardData | null>(null);
  const demoModeRef = useRef(false);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      switch (msg.type) {
        case 'toggleDemo':
          if (!demoModeRef.current) {
            // Entering demo mode: save current data, swap in demo
            setData(prev => {
              savedDataRef.current = prev;
              return DEMO_DATA;
            });
            demoModeRef.current = true;
            setDemoMode(true);
          } else {
            // Leaving demo mode: restore saved data
            demoModeRef.current = false;
            setDemoMode(false);
            if (savedDataRef.current) {
              setData(savedDataRef.current);
              savedDataRef.current = null;
            }
          }
          break;
        case 'update':
          // Ignore live updates while demo mode is active
          if (demoModeRef.current) break;
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
          if (demoModeRef.current) break;
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
        case 'governedTasks':
          setData(prev => ({ ...prev, governedTasks: msg.tasks }));
          break;
        case 'governanceStats':
          setData(prev => ({ ...prev, governanceStats: msg.stats }));
          break;
        case 'formatDocContentResult':
          setLastFormatResult({
            requestId: msg.requestId,
            success: msg.success,
            formattedContent: msg.formattedContent,
            error: msg.error,
          });
          break;
        case 'findingsUpdate':
          setData(prev => ({ ...prev, findings: msg.findings }));
          break;
        case 'findingDismissed':
          if (msg.success) {
            setData(prev => ({
              ...prev,
              findings: (prev.findings ?? []).map(f =>
                f.id === msg.findingId ? { ...f, status: 'dismissed' as const } : f
              ),
            }));
          }
          break;
        case 'researchBriefContent':
          setResearchBriefContent({
            briefPath: msg.briefPath,
            content: msg.content,
            error: msg.error,
          });
          break;
        case 'researchBriefsList':
          setResearchBriefs(msg.briefs);
          break;
        case 'showWizard':
          setShowWizard(true);
          break;
        case 'showTutorial':
          setShowTutorial(true);
          break;
        case 'bootstrapScaleResult':
          setBootstrapScaleProfile(msg.profile);
          break;
        case 'bootstrapStarted':
          setBootstrapRunning(true);
          setBootstrapResult(null);
          setBootstrapProgress({ phase: 'Starting', detail: 'Initializing bootstrap agent...' });
          break;
        case 'bootstrapProgress':
          setBootstrapProgress({ phase: msg.phase, detail: msg.detail, percent: msg.percent, activities: msg.activities });
          break;
        case 'bootstrapComplete':
          setBootstrapRunning(false);
          setBootstrapResult({ success: msg.success, reportPath: msg.reportPath, error: msg.error });
          setBootstrapProgress(null);
          break;
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  // Wizard is triggered explicitly via:
  // - VS Code walkthrough "Run the Setup Wizard" link
  // - Sidebar toolbar lightbulb button (collab.openSetupWizard command)
  // - SetupBanner "Run Setup Wizard" button
  // - SessionBar lightning bolt icon
  // - Extension sends 'showWizard' message

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
      lastFormatResult,
      showResearchPrompts, setShowResearchPrompts,
      researchPrompts,
      researchBriefs,
      researchBriefContent,
      showTutorial, setShowTutorial,
      showBootstrap, setShowBootstrap,
      bootstrapScaleProfile,
      bootstrapRunning,
      bootstrapProgress,
      bootstrapResult,
      demoMode,
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
