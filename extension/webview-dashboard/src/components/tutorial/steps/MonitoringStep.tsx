const PANELS = [
  {
    name: 'Session Bar',
    location: 'Top strip',
    desc: 'Shows current phase, task counts, and connection status. Contains Connect, Refresh, Validate buttons plus icons for Setup Wizard, Research, and Settings.',
    color: 'border-blue-500/30',
  },
  {
    name: 'Agent Cards',
    location: 'Below session bar',
    desc: 'One card per agent (Orchestrator, Worker, Quality Reviewer, KG Librarian, Governance Reviewer, Researcher, Steward). Color-coded status: green = active, gray = idle, red = blocked, amber = reviewing.',
    color: 'border-green-500/30',
  },
  {
    name: 'Governance Panel',
    location: 'Left side',
    desc: 'Displays your Vision Standards and Architecture Elements from the Knowledge Graph. Expandable cards show observations and relationships.',
    color: 'border-amber-500/30',
  },
  {
    name: 'Governed Tasks',
    location: 'Right side, Tasks tab',
    desc: 'Shows all tasks created with create_governed_task(). Each displays its review status: Pending Review, Approved, Blocked, In Progress, or Completed.',
    color: 'border-purple-500/30',
  },
  {
    name: 'Activity Feed',
    location: 'Right side, Activity tab',
    desc: 'Chronological log of all agent actions: governance decisions, quality findings, KG operations, status changes. Click an agent card to filter.',
    color: 'border-teal-500/30',
  },
];

export function MonitoringStep() {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold">Monitoring Progress</h3>
      <p className="text-vscode-muted">
        The dashboard updates every 10 seconds. Here's what each area shows:
      </p>

      <div className="space-y-3">
        {PANELS.map((panel) => (
          <div key={panel.name} className={`p-3 rounded-lg border ${panel.color} bg-vscode-widget-bg/30 space-y-1`}>
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-sm">{panel.name}</h4>
              <span className="text-xs text-vscode-muted px-2 py-0.5 rounded bg-vscode-widget-bg">{panel.location}</span>
            </div>
            <p className="text-xs text-vscode-muted">{panel.desc}</p>
          </div>
        ))}
      </div>

      <div className="p-3 rounded-lg border border-blue-500/30 bg-blue-900/10">
        <p className="text-xs text-blue-200">
          <strong>Tip:</strong> You don't need to manually refresh. The dashboard polls automatically.
          But you can click Refresh to force an immediate update.
        </p>
      </div>
    </div>
  );
}
