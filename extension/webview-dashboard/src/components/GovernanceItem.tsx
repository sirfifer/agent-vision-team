import { useState } from 'react';
import { useDashboard } from '../context/DashboardContext';
import type { Entity } from '../types';

const tierBadgeClass: Record<string, string> = {
  vision_standard: 'bg-tier-vision/20 text-tier-vision',
  architectural_standard: 'bg-tier-architecture/20 text-tier-architecture',
  pattern: 'bg-tier-architecture/20 text-tier-architecture',
  component: 'bg-tier-quality/20 text-tier-quality',
  problem: 'bg-tier-vision/20 text-tier-vision',
  solution_pattern: 'bg-tier-quality/20 text-tier-quality',
};

const typeDescriptions: Record<string, string> = {
  vision_standard: 'Vision Standard: a core principle or invariant. Human-only modifiable. Violations are caught before any code is written.',
  architectural_standard: 'Architectural Standard: a design rule verified across the codebase. Modifiable with human approval.',
  pattern: 'Pattern: an established implementation pattern that agents should follow. Deviations require governance review.',
  component: 'Component: a tracked system component with observations about its state and behavior.',
  problem: 'Problem: a tracked issue or concern that needs attention.',
  solution_pattern: 'Solution Pattern: a proven approach promoted from recurring successful implementations.',
};

export function GovernanceItem({ entity }: { entity: Entity }) {
  const [expanded, setExpanded] = useState(false);
  const { data, governanceFilter, setGovernanceFilter } = useDashboard();

  const relatedActivities = data.activities.filter(a => a.governanceRef === entity.name);
  const isFiltering = governanceFilter === entity.name;
  const typeDesc = typeDescriptions[entity.entityType] ?? entity.entityType;

  return (
    <div className={`border-b border-vscode-border last:border-b-0 ${isFiltering ? 'bg-tier-quality/5' : ''}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-vscode-widget-bg/50 transition-colors"
        title={`${entity.name}: ${entity.observations[0] ?? 'No observations'}. Click to expand and see all observations.`}
      >
        <span className="text-2xs text-vscode-muted w-4 shrink-0">{expanded ? '\u25BC' : '\u25B6'}</span>
        <span className="text-xs font-medium truncate flex-1">{entity.name}</span>
        <span
          className={`text-2xs px-1.5 py-0.5 rounded-full font-semibold uppercase ${tierBadgeClass[entity.entityType] ?? 'bg-vscode-widget-bg text-vscode-muted'}`}
          title={typeDesc}
        >
          {entity.entityType.replace('_', ' ')}
        </span>
        {relatedActivities.length > 0 && (
          <span className="text-2xs text-vscode-muted" title={`${relatedActivities.length} activity entries reference this entity`}>{relatedActivities.length}</span>
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-2 ml-6">
          {entity.observations.length > 0 ? (
            <ul className="space-y-1 mb-2">
              {entity.observations.map((obs, i) => (
                <li key={i} className="text-xs text-vscode-muted flex gap-1.5" title={obs}>
                  <span className="shrink-0 mt-0.5">&#8226;</span>
                  <span>{obs}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-vscode-muted italic mb-2" title="This entity has no observations yet. Observations are added via add_observations() on the Knowledge Graph server.">No observations</p>
          )}

          {relatedActivities.length > 0 && (
            <div className="mt-1">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setGovernanceFilter(isFiltering ? null : entity.name);
                }}
                className={`text-2xs px-2 py-0.5 rounded transition-colors ${
                  isFiltering
                    ? 'bg-tier-quality text-white'
                    : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
                }`}
                title={isFiltering ? 'Remove the governance filter from the Activity Feed' : `Filter the Activity Feed to show only activities referencing ${entity.name}`}
              >
                {isFiltering ? 'Clear filter' : `Show ${relatedActivities.length} activities`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
