import { useState, useEffect } from 'react';
import { useDashboard } from '../context/DashboardContext';
import type { ProjectConfig, QualityGatesConfig, ContextReinforcementConfig } from '../types';
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

  const updateContextReinforcement = (updates: Partial<ContextReinforcementConfig>) => {
    const current = draftConfig.settings.contextReinforcement ?? {
      enabled: true,
      toolCallThreshold: 8,
      maxTokensPerInjection: 400,
      debounceSeconds: 30,
      maxInjectionsPerSession: 10,
      jaccardThreshold: 0.15,
      postCompactionReinject: true,
      routerAutoRegenerate: true,
      sessionContextEnabled: true,
      sessionContextDebounceSeconds: 60,
      maxDiscoveriesPerSession: 10,
      refreshInterval: 5,
      distillationModel: 'haiku',
    };
    setDraftConfig((prev) =>
      prev
        ? {
            ...prev,
            settings: {
              ...prev.settings,
              contextReinforcement: { ...current, ...updates },
            },
          }
        : null,
    );
    setHasChanges(true);
  };

  const cr = draftConfig.settings.contextReinforcement ?? {
    enabled: true,
    toolCallThreshold: 8,
    maxTokensPerInjection: 400,
    debounceSeconds: 30,
    maxInjectionsPerSession: 10,
    jaccardThreshold: 0.15,
    postCompactionReinject: true,
    routerAutoRegenerate: true,
    sessionContextEnabled: true,
    sessionContextDebounceSeconds: 60,
    maxDiscoveriesPerSession: 10,
    refreshInterval: 5,
    distillationModel: 'haiku',
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

          {/* Context Reinforcement */}
          <div className="space-y-3">
            <h3 className="font-medium">Context Reinforcement</h3>
            <p className="text-xs text-vscode-muted">
              Prevents context drift in long sessions by injecting relevant reminders
            </p>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={cr.enabled}
                onChange={() => updateContextReinforcement({ enabled: !cr.enabled })}
                className="mt-1"
              />
              <div>
                <span>Enable Context Reinforcement</span>
                <p className="text-xs text-vscode-muted">
                  Inject context reminders during Write/Edit/Bash/Task operations
                </p>
              </div>
            </label>

            {cr.enabled && (
              <div className="space-y-4 pl-6 border-l-2 border-vscode-border ml-1">
                <div>
                  <label className="text-sm">Tool Call Threshold</label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="3"
                      max="25"
                      value={cr.toolCallThreshold}
                      onChange={(e) =>
                        updateContextReinforcement({
                          toolCallThreshold: Number(e.target.value),
                        })
                      }
                      className="flex-1"
                    />
                    <span className="w-8 text-right font-mono text-sm">{cr.toolCallThreshold}</span>
                  </div>
                  <p className="text-xs text-vscode-muted">
                    Calls before reinforcement activates (default: 8)
                  </p>
                </div>

                <div>
                  <label className="text-sm">Max Tokens Per Injection</label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="100"
                      max="800"
                      step="50"
                      value={cr.maxTokensPerInjection}
                      onChange={(e) =>
                        updateContextReinforcement({
                          maxTokensPerInjection: Number(e.target.value),
                        })
                      }
                      className="flex-1"
                    />
                    <span className="w-12 text-right font-mono text-sm">
                      {cr.maxTokensPerInjection}
                    </span>
                  </div>
                  <p className="text-xs text-vscode-muted">
                    Token budget per injection (default: 400)
                  </p>
                </div>

                <div>
                  <label className="text-sm">Debounce (seconds)</label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="10"
                      max="120"
                      step="5"
                      value={cr.debounceSeconds}
                      onChange={(e) =>
                        updateContextReinforcement({
                          debounceSeconds: Number(e.target.value),
                        })
                      }
                      className="flex-1"
                    />
                    <span className="w-12 text-right font-mono text-sm">{cr.debounceSeconds}s</span>
                  </div>
                  <p className="text-xs text-vscode-muted">
                    Minimum gap between same-route injections (default: 30s)
                  </p>
                </div>

                <div>
                  <label className="text-sm">Max Injections Per Session</label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="3"
                      max="30"
                      value={cr.maxInjectionsPerSession}
                      onChange={(e) =>
                        updateContextReinforcement({
                          maxInjectionsPerSession: Number(e.target.value),
                        })
                      }
                      className="flex-1"
                    />
                    <span className="w-8 text-right font-mono text-sm">
                      {cr.maxInjectionsPerSession}
                    </span>
                  </div>
                  <p className="text-xs text-vscode-muted">
                    Session-wide injection cap (default: 10)
                  </p>
                </div>

                <div>
                  <label className="text-sm">Jaccard Threshold</label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="5"
                      max="50"
                      step="5"
                      value={Math.round(cr.jaccardThreshold * 100)}
                      onChange={(e) =>
                        updateContextReinforcement({
                          jaccardThreshold: Number(e.target.value) / 100,
                        })
                      }
                      className="flex-1"
                    />
                    <span className="w-12 text-right font-mono text-sm">
                      {cr.jaccardThreshold.toFixed(2)}
                    </span>
                  </div>
                  <p className="text-xs text-vscode-muted">
                    Keyword match sensitivity (default: 0.15)
                  </p>
                </div>

                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={cr.postCompactionReinject}
                    onChange={() =>
                      updateContextReinforcement({
                        postCompactionReinject: !cr.postCompactionReinject,
                      })
                    }
                    className="mt-1"
                  />
                  <div>
                    <span className="text-sm">Post-Compaction Reinject</span>
                    <p className="text-xs text-vscode-muted">
                      Re-inject vision context after context compaction
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={cr.routerAutoRegenerate}
                    onChange={() =>
                      updateContextReinforcement({
                        routerAutoRegenerate: !cr.routerAutoRegenerate,
                      })
                    }
                    className="mt-1"
                  />
                  <div>
                    <span className="text-sm">Auto-Regenerate Router</span>
                    <p className="text-xs text-vscode-muted">
                      Regenerate context router when KG changes
                    </p>
                  </div>
                </label>

                <div className="mt-4 pt-4 border-t border-vscode-border">
                  <h4 className="text-sm font-medium mb-3">Session Context Distillation</h4>
                  <p className="text-xs text-vscode-muted mb-3">
                    Distills the original prompt into key points and tracks milestones during work
                  </p>

                  <label className="flex items-start gap-3 cursor-pointer mb-3">
                    <input
                      type="checkbox"
                      checked={cr.sessionContextEnabled}
                      onChange={() =>
                        updateContextReinforcement({
                          sessionContextEnabled: !cr.sessionContextEnabled,
                        })
                      }
                      className="mt-1"
                    />
                    <div>
                      <span className="text-sm">Enable Session Context</span>
                      <p className="text-xs text-vscode-muted">
                        Distill and re-inject the starting prompt as goals evolve
                      </p>
                    </div>
                  </label>

                  {cr.sessionContextEnabled && (
                    <div className="space-y-4 pl-4">
                      <div>
                        <label className="text-sm">Session Context Debounce (seconds)</label>
                        <div className="flex items-center gap-4">
                          <input
                            type="range"
                            min="30"
                            max="180"
                            step="10"
                            value={cr.sessionContextDebounceSeconds}
                            onChange={(e) =>
                              updateContextReinforcement({
                                sessionContextDebounceSeconds: Number(e.target.value),
                              })
                            }
                            className="flex-1"
                          />
                          <span className="w-12 text-right font-mono text-sm">
                            {cr.sessionContextDebounceSeconds}s
                          </span>
                        </div>
                        <p className="text-xs text-vscode-muted">
                          Minimum gap between session context injections (default: 60s)
                        </p>
                      </div>

                      <div>
                        <label className="text-sm">Max Discoveries Per Session</label>
                        <div className="flex items-center gap-4">
                          <input
                            type="range"
                            min="3"
                            max="20"
                            value={cr.maxDiscoveriesPerSession}
                            onChange={(e) =>
                              updateContextReinforcement({
                                maxDiscoveriesPerSession: Number(e.target.value),
                              })
                            }
                            className="flex-1"
                          />
                          <span className="w-8 text-right font-mono text-sm">
                            {cr.maxDiscoveriesPerSession}
                          </span>
                        </div>
                        <p className="text-xs text-vscode-muted">
                          Cap on milestones/findings tracked per session (default: 10)
                        </p>
                      </div>

                      <div>
                        <label className="text-sm">Refresh Interval</label>
                        <div className="flex items-center gap-4">
                          <input
                            type="range"
                            min="3"
                            max="15"
                            value={cr.refreshInterval}
                            onChange={(e) =>
                              updateContextReinforcement({
                                refreshInterval: Number(e.target.value),
                              })
                            }
                            className="flex-1"
                          />
                          <span className="w-8 text-right font-mono text-sm">
                            {cr.refreshInterval}
                          </span>
                        </div>
                        <p className="text-xs text-vscode-muted">
                          Re-distill context every N injections (default: 5)
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
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
