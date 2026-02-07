import { useDashboard } from '../context/DashboardContext';

const ResearchIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 7v6m3-3H7" />
  </svg>
);

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
  const { data, sendCommand, sendMessage, setShowSettings, setShowWizard, setShowTutorial, setShowResearchPrompts, researchPrompts, demoMode } = useDashboard();
  const { connectionStatus, sessionPhase, governanceStats, governedTasks } = data;

  const needsHumanCount = governedTasks.filter(t =>
    t.reviews.some(r => r.status === 'needs_human_review')
  ).length;

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-vscode-border bg-vscode-widget-bg text-xs">
      {demoMode && (
        <span className="px-2 py-0.5 rounded bg-purple-600 text-white font-bold text-2xs uppercase tracking-wider animate-pulse" title="Demo mode is active. Data shown is synthetic. Click Toggle Demo in the sidebar to deactivate.">
          Demo
        </span>
      )}
      <div className="flex items-center gap-1.5" title="Current orchestration phase. Tracks where the session is in its lifecycle (planning, implementing, reviewing).">
        <span className="text-vscode-muted uppercase tracking-wider">Phase</span>
        <span className="font-semibold">{sessionPhase || 'inactive'}</span>
      </div>

      <div className="w-px h-4 bg-vscode-border" />

      <div className="flex items-center gap-1.5" title="Governance status: governed task breakdown">
        <span className="text-vscode-muted uppercase tracking-wider">Gov</span>
        {governanceStats.totalGovernedTasks > 0 ? (
          <>
            {governanceStats.blocked > 0 && (
              <span className="px-1.5 py-0.5 rounded text-2xs font-semibold bg-red-500/20 text-red-400">
                {governanceStats.blocked} blocked
              </span>
            )}
            {needsHumanCount > 0 && (
              <span className="px-1.5 py-0.5 rounded text-2xs font-semibold bg-purple-500/20 text-purple-400">
                {needsHumanCount} needs review
              </span>
            )}
            {governanceStats.pendingReviews > 0 && (
              <span className="px-1.5 py-0.5 rounded text-2xs font-semibold bg-yellow-500/20 text-yellow-400">
                {governanceStats.pendingReviews} pending
              </span>
            )}
            <span className="px-1.5 py-0.5 rounded text-2xs font-semibold bg-green-500/20 text-green-400">
              {governanceStats.approved} approved
            </span>
          </>
        ) : (
          <span className="text-vscode-muted">no tasks</span>
        )}
      </div>

      {data.jobSummary && data.jobSummary.running > 0 && (
        <>
          <div className="w-px h-4 bg-vscode-border" />
          <div className="flex items-center gap-1.5" title={`${data.jobSummary.running} job(s) currently running`}>
            <span className="text-vscode-muted uppercase tracking-wider">Jobs</span>
            <span className="px-1.5 py-0.5 rounded text-2xs font-semibold bg-blue-500/20 text-blue-400">
              {data.jobSummary.running} running
            </span>
          </div>
        </>
      )}

      <div className="w-px h-4 bg-vscode-border" />

      <div className="flex items-center gap-1.5" title={statusTooltips[connectionStatus] ?? 'Unknown connection status'}>
        <span className={`w-2 h-2 rounded-full ${statusColors[connectionStatus] ?? 'bg-agent-idle'}`} />
        <span className="capitalize">{connectionStatus}</span>
      </div>

      {/* Hook governance indicator */}
      {data.hookGovernanceStatus && data.hookGovernanceStatus.totalInterceptions > 0 && (
        <>
          <div className="w-px h-4 bg-vscode-border" />
          <div
            className="flex items-center gap-1.5"
            title={`Hook governance: ${data.hookGovernanceStatus.totalInterceptions} interception(s)${data.hookGovernanceStatus.lastInterceptionAt ? `, last: ${data.hookGovernanceStatus.lastInterceptionAt}` : ''}`}
          >
            <span className="w-2 h-2 rounded-full bg-green-400" />
            <span className="text-vscode-muted">Hook</span>
            <span className="font-semibold">{data.hookGovernanceStatus.totalInterceptions}</span>
          </div>
        </>
      )}

      {/* Checkpoint badge */}
      {data.sessionState?.lastCheckpoint && (
        <>
          <div className="w-px h-4 bg-vscode-border" />
          <div className="flex items-center gap-1" title={`Last checkpoint tag: ${data.sessionState.lastCheckpoint}`}>
            <span className="text-vscode-muted">CP</span>
            <span className="text-2xs px-1.5 py-0.5 rounded bg-vscode-widget-bg font-mono">
              {data.sessionState.lastCheckpoint}
            </span>
          </div>
        </>
      )}

      {/* Worktree count */}
      {data.sessionState?.activeWorktrees && data.sessionState.activeWorktrees.length > 0 && (
        <>
          <div className="w-px h-4 bg-vscode-border" />
          <div
            className="flex items-center gap-1"
            title={`Active worktrees: ${data.sessionState.activeWorktrees.join(', ')}`}
          >
            <span className="text-vscode-muted">WT</span>
            <span className="font-semibold">{data.sessionState.activeWorktrees.length}</span>
          </div>
        </>
      )}

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
          onClick={() => setShowTutorial(true)}
          className="p-1.5 rounded hover:bg-vscode-widget-bg transition-colors"
          title="Open Workflow Tutorial"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </button>
        <button
          onClick={() => setShowResearchPrompts(true)}
          className="p-1.5 rounded hover:bg-vscode-widget-bg transition-colors relative"
          title="Research Prompts - Track external changes and research new features"
        >
          <ResearchIcon />
          {researchPrompts.length > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-purple-500 text-[9px] font-bold rounded-full flex items-center justify-center">
              {researchPrompts.length}
            </span>
          )}
        </button>
        <button
          onClick={() => { sendMessage({ type: 'openSettings' }); setShowSettings(true); }}
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
