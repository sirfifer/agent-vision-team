import { useState } from 'react';
import { useDashboard } from '../../../context/DashboardContext';
import type { ProjectConfig } from '../../../types';

interface VisionDocsStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

const TEMPLATE = `# [Standard Name]

## Statement
[Clear, actionable statement of the standard]

## Rationale
[Why this standard exists and what problem it solves]

## Examples
- Compliant: [Example of code/behavior that follows this standard]
- Violation: [Example of code/behavior that violates this standard]
`;

export function VisionDocsStep(_props: VisionDocsStepProps) {
  const { visionDocs, sendMessage } = useDashboard();
  const [newDocName, setNewDocName] = useState('');
  const [newDocContent, setNewDocContent] = useState(TEMPLATE);
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = () => {
    if (!newDocName.trim()) return;

    setIsCreating(true);
    sendMessage({
      type: 'createVisionDoc',
      name: newDocName.trim(),
      content: newDocContent,
    });

    // Reset form after a brief delay
    setTimeout(() => {
      setNewDocName('');
      setNewDocContent(TEMPLATE);
      setIsCreating(false);
    }, 500);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-2">Vision Documents</h3>
        <p className="text-vscode-muted">
          Vision documents define your project's core principles and invariants.
          These are protected standards that AI agents cannot modify.
        </p>
      </div>

      {/* Existing documents */}
      <div>
        <h4 className="font-medium mb-2">
          Existing Documents ({visionDocs.length})
        </h4>
        {visionDocs.length > 0 ? (
          <div className="space-y-2">
            {visionDocs.map(doc => (
              <div
                key={doc.path}
                className="flex items-center gap-2 p-2 rounded bg-vscode-widget-bg border border-vscode-border"
              >
                <svg className="w-4 h-4 text-tier-vision" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="flex-1">{doc.name}</span>
                {doc.title && (
                  <span className="text-sm text-vscode-muted">{doc.title}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-vscode-muted italic">
            No vision documents found. Create your first one below.
          </p>
        )}
      </div>

      {/* Create new document */}
      <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
        <h4 className="font-medium mb-3">Create New Vision Document</h4>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">
              Document Name
            </label>
            <input
              type="text"
              value={newDocName}
              onChange={e => setNewDocName(e.target.value)}
              placeholder="e.g., dependency-injection"
              className="w-full px-3 py-2 rounded bg-vscode-input-bg border border-vscode-border text-vscode-fg placeholder:text-vscode-muted focus:outline-none focus:border-vscode-btn-bg"
            />
            <p className="text-xs text-vscode-muted mt-1">
              Will be saved as <code>.avt/vision/{newDocName || '[name]'}.md</code>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Content
            </label>
            <textarea
              value={newDocContent}
              onChange={e => setNewDocContent(e.target.value)}
              rows={12}
              className="w-full px-3 py-2 rounded bg-vscode-input-bg border border-vscode-border text-vscode-fg font-mono text-sm focus:outline-none focus:border-vscode-btn-bg"
            />
          </div>

          <button
            onClick={handleCreate}
            disabled={!newDocName.trim() || isCreating}
            className="px-4 py-2 rounded bg-tier-vision text-white hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreating ? 'Creating...' : 'Create Document'}
          </button>
        </div>
      </div>

      <div className="p-3 rounded bg-blue-500/10 border border-blue-500/30 text-sm">
        <strong>Tip:</strong> Vision standards should be high-level principles that rarely change.
        Examples: "All services use protocol-based dependency injection", "No singletons in production code".
      </div>
    </div>
  );
}
