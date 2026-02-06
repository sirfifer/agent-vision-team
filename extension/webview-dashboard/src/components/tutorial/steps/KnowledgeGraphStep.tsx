export function KnowledgeGraphStep() {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold">The Knowledge Graph</h3>
      <p className="text-vscode-muted">
        The Knowledge Graph is your project's persistent institutional memory. Agents query it before every decision.
      </p>

      {/* Three-tier visual */}
      <div className="space-y-2">
        <div className="p-3 rounded-lg border-2 border-red-500/40 bg-red-900/10">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-bold text-sm text-red-300">Vision (Tier 1)</h4>
              <p className="text-xs text-vscode-muted mt-1">
                Core principles and invariants. <strong>Only humans can modify these.</strong>
              </p>
            </div>
            <span className="text-xs px-2 py-1 rounded bg-red-900/40 text-red-300 border border-red-500/30">Immutable</span>
          </div>
        </div>
        <div className="p-3 rounded-lg border-2 border-amber-500/40 bg-amber-900/10">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-bold text-sm text-amber-300">Architecture (Tier 2)</h4>
              <p className="text-xs text-vscode-muted mt-1">
                Patterns, components, and design decisions. Modifiable with orchestrator approval.
              </p>
            </div>
            <span className="text-xs px-2 py-1 rounded bg-amber-900/40 text-amber-300 border border-amber-500/30">Protected</span>
          </div>
        </div>
        <div className="p-3 rounded-lg border-2 border-green-500/40 bg-green-900/10">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-bold text-sm text-green-300">Quality (Tier 3)</h4>
              <p className="text-xs text-vscode-muted mt-1">
                Observations, findings, and troubleshooting notes. Any agent can create these.
              </p>
            </div>
            <span className="text-xs px-2 py-1 rounded bg-green-900/40 text-green-300 border border-green-500/30">Open</span>
          </div>
        </div>
      </div>

      <p className="text-xs text-vscode-muted italic">
        Lower tiers cannot modify or contradict higher tiers. A quality finding can never override a vision standard.
      </p>

      {/* How it works */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 rounded-lg border border-vscode-border space-y-2">
          <h4 className="font-semibold text-sm">What gets stored</h4>
          <ul className="text-xs text-vscode-muted space-y-1">
            <li>&bull; Vision standards from <code className="px-1 py-0.5 bg-vscode-widget-bg rounded">docs/vision/</code></li>
            <li>&bull; Architecture patterns from <code className="px-1 py-0.5 bg-vscode-widget-bg rounded">docs/architecture/</code></li>
            <li>&bull; Solution patterns promoted from recurring observations</li>
            <li>&bull; Decision history &mdash; what was decided and why</li>
          </ul>
        </div>
        <div className="p-3 rounded-lg border border-vscode-border space-y-2">
          <h4 className="font-semibold text-sm">How agents use it</h4>
          <ul className="text-xs text-vscode-muted space-y-1">
            <li>&bull; Query <code className="px-1 py-0.5 bg-vscode-widget-bg rounded">search_nodes()</code> before starting work</li>
            <li>&bull; Load all vision constraints with <code className="px-1 py-0.5 bg-vscode-widget-bg rounded">get_entities_by_tier("vision")</code></li>
            <li>&bull; KG Librarian curates: consolidates duplicates, promotes patterns</li>
            <li>&bull; Important entries sync to <code className="px-1 py-0.5 bg-vscode-widget-bg rounded">.avt/memory/</code> archival files</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
