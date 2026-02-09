import { useState } from 'react';
import { useDashboard } from '../context/DashboardContext';
import type { DecisionHistoryEntry } from '../types';

const categoryLabels: Record<string, string> = {
  pattern_choice: 'Pattern Choice',
  component_design: 'Component Design',
  api_design: 'API Design',
  deviation: 'Deviation',
  scope_change: 'Scope Change',
};

const categoryColors: Record<string, string> = {
  pattern_choice: 'bg-blue-500/20 text-blue-400',
  component_design: 'bg-cyan-500/20 text-cyan-400',
  api_design: 'bg-indigo-500/20 text-indigo-400',
  deviation: 'bg-amber-500/20 text-amber-400',
  scope_change: 'bg-orange-500/20 text-orange-400',
};

const verdictColors: Record<string, string> = {
  approved: 'bg-green-500/20 text-green-400',
  blocked: 'bg-red-500/20 text-red-400',
  needs_human_review: 'bg-purple-500/20 text-purple-400',
};

const verdictLabels: Record<string, string> = {
  approved: 'Approved',
  blocked: 'Needs Revision',
  needs_human_review: 'Needs Human Review',
};

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

function DecisionCard({ decision }: { decision: DecisionHistoryEntry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-vscode-border rounded bg-vscode-widget-bg">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-3 py-2 hover:bg-vscode-widget-bg/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-vscode-muted">{expanded ? '\u25BC' : '\u25B6'}</span>
          <span className={`text-2xs px-1.5 py-0.5 rounded font-medium ${categoryColors[decision.category] ?? 'bg-vscode-widget-bg text-vscode-muted'}`}>
            {categoryLabels[decision.category] ?? decision.category}
          </span>
          <span className="text-xs font-medium flex-1 truncate">{decision.summary}</span>
          {decision.verdict && (
            <span className={`text-2xs px-1.5 py-0.5 rounded font-medium ${verdictColors[decision.verdict] ?? 'bg-vscode-widget-bg text-vscode-muted'}`}>
              {verdictLabels[decision.verdict] ?? decision.verdict.replace('_', ' ')}
            </span>
          )}
          {!decision.verdict && (
            <span className="text-2xs px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-400 font-medium">
              pending
            </span>
          )}
          <span className="text-2xs text-vscode-muted shrink-0">
            {formatRelativeTime(decision.createdAt)}
          </span>
        </div>
        <div className="flex items-center gap-2 mt-1 ml-5">
          <span className="text-2xs text-vscode-muted">by {decision.agent}</span>
          <span className="text-2xs text-vscode-muted">confidence: {decision.confidence}</span>
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-1 border-t border-vscode-border space-y-2">
          <div className="text-2xs text-vscode-muted">
            <span className="font-medium">Decision ID:</span> {decision.id}
          </div>
          <div className="text-2xs text-vscode-muted">
            <span className="font-medium">Task:</span> {decision.taskId}
          </div>
          {decision.guidance && (
            <div className="text-2xs p-2 rounded bg-vscode-bg border border-vscode-border">
              <div className="font-medium mb-1">Guidance</div>
              <div className="text-vscode-muted">{decision.guidance}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function DecisionExplorer({ className = '' }: { className?: string }) {
  const { data } = useDashboard();
  const decisions = data.decisionHistory ?? [];
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [verdictFilter, setVerdictFilter] = useState<string | null>(null);

  const categories = ['pattern_choice', 'component_design', 'api_design', 'deviation', 'scope_change'];
  const verdicts = ['approved', 'blocked', 'needs_human_review'];

  const filtered = decisions.filter(d => {
    if (categoryFilter && d.category !== categoryFilter) return false;
    if (verdictFilter === 'pending' && d.verdict !== null) return false;
    if (verdictFilter && verdictFilter !== 'pending' && d.verdict !== verdictFilter) return false;
    return true;
  });

  return (
    <div className={className}>
      <div className="px-3 py-2 border-b border-vscode-border">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">
            Decisions
          </h2>
          {decisions.length > 0 && (
            <span className="text-2xs px-1.5 py-0.5 rounded-full bg-tier-architecture/20 text-tier-architecture font-semibold">
              {decisions.length}
            </span>
          )}
        </div>

        {/* Category filters */}
        <div className="flex gap-1 mt-2 flex-wrap">
          <button
            onClick={() => setCategoryFilter(null)}
            className={`text-2xs px-1.5 py-0.5 rounded transition-colors ${
              !categoryFilter ? 'bg-tier-quality text-white' : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
            }`}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(categoryFilter === cat ? null : cat)}
              className={`text-2xs px-1.5 py-0.5 rounded transition-colors ${
                categoryFilter === cat ? 'bg-tier-quality text-white' : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
              }`}
            >
              {categoryLabels[cat] ?? cat}
            </button>
          ))}
        </div>

        {/* Verdict filters */}
        <div className="flex gap-1 mt-1 flex-wrap">
          <button
            onClick={() => setVerdictFilter(null)}
            className={`text-2xs px-1.5 py-0.5 rounded transition-colors ${
              !verdictFilter ? 'bg-tier-quality text-white' : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
            }`}
          >
            All Verdicts
          </button>
          {verdicts.map(v => (
            <button
              key={v}
              onClick={() => setVerdictFilter(verdictFilter === v ? null : v)}
              className={`text-2xs px-1.5 py-0.5 rounded transition-colors ${
                verdictFilter === v ? 'bg-tier-quality text-white' : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
              }`}
            >
              {verdictLabels[v] ?? v.replace('_', ' ')}
            </button>
          ))}
          <button
            onClick={() => setVerdictFilter(verdictFilter === 'pending' ? null : 'pending')}
            className={`text-2xs px-1.5 py-0.5 rounded transition-colors ${
              verdictFilter === 'pending' ? 'bg-tier-quality text-white' : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
            }`}
          >
            pending
          </button>
        </div>
      </div>

      <div className="p-2 space-y-2">
        {filtered.length === 0 ? (
          <div className="px-3 py-8 text-xs text-vscode-muted text-center italic">
            {decisions.length === 0
              ? 'No decisions yet. Decisions submitted via submit_decision() will appear here.'
              : 'No decisions match the current filters.'}
          </div>
        ) : (
          filtered.map(d => <DecisionCard key={d.id} decision={d} />)
        )}
      </div>
    </div>
  );
}
