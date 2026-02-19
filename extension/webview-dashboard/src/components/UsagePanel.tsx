import { useState, useEffect } from 'react';
import { useDashboard } from '../context/DashboardContext';

interface UsageSummary {
  period: string;
  call_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cache_reads: number;
  total_cache_creation: number;
  total_duration_ms: number;
  total_prompt_bytes: number;
}

interface UsageBreakdownEntry {
  agent?: string;
  operation?: string;
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  duration_ms: number;
  avg_prompt_bytes?: number;
}

interface PromptSizeTrend {
  operation: string;
  avg_prompt_bytes: number;
  call_count: number;
}

interface UsageReport {
  period: string;
  group_by: string;
  summary: UsageSummary;
  breakdown: UsageBreakdownEntry[];
  prompt_size_trend: PromptSizeTrend[];
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatDuration(ms: number): string {
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`;
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(1)}s`;
  return `${ms}ms`;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)}MB`;
  if (bytes >= 1_024) return `${(bytes / 1_024).toFixed(1)}KB`;
  return `${bytes}B`;
}

export function UsagePanel({ className = '' }: { className?: string }) {
  const { sendMessage } = useDashboard();
  const [report, setReport] = useState<UsageReport | null>(null);
  const [period, setPeriod] = useState<'day' | 'week'>('day');
  const [groupBy, setGroupBy] = useState<'agent' | 'operation'>('agent');
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const handler = (event: MessageEvent) => {
      const msg = event.data;
      if (msg.type === 'usageReport') {
        setReport(msg.report);
        setLoading(false);
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    sendMessage({ type: 'requestUsageReport', period, groupBy } as never);
  }, [period, groupBy, isOpen, sendMessage]);

  return (
    <div className={className}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-vscode-widget-bg/50 transition-colors border-b border-vscode-border"
        title="Token usage for governance AI calls. Tracks consumption patterns and detects prompt bloat."
      >
        <span className="text-xs text-vscode-muted">{isOpen ? '\u25BC' : '\u25B6'}</span>
        <span className="text-xs font-semibold flex-1 text-left">Token Usage</span>
        {report && (
          <span className="text-2xs px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-semibold">
            {formatTokens(report.summary.total_tokens)}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="px-3 py-2 space-y-3">
          {/* Controls */}
          <div className="flex items-center gap-2">
            <div className="flex rounded overflow-hidden border border-vscode-border">
              <button
                onClick={() => setPeriod('day')}
                className={`px-2 py-0.5 text-2xs font-medium transition-colors ${
                  period === 'day'
                    ? 'bg-blue-600 text-white'
                    : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
                }`}
              >
                Day
              </button>
              <button
                onClick={() => setPeriod('week')}
                className={`px-2 py-0.5 text-2xs font-medium transition-colors ${
                  period === 'week'
                    ? 'bg-blue-600 text-white'
                    : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
                }`}
              >
                Week
              </button>
            </div>
            <div className="flex rounded overflow-hidden border border-vscode-border">
              <button
                onClick={() => setGroupBy('agent')}
                className={`px-2 py-0.5 text-2xs font-medium transition-colors ${
                  groupBy === 'agent'
                    ? 'bg-blue-600 text-white'
                    : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
                }`}
              >
                By Agent
              </button>
              <button
                onClick={() => setGroupBy('operation')}
                className={`px-2 py-0.5 text-2xs font-medium transition-colors ${
                  groupBy === 'operation'
                    ? 'bg-blue-600 text-white'
                    : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
                }`}
              >
                By Operation
              </button>
            </div>
          </div>

          {loading && <div className="text-xs text-vscode-muted text-center py-2">Loading...</div>}

          {report && !loading && (
            <>
              {/* Summary stats */}
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-vscode-widget-bg/50 rounded px-2 py-1.5 text-center">
                  <div className="text-2xs text-vscode-muted">Calls</div>
                  <div className="text-sm font-semibold">{report.summary.call_count}</div>
                </div>
                <div className="bg-vscode-widget-bg/50 rounded px-2 py-1.5 text-center">
                  <div className="text-2xs text-vscode-muted">Tokens</div>
                  <div className="text-sm font-semibold">
                    {formatTokens(report.summary.total_tokens)}
                  </div>
                </div>
                <div className="bg-vscode-widget-bg/50 rounded px-2 py-1.5 text-center">
                  <div className="text-2xs text-vscode-muted">Duration</div>
                  <div className="text-sm font-semibold">
                    {formatDuration(report.summary.total_duration_ms)}
                  </div>
                </div>
              </div>

              {/* Breakdown table */}
              {report.breakdown.length > 0 && (
                <div>
                  <div className="text-2xs text-vscode-muted uppercase tracking-wider mb-1">
                    Breakdown by {groupBy}
                  </div>
                  <table className="w-full text-2xs">
                    <thead>
                      <tr className="text-vscode-muted border-b border-vscode-border">
                        <th className="text-left py-1 pr-2">
                          {groupBy === 'agent' ? 'Agent' : 'Operation'}
                        </th>
                        <th className="text-right py-1 px-1">Calls</th>
                        <th className="text-right py-1 px-1">In</th>
                        <th className="text-right py-1 px-1">Out</th>
                        <th className="text-right py-1 pl-1">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.breakdown.map((row, i) => (
                        <tr key={i} className="border-b border-vscode-border/50">
                          <td className="py-1 pr-2 font-medium truncate max-w-[120px]">
                            {row.agent || row.operation || 'unknown'}
                          </td>
                          <td className="text-right py-1 px-1 text-vscode-muted">
                            {row.call_count}
                          </td>
                          <td className="text-right py-1 px-1">{formatTokens(row.input_tokens)}</td>
                          <td className="text-right py-1 px-1">
                            {formatTokens(row.output_tokens)}
                          </td>
                          <td className="text-right py-1 pl-1 text-vscode-muted">
                            {formatDuration(row.duration_ms)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Prompt size trend */}
              {report.prompt_size_trend.length > 0 && (
                <div>
                  <div className="text-2xs text-vscode-muted uppercase tracking-wider mb-1">
                    Prompt Size by Operation
                  </div>
                  <div className="space-y-1">
                    {report.prompt_size_trend.map((entry, i) => {
                      const maxBytes = Math.max(
                        ...report.prompt_size_trend.map((e) => e.avg_prompt_bytes),
                        1,
                      );
                      const pct = (entry.avg_prompt_bytes / maxBytes) * 100;
                      return (
                        <div key={i} className="flex items-center gap-2">
                          <span className="text-2xs w-24 truncate" title={entry.operation}>
                            {entry.operation}
                          </span>
                          <div className="flex-1 h-2 bg-vscode-widget-bg rounded overflow-hidden">
                            <div
                              className="h-full bg-blue-500/60 rounded"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="text-2xs text-vscode-muted w-12 text-right">
                            {formatBytes(entry.avg_prompt_bytes)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {report.breakdown.length === 0 && (
                <div className="text-xs text-vscode-muted text-center py-2 italic">
                  No usage data for this period
                </div>
              )}
            </>
          )}

          {!report && !loading && (
            <div className="text-xs text-vscode-muted text-center py-2 italic">
              No usage data available
            </div>
          )}
        </div>
      )}
    </div>
  );
}
