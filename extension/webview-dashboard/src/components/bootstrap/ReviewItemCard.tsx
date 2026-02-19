import { useState } from 'react';
import type { BootstrapReviewItem, BootstrapReviewItemStatus } from '../../types';

const STATUS_STYLES: Record<BootstrapReviewItemStatus, string> = {
  pending: 'bg-vscode-widget-bg text-vscode-muted',
  approved: 'bg-green-500/20 text-green-400',
  rejected: 'bg-red-500/20 text-red-400',
  edited: 'bg-blue-500/20 text-blue-400',
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  vision_standard: 'Vision Standard',
  architectural_standard: 'Arch Standard',
  pattern: 'Pattern',
  component: 'Component',
  coding_convention: 'Convention',
  observation: 'Observation',
};

const CONFIDENCE_STYLES: Record<string, string> = {
  high: 'bg-green-500/15 text-green-400',
  medium: 'bg-yellow-500/15 text-yellow-400',
  low: 'bg-orange-500/15 text-orange-400',
};

export function ReviewItemCard({
  item,
  onApprove,
  onReject,
  onEdit,
}: {
  item: BootstrapReviewItem;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEdit: (id: string, observations: string[]) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState('');

  const handleStartEdit = () => {
    const obs = item.editedObservations || item.observations;
    setEditText(obs.join('\n'));
    setEditing(true);
    setExpanded(true);
  };

  const handleSaveEdit = () => {
    const newObs = editText
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    if (newObs.length > 0) {
      onEdit(item.id, newObs);
    }
    setEditing(false);
  };

  const handleCancelEdit = () => {
    setEditing(false);
    setEditText('');
  };

  const entityLabel = ENTITY_TYPE_LABELS[item.entityType] || item.entityType;

  return (
    <div
      className={`border rounded bg-vscode-widget-bg ${
        item.isContradiction ? 'border-yellow-500/30' : 'border-vscode-border'
      }`}
    >
      {/* Header row */}
      <div
        className="px-3 py-2 flex items-center gap-2 cursor-pointer select-none"
        onClick={() => !editing && setExpanded(!expanded)}
      >
        {/* Expand indicator */}
        <span className="text-2xs text-vscode-muted w-3 flex-shrink-0">
          {expanded ? '\u25BC' : '\u25B6'}
        </span>

        {/* Status badge */}
        <span
          className={`text-2xs px-1.5 py-0.5 rounded font-medium ${STATUS_STYLES[item.status]}`}
        >
          {item.status}
        </span>

        {/* Entity type badge */}
        <span className="text-2xs px-1.5 py-0.5 rounded bg-vscode-bg text-vscode-muted">
          {entityLabel}
        </span>

        {/* Confidence badge */}
        {item.confidence && (
          <span
            className={`text-2xs px-1.5 py-0.5 rounded ${CONFIDENCE_STYLES[item.confidence] || ''}`}
          >
            {item.confidence}
          </span>
        )}

        {/* Contradiction indicator */}
        {item.isContradiction && (
          <span className="text-2xs px-1.5 py-0.5 rounded bg-yellow-500/15 text-yellow-400">
            contradiction
          </span>
        )}

        {/* User-created indicator */}
        {item.isUserCreated && (
          <span className="text-2xs px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400">
            manual
          </span>
        )}

        {/* Name and description */}
        <div className="flex-1 min-w-0">
          <span className="text-xs font-medium truncate block">{item.name}</span>
          {!expanded && (
            <span className="text-2xs text-vscode-muted truncate block">{item.description}</span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          {item.status !== 'approved' && (
            <button
              onClick={() => onApprove(item.id)}
              className="text-2xs px-2 py-0.5 rounded bg-green-500/15 text-green-400 hover:bg-green-500/25 transition-colors"
              title="Approve"
            >
              Approve
            </button>
          )}
          {item.status !== 'rejected' && (
            <button
              onClick={() => onReject(item.id)}
              className="text-2xs px-2 py-0.5 rounded bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors"
              title="Reject"
            >
              Reject
            </button>
          )}
          {!editing && item.status !== 'rejected' && (
            <button
              onClick={handleStartEdit}
              className="text-2xs px-2 py-0.5 rounded bg-blue-500/15 text-blue-400 hover:bg-blue-500/25 transition-colors"
              title="Edit observations"
            >
              Edit
            </button>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-3 pb-3 pt-1 border-t border-vscode-border space-y-2">
          {editing ? (
            <>
              <div className="text-2xs font-medium text-vscode-muted">
                Edit observations (one per line):
              </div>
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className="w-full h-32 text-2xs p-2 rounded bg-vscode-bg border border-vscode-border text-vscode-fg resize-y font-mono"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSaveEdit}
                  disabled={!editText.trim()}
                  className="text-2xs px-2.5 py-1 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Save Changes
                </button>
                <button
                  onClick={handleCancelEdit}
                  className="text-2xs px-2.5 py-1 rounded bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg border border-vscode-border transition-colors"
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Observations */}
              <ul className="space-y-1">
                {(item.editedObservations || item.observations).map((obs, i) => (
                  <li key={i} className="text-2xs text-vscode-fg flex items-start gap-1.5">
                    <span className="text-vscode-muted flex-shrink-0 mt-0.5">&bull;</span>
                    <span>{obs}</span>
                  </li>
                ))}
              </ul>

              {/* Source files */}
              {item.sourceFiles && item.sourceFiles.length > 0 && (
                <div className="text-2xs text-vscode-muted pt-1 border-t border-vscode-border/50">
                  <span className="font-medium">Sources:</span> {item.sourceFiles.join(', ')}
                </div>
              )}

              {/* Source evidence */}
              {item.sourceEvidence && (
                <div className="text-2xs text-vscode-muted italic">{item.sourceEvidence}</div>
              )}

              {/* Contradiction details */}
              {item.isContradiction && item.contradiction && (
                <div className="mt-2 pt-2 border-t border-yellow-500/20 space-y-2">
                  <div className="text-2xs font-semibold text-yellow-400 uppercase tracking-wider">
                    Competing Approaches
                  </div>
                  {item.contradiction.alternatives.map((alt, i) => (
                    <div key={i} className="bg-vscode-bg rounded p-2 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium">{alt.name}</span>
                        <span className="text-2xs text-vscode-muted">
                          {alt.usage} ({alt.percentage}%)
                        </span>
                      </div>
                      {/* Usage bar */}
                      <div className="w-full h-1 bg-vscode-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${Math.min(alt.percentage, 100)}%` }}
                        />
                      </div>
                      <div className="text-2xs text-vscode-muted">{alt.description}</div>
                      <div className="text-2xs italic text-vscode-fg">
                        {alt.qualitativeAssessment}
                      </div>
                    </div>
                  ))}
                  {/* Recommendation */}
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded p-2">
                    <div className="text-2xs font-medium text-blue-400 mb-0.5">Recommendation</div>
                    <div className="text-2xs text-vscode-fg">
                      {item.contradiction.recommendation}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
