import { useState } from 'react';
import { useDashboard } from '../../../context/DashboardContext';
import type { ProjectConfig } from '../../../types';

interface ArchitectureDocsStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

const TEMPLATE = `# [Document Title]

## Type
[standard | pattern | component]

## Description
[What this architectural element is and its purpose]

## Usage
[When and how to use this pattern/component/standard]

## Examples
\`\`\`typescript
// Example code showing proper usage
\`\`\`

## Related
- [Links to related architectural elements]
`;

export function ArchitectureDocsStep(_props: ArchitectureDocsStepProps) {
  const { architectureDocs, sendMessage } = useDashboard();
  const [newDocName, setNewDocName] = useState('');
  const [newDocContent, setNewDocContent] = useState(TEMPLATE);
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = () => {
    if (!newDocName.trim()) return;

    setIsCreating(true);
    sendMessage({
      type: 'createArchDoc',
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
        <h3 className="text-xl font-semibold mb-2">Architecture Documents</h3>
        <p className="text-vscode-muted">
          Architecture documents describe your project's patterns, components, and technical standards.
          The orchestrator can propose changes, but human approval is required.
        </p>
      </div>

      {/* Existing documents */}
      <div>
        <h4 className="font-medium mb-2">
          Existing Documents ({architectureDocs.length})
        </h4>
        {architectureDocs.length > 0 ? (
          <div className="space-y-2">
            {architectureDocs.map(doc => (
              <div
                key={doc.path}
                className="flex items-center gap-2 p-2 rounded bg-vscode-widget-bg border border-vscode-border"
              >
                <svg className="w-4 h-4 text-tier-architecture" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
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
            No architecture documents found. Create your first one below.
          </p>
        )}
      </div>

      {/* Create new document */}
      <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
        <h4 className="font-medium mb-3">Create New Architecture Document</h4>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">
              Document Name
            </label>
            <input
              type="text"
              value={newDocName}
              onChange={e => setNewDocName(e.target.value)}
              placeholder="e.g., service-registry-pattern"
              className="w-full px-3 py-2 rounded bg-vscode-input-bg border border-vscode-border text-vscode-fg placeholder:text-vscode-muted focus:outline-none focus:border-vscode-btn-bg"
            />
            <p className="text-xs text-vscode-muted mt-1">
              Will be saved as <code>.avt/architecture/{newDocName || '[name]'}.md</code>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Content
            </label>
            <textarea
              value={newDocContent}
              onChange={e => setNewDocContent(e.target.value)}
              rows={14}
              className="w-full px-3 py-2 rounded bg-vscode-input-bg border border-vscode-border text-vscode-fg font-mono text-sm focus:outline-none focus:border-vscode-btn-bg"
            />
          </div>

          <button
            onClick={handleCreate}
            disabled={!newDocName.trim() || isCreating}
            className="px-4 py-2 rounded bg-tier-architecture text-white hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreating ? 'Creating...' : 'Create Document'}
          </button>
        </div>
      </div>

      <div className="p-3 rounded bg-blue-500/10 border border-blue-500/30 text-sm">
        <strong>Tip:</strong> Architecture documents can be standards, patterns, or components.
        Set the <code>## Type</code> section to categorize them properly.
      </div>
    </div>
  );
}
