import { useState } from 'react';
import { useDashboard } from '../context/DashboardContext';
import type { GovernedTask, TaskReviewInfo, GovernedTaskStatus } from '../types';

const verdictDisplayLabels: Record<string, string> = {
  approved: 'approved',
  blocked: 'needs revision',
  needs_human_review: 'needs human review',
};

const statusConfig: Record<GovernedTaskStatus, { label: string; color: string; bgColor: string }> =
  {
    pending_review: {
      label: 'Pending Review',
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/20',
    },
    approved: { label: 'Approved', color: 'text-green-400', bgColor: 'bg-green-500/20' },
    blocked: { label: 'Needs Revision', color: 'text-red-400', bgColor: 'bg-red-500/20' },
    in_progress: { label: 'In Progress', color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
    completed: { label: 'Completed', color: 'text-vscode-muted', bgColor: 'bg-vscode-widget-bg' },
  };

function ReviewBadge({ review }: { review: TaskReviewInfo }) {
  const verdictColors: Record<string, string> = {
    pending: 'bg-yellow-500/20 text-yellow-400',
    approved: 'bg-green-500/20 text-green-400',
    blocked: 'bg-red-500/20 text-red-400',
    needs_human_review: 'bg-purple-500/20 text-purple-400',
  };

  return (
    <span
      className={`text-2xs px-1.5 py-0.5 rounded ${verdictColors[review.status] ?? 'bg-vscode-widget-bg text-vscode-muted'}`}
      title={review.guidance ? `${review.reviewType}: ${review.guidance}` : review.reviewType}
    >
      {review.reviewType}
    </span>
  );
}

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

function TaskCard({ task }: { task: GovernedTask }) {
  const [expanded, setExpanded] = useState(false);
  const config = statusConfig[task.status];

  return (
    <div className="border border-vscode-border rounded bg-vscode-widget-bg">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-3 py-2 hover:bg-vscode-widget-bg/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-vscode-muted">{expanded ? '\u25BC' : '\u25B6'}</span>
          <span
            className={`text-2xs px-1.5 py-0.5 rounded ${config.bgColor} ${config.color} font-medium`}
          >
            {config.label}
          </span>
          <span className="text-xs font-medium flex-1 truncate">{task.subject}</span>
          <span className="text-2xs text-vscode-muted shrink-0">
            {formatRelativeTime(task.createdAt)}
          </span>
        </div>
        {task.reviews.length > 0 && (
          <div className="flex gap-1 mt-1.5 ml-5">
            {task.reviews.map((r) => (
              <ReviewBadge key={r.id} review={r} />
            ))}
          </div>
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-1 border-t border-vscode-border space-y-2">
          <div className="text-2xs text-vscode-muted">
            <span className="font-medium">Task ID:</span> {task.implementationTaskId}
          </div>
          {task.reviews.map((r) => (
            <div
              key={r.id}
              className="text-2xs p-2 rounded bg-vscode-bg border border-vscode-border"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium">{r.reviewType} review</span>
                <span className="text-vscode-muted">({r.status})</span>
              </div>
              {r.verdict && (
                <div className="text-vscode-muted">
                  Verdict: {verdictDisplayLabels[r.verdict] ?? r.verdict}
                </div>
              )}
              {r.guidance && <div className="mt-1">{r.guidance}</div>}
              {r.completedAt && (
                <div className="text-vscode-muted mt-1">
                  Completed: {formatRelativeTime(r.completedAt)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

type StatusFilter = 'all' | 'pending_review' | 'approved' | 'blocked' | 'completed';

const filterConfig: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pending_review', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'blocked', label: 'Needs Revision' },
  { key: 'completed', label: 'Completed' },
];

export function TaskBoard({ className = '' }: { className?: string }) {
  const { data } = useDashboard();
  const { governedTasks, governanceStats } = data;
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const filteredTasks =
    statusFilter === 'all' ? governedTasks : governedTasks.filter((t) => t.status === statusFilter);

  const pendingCount = governedTasks.filter((t) => t.status === 'pending_review').length;
  const blockedCount = governedTasks.filter((t) => t.status === 'blocked').length;
  const approvedCount = governedTasks.filter((t) => t.status === 'approved').length;

  return (
    <div className={className}>
      <div className="px-3 py-2 border-b border-vscode-border">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">
            Governed Tasks
          </h2>
          {governanceStats.totalGovernedTasks > 0 && (
            <span className="text-2xs px-1.5 py-0.5 rounded-full bg-tier-architecture/20 text-tier-architecture font-semibold">
              {governanceStats.totalGovernedTasks}
            </span>
          )}
        </div>

        {/* Status filter tabs */}
        <div className="flex gap-1 mt-2 flex-wrap">
          {filterConfig.map((f) => (
            <button
              key={f.key}
              onClick={() => setStatusFilter(f.key)}
              className={`text-2xs px-1.5 py-0.5 rounded transition-colors ${
                statusFilter === f.key
                  ? 'bg-tier-quality text-white'
                  : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Summary stats */}
        {(governanceStats.totalDecisions > 0 || governedTasks.length > 0) && (
          <div className="flex gap-3 mt-1.5 text-2xs text-vscode-muted">
            {pendingCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
                {pendingCount} pending
              </span>
            )}
            {approvedCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                {approvedCount} approved
              </span>
            )}
            {blockedCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                {blockedCount} needs revision
              </span>
            )}
            {governanceStats.totalDecisions > 0 && (
              <span>{governanceStats.totalDecisions} decisions</span>
            )}
          </div>
        )}
      </div>

      <div className="p-2 space-y-2">
        {filteredTasks.length === 0 ? (
          <div className="px-3 py-8 text-xs text-vscode-muted text-center italic">
            {governedTasks.length === 0 ? (
              <>
                No governed tasks yet. Tasks created via{' '}
                <code className="text-2xs">create_governed_task()</code> will appear here.
              </>
            ) : (
              'No tasks match the current filter.'
            )}
          </div>
        ) : (
          filteredTasks.map((task) => <TaskCard key={task.id} task={task} />)
        )}
      </div>
    </div>
  );
}
