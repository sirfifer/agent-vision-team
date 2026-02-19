import { useState, useEffect } from 'react';
import { useDashboard } from '../context/DashboardContext';
import type { ProjectConfig, QualityGatesConfig } from '../types';
import { WarningDialog } from './ui/WarningDialog';

type WarningType = 'mockTests' | 'mockTestsForCostlyOps' | null;

const WARNINGS: Record<
  Exclude<WarningType, null>,
  { title: string; message: string; severity: 'warning' | 'danger' }
> = {
  mockTests: {
    title: 'Enable Mock Tests?',
    message:
      'Mocking all tests significantly reduces the value of AI-assisted development. Real tests catch real bugs that mocks hide. We strongly recommend leaving this OFF.',
    severity: 'danger',
  },
  mockTestsForCostlyOps: {
    title: 'Disable Mock Tests for Costly Operations?',
    message:
      'Disabling this means tests will make real API calls, database connections, and other operations that may incur costs or rate-limiting.',
    severity: 'warning',
  },
};

export function SettingsPanel() {
  const { showSettings, setShowSettings, projectConfig, sendMessage } = useDashboard();
  const [draftConfig, setDraftConfig] = useState<ProjectConfig | null>(null);
  const [pendingWarning, setPendingWarning] = useState<WarningType>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize draft config when panel opens
  useEffect(() => {
    if (showSettings && projectConfig) {
      setDraftConfig(projectConfig);
      setHasChanges(false);
    }
  }, [showSettings, projectConfig]);

  if (!showSettings || !draftConfig) {
    return null;
  }

  const updateSettings = (updates: Partial<ProjectConfig['settings']>) => {
    setDraftConfig((prev) =>
      prev
        ? {
            ...prev,
            settings: { ...prev.settings, ...updates },
          }
        : null,
    );
    setHasChanges(true);
  };

  const handleMockTestsToggle = () => {
    if (!draftConfig.settings.mockTests) {
      setPendingWarning('mockTests');
    } else {
      updateSettings({ mockTests: false });
    }
  };

  const handleMockCostlyOpsToggle = () => {
    if (draftConfig.settings.mockTestsForCostlyOps) {
      setPendingWarning('mockTestsForCostlyOps');
    } else {
      updateSettings({ mockTestsForCostlyOps: true });
    }
  };

  const handleWarningConfirm = () => {
    if (pendingWarning === 'mockTests') {
      updateSettings({ mockTests: true });
    } else if (pendingWarning === 'mockTestsForCostlyOps') {
      updateSettings({ mockTestsForCostlyOps: false });
    }
    setPendingWarning(null);
  };

  const handleGateToggle = (gate: keyof QualityGatesConfig) => {
    updateSettings({
      qualityGates: {
        ...draftConfig.settings.qualityGates,
        [gate]: !draftConfig.settings.qualityGates[gate],
      },
    });
  };

  const handleSave = () => {
    sendMessage({ type: 'saveProjectConfig', config: draftConfig });
    setHasChanges(false);
    setShowSettings(false);
  };

  const handleClose = () => {
    if (hasChanges) {
      // Could show a confirmation dialog here
    }
    setShowSettings(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
      <div className="w-full max-w-md bg-vscode-bg border-l border-vscode-border shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-vscode-border">
          <h2 className="text-lg font-semibold">Settings</h2>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-vscode-widget-bg rounded transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Coverage threshold */}
          <div>
            <h3 className="font-medium mb-2">Coverage Threshold</h3>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="0"
                max="100"
                value={draftConfig.settings.coverageThreshold}
                onChange={(e) => updateSettings({ coverageThreshold: Number(e.target.value) })}
                className="flex-1"
              />
              <span className="w-12 text-right font-mono">
                {draftConfig.settings.coverageThreshold}%
              </span>
            </div>
          </div>

          {/* Test Mocking */}
          <div className="space-y-3">
            <h3 className="font-medium">Test Mocking</h3>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={draftConfig.settings.mockTests}
                onChange={handleMockTestsToggle}
                className="mt-1"
              />
              <div>
                <div className="flex items-center gap-2">
                  <span>Mock All Tests</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
                    Not Recommended
                  </span>
                </div>
                <p className="text-xs text-vscode-muted">Disables real test execution</p>
              </div>
            </label>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={draftConfig.settings.mockTestsForCostlyOps}
                onChange={handleMockCostlyOpsToggle}
                className="mt-1"
              />
              <div>
                <div className="flex items-center gap-2">
                  <span>Mock Costly Operations</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-tier-quality/20 text-tier-quality">
                    Recommended
                  </span>
                </div>
                <p className="text-xs text-vscode-muted">Mock API calls and external services</p>
              </div>
            </label>
          </div>

          {/* Governance */}
          <div className="space-y-3">
            <h3 className="font-medium">Governance</h3>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={draftConfig.settings.autoGovernance}
                onChange={() =>
                  updateSettings({ autoGovernance: !draftConfig.settings.autoGovernance })
                }
                className="mt-1"
              />
              <div>
                <span>Auto-Governance</span>
                <p className="text-xs text-vscode-muted">
                  Require governance checkpoints for agent decisions
                </p>
              </div>
            </label>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={draftConfig.settings.kgAutoCuration}
                onChange={() =>
                  updateSettings({ kgAutoCuration: !draftConfig.settings.kgAutoCuration })
                }
                className="mt-1"
              />
              <div>
                <span>KG Auto-Curation</span>
                <p className="text-xs text-vscode-muted">Run kg-librarian after task completion</p>
              </div>
            </label>
          </div>

          {/* Quality Gates */}
          <div>
            <h3 className="font-medium mb-3">Quality Gates</h3>
            <div className="grid grid-cols-2 gap-2">
              {(Object.keys(draftConfig.settings.qualityGates) as (keyof QualityGatesConfig)[]).map(
                (gate) => (
                  <label key={gate} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={draftConfig.settings.qualityGates[gate]}
                      onChange={() => handleGateToggle(gate)}
                    />
                    <span className="capitalize text-sm">{gate}</span>
                  </label>
                ),
              )}
            </div>
          </div>

          {/* Re-run wizard */}
          <div className="pt-4 border-t border-vscode-border">
            <button
              onClick={() => {
                setShowSettings(false);
                // Trigger wizard re-open (handled by parent)
              }}
              className="text-sm text-vscode-muted hover:text-vscode-fg transition-colors"
            >
              Re-run Setup Wizard...
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-vscode-border">
          <button
            onClick={handleClose}
            className="px-4 py-2 rounded bg-vscode-btn2-bg text-vscode-btn2-fg hover:opacity-80 transition-opacity"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges}
            className="px-4 py-2 rounded bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save Changes
          </button>
        </div>
      </div>

      {/* Warning Dialog */}
      {pendingWarning && (
        <WarningDialog
          title={WARNINGS[pendingWarning].title}
          message={WARNINGS[pendingWarning].message}
          severity={WARNINGS[pendingWarning].severity}
          onConfirm={handleWarningConfirm}
          onCancel={() => setPendingWarning(null)}
        />
      )}
    </div>
  );
}
