interface ReadyStepProps {
  onLaunchWizard: () => void;
}

const QUICK_REF = [
  { action: 'Open the dashboard', how: 'Click "Open Dashboard" in sidebar Actions' },
  { action: 'Run project setup', how: 'Click "Setup Wizard" in sidebar Actions' },
  { action: 'Start working', how: 'Open terminal, run claude, describe your task' },
  { action: 'Monitor agents', how: 'Watch the Agent Cards strip at the top of the dashboard' },
  { action: 'Check quality', how: 'Click "Validate" in the session bar' },
  { action: 'Search memory', how: 'Use the Memory Browser search in the sidebar' },
  { action: 'Track external changes', how: 'Set up Research Prompts from the dashboard' },
  { action: 'Create a task brief', how: 'Command Palette: "Create Task Brief"' },
];

export function ReadyStep({ onLaunchWizard }: ReadyStepProps) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h3 className="text-2xl font-bold">You're Ready!</h3>
        <p className="text-vscode-muted">
          You now understand the full workflow. Here's a quick reference to keep handy.
        </p>
      </div>

      {/* Quick reference table */}
      <div className="rounded-lg border border-vscode-border overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-vscode-widget-bg">
              <th className="text-left px-3 py-2 font-semibold text-vscode-muted">Action</th>
              <th className="text-left px-3 py-2 font-semibold text-vscode-muted">How</th>
            </tr>
          </thead>
          <tbody>
            {QUICK_REF.map((item, i) => (
              <tr key={i} className={i % 2 === 0 ? '' : 'bg-vscode-widget-bg/30'}>
                <td className="px-3 py-2 font-medium">{item.action}</td>
                <td className="px-3 py-2 text-vscode-muted">{item.how}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* CTAs */}
      <div className="flex items-center justify-center gap-4 pt-4">
        <button
          onClick={onLaunchWizard}
          className="px-5 py-2 rounded-lg bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity font-semibold text-sm"
        >
          Launch Setup Wizard
        </button>
      </div>

      <p className="text-center text-xs text-vscode-muted">
        The system handles complexity. You provide the goals, agents handle execution, and the
        dashboard keeps you informed.
      </p>
    </div>
  );
}
