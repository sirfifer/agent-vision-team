import { useState } from 'react';
import type { ProjectConfig, QualityGatesConfig } from '../../../types';
import { WarningDialog } from '../../ui/WarningDialog';

interface SettingsStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

type WarningType = 'mockTests' | 'mockTestsForCostlyOps' | null;

const WARNINGS: Record<Exclude<WarningType, null>, { title: string; message: string; severity: 'warning' | 'danger' }> = {
  mockTests: {
    title: 'Enable Mock Tests?',
    message: 'Mocking all tests significantly reduces the value of AI-assisted development. Real tests catch real bugs that mocks hide. We strongly recommend leaving this OFF unless you have a specific reason to enable it.',
    severity: 'danger',
  },
  mockTestsForCostlyOps: {
    title: 'Disable Mock Tests for Costly Operations?',
    message: 'Disabling this means tests will make real API calls, database connections, and other operations that may incur costs or rate-limiting. Only disable if you have dedicated test accounts and budgets.',
    severity: 'warning',
  },
};

export function SettingsStep({ config, updateSettings }: SettingsStepProps) {
  const [pendingWarning, setPendingWarning] = useState<WarningType>(null);

  const handleMockTestsToggle = () => {
    if (!config.settings.mockTests) {
      // Turning ON — show warning
      setPendingWarning('mockTests');
    } else {
      // Turning OFF — no warning needed
      updateSettings({ mockTests: false });
    }
  };

  const handleMockCostlyOpsToggle = () => {
    if (config.settings.mockTestsForCostlyOps) {
      // Turning OFF — show warning
      setPendingWarning('mockTestsForCostlyOps');
    } else {
      // Turning ON — no warning needed
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

  const handleWarningCancel = () => {
    setPendingWarning(null);
  };

  const handleGateToggle = (gate: keyof QualityGatesConfig) => {
    updateSettings({
      qualityGates: {
        ...config.settings.qualityGates,
        [gate]: !config.settings.qualityGates[gate],
      },
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-2">Project Settings</h3>
        <p className="text-vscode-muted">
          Configure how the AI agents behave during development.
        </p>
      </div>

      {/* Mock Tests Settings */}
      <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
        <h4 className="font-medium mb-4">Test Mocking</h4>

        <div className="space-y-4">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={config.settings.mockTests}
              onChange={handleMockTestsToggle}
              className="mt-1"
            />
            <div>
              <div className="font-medium">
                Mock All Tests
                <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
                  Not Recommended
                </span>
              </div>
              <p className="text-sm text-vscode-muted">
                Replace all test execution with mocks. This prevents real test validation
                and significantly reduces the value of AI-assisted development.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={config.settings.mockTestsForCostlyOps}
              onChange={handleMockCostlyOpsToggle}
              className="mt-1"
            />
            <div>
              <div className="font-medium">
                Mock Tests for Costly Operations
                <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-tier-quality/20 text-tier-quality">
                  Recommended
                </span>
              </div>
              <p className="text-sm text-vscode-muted">
                Mock operations that require API keys, make network calls, or incur costs.
                Tests still run but external dependencies are simulated.
              </p>
            </div>
          </label>
        </div>
      </div>

      {/* Governance Settings */}
      <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
        <h4 className="font-medium mb-4">Governance</h4>

        <div className="space-y-4">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={config.settings.autoGovernance}
              onChange={() => updateSettings({ autoGovernance: !config.settings.autoGovernance })}
              className="mt-1"
            />
            <div>
              <div className="font-medium">Auto-Governance</div>
              <p className="text-sm text-vscode-muted">
                Require governance checkpoints for significant agent decisions.
                The governance-reviewer agent will validate changes against standards.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={config.settings.kgAutoCuration}
              onChange={() => updateSettings({ kgAutoCuration: !config.settings.kgAutoCuration })}
              className="mt-1"
            />
            <div>
              <div className="font-medium">KG Auto-Curation</div>
              <p className="text-sm text-vscode-muted">
                Automatically run the kg-librarian agent after task completion to
                maintain and curate the Knowledge Graph.
              </p>
            </div>
          </label>
        </div>
      </div>

      {/* Quality Gates */}
      <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
        <h4 className="font-medium mb-4">Quality Gates</h4>
        <p className="text-sm text-vscode-muted mb-4">
          Select which quality gates must pass before code can be committed.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {(Object.keys(config.settings.qualityGates) as (keyof QualityGatesConfig)[]).map(gate => (
            <label key={gate} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.settings.qualityGates[gate]}
                onChange={() => handleGateToggle(gate)}
              />
              <span className="capitalize">{gate}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Warning Dialog */}
      {pendingWarning && (
        <WarningDialog
          title={WARNINGS[pendingWarning].title}
          message={WARNINGS[pendingWarning].message}
          severity={WARNINGS[pendingWarning].severity}
          onConfirm={handleWarningConfirm}
          onCancel={handleWarningCancel}
        />
      )}
    </div>
  );
}
