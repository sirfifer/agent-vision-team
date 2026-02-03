import { useDashboard } from '../context/DashboardContext';

const statusColors: Record<string, string> = {
  connected: 'bg-tier-quality',
  disconnected: 'bg-agent-idle',
  error: 'bg-tier-vision',
};

export function SessionBar() {
  const { data, sendCommand } = useDashboard();
  const { connectionStatus, sessionPhase, tasks } = data;

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-vscode-border bg-vscode-widget-bg text-xs">
      <div className="flex items-center gap-1.5">
        <span className="text-vscode-muted uppercase tracking-wider">Phase</span>
        <span className="font-semibold">{sessionPhase || 'inactive'}</span>
      </div>

      <div className="w-px h-4 bg-vscode-border" />

      <div className="flex items-center gap-1.5">
        <span className="text-vscode-muted uppercase tracking-wider">Tasks</span>
        <span className="font-semibold">{tasks.active}/{tasks.total}</span>
      </div>

      <div className="w-px h-4 bg-vscode-border" />

      <div className="flex items-center gap-1.5">
        <span className={`w-2 h-2 rounded-full ${statusColors[connectionStatus] ?? 'bg-agent-idle'}`} />
        <span className="capitalize">{connectionStatus}</span>
      </div>

      <div className="ml-auto flex gap-1.5">
        <button
          onClick={() => sendCommand('connect')}
          className="px-2.5 py-1 rounded bg-vscode-btn2-bg text-vscode-btn2-fg hover:opacity-80 transition-opacity"
        >
          Connect
        </button>
        <button
          onClick={() => sendCommand('refresh')}
          className="px-2.5 py-1 rounded bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity"
        >
          Refresh
        </button>
        <button
          onClick={() => sendCommand('validate')}
          className="px-2.5 py-1 rounded bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity"
        >
          Validate
        </button>
      </div>
    </div>
  );
}
