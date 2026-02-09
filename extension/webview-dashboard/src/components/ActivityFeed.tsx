import { useDashboard } from '../context/DashboardContext';
import { ActivityEntryComponent } from './ActivityEntry';
import type { ActivityType } from '../types';

const typeFilters: { label: string; value: ActivityType | null; tooltip: string }[] = [
  { label: 'All', value: null, tooltip: 'Show all activity types' },
  { label: 'Decision', value: 'decision', tooltip: 'Governance decisions submitted by agents via submit_decision()' },
  { label: 'Review', value: 'review', tooltip: 'Governance review verdicts (approved, needs revision, needs human review)' },
  { label: 'Finding', value: 'finding', tooltip: 'Quality findings from validation, linting, or code review' },
  { label: 'Research', value: 'research', tooltip: 'Research activities: prompt creation, execution, and completion' },
  { label: 'Guidance', value: 'guidance', tooltip: 'Guidance provided to agents by reviewers or governance' },
  { label: 'Response', value: 'response', tooltip: 'Agent responses and acknowledgments' },
  { label: 'Drift', value: 'drift', tooltip: 'Drift detection alerts (time, loop, scope, or quality drift)' },
];

export function ActivityFeed({ className = '' }: { className?: string }) {
  const { data, agentFilter, governanceFilter, typeFilter, setTypeFilter } = useDashboard();

  let filtered = data.activities;
  if (agentFilter) {
    filtered = filtered.filter(a => a.agent === agentFilter);
  }
  if (governanceFilter) {
    filtered = filtered.filter(a => a.governanceRef === governanceFilter);
  }
  if (typeFilter) {
    filtered = filtered.filter(a => a.type === typeFilter);
  }

  return (
    <div className={`flex flex-col ${className}`}>
      <div className="px-3 py-2 border-b border-vscode-border flex items-center gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted" title="Chronological feed of all agent activity: decisions, reviews, findings, guidance, and drift alerts. Filter by type using the tabs or by agent/entity using the cards and governance panel.">Activity</h2>
        <div className="flex gap-1 ml-auto">
          {typeFilters.map(f => (
            <button
              key={f.label}
              onClick={() => setTypeFilter(typeFilter === f.value ? null : f.value)}
              title={f.tooltip}
              className={`text-2xs px-2 py-0.5 rounded transition-colors ${
                typeFilter === f.value
                  ? 'bg-vscode-btn-bg text-vscode-btn-fg'
                  : 'text-vscode-muted hover:text-vscode-fg hover:bg-vscode-widget-bg'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {(agentFilter || governanceFilter) && (
        <div className="px-3 py-1.5 bg-vscode-widget-bg border-b border-vscode-border flex items-center gap-2 text-2xs" title="Active filters applied to the activity feed. Click an agent card or governance entity to toggle filters.">
          <span className="text-vscode-muted">Filtering:</span>
          {agentFilter && (
            <span className="bg-tier-quality/20 text-tier-quality px-1.5 py-0.5 rounded" title={`Showing only activities from agent: ${agentFilter}. Click the agent card again to clear.`}>
              agent: {agentFilter}
            </span>
          )}
          {governanceFilter && (
            <span className="bg-tier-architecture/20 text-tier-architecture px-1.5 py-0.5 rounded" title={`Showing only activities referencing governance entity: ${governanceFilter}. Click "Clear filter" in the governance panel to remove.`}>
              ref: {governanceFilter}
            </span>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs text-vscode-muted italic py-8" title={data.activities.length === 0 ? 'Activity entries appear as agents work: decisions, reviews, quality findings, and status updates' : 'Try removing filters to see all activities'}>
            {data.activities.length === 0
              ? 'No activity yet \u2014 connect and run commands to see events here'
              : 'No activities match current filters'}
          </div>
        ) : (
          filtered.map(entry => (
            <ActivityEntryComponent key={entry.id} entry={entry} />
          ))
        )}
      </div>
    </div>
  );
}
