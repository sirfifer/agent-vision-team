import { useState } from 'react';
import { DashboardProvider } from './context/DashboardContext';
import { SessionBar } from './components/SessionBar';
import { SetupBanner } from './components/SetupBanner';
import { AgentCards } from './components/AgentCards';
import { GovernancePanel } from './components/GovernancePanel';
import { ActivityFeed } from './components/ActivityFeed';
import { TaskBoard } from './components/TaskBoard';
import { SetupWizard } from './components/wizard/SetupWizard';
import { SettingsPanel } from './components/SettingsPanel';
import { ResearchPromptsPanel } from './components/ResearchPromptsPanel';

type RightTab = 'tasks' | 'activity';

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
        {activeTab === 'tasks' ? <TaskBoard /> : <ActivityFeed />}
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
        <AgentCards />
        <div className="flex-1 flex min-h-0">
          <GovernancePanel className="w-2/5 overflow-y-auto" />
          <RightPanel className="w-3/5" />
        </div>
      </div>
      {/* Overlays */}
      <SetupWizard />
      <SettingsPanel />
      <ResearchPromptsPanel />
    </DashboardProvider>
  );
}
