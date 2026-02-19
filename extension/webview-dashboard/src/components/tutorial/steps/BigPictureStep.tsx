export function BigPictureStep() {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold">The Big Picture</h3>
      <p className="text-vscode-muted">
        The system has two halves. Understanding which does what is the key to getting started.
      </p>

      <div className="grid grid-cols-2 gap-4">
        {/* Dashboard side */}
        <div className="p-4 rounded-lg border-2 border-blue-500/40 bg-blue-900/10 space-y-3">
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-blue-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
            <h4 className="font-bold text-blue-300">This Dashboard</h4>
          </div>
          <p className="text-sm text-vscode-muted">
            Your <strong>observability window</strong>. It shows what agents are doing, governance
            status, knowledge graph contents, and quality results.
          </p>
          <p className="text-xs text-blue-300/70 font-medium">You watch here.</p>
        </div>

        {/* CLI side */}
        <div className="p-4 rounded-lg border-2 border-green-500/40 bg-green-900/10 space-y-3">
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-green-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <h4 className="font-bold text-green-300">Claude Code CLI</h4>
          </div>
          <p className="text-sm text-vscode-muted">
            Where <strong>work actually happens</strong>. You open your terminal, run{' '}
            <code className="px-1.5 py-0.5 bg-vscode-widget-bg rounded text-xs">claude</code>, and
            give it tasks. Claude decomposes work and coordinates agents.
          </p>
          <p className="text-xs text-green-300/70 font-medium">You drive here.</p>
        </div>
      </div>

      {/* Flow diagram */}
      <div className="flex items-center justify-center gap-2 py-4 text-xs text-vscode-muted">
        <span className="px-3 py-1.5 rounded bg-vscode-widget-bg border border-vscode-border font-semibold">
          You
        </span>
        <span>&rarr;</span>
        <span className="px-3 py-1.5 rounded bg-green-900/20 border border-green-500/30 font-semibold text-green-300">
          Claude Code CLI
        </span>
        <span>&rarr;</span>
        <span className="px-3 py-1.5 rounded bg-vscode-widget-bg border border-vscode-border font-semibold">
          Agent Team
        </span>
        <span>&larr;</span>
        <span className="px-3 py-1.5 rounded bg-blue-900/20 border border-blue-500/30 font-semibold text-blue-300">
          Dashboard
        </span>
      </div>

      {/* Key insight */}
      <div className="p-4 rounded-lg border border-amber-500/30 bg-amber-900/10">
        <p className="text-sm font-medium text-amber-200">
          Key insight: The dashboard does not control agents. It observes them. Claude Code CLI is
          the driver &mdash; you give it tasks, and it orchestrates the team.
        </p>
      </div>
    </div>
  );
}
