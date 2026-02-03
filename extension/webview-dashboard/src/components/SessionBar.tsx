import { useDashboard } from '../context/DashboardContext';

const statusColors: Record<string, string> = {
  connected: 'bg-tier-quality',
  disconnected: 'bg-agent-idle',
  error: 'bg-tier-vision',
};

const statusTooltips: Record<string, string> = {
  connected: 'All MCP servers are connected and responding',
  disconnected: 'Not connected to MCP servers',
  error: 'Connection to one or more MCP servers failed',
};

export function SessionBar() {
  const { data, sendCommand, setShowSettings, setShowWizard } = useDashboard();
  const { connectionStatus, sessionPhase, tasks } = data;

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-vscode-border bg-vscode-widget-bg text-xs">
      <div className="flex items-center gap-1.5" title="Current orchestration phase. Tracks where the session is in its lifecycle (planning, implementing, reviewing).">
        <span className="text-vscode-muted uppercase tracking-wider">Phase</span>
        <span className="font-semibold">{sessionPhase || 'inactive'}</span>
      </div>

      <div className="w-px h-4 bg-vscode-border" />

      <div className="flex items-center gap-1.5" title={`${tasks.active} active task briefs out of ${tasks.total} total in .avt/task-briefs/`}>
        <span className="text-vscode-muted uppercase tracking-wider">Tasks</span>
        <span className="font-semibold">{tasks.active}/{tasks.total}</span>
      </div>

      <div className="w-px h-4 bg-vscode-border" />

      <div className="flex items-center gap-1.5" title={statusTooltips[connectionStatus] ?? 'Unknown connection status'}>
        <span className={`w-2 h-2 rounded-full ${statusColors[connectionStatus] ?? 'bg-agent-idle'}`} />
        <span className="capitalize">{connectionStatus}</span>
      </div>

      <div className="ml-auto flex gap-1.5">
        <button
          onClick={() => sendCommand('connect')}
          className="px-2.5 py-1 rounded bg-vscode-btn2-bg text-vscode-btn2-fg hover:opacity-80 transition-opacity"
          title="Start all MCP servers (Knowledge Graph, Quality, Governance) and establish connections"
        >
          Connect
        </button>
        <button
          onClick={() => sendCommand('refresh')}
          className="px-2.5 py-1 rounded bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity"
          title="Reload Knowledge Graph entities, governance decision history, and task counts from servers"
        >
          Refresh
        </button>
        <button
          onClick={() => sendCommand('validate')}
          className="px-2.5 py-1 rounded bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity"
          title="Run all quality gates (build, lint, tests, coverage, findings) via the Quality MCP server"
        >
          Validate
        </button>
        <div className="w-px h-6 bg-vscode-border mx-1" />
        <button
          onClick={() => setShowWizard(true)}
          className="p-1.5 rounded hover:bg-vscode-widget-bg transition-colors"
          title="Open Setup Wizard"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </button>
        <button
          onClick={() => setShowSettings(true)}
          className="p-1.5 rounded hover:bg-vscode-widget-bg transition-colors"
          title="Open Settings"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
