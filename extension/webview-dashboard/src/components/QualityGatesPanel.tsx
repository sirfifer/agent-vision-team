import { useDashboard } from '../context/DashboardContext';

function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

export function QualityGatesPanel({ className = '' }: { className?: string }) {
  const { data } = useDashboard();
  const results = data.qualityGateResults;

  if (!results) {
    return (
      <div className={`px-4 py-2 border-b border-vscode-border ${className}`}>
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">Quality Gates</h2>
          <span className="text-2xs text-vscode-muted italic">Not yet run</span>
        </div>
      </div>
    );
  }

  const gates = [results.build, results.lint, results.tests, results.coverage, results.findings];
  const failedCount = gates.filter(g => !g.passed).length;

  return (
    <div className={`px-4 py-2 border-b border-vscode-border ${className}`}>
      <div className="flex items-center gap-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted shrink-0">Quality Gates</h2>

        <div className="flex items-center gap-2 flex-1">
          {gates.map(gate => (
            <div
              key={gate.name}
              className={`flex items-center gap-1 px-2 py-0.5 rounded text-2xs font-medium ${
                gate.passed
                  ? 'bg-green-500/10 text-green-400'
                  : 'bg-red-500/10 text-red-400'
              }`}
              title={`${gate.name}: ${gate.detail || (gate.passed ? 'Passed' : 'Failed')}`}
            >
              <span>{gate.passed ? '\u2713' : '\u2717'}</span>
              <span className="capitalize">{gate.name}</span>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {results.all_passed ? (
            <span className="text-2xs font-medium text-green-400">All passed</span>
          ) : (
            <span className="text-2xs font-medium text-red-400">{failedCount} failed</span>
          )}
          {results.timestamp && (
            <span className="text-2xs text-vscode-muted">{formatRelativeTime(results.timestamp)}</span>
          )}
        </div>
      </div>
    </div>
  );
}
