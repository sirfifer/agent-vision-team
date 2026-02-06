const GATES = [
  { name: 'Build', desc: 'Code compiles/builds successfully', icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
  { name: 'Lint', desc: 'No lint violations (or only auto-fixable ones)', icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4' },
  { name: 'Test', desc: 'All tests pass', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4' },
  { name: 'Coverage', desc: 'Meets configured threshold (default 80%)', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { name: 'Findings', desc: 'No critical or unresolved findings', icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' },
];

export function QualityGatesStep() {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold">Quality Gates</h3>
      <p className="text-vscode-muted">
        Workers must pass all 5 gates before work can be merged. Quality is deterministic, not subjective.
      </p>

      <div className="grid grid-cols-5 gap-2">
        {GATES.map((gate) => (
          <div key={gate.name} className="p-3 rounded-lg border border-vscode-border bg-vscode-widget-bg/30 text-center space-y-2">
            <svg className="w-6 h-6 mx-auto text-tier-quality" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={gate.icon} />
            </svg>
            <h4 className="font-bold text-xs">{gate.name}</h4>
            <p className="text-[10px] text-vscode-muted leading-tight">{gate.desc}</p>
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <div className="p-3 rounded-lg border border-vscode-border space-y-2">
          <h4 className="font-semibold text-sm">How to run gates</h4>
          <ul className="text-xs text-vscode-muted space-y-1">
            <li>&bull; <strong>From the dashboard:</strong> Click the <strong>Validate</strong> button in the session bar</li>
            <li>&bull; <strong>From Claude Code:</strong> Workers call <code className="px-1 py-0.5 bg-vscode-widget-bg rounded">check_all_gates()</code> before completion</li>
            <li>&bull; <strong>Detailed report:</strong> Use <code className="px-1 py-0.5 bg-vscode-widget-bg rounded">validate()</code> for a human-readable summary</li>
          </ul>
        </div>

        <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-900/10">
          <h4 className="font-semibold text-sm text-amber-200">When gates fail</h4>
          <p className="text-xs text-vscode-muted mt-1">
            Workers fix the issue and resubmit. The quality reviewer routes findings back with context.
            Every dismissed finding requires a justification &mdash; no silent dismissals.
          </p>
        </div>
      </div>
    </div>
  );
}
