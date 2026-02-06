export function WelcomeStep() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-3">
        <h3 className="text-2xl font-bold">Welcome to the Workflow Tutorial</h3>
        <p className="text-vscode-muted text-base max-w-lg mx-auto">
          This tutorial walks you through exactly how to use the Collaborative Intelligence System
          &mdash; from initial setup to giving Claude work to monitoring agent progress.
        </p>
        <span className="inline-block px-3 py-1 rounded-full bg-vscode-widget-bg text-vscode-muted text-xs">
          ~5 minutes
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 mt-8">
        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg text-center space-y-2">
          <div className="text-2xl">1</div>
          <h4 className="font-semibold text-sm">Configure Your Project</h4>
          <p className="text-xs text-vscode-muted">
            Set up vision standards, quality gates, and agent permissions
          </p>
        </div>
        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg text-center space-y-2">
          <div className="text-2xl">2</div>
          <h4 className="font-semibold text-sm">Work with Claude</h4>
          <p className="text-xs text-vscode-muted">
            Give Claude tasks in the CLI and let the agent team handle execution
          </p>
        </div>
        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg text-center space-y-2">
          <div className="text-2xl">3</div>
          <h4 className="font-semibold text-sm">Monitor Progress</h4>
          <p className="text-xs text-vscode-muted">
            Watch agents work, review governance decisions, and track quality
          </p>
        </div>
      </div>

      <p className="text-center text-vscode-muted text-xs mt-4">
        Click <strong>Next</strong> to begin.
      </p>
    </div>
  );
}
