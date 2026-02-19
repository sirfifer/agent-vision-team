export function StartingWorkStep() {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold">Starting Work with Claude</h3>
      <p className="text-vscode-muted">
        Once your project is configured, starting work is straightforward:
      </p>

      {/* Terminal mockup */}
      <div className="rounded-lg border border-vscode-border overflow-hidden">
        <div className="px-4 py-2 bg-vscode-widget-bg border-b border-vscode-border text-xs text-vscode-muted flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500/60" />
          <span className="w-3 h-3 rounded-full bg-yellow-500/60" />
          <span className="w-3 h-3 rounded-full bg-green-500/60" />
          <span className="ml-2">Terminal</span>
        </div>
        <div className="p-4 bg-black/40 font-mono text-sm space-y-2">
          <div>
            <span className="text-green-400">$</span> <span className="text-white">claude</span>
          </div>
          <div className="text-vscode-muted">
            &gt; Add authentication to the API using JWT with refresh tokens
          </div>
        </div>
      </div>

      <p className="text-sm text-vscode-muted">
        That's it. You describe your task in natural language. Claude reads your{' '}
        <code className="px-1.5 py-0.5 bg-vscode-widget-bg rounded text-xs">CLAUDE.md</code> file,
        queries the Knowledge Graph for context, and decides how to decompose the work.
      </p>

      {/* What happens next */}
      <h4 className="font-semibold text-sm">What happens next:</h4>
      <div className="space-y-3">
        <div className="flex gap-3 items-start">
          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-900/30 text-blue-300 text-xs font-bold flex-shrink-0">
            1
          </span>
          <div>
            <p className="text-sm font-medium">Claude creates task briefs</p>
            <p className="text-xs text-vscode-muted">
              Discrete, scopeable units of work are written to{' '}
              <code className="px-1 py-0.5 bg-vscode-widget-bg rounded">.avt/task-briefs/</code>
            </p>
          </div>
        </div>
        <div className="flex gap-3 items-start">
          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-amber-900/30 text-amber-300 text-xs font-bold flex-shrink-0">
            2
          </span>
          <div>
            <p className="text-sm font-medium">Each task is paired with a governance review</p>
            <p className="text-xs text-vscode-muted">
              Tasks are <strong>governed from creation</strong> with rapid automated review before
              work begins
            </p>
          </div>
        </div>
        <div className="flex gap-3 items-start">
          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-green-900/30 text-green-300 text-xs font-bold flex-shrink-0">
            3
          </span>
          <div>
            <p className="text-sm font-medium">Workers pick up approved tasks</p>
            <p className="text-xs text-vscode-muted">
              Specialized worker agents implement each task independently
            </p>
          </div>
        </div>
        <div className="flex gap-3 items-start">
          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-900/30 text-purple-300 text-xs font-bold flex-shrink-0">
            4
          </span>
          <div>
            <p className="text-sm font-medium">You monitor progress on the dashboard</p>
            <p className="text-xs text-vscode-muted">
              Agent cards, governed tasks, and activity feed update every 10 seconds
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
