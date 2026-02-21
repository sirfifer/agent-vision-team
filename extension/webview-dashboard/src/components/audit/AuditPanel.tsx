import { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import type { AuditHealthData, AuditRecommendation, AuditEvent } from '../../types';

function formatTimestamp(ts: number): string {
  if (!ts) return 'never';
  const d = new Date(ts * 1000);
  const now = Date.now();
  const diff = now - d.getTime();
  if (diff < 60_000) return 'just now';
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)}h ago`;
  return d.toLocaleDateString();
}

function severityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'text-red-400';
    case 'warning':
      return 'text-yellow-400';
    case 'info':
      return 'text-blue-400';
    default:
      return 'text-vscode-muted';
  }
}

function categoryLabel(category: string): string {
  switch (category) {
    case 'setting_tune':
      return 'Setting';
    case 'prompt_revision':
      return 'Prompt';
    case 'range_adjustment':
      return 'Range';
    case 'governance_health':
      return 'Governance';
    case 'coverage_gap':
      return 'Coverage';
    default:
      return 'General';
  }
}

function HealthStrip({ health }: { health: AuditHealthData | null }) {
  if (!health) {
    return <div className="px-3 py-2 text-xs text-vscode-muted">Loading audit health...</div>;
  }

  if (!health.enabled) {
    return (
      <div className="px-3 py-2.5 bg-vscode-widget-bg/50 border-b border-vscode-border">
        <div className="flex items-center gap-2 text-xs text-vscode-muted">
          <span className="w-2 h-2 rounded-full bg-gray-500" />
          Audit system disabled. Enable in project settings.
        </div>
      </div>
    );
  }

  const hasAnoms = health.recent_anomalies > 0;

  return (
    <div className="px-3 py-2.5 bg-vscode-widget-bg/50 border-b border-vscode-border">
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${hasAnoms ? 'bg-yellow-400' : 'bg-green-400'}`} />
          <span className="text-vscode-fg font-medium">
            {hasAnoms ? `${health.recent_anomalies} anomalies` : 'Healthy'}
          </span>
        </div>
        <div className="text-vscode-muted">{health.total_events.toLocaleString()} events total</div>
        <div className="text-vscode-muted">{health.events_last_hour} in last hour</div>
        <div className="text-vscode-muted">
          {health.active_recommendations} active recommendations
        </div>
        {health.last_processed_at && (
          <div className="text-vscode-muted ml-auto">
            Processed {formatTimestamp(health.last_processed_at)}
          </div>
        )}
      </div>
    </div>
  );
}

function RecommendationCard({
  rec,
  onDismiss,
}: {
  rec: AuditRecommendation;
  onDismiss: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-vscode-border rounded-md overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 text-left hover:bg-vscode-widget-bg/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${severityColor(rec.severity)}`}>
            {rec.severity.toUpperCase()}
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded bg-vscode-widget-bg text-vscode-muted">
            {categoryLabel(rec.category)}
          </span>
          {rec.escalation_tier && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-300">
              {rec.escalation_tier}
            </span>
          )}
          <span className="text-xs text-vscode-muted ml-auto">
            {rec.evidence_count}x seen | {formatTimestamp(rec.last_seen_at)}
          </span>
        </div>
        <div className="text-xs text-vscode-fg mt-1 truncate">{rec.description}</div>
      </button>

      {expanded && (
        <div className="px-3 py-2 border-t border-vscode-border bg-vscode-widget-bg/30 text-xs space-y-2">
          {rec.suggestion && (
            <div>
              <span className="text-vscode-muted">Suggestion: </span>
              <span className="text-vscode-fg">{rec.suggestion}</span>
            </div>
          )}
          {rec.analysis && (
            <div>
              <span className="text-vscode-muted">Analysis: </span>
              <span className="text-vscode-fg">{rec.analysis}</span>
            </div>
          )}
          {rec.latest_metric_values && Object.keys(rec.latest_metric_values).length > 0 && (
            <div>
              <span className="text-vscode-muted">Metrics: </span>
              <span className="text-vscode-fg font-mono">
                {JSON.stringify(rec.latest_metric_values)}
              </span>
            </div>
          )}
          <div className="flex gap-2 pt-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDismiss(rec.id);
              }}
              className="px-2 py-1 rounded text-xs bg-vscode-widget-bg hover:bg-red-900/30 text-vscode-muted hover:text-red-300 transition-colors"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function EventRow({ event }: { event: AuditEvent }) {
  return (
    <div className="flex items-start gap-2 px-3 py-1.5 text-xs hover:bg-vscode-widget-bg/30">
      <span className="text-vscode-muted shrink-0 w-14">{formatTimestamp(event.ts)}</span>
      <span className="text-blue-300 shrink-0 font-mono">{event.type}</span>
      <span className="text-vscode-muted truncate">
        {event.source ? `[${event.source}]` : ''}{' '}
        {Object.entries(event.data || {})
          .slice(0, 3)
          .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
          .join(' ')}
      </span>
    </div>
  );
}

type AuditTab = 'recommendations' | 'events';

export function AuditPanel({ className = '' }: { className?: string }) {
  const { sendMessage } = useDashboard();
  const [health, setHealth] = useState<AuditHealthData | null>(null);
  const [recommendations, setRecommendations] = useState<AuditRecommendation[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [activeTab, setActiveTab] = useState<AuditTab>('recommendations');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      switch (msg.type) {
        case 'auditHealth':
          setHealth(msg.data);
          setLoading(false);
          break;
        case 'auditRecommendations':
          setRecommendations(msg.recommendations);
          break;
        case 'auditEvents':
          setEvents(msg.events);
          break;
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  const refresh = () => {
    setLoading(true);
    sendMessage({ type: 'requestAuditHealth' });
    sendMessage({ type: 'requestAuditRecommendations' });
    sendMessage({ type: 'requestAuditEvents', limit: 50 });
  };

  // Load on mount
  useEffect(() => {
    refresh();
  }, []);

  const handleDismiss = (id: string) => {
    sendMessage({ type: 'dismissAuditRecommendation', id, reason: 'Dismissed by user' });
    setRecommendations((prev) => prev.filter((r) => r.id !== id));
  };

  const activeRecs = recommendations.filter((r) => r.status === 'active');

  return (
    <div className={`flex flex-col ${className}`}>
      <HealthStrip health={health} />

      <div className="flex items-center border-b border-vscode-border shrink-0">
        <button
          onClick={() => setActiveTab('recommendations')}
          className={`px-3 py-1.5 text-xs font-medium transition-colors ${
            activeTab === 'recommendations'
              ? 'text-vscode-fg border-b-2 border-yellow-400'
              : 'text-vscode-muted hover:text-vscode-fg'
          }`}
        >
          Recommendations ({activeRecs.length})
        </button>
        <button
          onClick={() => setActiveTab('events')}
          className={`px-3 py-1.5 text-xs font-medium transition-colors ${
            activeTab === 'events'
              ? 'text-vscode-fg border-b-2 border-blue-400'
              : 'text-vscode-muted hover:text-vscode-fg'
          }`}
        >
          Events ({events.length})
        </button>
        <button
          onClick={refresh}
          disabled={loading}
          className="ml-auto px-2 py-1 text-xs text-vscode-muted hover:text-vscode-fg transition-colors disabled:opacity-50"
          title="Refresh audit data"
        >
          {loading ? '...' : 'Refresh'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'recommendations' && (
          <div className="p-2 space-y-2">
            {activeRecs.length === 0 ? (
              <div className="text-xs text-vscode-muted text-center py-4">
                No active recommendations. The system is healthy.
              </div>
            ) : (
              activeRecs.map((rec) => (
                <RecommendationCard key={rec.id} rec={rec} onDismiss={handleDismiss} />
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="divide-y divide-vscode-border/50">
            {events.length === 0 ? (
              <div className="text-xs text-vscode-muted text-center py-4">
                No audit events recorded yet.
              </div>
            ) : (
              events.map((evt) => <EventRow key={evt.id} event={evt} />)
            )}
          </div>
        )}
      </div>
    </div>
  );
}
