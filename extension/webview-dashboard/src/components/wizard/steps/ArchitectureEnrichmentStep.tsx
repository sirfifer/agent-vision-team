import { useState, useCallback, useEffect } from 'react';
import { useDashboard } from '../../../context/DashboardContext';
import type {
  ProjectConfig,
  EnrichmentEntityStatus,
  EnrichmentValidationResult,
  EntityMetadataSuggestion,
} from '../../../types';

interface ArchitectureEnrichmentStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

interface EntityEditState {
  intent: string;
  metrics: string[];
  visionAlignments: string[];
}

export function ArchitectureEnrichmentStep({ config, onSkip }: ArchitectureEnrichmentStepProps) {
  const { sendMessage, enrichmentResult, entitySuggestions } = useDashboard();

  const [isValidating, setIsValidating] = useState(false);
  const [expandedEntity, setExpandedEntity] = useState<string | null>(null);
  const [editStates, setEditStates] = useState<Record<string, EntityEditState>>({});
  const [suggestingFor, setSuggestingFor] = useState<string | null>(null);
  const [savingFor, setSavingFor] = useState<string | null>(null);

  // Trigger validation on mount if architecture was ingested
  useEffect(() => {
    if (!enrichmentResult && config.ingestion.lastArchitectureIngest) {
      handleValidate();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleValidate = useCallback(() => {
    setIsValidating(true);
    sendMessage({ type: 'validateEnrichment' });
    setTimeout(() => setIsValidating(false), 2000);
  }, [sendMessage]);

  const handleSuggest = useCallback((entity: EnrichmentEntityStatus) => {
    setSuggestingFor(entity.name);
    const requestId = `suggest-${entity.name}-${Date.now()}`;
    sendMessage({
      type: 'suggestEntityMetadata',
      entityName: entity.name,
      existingObservations: entity.existingObservations,
      requestId,
    });
  }, [sendMessage]);

  const handleSave = useCallback((entityName: string) => {
    const state = editStates[entityName];
    if (!state) return;

    setSavingFor(entityName);
    sendMessage({
      type: 'saveEntityMetadata',
      entityName,
      intent: state.intent,
      metrics: state.metrics,
      visionAlignments: state.visionAlignments,
    });
    setTimeout(() => {
      setSavingFor(null);
      handleValidate();
    }, 1500);
  }, [editStates, sendMessage, handleValidate]);

  // Apply suggestion to edit state
  const applySuggestion = useCallback((entityName: string, suggestion: EntityMetadataSuggestion) => {
    setEditStates(prev => ({
      ...prev,
      [entityName]: {
        intent: suggestion.intent,
        metrics: suggestion.suggestedMetrics.map(m => `${m.name}|${m.criteria}|${m.baseline}`),
        visionAlignments: suggestion.visionAlignments.map(v => `${v.visionStandard}|${v.explanation}`),
      },
    }));
    setSuggestingFor(null);
  }, []);

  // Watch for suggestion responses
  useEffect(() => {
    if (suggestingFor && entitySuggestions[suggestingFor]) {
      applySuggestion(suggestingFor, entitySuggestions[suggestingFor]);
    }
  }, [entitySuggestions, suggestingFor, applySuggestion]);

  const updateEditState = useCallback((entityName: string, field: keyof EntityEditState, value: string | string[]) => {
    setEditStates(prev => ({
      ...prev,
      [entityName]: {
        ...prev[entityName] || { intent: '', metrics: [], visionAlignments: [] },
        [field]: value,
      },
    }));
  }, []);

  const completenessIcon = (completeness: string) => {
    switch (completeness) {
      case 'full':
        return (
          <svg className="w-5 h-5 text-tier-quality" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'partial':
        return (
          <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  // No architecture ingested yet
  if (!config.ingestion.lastArchitectureIngest) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-xl font-semibold mb-2">Architecture Enrichment</h3>
          <p className="text-vscode-muted">
            No architecture documents have been ingested yet. Skip this step or go back to ingest architecture documents first.
          </p>
        </div>
        <button
          onClick={onSkip}
          className="px-4 py-2 rounded bg-vscode-button-bg text-vscode-button-fg text-sm hover:opacity-80"
        >
          Skip
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-2">Architecture Enrichment</h3>
        <p className="text-vscode-muted">
          Each architectural decision should carry its intent (why it exists) and vision alignment
          (which vision standards it serves). Optional metrics can measure whether the intent is
          being served. This enables intelligent governance and architectural evolution.
        </p>
      </div>

      {/* Validate button */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleValidate}
          disabled={isValidating}
          className="px-3 py-1.5 rounded bg-tier-architecture text-white text-sm hover:opacity-80 transition-opacity disabled:opacity-50"
        >
          {isValidating ? 'Validating...' : enrichmentResult ? 'Re-validate' : 'Check Completeness'}
        </button>
        {enrichmentResult && (
          <span className="text-sm text-vscode-muted">
            {enrichmentResult.complete} complete, {enrichmentResult.partial} partial, {enrichmentResult.missing} missing of {enrichmentResult.total} entities
          </span>
        )}
      </div>

      {/* Entity list */}
      {enrichmentResult && enrichmentResult.entities.length > 0 && (
        <div className="space-y-2">
          {enrichmentResult.entities.map(entity => (
            <div
              key={entity.name}
              className="rounded-lg border border-vscode-border bg-vscode-widget-bg overflow-hidden"
            >
              {/* Entity header */}
              <button
                onClick={() => setExpandedEntity(expandedEntity === entity.name ? null : entity.name)}
                className="w-full flex items-center gap-3 p-3 text-left hover:bg-vscode-list-hover-bg transition-colors"
              >
                {completenessIcon(entity.completeness)}
                <div className="flex-1">
                  <span className="font-medium">{entity.name}</span>
                  <span className="text-xs text-vscode-muted ml-2">({entity.entityType})</span>
                </div>
                {entity.missingFields.length > 0 && (
                  <span className="text-xs text-amber-400">
                    Missing: {entity.missingFields.join(', ')}
                  </span>
                )}
                <svg
                  className={`w-4 h-4 transition-transform ${expandedEntity === entity.name ? 'rotate-180' : ''}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Expanded editor */}
              {expandedEntity === entity.name && (
                <div className="border-t border-vscode-border p-4 space-y-4">
                  {/* Suggest button */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSuggest(entity)}
                      disabled={suggestingFor === entity.name}
                      className="px-3 py-1 rounded bg-blue-600 text-white text-xs hover:opacity-80 disabled:opacity-50"
                    >
                      {suggestingFor === entity.name ? 'Suggesting...' : 'Suggest with Claude'}
                    </button>
                  </div>

                  {/* Intent */}
                  <div>
                    <label className="block text-sm font-medium mb-1">Intent</label>
                    <p className="text-xs text-vscode-muted mb-1">Why does this architectural decision exist? What problem does it solve?</p>
                    <textarea
                      value={editStates[entity.name]?.intent || ''}
                      onChange={e => updateEditState(entity.name, 'intent', e.target.value)}
                      rows={2}
                      className="w-full bg-vscode-input-bg text-vscode-input-fg border border-vscode-input-border rounded p-2 text-sm"
                      placeholder="e.g., Decouple service creation from consumption to enable isolated testing"
                    />
                  </div>

                  {/* Vision Alignment */}
                  <div>
                    <label className="block text-sm font-medium mb-1">Vision Alignment</label>
                    <p className="text-xs text-vscode-muted mb-1">
                      Which vision standards does this serve? Format: vision_standard_name|explanation
                    </p>
                    <textarea
                      value={(editStates[entity.name]?.visionAlignments || []).join('\n')}
                      onChange={e => updateEditState(entity.name, 'visionAlignments', e.target.value.split('\n').filter(l => l.trim()))}
                      rows={2}
                      className="w-full bg-vscode-input-bg text-vscode-input-fg border border-vscode-input-border rounded p-2 text-sm font-mono"
                      placeholder="protocol_based_di|Enables protocol-based service swapping"
                    />
                  </div>

                  {/* Save */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSave(entity.name)}
                      disabled={savingFor === entity.name || !editStates[entity.name]?.intent}
                      className="px-3 py-1.5 rounded bg-tier-quality text-white text-sm hover:opacity-80 disabled:opacity-50"
                    >
                      {savingFor === entity.name ? 'Saving...' : 'Save Metadata'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Summary for complete entities */}
      {enrichmentResult && enrichmentResult.complete === enrichmentResult.total && enrichmentResult.total > 0 && (
        <div className="p-3 rounded bg-tier-quality/10 border border-tier-quality/30 text-sm">
          All {enrichmentResult.total} architecture entities have complete metadata.
        </div>
      )}

      <div className="p-3 rounded bg-blue-500/10 border border-blue-500/30 text-sm">
        <strong>Note:</strong> Enrichment is collaborative, not blocking. You can skip this step and
        enrich entities later. Entities with partial metadata still function normally; the system will
        nudge toward completeness over time.
      </div>
    </div>
  );
}
