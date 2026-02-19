import { useState, useMemo } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { ReviewItemCard } from './ReviewItemCard';
import { AddItemForm } from './AddItemForm';
import type { BootstrapReviewItem } from '../../types';

type TierTab = 'vision' | 'architecture' | 'quality';

const TIER_LABELS: Record<TierTab, string> = {
  vision: 'Vision',
  architecture: 'Architecture',
  quality: 'Quality',
};

const TIER_COLORS: Record<TierTab, string> = {
  vision: 'text-tier-vision',
  architecture: 'text-tier-architecture',
  quality: 'text-tier-quality',
};

export function BootstrapReviewPanel() {
  const { bootstrapReviewItems, bootstrapReviewResult, sendMessage, setShowBootstrap } =
    useDashboard();
  const [items, setItems] = useState<BootstrapReviewItem[]>(bootstrapReviewItems || []);
  const [activeTab, setActiveTab] = useState<TierTab>('vision');
  const [finalizing, setFinalizing] = useState(false);
  const [isAddingItem, setIsAddingItem] = useState(false);

  // Group items by tier
  const grouped = useMemo(() => {
    const groups: Record<TierTab, BootstrapReviewItem[]> = {
      vision: [],
      architecture: [],
      quality: [],
    };
    for (const item of items) {
      if (item.tier in groups) {
        groups[item.tier].push(item);
      }
    }
    return groups;
  }, [items]);

  // Count stats
  const stats = useMemo(() => {
    let reviewed = 0;
    let pending = 0;
    let approved = 0;
    let rejected = 0;
    let edited = 0;
    for (const item of items) {
      if (item.status === 'pending') pending++;
      else {
        reviewed++;
        if (item.status === 'approved') approved++;
        else if (item.status === 'rejected') rejected++;
        else if (item.status === 'edited') edited++;
      }
    }
    return { reviewed, pending, approved, rejected, edited, total: items.length };
  }, [items]);

  const updateItem = (id: string, updates: Partial<BootstrapReviewItem>) => {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...updates } : item)));
  };

  const handleApprove = (id: string) => {
    updateItem(id, { status: 'approved' });
  };

  const handleReject = (id: string) => {
    updateItem(id, { status: 'rejected' });
  };

  const handleEdit = (id: string, observations: string[]) => {
    updateItem(id, { status: 'edited', editedObservations: observations });
  };

  const handleApproveAll = () => {
    setItems((prev) =>
      prev.map((item) =>
        item.tier === activeTab && item.status === 'pending'
          ? { ...item, status: 'approved' as const }
          : item,
      ),
    );
  };

  const handleRejectAll = () => {
    setItems((prev) =>
      prev.map((item) =>
        item.tier === activeTab && item.status === 'pending'
          ? { ...item, status: 'rejected' as const }
          : item,
      ),
    );
  };

  const handleAddItem = (item: BootstrapReviewItem) => {
    setItems((prev) => [...prev, item]);
    setIsAddingItem(false);
  };

  const handleFinalize = () => {
    setFinalizing(true);
    sendMessage({ type: 'finalizeBootstrapReview', items });
  };

  // Show finalization result
  if (bootstrapReviewResult) {
    return (
      <div className="px-6 py-8 space-y-4 text-center">
        {bootstrapReviewResult.success ? (
          <>
            <div className="w-12 h-12 mx-auto rounded-full bg-green-500/15 flex items-center justify-center">
              <svg
                className="w-6 h-6 text-green-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <div>
              <div className="text-sm font-semibold">Review Finalized</div>
              <div className="text-xs text-vscode-muted mt-2 space-y-1">
                <div>
                  <span className="text-green-400 font-medium">
                    {bootstrapReviewResult.approved}
                  </span>{' '}
                  approved
                </div>
                {bootstrapReviewResult.edited > 0 && (
                  <div>
                    <span className="text-blue-400 font-medium">
                      {bootstrapReviewResult.edited}
                    </span>{' '}
                    edited
                  </div>
                )}
                {bootstrapReviewResult.rejected > 0 && (
                  <div>
                    <span className="text-red-400 font-medium">
                      {bootstrapReviewResult.rejected}
                    </span>{' '}
                    removed from Knowledge Graph
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="w-12 h-12 mx-auto rounded-full bg-red-500/15 flex items-center justify-center">
              <svg
                className="w-6 h-6 text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <div>
              <div className="text-sm font-semibold text-red-400">Finalization Failed</div>
              {bootstrapReviewResult.errors.length > 0 && (
                <div className="text-xs text-vscode-muted mt-1">
                  {bootstrapReviewResult.errors[0]}
                </div>
              )}
            </div>
          </>
        )}
        <button
          onClick={() => setShowBootstrap(false)}
          className="px-4 py-2 text-sm rounded-lg bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity"
        >
          Close
        </button>
      </div>
    );
  }

  const currentItems = grouped[activeTab];
  const currentPending = currentItems.filter((i) => i.status === 'pending').length;
  const totalActionable = stats.approved + stats.edited + stats.rejected;

  return (
    <div className="flex flex-col" style={{ maxHeight: '70vh' }}>
      {/* Header */}
      <div className="px-5 py-3 border-b border-vscode-border">
        <div className="text-xs text-vscode-muted mb-2">
          Review each discovery before it becomes permanent in the Knowledge Graph. You can also add
          items manually.
        </div>

        {/* Tab bar - always show all three tiers */}
        <div className="flex items-center gap-1">
          {(Object.keys(TIER_LABELS) as TierTab[]).map((tier) => {
            const count = grouped[tier].length;
            const isActive = activeTab === tier;
            return (
              <button
                key={tier}
                onClick={() => {
                  setActiveTab(tier);
                  setIsAddingItem(false);
                }}
                className={`px-3 py-1.5 text-xs rounded-t transition-colors ${
                  isActive
                    ? 'bg-vscode-bg border border-vscode-border border-b-transparent font-semibold text-vscode-fg -mb-px'
                    : 'text-vscode-muted hover:text-vscode-fg'
                }`}
              >
                <span className={isActive ? TIER_COLORS[tier] || '' : ''}>{TIER_LABELS[tier]}</span>
                <span className="ml-1.5 text-2xs opacity-70">({count})</span>
              </button>
            );
          })}

          <div className="flex-1" />

          {/* Progress indicator */}
          {stats.total > 0 && (
            <span className="text-2xs text-vscode-muted">
              Reviewed: {stats.reviewed}/{stats.total}
            </span>
          )}
        </div>
      </div>

      {/* Section header with bulk actions */}
      <div className="flex items-center justify-between px-5 py-2 bg-vscode-bg/50">
        <span className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">
          {TIER_LABELS[activeTab]} ({currentItems.length})
        </span>
        <div className="flex gap-1.5">
          {currentPending > 0 && (
            <>
              <button
                onClick={handleApproveAll}
                className="text-2xs px-2 py-0.5 rounded bg-green-500/15 text-green-400 hover:bg-green-500/25 transition-colors"
              >
                Approve All Pending
              </button>
              <button
                onClick={handleRejectAll}
                className="text-2xs px-2 py-0.5 rounded bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors"
              >
                Reject All Pending
              </button>
            </>
          )}
          {!isAddingItem && (
            <button
              onClick={() => setIsAddingItem(true)}
              className="text-2xs px-2 py-0.5 rounded bg-blue-500/15 text-blue-400 hover:bg-blue-500/25 transition-colors"
            >
              + Add Item
            </button>
          )}
        </div>
      </div>

      {/* Item list */}
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-2">
        {/* Add item form (shown at top when active) */}
        {isAddingItem && (
          <AddItemForm
            tier={activeTab}
            onAdd={handleAddItem}
            onCancel={() => setIsAddingItem(false)}
          />
        )}

        {currentItems.length === 0 && !isAddingItem ? (
          <div className="text-center py-8 space-y-3">
            <div className="text-xs text-vscode-muted italic">
              No {TIER_LABELS[activeTab].toLowerCase()} items were discovered by the bootstrap.
            </div>
            <button
              onClick={() => setIsAddingItem(true)}
              className="text-xs px-3 py-1.5 rounded bg-blue-500/15 text-blue-400 hover:bg-blue-500/25 transition-colors"
            >
              + Add {TIER_LABELS[activeTab]} Item
            </button>
          </div>
        ) : (
          currentItems.map((item) => (
            <ReviewItemCard
              key={item.id}
              item={item}
              onApprove={handleApprove}
              onReject={handleReject}
              onEdit={handleEdit}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-5 py-3 border-t border-vscode-border">
        <button
          onClick={() => setShowBootstrap(false)}
          className="px-3 py-1.5 text-xs rounded border border-vscode-border text-vscode-muted hover:text-vscode-fg hover:bg-vscode-bg transition-colors"
        >
          Cancel
        </button>

        <div className="flex items-center gap-3">
          {stats.pending > 0 && (
            <span className="text-2xs text-yellow-400">
              {stats.pending} item{stats.pending !== 1 ? 's' : ''} not yet reviewed
            </span>
          )}
          <button
            onClick={
              stats.total === 0 && totalActionable === 0
                ? () => setShowBootstrap(false)
                : handleFinalize
            }
            disabled={finalizing}
            className="px-4 py-1.5 text-xs font-semibold rounded bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {finalizing
              ? 'Finalizing...'
              : stats.total === 0 && totalActionable === 0
                ? 'Done'
                : `Finalize: Apply ${stats.approved + stats.edited} approved, remove ${stats.rejected}`}
          </button>
        </div>
      </div>
    </div>
  );
}
