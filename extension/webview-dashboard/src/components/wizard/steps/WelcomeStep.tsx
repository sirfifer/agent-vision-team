import type { ProjectConfig } from '../../../types';

interface WelcomeStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export function WelcomeStep(_props: WelcomeStepProps) {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-2xl font-bold mb-2">Welcome to the Collaborative Intelligence System</h3>
        <p className="text-vscode-muted">
          This wizard will help you configure your project for AI-assisted development
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">📚</span>
            <h4 className="font-semibold">Vision & Architecture Docs</h4>
          </div>
          <p className="text-sm text-vscode-muted">
            Define your project's core principles and architectural standards in markdown files.
            These become the source of truth for AI agents.
          </p>
        </div>

        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">🧠</span>
            <h4 className="font-semibold">Knowledge Graph</h4>
          </div>
          <p className="text-sm text-vscode-muted">
            Your documents are ingested into a searchable knowledge graph that agents
            query for context and constraints.
          </p>
        </div>

        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">✅</span>
            <h4 className="font-semibold">Quality Gates</h4>
          </div>
          <p className="text-sm text-vscode-muted">
            Configure automated quality checks (build, lint, test, coverage) that
            run before any code is committed.
          </p>
        </div>

        <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">🛡️</span>
            <h4 className="font-semibold">Governance</h4>
          </div>
          <p className="text-sm text-vscode-muted">
            The three-tier hierarchy (Vision {`>`} Architecture {`>`} Quality) ensures
            agents respect your project's standards.
          </p>
        </div>
      </div>

      <div className="p-4 rounded-lg border border-blue-500/30 bg-blue-500/10">
        <h4 className="font-semibold mb-2">What this wizard will configure:</h4>
        <ul className="list-disc list-inside space-y-1 text-sm text-vscode-muted">
          <li>Vision standards documents in <code className="bg-vscode-widget-bg px-1 rounded">.avt/vision/</code></li>
          <li>Architecture documents in <code className="bg-vscode-widget-bg px-1 rounded">.avt/architecture/</code></li>
          <li>Quality commands (test, lint, build) for your languages</li>
          <li>Claude Code permissions for autonomous operation</li>
          <li>Settings for mock tests, governance, and coverage thresholds</li>
          <li>Knowledge Graph ingestion of your documents</li>
        </ul>
      </div>

      <p className="text-center text-sm text-vscode-muted">
        Click <strong>Get Started</strong> to begin configuring your project.
        You can skip steps and come back later.
      </p>
    </div>
  );
}
