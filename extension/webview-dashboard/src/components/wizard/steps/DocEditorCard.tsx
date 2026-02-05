import type { UseDocEditorReturn } from '../../../hooks/useDocEditor';

interface DocEditorCardProps {
  tier: 'vision' | 'architecture';
  editor: UseDocEditorReturn;
  tierColorClass: string;
  placeholderText: string;
}

export function DocEditorCard({
  tier,
  editor,
  tierColorClass,
  placeholderText,
}: DocEditorCardProps) {
  const {
    docName,
    setDocName,
    isNameLocked,
    toggleNameLock,
    content,
    setContent,
    phase,
    errorMessage,
    errorContext,
    handleFormat,
    handleSave,
    handleReformat,
    handleSaveAsIs,
    handleReset,
  } = editor;

  const tierLabel = tier === 'vision' ? 'Vision' : 'Architecture';
  const dirPath = `docs/${tier}`;

  return (
    <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
      <h4 className="font-medium mb-3">Create New {tierLabel} Document</h4>

      <div className="space-y-3">
        {/* Document Name Field */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Document Name
          </label>
          <input
            type="text"
            value={docName}
            onChange={e => setDocName(e.target.value)}
            disabled={isNameLocked}
            className={`w-full px-3 py-2 rounded border text-vscode-fg focus:outline-none focus:border-vscode-btn-bg ${
              isNameLocked
                ? 'bg-vscode-bg border-vscode-border opacity-70 cursor-not-allowed'
                : 'bg-vscode-input-bg border-vscode-border placeholder:text-vscode-muted'
            }`}
          />
          <div className="flex items-center justify-between mt-1">
            <p className="text-xs text-vscode-muted">
              Will be saved as <code>{dirPath}/{docName || '[name]'}.md</code>
            </p>
            <button
              type="button"
              onClick={toggleNameLock}
              className="text-xs text-vscode-link hover:underline"
            >
              {isNameLocked ? 'Customize name' : 'Reset to default'}
            </button>
          </div>
        </div>

        {/* Content Textarea */}
        <div className="relative">
          <label className="block text-sm font-medium mb-1">
            Content
          </label>

          {/* Review banner */}
          {phase === 'reviewing' && (
            <div className="mb-2 p-2 rounded bg-green-500/10 border border-green-500/30 text-sm text-green-300">
              Review the formatted document below. Edit if needed, then save.
            </div>
          )}

          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            disabled={phase === 'formatting' || phase === 'saving'}
            placeholder={phase === 'formatting' ? '' : placeholderText}
            rows={12}
            className={`w-full px-3 py-2 rounded bg-vscode-input-bg border border-vscode-border text-vscode-fg font-mono text-sm focus:outline-none focus:border-vscode-btn-bg ${
              (phase === 'formatting' || phase === 'saving')
                ? 'opacity-50 cursor-not-allowed'
                : ''
            }`}
          />

          {/* Spinner overlay during formatting */}
          {phase === 'formatting' && (
            <div className="absolute inset-0 top-6 flex items-center justify-center rounded bg-black/30">
              <div className="flex items-center gap-2 px-4 py-2 rounded bg-vscode-widget-bg border border-vscode-border shadow-lg">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span className="text-sm">Formatting with Claude...</span>
              </div>
            </div>
          )}
        </div>

        {/* Error message */}
        {phase === 'error' && errorMessage && (
          <div className="p-3 rounded bg-red-500/10 border border-red-500/30 text-sm text-red-300">
            <strong>Error:</strong> {errorMessage}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {/* Idle: no buttons (content is empty) */}

          {/* Drafting: Clean Up & Format */}
          {(phase === 'idle' || phase === 'drafting') && (
            <button
              onClick={handleFormat}
              disabled={!content.trim()}
              className={`px-4 py-2 rounded ${tierColorClass} text-white hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              Clean Up &amp; Format
            </button>
          )}

          {/* Formatting: disabled spinner button */}
          {phase === 'formatting' && (
            <button
              disabled
              className={`px-4 py-2 rounded ${tierColorClass} text-white opacity-50 cursor-not-allowed`}
            >
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Formatting...
              </span>
            </button>
          )}

          {/* Reviewing: Save + Re-format + Start Over */}
          {phase === 'reviewing' && (
            <>
              <button
                onClick={handleSave}
                className={`px-4 py-2 rounded ${tierColorClass} text-white hover:opacity-80 transition-opacity`}
              >
                Save Document
              </button>
              <button
                onClick={handleReformat}
                className="px-4 py-2 rounded bg-vscode-btn2-bg text-vscode-btn2-fg hover:opacity-80 transition-opacity"
              >
                Re-format
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="text-sm text-vscode-link hover:underline ml-2"
              >
                Start Over
              </button>
            </>
          )}

          {/* Error: Retry + Save as-is (or edit) */}
          {phase === 'error' && errorContext === 'format' && (
            <>
              <button
                onClick={handleFormat}
                className={`px-4 py-2 rounded ${tierColorClass} text-white hover:opacity-80 transition-opacity`}
              >
                Retry Format
              </button>
              <button
                onClick={handleSaveAsIs}
                disabled={!content.trim()}
                className="px-4 py-2 rounded bg-vscode-btn2-bg text-vscode-btn2-fg hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save as-is
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="text-sm text-vscode-link hover:underline ml-2"
              >
                Start Over
              </button>
            </>
          )}

          {phase === 'error' && errorContext === 'save' && (
            <>
              <button
                onClick={handleSave}
                className={`px-4 py-2 rounded ${tierColorClass} text-white hover:opacity-80 transition-opacity`}
              >
                Retry Save
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="text-sm text-vscode-link hover:underline ml-2"
              >
                Start Over
              </button>
            </>
          )}

          {/* Saving: disabled spinner button */}
          {phase === 'saving' && (
            <button
              disabled
              className={`px-4 py-2 rounded ${tierColorClass} text-white opacity-50 cursor-not-allowed`}
            >
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Saving...
              </span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
