import { useState } from 'react';
import { useDashboard } from '../context/DashboardContext';
import type { TrustFinding } from '../types';

const severityColors: Record<string, string> = {
  critical: 'bg-red-600/20 text-red-400',
  high: 'bg-red-500/20 text-red-400',
  medium: 'bg-amber-500/20 text-amber-400',
  low: 'bg-yellow-500/20 text-yellow-400',
  info: 'bg-blue-500/20 text-blue-400',
};

function FindingCard({
  finding,
  onDismiss,
}: {
  finding: TrustFinding;
  onDismiss: (id: string, justification: string) => void;
}) {
  const [showDismiss, setShowDismiss] = useState(false);
  const [justification, setJustification] = useState('');

  const handleDismiss = () => {
    if (justification.trim()) {
      onDismiss(finding.id, justification.trim());
      setShowDismiss(false);
      setJustification('');
    }
  };

  return (
    <div className="border border-vscode-border rounded bg-vscode-widget-bg">
      <div className="px-3 py-2">
        <div className="flex items-center gap-2">
          <span
            className={`text-2xs px-1.5 py-0.5 rounded font-medium uppercase ${severityColors[finding.severity] ?? 'bg-vscode-widget-bg text-vscode-muted'}`}
          >
            {finding.severity}
          </span>
          <span className="text-xs font-medium flex-1 truncate">{finding.description}</span>
          {finding.status === 'open' && (
            <button
              onClick={() => setShowDismiss(!showDismiss)}
              className="text-2xs px-1.5 py-0.5 rounded bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg transition-colors"
            >
              Dismiss
            </button>
          )}
          {finding.status === 'dismissed' && (
            <span className="text-2xs px-1.5 py-0.5 rounded bg-vscode-widget-bg text-vscode-muted italic">
              dismissed
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1 text-2xs text-vscode-muted">
          <span>Tool: {finding.tool}</span>
          {finding.component && <span>Component: {finding.component}</span>}
        </div>
      </div>

      {showDismiss && (
        <div className="px-3 pb-3 pt-1 border-t border-vscode-border">
          <div className="text-2xs font-medium mb-1">Justification (required)</div>
          <textarea
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder="Explain why this finding is being dismissed..."
            className="w-full h-16 text-2xs p-2 rounded bg-vscode-bg border border-vscode-border text-vscode-fg resize-none"
          />
          <div className="flex gap-2 mt-1.5">
            <button
              onClick={handleDismiss}
              disabled={!justification.trim()}
              className="text-2xs px-2 py-0.5 rounded bg-tier-quality text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Confirm Dismiss
            </button>
            <button
              onClick={() => {
                setShowDismiss(false);
                setJustification('');
              }}
              className="text-2xs px-2 py-0.5 rounded bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function FindingsPanel({ className = '' }: { className?: string }) {
  const { data, sendMessage } = useDashboard();
  const findings = data.findings ?? [];
  const [showDismissed, setShowDismissed] = useState(false);

  const openFindings = findings.filter((f) => f.status === 'open');
  const dismissedFindings = findings.filter((f) => f.status === 'dismissed');

  const handleDismiss = (findingId: string, justification: string) => {
    sendMessage({
      type: 'dismissFinding',
      findingId,
      justification,
      dismissedBy: 'dashboard-user',
    });
  };

  return (
    <div className={className}>
      <button
        onClick={() => setShowDismissed(!showDismissed)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-vscode-widget-bg/50 transition-colors border-b border-vscode-border"
      >
        <span className="text-xs text-vscode-muted">
          {findings.length > 0 ? (showDismissed ? '▼' : '▶') : '▶'}
        </span>
        <span className="text-xs font-semibold flex-1 text-left">Quality Findings</span>
        {openFindings.length > 0 && (
          <span className="text-2xs px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 font-semibold">
            {openFindings.length} open
          </span>
        )}
        {dismissedFindings.length > 0 && (
          <span className="text-2xs px-1.5 py-0.5 rounded-full bg-vscode-widget-bg text-vscode-muted font-semibold">
            {dismissedFindings.length} dismissed
          </span>
        )}
      </button>

      {findings.length === 0 ? (
        <div className="px-3 py-4 text-xs text-vscode-muted text-center italic">
          No findings recorded
        </div>
      ) : (
        <div className="p-2 space-y-2">
          {openFindings.map((f) => (
            <FindingCard key={f.id} finding={f} onDismiss={handleDismiss} />
          ))}
          {showDismissed && dismissedFindings.length > 0 && (
            <>
              <div className="text-2xs text-vscode-muted px-1 pt-1">Dismissed</div>
              {dismissedFindings.map((f) => (
                <FindingCard key={f.id} finding={f} onDismiss={handleDismiss} />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
