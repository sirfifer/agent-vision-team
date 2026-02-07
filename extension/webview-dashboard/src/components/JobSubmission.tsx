import { useState } from 'react';
import { useDashboard } from '../context/DashboardContext';

const AGENT_TYPES = [
  { value: '', label: 'Orchestrator (default)' },
  { value: 'worker', label: 'Worker' },
  { value: 'researcher', label: 'Researcher' },
  { value: 'quality-reviewer', label: 'Quality Reviewer' },
  { value: 'kg-librarian', label: 'KG Librarian' },
  { value: 'project-steward', label: 'Project Steward' },
];

const MODELS = [
  { value: 'opus', label: 'Opus (most capable)' },
  { value: 'sonnet', label: 'Sonnet (balanced)' },
  { value: 'haiku', label: 'Haiku (fastest)' },
];

export function JobSubmission() {
  const [prompt, setPrompt] = useState('');
  const [agentType, setAgentType] = useState('');
  const [model, setModel] = useState('opus');
  const [submitting, setSubmitting] = useState(false);
  const [lastJobId, setLastJobId] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    setSubmitting(true);
    setLastJobId(null);

    try {
      const apiBase = (window as any).__AVT_API_BASE__ || '';
      const apiKey = (window as any).__AVT_API_KEY__ || '';
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

      const resp = await fetch(`${apiBase}/api/jobs`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          prompt: prompt.trim(),
          agent_type: agentType || null,
          model,
        }),
      });
      const data = await resp.json();
      if (data.job?.id) {
        setLastJobId(data.job.id);
        setPrompt('');
      }
    } catch (err) {
      console.error('Failed to submit job:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-4 space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted">Submit Job</h3>

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe the work you want done..."
        className="w-full h-28 px-3 py-2 text-sm rounded bg-[var(--vscode-input-background)] text-[var(--vscode-input-foreground)] border border-[var(--vscode-input-border)] focus:outline-none focus:border-[var(--vscode-focusBorder)] resize-none"
      />

      <div className="flex gap-3">
        <div className="flex-1">
          <label className="block text-xs text-vscode-muted mb-1">Agent Type</label>
          <select
            value={agentType}
            onChange={(e) => setAgentType(e.target.value)}
            className="w-full px-2 py-1.5 text-sm rounded bg-[var(--vscode-dropdown-background)] text-[var(--vscode-foreground)] border border-[var(--vscode-input-border)]"
          >
            {AGENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        <div className="flex-1">
          <label className="block text-xs text-vscode-muted mb-1">Model</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-2 py-1.5 text-sm rounded bg-[var(--vscode-dropdown-background)] text-[var(--vscode-foreground)] border border-[var(--vscode-input-border)]"
          >
            {MODELS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={!prompt.trim() || submitting}
        className="w-full px-4 py-2 text-sm font-medium rounded bg-[var(--vscode-button-background)] text-[var(--vscode-button-foreground)] hover:bg-[var(--vscode-button-hoverBackground)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {submitting ? 'Submitting...' : 'Submit Job'}
      </button>

      {lastJobId && (
        <div className="text-xs text-green-400">
          Job submitted: {lastJobId}
        </div>
      )}
    </div>
  );
}
