import { useState } from 'react';
import { useDashboard } from '../context/DashboardContext';
import { GovernanceItem } from './GovernanceItem';
import { FindingsPanel } from './FindingsPanel';
import { UsagePanel } from './UsagePanel';

export function GovernancePanel({ className = '' }: { className?: string }) {
  const { data } = useDashboard();
  const [visionOpen, setVisionOpen] = useState(true);
  const [archOpen, setArchOpen] = useState(true);

  return (
    <div className={`border-r border-vscode-border ${className}`} title="Governance panel: shows the three-tier hierarchy of standards and patterns from the Knowledge Graph">
      <div className="px-3 py-2 border-b border-vscode-border">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted" title="Entities loaded from the Knowledge Graph, organized by protection tier. Vision standards are inviolable; architecture patterns guide implementation.">Governance</h2>
      </div>

      {/* Vision Standards */}
      <div>
        <button
          onClick={() => setVisionOpen(!visionOpen)}
          className="w-full flex items-center gap-2 px-3 py-2 hover:bg-vscode-widget-bg/50 transition-colors border-b border-vscode-border"
          title="Vision Standards: core principles and invariants that are human-only modifiable. These override all other concerns. Click to expand/collapse."
        >
          <span className="text-xs text-vscode-muted">{visionOpen ? '\u25BC' : '\u25B6'}</span>
          <span className="text-xs font-semibold flex-1 text-left">Vision Standards</span>
          <span className="text-2xs px-1.5 py-0.5 rounded-full bg-tier-vision/20 text-tier-vision font-semibold" title={`${data.visionStandards.length} vision standard(s) loaded from the Knowledge Graph`}>
            {data.visionStandards.length}
          </span>
        </button>
        {visionOpen && (
          <div>
            {data.visionStandards.length === 0 ? (
              <div className="px-3 py-4 text-xs text-vscode-muted text-center italic" title="Use 'Refresh' to load vision standards from the Knowledge Graph, or create them with create_entities() using entityType: 'vision_standard'">
                No vision standards loaded
              </div>
            ) : (
              data.visionStandards.map(entity => (
                <GovernanceItem key={entity.name} entity={entity} />
              ))
            )}
          </div>
        )}
      </div>

      {/* Architecture */}
      <div>
        <button
          onClick={() => setArchOpen(!archOpen)}
          className="w-full flex items-center gap-2 px-3 py-2 hover:bg-vscode-widget-bg/50 transition-colors border-b border-vscode-border"
          title="Architecture: patterns, components, and standards that guide implementation. Modifiable with human approval. Click to expand/collapse."
        >
          <span className="text-xs text-vscode-muted">{archOpen ? '\u25BC' : '\u25B6'}</span>
          <span className="text-xs font-semibold flex-1 text-left">Architecture</span>
          <span className="text-2xs px-1.5 py-0.5 rounded-full bg-tier-architecture/20 text-tier-architecture font-semibold" title={`${data.architecturalElements.length} architectural element(s) loaded from the Knowledge Graph`}>
            {data.architecturalElements.length}
          </span>
        </button>
        {archOpen && (
          <div>
            {data.architecturalElements.length === 0 ? (
              <div className="px-3 py-4 text-xs text-vscode-muted text-center italic" title="Use 'Refresh' to load architectural entities from the Knowledge Graph">
                No architectural elements loaded
              </div>
            ) : (
              data.architecturalElements.map(entity => (
                <GovernanceItem key={entity.name} entity={entity} />
              ))
            )}
          </div>
        )}
      </div>

      {/* Quality Findings */}
      <FindingsPanel />

      {/* Token Usage */}
      <UsagePanel />
    </div>
  );
}
