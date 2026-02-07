import { useState } from 'react';
import { DashboardProvider, useDashboard } from './context/DashboardContext';
import { SessionBar } from './components/SessionBar';
import { SetupBanner } from './components/SetupBanner';
import { AgentCards } from './components/AgentCards';
import { QualityGatesPanel } from './components/QualityGatesPanel';
import { GovernancePanel } from './components/GovernancePanel';
import { ActivityFeed } from './components/ActivityFeed';
import { TaskBoard } from './components/TaskBoard';
import { DecisionExplorer } from './components/DecisionExplorer';
import { SetupWizard } from './components/wizard/SetupWizard';
import { SettingsPanel } from './components/SettingsPanel';
import { ResearchPromptsPanel } from './components/ResearchPromptsPanel';
import { WorkflowTutorial } from './components/tutorial/WorkflowTutorial';

type RightTab = 'tasks' | 'decisions' | 'activity';

function ConnectionBanner() {
  const { data, sendCommand } = useDashboard();

  if (data.connectionStatus === 'connected') return null;

  const isError = data.connectionStatus === 'error';

  return (
    <div className={`flex items-center gap-3 px-4 py-3 border-b ${
      isError
        ? 'bg-red-900/20 border-red-600/40 text-red-200'
        : 'bg-blue-900/20 border-blue-600/40 text-blue-200'
    }`}>
      <svg className={`w-5 h-5 flex-shrink-0 ${isError ? 'text-red-400' : 'text-blue-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        {isError ? (
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        ) : (
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        )}
      </svg>
      <span className="flex-1 text-sm">
        {isError
          ? 'Failed to connect to MCP servers. Governance, quality gates, and knowledge graph are unavailable.'
          : 'Not connected to MCP servers. Click Connect to activate governance, quality gates, and knowledge graph.'}
      </span>
      <button
        onClick={() => sendCommand('connect')}
        className={`px-3 py-1.5 rounded font-medium text-sm transition-colors ${
          isError
            ? 'bg-red-600 hover:bg-red-500 text-white'
            : 'bg-blue-600 hover:bg-blue-500 text-white'
        }`}
      >
        {isError ? 'Retry' : 'Connect'}
      </button>
    </div>
  );
}

function RightPanel({ className }: { className?: string }) {
  const [activeTab, setActiveTab] = useState<RightTab>('tasks');

  return (
    <div className={`flex flex-col ${className ?? ''}`}>
      {/* Tab bar */}
      <div className="flex border-b border-vscode-border shrink-0">
        <button
          onClick={() => setActiveTab('tasks')}
          className={`px-4 py-1.5 text-xs font-medium transition-colors ${
            activeTab === 'tasks'
              ? 'text-vscode-fg border-b-2 border-tier-quality'
              : 'text-vscode-muted hover:text-vscode-fg'
          }`}
        >
          Governed Tasks
        </button>
        <button
          onClick={() => setActiveTab('decisions')}
          className={`px-4 py-1.5 text-xs font-medium transition-colors ${
            activeTab === 'decisions'
              ? 'text-vscode-fg border-b-2 border-tier-quality'
              : 'text-vscode-muted hover:text-vscode-fg'
          }`}
        >
          Decisions
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`px-4 py-1.5 text-xs font-medium transition-colors ${
            activeTab === 'activity'
              ? 'text-vscode-fg border-b-2 border-tier-quality'
              : 'text-vscode-muted hover:text-vscode-fg'
          }`}
        >
          Activity
        </button>
      </div>
      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'tasks' && <TaskBoard />}
        {activeTab === 'decisions' && <DecisionExplorer />}
        {activeTab === 'activity' && <ActivityFeed />}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <DashboardProvider>
      <div className="h-screen flex flex-col bg-vscode-bg text-vscode-fg text-sm">
        <SessionBar />
        <SetupBanner />
        <ConnectionBanner />
        <AgentCards />
        <QualityGatesPanel />
        <div className="flex-1 flex min-h-0">
          <GovernancePanel className="w-2/5 overflow-y-auto" />
          <RightPanel className="w-3/5" />
        </div>
      </div>
      {/* Overlays */}
      <SetupWizard />
      <SettingsPanel />
      <ResearchPromptsPanel />
      <WorkflowTutorial />
    </DashboardProvider>
  );
}
