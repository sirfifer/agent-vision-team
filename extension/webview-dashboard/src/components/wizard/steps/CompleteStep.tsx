import { useDashboard } from '../../../context/DashboardContext';
import type { ProjectConfig } from '../../../types';

interface CompleteStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
  onComplete: () => void;
}

export function CompleteStep({ config, onComplete }: CompleteStepProps) {
  const { visionDocs, architectureDocs } = useDashboard();

  const enabledGates = Object.entries(config.settings.qualityGates)
    .filter(([, enabled]) => enabled)
    .map(([gate]) => gate);

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-tier-quality/20 mb-4">
          <svg className="w-8 h-8 text-tier-quality" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-2xl font-bold mb-2">Setup Complete!</h3>
        <p className="text-vscode-muted">
          Your project is now configured for AI-assisted development
        </p>
      </div>

      {/* Summary */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <h4 className="font-medium mb-2 flex items-center gap-2">
            <span className="text-tier-vision">Vision Documents</span>
          </h4>
          <p className="text-2xl font-bold">{visionDocs.length}</p>
          <p className="text-sm text-vscode-muted">
            {config.ingestion.lastVisionIngest
              ? `Last ingested: ${new Date(config.ingestion.lastVisionIngest).toLocaleDateString()}`
              : 'Not yet ingested'}
          </p>
        </div>

        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <h4 className="font-medium mb-2 flex items-center gap-2">
            <span className="text-tier-architecture">Architecture Documents</span>
          </h4>
          <p className="text-2xl font-bold">{architectureDocs.length}</p>
          <p className="text-sm text-vscode-muted">
            {config.ingestion.lastArchitectureIngest
              ? `Last ingested: ${new Date(config.ingestion.lastArchitectureIngest).toLocaleDateString()}`
              : 'Not yet ingested'}
          </p>
        </div>

        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <h4 className="font-medium mb-2">Languages</h4>
          <p className="text-2xl font-bold">{config.languages.length}</p>
          <p className="text-sm text-vscode-muted">
            {config.languages.length > 0 ? config.languages.join(', ') : 'None configured'}
          </p>
        </div>

        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <h4 className="font-medium mb-2">Coverage Threshold</h4>
          <p className="text-2xl font-bold">{config.settings.coverageThreshold}%</p>
          <p className="text-sm text-vscode-muted">
            Minimum required test coverage
          </p>
        </div>

        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <h4 className="font-medium mb-2">Quality Gates</h4>
          <p className="text-2xl font-bold">{enabledGates.length}/5</p>
          <p className="text-sm text-vscode-muted">
            {enabledGates.join(', ') || 'None enabled'}
          </p>
        </div>

        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <h4 className="font-medium mb-2">Permissions</h4>
          <p className="text-2xl font-bold">{config.permissions.length}</p>
          <p className="text-sm text-vscode-muted">
            Claude Code allowed operations
          </p>
        </div>
      </div>

      {/* Settings summary */}
      <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
        <h4 className="font-medium mb-3">Settings</h4>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex items-center gap-2">
            <span className={config.settings.mockTests ? 'text-red-400' : 'text-tier-quality'}>
              {config.settings.mockTests ? '!' : ''}
            </span>
            <span>Mock Tests: {config.settings.mockTests ? 'ON' : 'OFF'}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={config.settings.mockTestsForCostlyOps ? 'text-tier-quality' : 'text-amber-400'}>
              {config.settings.mockTestsForCostlyOps ? '' : '!'}
            </span>
            <span>Mock Costly Ops: {config.settings.mockTestsForCostlyOps ? 'ON' : 'OFF'}</span>
          </div>
          <div>Auto-Governance: {config.settings.autoGovernance ? 'ON' : 'OFF'}</div>
          <div>KG Auto-Curation: {config.settings.kgAutoCuration ? 'ON' : 'OFF'}</div>
        </div>
      </div>

      {/* Warnings */}
      {(config.settings.mockTests || !config.settings.mockTestsForCostlyOps) && (
        <div className="p-4 rounded-lg border border-amber-500/50 bg-amber-500/10">
          <h4 className="font-medium text-amber-400 mb-2">Warnings</h4>
          <ul className="list-disc list-inside text-sm text-vscode-muted space-y-1">
            {config.settings.mockTests && (
              <li>Mock Tests is enabled - real test validation is disabled</li>
            )}
            {!config.settings.mockTestsForCostlyOps && (
              <li>Mock Costly Ops is disabled - tests may incur API costs</li>
            )}
          </ul>
        </div>
      )}

      <div className="p-4 rounded-lg border border-tier-quality/50 bg-tier-quality/10">
        <p className="text-sm">
          Click <strong>Complete Setup</strong> to save your configuration and start using
          the Collaborative Intelligence System. You can always adjust settings later
          using the gear icon in the dashboard.
        </p>
      </div>
    </div>
  );
}
