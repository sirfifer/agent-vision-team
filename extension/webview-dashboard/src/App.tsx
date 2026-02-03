import { DashboardProvider } from './context/DashboardContext';
import { SessionBar } from './components/SessionBar';
import { SetupBanner } from './components/SetupBanner';
import { AgentCards } from './components/AgentCards';
import { GovernancePanel } from './components/GovernancePanel';
import { ActivityFeed } from './components/ActivityFeed';
import { SetupWizard } from './components/wizard/SetupWizard';
import { SettingsPanel } from './components/SettingsPanel';

export default function App() {
  return (
    <DashboardProvider>
      <div className="h-screen flex flex-col bg-vscode-bg text-vscode-fg text-sm">
        <SessionBar />
        <SetupBanner />
        <AgentCards />
        <div className="flex-1 flex min-h-0">
          <GovernancePanel className="w-2/5 overflow-y-auto" />
          <ActivityFeed className="w-3/5 overflow-y-auto" />
        </div>
      </div>
      {/* Overlays */}
      <SetupWizard />
      <SettingsPanel />
    </DashboardProvider>
  );
}
