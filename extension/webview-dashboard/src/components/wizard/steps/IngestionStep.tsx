import { useState } from 'react';
import { useDashboard } from '../../../context/DashboardContext';
import type { ProjectConfig } from '../../../types';

interface IngestionStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export function IngestionStep({ config, updateConfig }: IngestionStepProps) {
  const { visionDocs, architectureDocs, lastIngestionResult, sendMessage } = useDashboard();
  const [isIngesting, setIsIngesting] = useState<'vision' | 'architecture' | null>(null);
  const [visionIngested, setVisionIngested] = useState(config.ingestion.lastVisionIngest !== null);
  const [archIngested, setArchIngested] = useState(config.ingestion.lastArchitectureIngest !== null);

  const handleIngestVision = () => {
    setIsIngesting('vision');
    sendMessage({ type: 'ingestDocs', tier: 'vision' });

    // Simulate completion (in real implementation, this would be handled by the message response)
    setTimeout(() => {
      setIsIngesting(null);
      setVisionIngested(true);
      updateConfig({
        ingestion: {
          ...config.ingestion,
          lastVisionIngest: new Date().toISOString(),
          visionDocCount: visionDocs.length,
        },
      });
    }, 2000);
  };

  const handleIngestArchitecture = () => {
    setIsIngesting('architecture');
    sendMessage({ type: 'ingestDocs', tier: 'architecture' });

    // Simulate completion
    setTimeout(() => {
      setIsIngesting(null);
      setArchIngested(true);
      updateConfig({
        ingestion: {
          ...config.ingestion,
          lastArchitectureIngest: new Date().toISOString(),
          architectureDocCount: architectureDocs.length,
        },
      });
    }, 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-2">Document Ingestion</h3>
        <p className="text-vscode-muted">
          Ingest your vision and architecture documents into the Knowledge Graph.
          This makes them searchable and accessible to AI agents.
        </p>
      </div>

      {/* Vision Documents */}
      <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="font-medium">Vision Documents</h4>
            <p className="text-sm text-vscode-muted">
              {visionDocs.length} document{visionDocs.length !== 1 ? 's' : ''} in .avt/vision/
            </p>
          </div>
          <div className="flex items-center gap-2">
            {visionIngested && (
              <span className="flex items-center gap-1 text-tier-quality text-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Ingested
              </span>
            )}
            <button
              onClick={handleIngestVision}
              disabled={visionDocs.length === 0 || isIngesting !== null}
              className="px-3 py-1.5 rounded bg-tier-vision text-white text-sm hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isIngesting === 'vision' ? (
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Ingesting...
                </span>
              ) : visionIngested ? (
                'Re-ingest'
              ) : (
                'Ingest Vision Docs'
              )}
            </button>
          </div>
        </div>

        {visionDocs.length > 0 ? (
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {visionDocs.map(doc => (
              <div key={doc.path} className="text-sm text-vscode-muted flex items-center gap-2">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {doc.name}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-amber-400 italic">
            No vision documents found. Go back to create some first.
          </p>
        )}
      </div>

      {/* Architecture Documents */}
      <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="font-medium">Architecture Documents</h4>
            <p className="text-sm text-vscode-muted">
              {architectureDocs.length} document{architectureDocs.length !== 1 ? 's' : ''} in .avt/architecture/
            </p>
          </div>
          <div className="flex items-center gap-2">
            {archIngested && (
              <span className="flex items-center gap-1 text-tier-quality text-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Ingested
              </span>
            )}
            <button
              onClick={handleIngestArchitecture}
              disabled={architectureDocs.length === 0 || isIngesting !== null}
              className="px-3 py-1.5 rounded bg-tier-architecture text-white text-sm hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isIngesting === 'architecture' ? (
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Ingesting...
                </span>
              ) : archIngested ? (
                'Re-ingest'
              ) : (
                'Ingest Architecture Docs'
              )}
            </button>
          </div>
        </div>

        {architectureDocs.length > 0 ? (
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {architectureDocs.map(doc => (
              <div key={doc.path} className="text-sm text-vscode-muted flex items-center gap-2">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                {doc.name}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-amber-400 italic">
            No architecture documents found. Go back to create some first.
          </p>
        )}
      </div>

      {/* Ingestion result */}
      {lastIngestionResult && (
        <div className={`p-4 rounded-lg border ${
          lastIngestionResult.errors.length > 0
            ? 'border-amber-500/50 bg-amber-500/10'
            : 'border-tier-quality/50 bg-tier-quality/10'
        }`}>
          <h4 className="font-medium mb-2">
            Last Ingestion: {lastIngestionResult.tier}
          </h4>
          <div className="text-sm space-y-1">
            <p>Ingested: {lastIngestionResult.ingested} entities</p>
            {lastIngestionResult.entities.length > 0 && (
              <p className="text-vscode-muted">
                Entities: {lastIngestionResult.entities.join(', ')}
              </p>
            )}
            {lastIngestionResult.errors.length > 0 && (
              <p className="text-amber-400">
                Errors: {lastIngestionResult.errors.join(', ')}
              </p>
            )}
          </div>
        </div>
      )}

      <div className="p-3 rounded bg-blue-500/10 border border-blue-500/30 text-sm">
        <strong>Note:</strong> Re-ingesting documents will replace existing entities in the Knowledge Graph.
        This is safe and recommended when documents have been updated.
      </div>
    </div>
  );
}
