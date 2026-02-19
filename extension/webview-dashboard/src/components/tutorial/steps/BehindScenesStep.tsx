const STAGES = [
  {
    label: 'Decompose',
    color: 'blue',
    icon: 'M4 6h16M4 12h16m-7 6h7',
    desc: 'Claude breaks your request into discrete, scopeable units of work. Each gets a task brief.',
  },
  {
    label: 'Governance Review',
    color: 'amber',
    icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
    desc: 'Each task is checked against your vision standards and architecture patterns before execution begins.',
  },
  {
    label: 'Worker Implementation',
    color: 'green',
    icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4',
    desc: 'Workers call submit_decision before every significant choice. The governance server reviews and returns a verdict.',
  },
  {
    label: 'Quality Gates',
    color: 'purple',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
    desc: 'Build, lint, test, coverage, and findings must all pass before work can be merged.',
  },
  {
    label: 'Merge & Checkpoint',
    color: 'teal',
    icon: 'M5 13l4 4L19 7',
    desc: 'Approved work is merged with a checkpoint tag for recovery. Session state is updated.',
  },
];

const colorMap: Record<string, { bg: string; border: string; text: string; iconColor: string }> = {
  blue: {
    bg: 'bg-blue-900/10',
    border: 'border-blue-500/30',
    text: 'text-blue-300',
    iconColor: 'text-blue-400',
  },
  amber: {
    bg: 'bg-amber-900/10',
    border: 'border-amber-500/30',
    text: 'text-amber-300',
    iconColor: 'text-amber-400',
  },
  green: {
    bg: 'bg-green-900/10',
    border: 'border-green-500/30',
    text: 'text-green-300',
    iconColor: 'text-green-400',
  },
  purple: {
    bg: 'bg-purple-900/10',
    border: 'border-purple-500/30',
    text: 'text-purple-300',
    iconColor: 'text-purple-400',
  },
  teal: {
    bg: 'bg-teal-900/10',
    border: 'border-teal-500/30',
    text: 'text-teal-300',
    iconColor: 'text-teal-400',
  },
};

export function BehindScenesStep() {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold">What Happens Behind the Scenes</h3>
      <p className="text-vscode-muted">
        Every task follows a governed development cycle. No shortcuts, no race conditions.
      </p>

      {/* Flow arrow strip */}
      <div className="flex items-center justify-center gap-1 text-xs text-vscode-muted py-2">
        {STAGES.map((stage, i) => (
          <div key={i} className="flex items-center">
            {i > 0 && <span className="mx-1">&rarr;</span>}
            <span
              className={`px-2 py-1 rounded ${colorMap[stage.color].bg} ${colorMap[stage.color].border} border ${colorMap[stage.color].text} font-medium`}
            >
              {stage.label}
            </span>
          </div>
        ))}
      </div>

      {/* Stage cards */}
      <div className="space-y-3">
        {STAGES.map((stage, i) => {
          const colors = colorMap[stage.color];
          return (
            <div
              key={i}
              className={`p-3 rounded-lg border ${colors.border} ${colors.bg} flex gap-3 items-start`}
            >
              <svg
                className={`w-5 h-5 ${colors.iconColor} flex-shrink-0 mt-0.5`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={stage.icon} />
              </svg>
              <div>
                <h4 className={`font-semibold text-sm ${colors.text}`}>{stage.label}</h4>
                <p className="text-xs text-vscode-muted mt-1">{stage.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
