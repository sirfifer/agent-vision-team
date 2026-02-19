interface SetupStepProps {
  onLaunchWizard: () => void;
}

const WIZARD_ITEMS = [
  {
    label: 'Vision Documents',
    desc: 'Define immutable principles and invariants that govern your project',
  },
  {
    label: 'Architecture Documents',
    desc: 'Describe patterns, components, and technical standards',
  },
  {
    label: 'Quality Configuration',
    desc: 'Set test, lint, build, and format commands for your languages',
  },
  { label: 'Project Rules', desc: "Behavioral guidelines injected into every agent's context" },
  { label: 'Permissions', desc: 'Which tools and commands Claude Code can run autonomously' },
  { label: 'Settings', desc: 'Coverage thresholds, mock tests, governance automation' },
  {
    label: 'KG Ingestion',
    desc: 'Push your vision and architecture documents into the Knowledge Graph',
  },
];

export function SetupStep({ onLaunchWizard }: SetupStepProps) {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold">First: Run the Setup Wizard</h3>
      <p className="text-vscode-muted">
        Before using the system, configure your project. The Setup Wizard walks you through 7 key
        steps:
      </p>

      <div className="space-y-2">
        {WIZARD_ITEMS.map((item, i) => (
          <div key={i} className="flex gap-3 items-start p-2 rounded hover:bg-vscode-widget-bg/50">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-vscode-widget-bg text-vscode-muted text-xs font-bold flex-shrink-0 mt-0.5">
              {i + 1}
            </span>
            <div>
              <span className="font-semibold text-sm">{item.label}</span>
              <span className="text-vscode-muted text-xs ml-2">&mdash; {item.desc}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="text-center pt-4">
        <button
          onClick={onLaunchWizard}
          className="px-6 py-2.5 rounded-lg bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity font-semibold"
        >
          Launch Setup Wizard
        </button>
        <p className="text-xs text-vscode-muted mt-2">
          You can continue this tutorial after running the wizard &mdash; it will remember your
          place.
        </p>
      </div>
    </div>
  );
}
