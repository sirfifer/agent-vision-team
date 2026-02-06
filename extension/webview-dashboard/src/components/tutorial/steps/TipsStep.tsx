const TIPS = [
  {
    title: 'Give Claude big tasks',
    desc: 'Claude handles decomposition. Don\'t micro-manage — describe the goal, and it will break it into governed subtasks.',
    icon: 'M13 10V3L4 14h7v7l9-11h-7z',
  },
  {
    title: 'Monitor the dashboard',
    desc: 'Keep the dashboard open while work runs. Watch for blocked agents or pending reviews that might need attention.',
    icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  },
  {
    title: 'Trust the governance flow',
    desc: 'Every task is reviewed before execution. Vision conflicts halt all related work automatically. The system enforces correctness.',
    icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
  },
  {
    title: 'Research before building',
    desc: 'For unfamiliar domains or architectural decisions, spawn the researcher subagent first. Workers should implement, not research.',
    icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  },
  {
    title: 'Check governed task status',
    desc: 'If tasks are stuck in "pending_review," governance is the bottleneck. Check the Governed Tasks tab for details.',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
  },
  {
    title: 'Use checkpoints for safety',
    desc: 'After each meaningful unit of work, a git checkpoint tag is created. You can always roll back to the last known-good state.',
    icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  },
];

export function TipsStep() {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold">Tips & Common Patterns</h3>
      <p className="text-vscode-muted">
        Practical advice for getting the most out of the system:
      </p>

      <div className="grid grid-cols-2 gap-3">
        {TIPS.map((tip) => (
          <div key={tip.title} className="p-3 rounded-lg border border-vscode-border bg-vscode-widget-bg/30 space-y-2">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-tier-quality flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tip.icon} />
              </svg>
              <h4 className="font-semibold text-sm">{tip.title}</h4>
            </div>
            <p className="text-xs text-vscode-muted">{tip.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
