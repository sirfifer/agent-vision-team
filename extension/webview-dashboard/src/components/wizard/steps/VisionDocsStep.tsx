import { useDashboard } from '../../../context/DashboardContext';
import { useDocEditor } from '../../../hooks/useDocEditor';
import { DocEditorCard } from './DocEditorCard';
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

export function VisionDocsStep(_props: VisionDocsStepProps) {
  const { visionDocs, sendMessage, lastFormatResult } = useDashboard();

  const editor = useDocEditor({
    tier: 'vision',
    defaultName: 'vision',
    sendMessage,
    lastFormatResult,
    docCount: visionDocs.length,
  });

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-2">Vision Documents</h3>
        <p className="text-vscode-muted">
          Vision documents define your project's core principles and invariants. These are protected
          standards that AI agents cannot modify.
        </p>
      </div>

      {/* Existing documents */}
      <div>
        <h4 className="font-medium mb-2">Existing Documents ({visionDocs.length})</h4>
        {visionDocs.length > 0 ? (
          <div className="space-y-2">
            {visionDocs.map((doc) => (
              <div
                key={doc.path}
                className="flex items-center gap-2 p-2 rounded bg-vscode-widget-bg border border-vscode-border"
              >
                <svg
                  className="w-4 h-4 text-tier-vision"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <span className="flex-1">{doc.name}</span>
                {doc.title && <span className="text-sm text-vscode-muted">{doc.title}</span>}
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
      <DocEditorCard
        tier="vision"
        editor={editor}
        tierColorClass="bg-tier-vision"
        placeholderText={
          'Type, paste, or narrate your vision standards here.\n' +
          "Don't worry about formatting — just capture your ideas.\n\n" +
          'Examples: bullet points, stream of consciousness, pasted notes, etc.'
        }
      />

      <div className="p-3 rounded bg-blue-500/10 border border-blue-500/30 text-sm">
        <strong>Tip:</strong> Just dump your thoughts — bullet points, stream of consciousness,
        pasted text. The AI formatter will organize it into proper vision standards.
      </div>
    </div>
  );
}
