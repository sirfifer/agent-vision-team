import { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { getActiveProjectId } from '../../hooks/useTransport';
import type { BootstrapScaleProfile, BootstrapFocusAreas } from '../../types';

const TIER_COLORS: Record<string, string> = {
  Small: 'text-green-400',
  Medium: 'text-blue-400',
  Large: 'text-yellow-400',
  Massive: 'text-orange-400',
  Enterprise: 'text-red-400',
};

function ScaleBadge({ profile }: { profile: BootstrapScaleProfile }) {
  const tierColor = TIER_COLORS[profile.tier] || 'text-vscode-fg';
  const topLangs = profile.languages.slice(0, 4);

  return (
    <div className="rounded border border-vscode-border bg-vscode-bg px-3 py-2">
      <div className="flex items-center gap-4 text-xs">
        <span className={`font-bold ${tierColor}`}>{profile.tier}</span>
        <span><span className="text-vscode-muted">Files:</span> {profile.sourceFiles.toLocaleString()}</span>
        <span><span className="text-vscode-muted">LOC:</span> {profile.sourceLoc.toLocaleString()}</span>
        <span><span className="text-vscode-muted">~</span>{profile.estimatedTimeMinutes} min</span>
        <span className="text-vscode-muted">
          {topLangs.map(l => `.${l.extension}`).join(', ')}
        </span>
      </div>
    </div>
  );
}

function ProgressView() {
  const { bootstrapProgress, bootstrapResult, setShowBootstrap } = useDashboard();

  if (bootstrapResult) {
    return (
      <div className="px-6 py-8 space-y-4 text-center">
        {bootstrapResult.success ? (
          <>
            <div className="w-12 h-12 mx-auto rounded-full bg-green-500/15 flex items-center justify-center">
              <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <div className="text-sm font-semibold">Bootstrap Complete</div>
              <div className="text-xs text-vscode-muted mt-1">
                Review the bootstrap report to approve, reject, or revise each discovery.
              </div>
              {bootstrapResult.reportPath && (
                <div className="mt-2 text-xs font-mono text-blue-400">
                  {bootstrapResult.reportPath}
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            <div className="w-12 h-12 mx-auto rounded-full bg-red-500/15 flex items-center justify-center">
              <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div>
              <div className="text-sm font-semibold text-red-400">Bootstrap Failed</div>
              <div className="text-xs text-vscode-muted mt-1">
                {bootstrapResult.error || 'An unknown error occurred.'}
              </div>
            </div>
          </>
        )}
        <button
          onClick={() => setShowBootstrap(false)}
          className="px-4 py-2 text-sm rounded-lg bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity"
        >
          Close
        </button>
      </div>
    );
  }

  return (
    <div className="px-6 py-8 space-y-5">
      <div className="flex flex-col items-center gap-4">
        <svg className="w-8 h-8 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <div className="text-center">
          <div className="text-sm font-semibold">{bootstrapProgress?.phase || 'Starting...'}</div>
          <div className="text-xs text-vscode-muted mt-1">{bootstrapProgress?.detail || 'Initializing bootstrap agent...'}</div>
        </div>
      </div>

      {bootstrapProgress?.percent != null && (
        <div className="w-full bg-vscode-bg rounded-full h-1.5">
          <div
            className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${bootstrapProgress.percent}%` }}
          />
        </div>
      )}

      <p className="text-2xs text-vscode-muted text-center">
        This may take several minutes for large projects. You can close this dialog;
        the bootstrap will continue in the background and progress appears in the Activity feed.
      </p>
    </div>
  );
}

export function BootstrapDialog() {
  const {
    showBootstrap, setShowBootstrap, sendMessage,
    bootstrapScaleProfile, projectConfig,
    bootstrapRunning, bootstrapResult,
  } = useDashboard();
  const [context, setContext] = useState('');
  const [focusAreas, setFocusAreas] = useState<BootstrapFocusAreas>({
    visionStandards: true,
    architectureDocs: true,
    conventions: true,
    projectRules: true,
  });
  const [checkingScale, setCheckingScale] = useState(false);
  const [localScaleProfile, setLocalScaleProfile] = useState<BootstrapScaleProfile | null>(null);
  const [starting, setStarting] = useState(false);

  const scaleProfile = localScaleProfile || bootstrapScaleProfile;
  const showProgress = bootstrapRunning || bootstrapResult;

  if (!showBootstrap) return null;

  const isGatewayMode = !!(window as any).__AVT_API_BASE__;

  const handleScaleCheck = async () => {
    setCheckingScale(true);
    try {
      if (isGatewayMode) {
        const apiBase = (window as any).__AVT_API_BASE__ || '';
        const apiKey = (window as any).__AVT_API_KEY__ || '';
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;
        const projectId = getActiveProjectId();
        const resp = await fetch(`${apiBase}/api/projects/${projectId}/bootstrap/scale-check`, {
          method: 'POST',
          headers,
        });
        const data = await resp.json();
        setLocalScaleProfile(data.profile);
      } else {
        sendMessage({ type: 'bootstrapScaleCheck' });
      }
    } catch (err) {
      console.error('Scale check failed:', err);
    } finally {
      setCheckingScale(false);
    }
  };

  const handleStart = async () => {
    setStarting(true);
    try {
      if (isGatewayMode) {
        const apiBase = (window as any).__AVT_API_BASE__ || '';
        const apiKey = (window as any).__AVT_API_KEY__ || '';
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;
        const projectId = getActiveProjectId();
        const prompt = buildBootstrapPrompt(context, focusAreas);
        await fetch(`${apiBase}/api/projects/${projectId}/jobs`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ prompt, agent_type: 'project-bootstrapper', model: 'opus' }),
        });
        // Gateway mode: close dialog, job appears in Jobs tab
        setShowBootstrap(false);
      } else {
        sendMessage({ type: 'runBootstrap', context, focusAreas });
        // VS Code mode: dialog stays open, transitions to progress view
        // via bootstrapStarted message from extension host
      }
    } catch (err) {
      console.error('Bootstrap start failed:', err);
    } finally {
      setStarting(false);
    }
  };

  const handleClose = () => {
    setShowBootstrap(false);
    setLocalScaleProfile(null);
  };

  const toggleFocus = (key: keyof BootstrapFocusAreas) => {
    setFocusAreas(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const defaultContext = projectConfig?.metadata?.name
    ? `Project: ${projectConfig.metadata.name}${projectConfig.metadata.description ? `. ${projectConfig.metadata.description}` : ''}`
    : '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-vscode-widget-bg border border-vscode-border rounded-xl shadow-2xl w-full max-w-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-vscode-border">
          <div>
            <h2 className="text-base font-bold text-vscode-fg">Bootstrap Project</h2>
            <p className="text-2xs text-vscode-muted">
              Analyze your codebase and draft architecture documentation
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-1 rounded hover:bg-vscode-bg transition-colors text-vscode-muted hover:text-vscode-fg"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {showProgress ? (
          <ProgressView />
        ) : (
          <>
            <div className="px-5 py-4 space-y-4">
              {/* Compact "What Happens" - single paragraph */}
              <div className="text-xs text-vscode-muted leading-relaxed p-3 rounded-lg bg-vscode-bg border border-vscode-border">
                <span className="font-semibold text-vscode-fg">How it works:</span>{' '}
                AI agents analyze your source code, docs, and config to draft vision standards,
                architecture docs, a style guide, and project rules. A bootstrap report summarizes
                all discoveries. <span className="font-semibold text-green-400">Nothing is permanent</span>{' '}
                until you approve each item.
              </div>

              {/* Context */}
              <div className="space-y-1.5">
                <label className="text-2xs font-semibold uppercase tracking-wider text-vscode-muted">
                  Project Context <span className="font-normal">(optional)</span>
                </label>
                <textarea
                  value={context || defaultContext}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="e.g., 'Django API migrating to FastAPI' or 'Auth module is legacy, being replaced.'"
                  className="w-full h-14 px-3 py-2 text-xs rounded bg-vscode-bg text-vscode-fg border border-vscode-border focus:outline-none focus:border-[var(--vscode-focusBorder)] resize-none"
                />
              </div>

              {/* Focus Areas - inline */}
              <div className="space-y-1.5">
                <label className="text-2xs font-semibold uppercase tracking-wider text-vscode-muted">
                  Focus Areas
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {([
                    { key: 'visionStandards' as const, label: 'Vision Standards' },
                    { key: 'architectureDocs' as const, label: 'Architecture' },
                    { key: 'conventions' as const, label: 'Conventions' },
                    { key: 'projectRules' as const, label: 'Project Rules' },
                  ]).map(area => (
                    <button
                      key={area.key}
                      onClick={() => toggleFocus(area.key)}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs border transition-colors ${
                        focusAreas[area.key]
                          ? 'border-blue-500/50 bg-blue-500/10 text-vscode-fg'
                          : 'border-vscode-border bg-vscode-bg text-vscode-muted'
                      }`}
                    >
                      <div className={`w-3 h-3 rounded-sm border flex items-center justify-center ${
                        focusAreas[area.key] ? 'bg-blue-500 border-blue-500' : 'border-vscode-border'
                      }`}>
                        {focusAreas[area.key] && (
                          <svg className="w-2 h-2 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                      {area.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Scale Check - compact inline */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <label className="text-2xs font-semibold uppercase tracking-wider text-vscode-muted">
                    Scale
                  </label>
                  {!scaleProfile && !checkingScale && (
                    <button
                      onClick={handleScaleCheck}
                      className="text-2xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      Check project scale
                    </button>
                  )}
                  {checkingScale && (
                    <span className="flex items-center gap-1 text-2xs text-vscode-muted">
                      <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Analyzing...
                    </span>
                  )}
                </div>
                {scaleProfile && !checkingScale && <ScaleBadge profile={scaleProfile} />}
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 px-5 py-3 border-t border-vscode-border">
              <button
                onClick={handleClose}
                className="px-3 py-1.5 text-xs rounded border border-vscode-border text-vscode-muted hover:text-vscode-fg hover:bg-vscode-bg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleStart}
                disabled={starting || !Object.values(focusAreas).some(Boolean)}
                className="px-4 py-1.5 text-xs font-semibold rounded bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {starting ? 'Starting...' : 'Start Bootstrap'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function buildBootstrapPrompt(context: string, focusAreas: BootstrapFocusAreas): string {
  const areas: string[] = [];
  if (focusAreas.visionStandards) areas.push('vision standards');
  if (focusAreas.architectureDocs) areas.push('architecture documentation');
  if (focusAreas.conventions) areas.push('coding conventions and style guide');
  if (focusAreas.projectRules) areas.push('project rules');

  let prompt = 'Bootstrap this project.';
  if (areas.length < 4) {
    prompt += ` Focus on: ${areas.join(', ')}.`;
  }
  if (context.trim()) {
    prompt += `\n\nProject context from user:\n${context.trim()}`;
  }
  return prompt;
}
