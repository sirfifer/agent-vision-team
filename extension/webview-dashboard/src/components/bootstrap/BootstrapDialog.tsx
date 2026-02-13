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

function ScaleProfileCard({ profile }: { profile: BootstrapScaleProfile }) {
  const tierColor = TIER_COLORS[profile.tier] || 'text-vscode-fg';
  const topLangs = profile.languages.slice(0, 5);

  return (
    <div className="rounded-lg border border-vscode-border bg-vscode-bg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">Scale Profile</span>
        <span className={`text-sm font-bold ${tierColor}`}>{profile.tier}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-vscode-muted">Source Files</span>
          <div className="font-semibold text-sm">{profile.sourceFiles.toLocaleString()}</div>
        </div>
        <div>
          <span className="text-vscode-muted">Lines of Code</span>
          <div className="font-semibold text-sm">{profile.sourceLoc.toLocaleString()}</div>
        </div>
        <div>
          <span className="text-vscode-muted">Documentation Files</span>
          <div className="font-semibold text-sm">{profile.docFiles.toLocaleString()}</div>
        </div>
        <div>
          <span className="text-vscode-muted">Packages</span>
          <div className="font-semibold text-sm">{profile.packages.length}</div>
        </div>
      </div>

      {topLangs.length > 0 && (
        <div>
          <span className="text-xs text-vscode-muted">Languages</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {topLangs.map(l => (
              <span key={l.extension} className="px-2 py-0.5 rounded text-xs bg-vscode-widget-bg border border-vscode-border">
                .{l.extension} <span className="text-vscode-muted">({l.count})</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="pt-2 border-t border-vscode-border flex items-center justify-between text-xs">
        <span className="text-vscode-muted">Estimated time</span>
        <span className="font-semibold">~{profile.estimatedTimeMinutes} min</span>
      </div>
    </div>
  );
}

export function BootstrapDialog() {
  const { showBootstrap, setShowBootstrap, sendMessage, bootstrapScaleProfile, projectConfig } = useDashboard();
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
        // Response will come via bootstrapScaleResult message handled by context
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
      } else {
        sendMessage({ type: 'runBootstrap', context, focusAreas });
      }
      setShowBootstrap(false);
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
      <div className="bg-vscode-widget-bg border border-vscode-border rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-vscode-border">
          <div>
            <h2 className="text-lg font-bold text-vscode-fg">Bootstrap Project</h2>
            <p className="text-xs text-vscode-muted mt-0.5">
              Discover your project's architecture, standards, and conventions
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded hover:bg-vscode-bg transition-colors text-vscode-muted hover:text-vscode-fg"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* What Happens Section */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">What happens</h3>
            <div className="grid gap-3">
              <div className="flex gap-3 p-3 rounded-lg bg-vscode-bg border border-vscode-border">
                <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-blue-500/15 flex items-center justify-center">
                  <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium">Analysis</div>
                  <div className="text-xs text-vscode-muted mt-0.5">
                    The bootstrapper analyzes your source code, documentation, and configuration files
                    using specialized AI agents. For large projects, analysis is partitioned along natural
                    code boundaries and run in parallel.
                  </div>
                </div>
              </div>

              <div className="flex gap-3 p-3 rounded-lg bg-vscode-bg border border-vscode-border">
                <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-purple-500/15 flex items-center justify-center">
                  <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium">Draft Artifacts</div>
                  <div className="text-xs text-vscode-muted mt-0.5">
                    Creates draft documents: vision standards (core principles), architecture docs with
                    Mermaid diagrams, a style guide of coding conventions, project rules, and a
                    comprehensive bootstrap report summarizing all discoveries.
                  </div>
                </div>
              </div>

              <div className="flex gap-3 p-3 rounded-lg bg-vscode-bg border border-vscode-border">
                <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-green-500/15 flex items-center justify-center">
                  <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium">Your Approval Required</div>
                  <div className="text-xs text-vscode-muted mt-0.5">
                    Nothing becomes permanent without your explicit approval. You review every discovery
                    in the bootstrap report and mark each as Approve, Reject, or Revise. Only approved
                    items are ingested into the Knowledge Graph.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Optional Context */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">
              Project Context <span className="font-normal">(optional)</span>
            </label>
            <textarea
              value={context || defaultContext}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Help the bootstrapper understand your project. For example: 'This is a Django API migrating to FastAPI' or 'The auth module is legacy, being replaced.'"
              className="w-full h-20 px-3 py-2 text-sm rounded-lg bg-vscode-bg text-vscode-fg border border-vscode-border focus:outline-none focus:border-[var(--vscode-focusBorder)] resize-none"
            />
          </div>

          {/* Focus Areas */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">
              Focus Areas
            </label>
            <div className="grid grid-cols-2 gap-2">
              {([
                { key: 'visionStandards' as const, label: 'Vision Standards', desc: 'Core principles and invariants' },
                { key: 'architectureDocs' as const, label: 'Architecture Docs', desc: 'Components, patterns, and diagrams' },
                { key: 'conventions' as const, label: 'Conventions & Style', desc: 'Naming, formatting, and idioms' },
                { key: 'projectRules' as const, label: 'Project Rules', desc: 'Behavioral guidelines for agents' },
              ]).map(area => (
                <button
                  key={area.key}
                  onClick={() => toggleFocus(area.key)}
                  className={`flex items-start gap-2 p-2.5 rounded-lg border text-left transition-colors ${
                    focusAreas[area.key]
                      ? 'border-blue-500/50 bg-blue-500/10'
                      : 'border-vscode-border bg-vscode-bg opacity-60'
                  }`}
                >
                  <div className={`mt-0.5 w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center ${
                    focusAreas[area.key] ? 'bg-blue-500 border-blue-500' : 'border-vscode-border'
                  }`}>
                    {focusAreas[area.key] && (
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  <div>
                    <div className="text-xs font-medium">{area.label}</div>
                    <div className="text-2xs text-vscode-muted">{area.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Scale Check */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">
                Scale Assessment <span className="font-normal">(optional)</span>
              </label>
              <button
                onClick={handleScaleCheck}
                disabled={checkingScale}
                className="px-3 py-1 text-xs font-medium rounded bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity disabled:opacity-50"
              >
                {checkingScale ? 'Checking...' : scaleProfile ? 'Re-check' : 'Check Scale'}
              </button>
            </div>
            {!scaleProfile && !checkingScale && (
              <p className="text-2xs text-vscode-muted">
                Run a fast (~5 second) analysis to see project size, languages, and estimated bootstrap time.
              </p>
            )}
            {checkingScale && (
              <div className="flex items-center gap-2 text-xs text-vscode-muted py-2">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Analyzing project structure...
              </div>
            )}
            {scaleProfile && !checkingScale && (
              <ScaleProfileCard profile={scaleProfile} />
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-vscode-border">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm rounded-lg border border-vscode-border text-vscode-muted hover:text-vscode-fg hover:bg-vscode-bg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleStart}
            disabled={starting || !Object.values(focusAreas).some(Boolean)}
            className="px-5 py-2 text-sm font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-600/25"
          >
            {starting ? 'Starting...' : 'Start Bootstrap'}
          </button>
        </div>
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
