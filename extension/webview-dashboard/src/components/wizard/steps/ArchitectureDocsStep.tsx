import { useDashboard } from '../../../context/DashboardContext';
import { useDocEditor } from '../../../hooks/useDocEditor';
import { DocEditorCard } from './DocEditorCard';
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

export function ArchitectureDocsStep(_props: ArchitectureDocsStepProps) {
  const { architectureDocs, sendMessage, lastFormatResult } = useDashboard();

  const editor = useDocEditor({
    tier: 'architecture',
    defaultName: 'architecture',
    sendMessage,
    lastFormatResult,
    docCount: architectureDocs.length,
  });

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-2">Architecture Documents</h3>
        <p className="text-vscode-muted">
          Architecture documents describe your project's patterns, components, and technical
          standards. The orchestrator can propose changes, but human approval is required.
        </p>
      </div>

      {/* Existing documents */}
      <div>
        <h4 className="font-medium mb-2">Existing Documents ({architectureDocs.length})</h4>
        {architectureDocs.length > 0 ? (
          <div className="space-y-2">
            {architectureDocs.map((doc) => (
              <div
                key={doc.path}
                className="flex items-center gap-2 p-2 rounded bg-vscode-widget-bg border border-vscode-border"
              >
                <svg
                  className="w-4 h-4 text-tier-architecture"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                  />
                </svg>
                <span className="flex-1">{doc.name}</span>
                {doc.title && <span className="text-sm text-vscode-muted">{doc.title}</span>}
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
      <DocEditorCard
        tier="architecture"
        editor={editor}
        tierColorClass="bg-tier-architecture"
        placeholderText={
          'Type, paste, or narrate your architecture decisions here.\n' +
          "Don't worry about formatting — just capture your ideas.\n\n" +
          'Examples: patterns used, component descriptions, technical standards, design decisions, etc.'
        }
      />

      <div className="p-3 rounded bg-blue-500/10 border border-blue-500/30 text-sm">
        <strong>Tip:</strong> Just dump your thoughts — patterns, component descriptions, technical
        decisions. The AI formatter will organize it into a proper architecture document.
      </div>
    </div>
  );
}
