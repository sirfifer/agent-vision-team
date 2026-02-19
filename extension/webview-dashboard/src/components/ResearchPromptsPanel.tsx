import { useState, useEffect } from 'react';
import { useDashboard } from '../context/DashboardContext';
import type {
  ResearchPrompt,
  ResearchType,
  ResearchModelHint,
  ResearchOutputFormat,
  ResearchSchedule,
  ResearchStatus,
} from '../types';

const STATUS_COLORS: Record<ResearchStatus, string> = {
  pending: 'bg-yellow-500/20 text-yellow-400',
  scheduled: 'bg-blue-500/20 text-blue-400',
  in_progress: 'bg-purple-500/20 text-purple-400',
  completed: 'bg-green-500/20 text-green-400',
  failed: 'bg-red-500/20 text-red-400',
};

const SCHEDULE_LABELS: Record<NonNullable<ResearchSchedule['type']>, string> = {
  once: 'One-time',
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
};

function generateId(): string {
  return `rp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function getEmptyPrompt(): Omit<ResearchPrompt, 'id' | 'createdAt' | 'updatedAt'> {
  return {
    name: '',
    type: 'exploratory',
    topic: '',
    context: '',
    scope: '',
    modelHint: 'auto',
    output: 'research_brief',
    relatedEntities: [],
    status: 'pending',
  };
}

interface PromptEditorProps {
  prompt: Partial<ResearchPrompt>;
  onChange: (prompt: Partial<ResearchPrompt>) => void;
  onSave: () => void;
  onCancel: () => void;
  isNew: boolean;
}

function PromptEditor({ prompt, onChange, onSave, onCancel, isNew }: PromptEditorProps) {
  const [entities, setEntities] = useState(prompt.relatedEntities?.join(', ') || '');

  const handleEntitiesChange = (value: string) => {
    setEntities(value);
    onChange({
      ...prompt,
      relatedEntities: value
        .split(',')
        .map((e) => e.trim())
        .filter(Boolean),
    });
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">Name</label>
        <input
          type="text"
          value={prompt.name || ''}
          onChange={(e) => onChange({ ...prompt, name: e.target.value })}
          placeholder="e.g., Claude Code Updates Monitor"
          className="w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Type</label>
          <select
            value={prompt.type || 'exploratory'}
            onChange={(e) => onChange({ ...prompt, type: e.target.value as ResearchType })}
            className="w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
          >
            <option value="periodic">Periodic/Maintenance</option>
            <option value="exploratory">Exploratory/Design</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Model Hint</label>
          <select
            value={prompt.modelHint || 'auto'}
            onChange={(e) =>
              onChange({ ...prompt, modelHint: e.target.value as ResearchModelHint })
            }
            className="w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
          >
            <option value="auto">Auto (based on complexity)</option>
            <option value="opus">Opus (complex research)</option>
            <option value="sonnet">Sonnet (routine checks)</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Topic</label>
        <input
          type="text"
          value={prompt.topic || ''}
          onChange={(e) => onChange({ ...prompt, topic: e.target.value })}
          placeholder="What to research"
          className="w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Context</label>
        <textarea
          value={prompt.context || ''}
          onChange={(e) => onChange({ ...prompt, context: e.target.value })}
          placeholder="Why this research matters now"
          rows={2}
          className="w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus resize-none"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Scope</label>
        <textarea
          value={prompt.scope || ''}
          onChange={(e) => onChange({ ...prompt, scope: e.target.value })}
          placeholder="Boundaries of the research"
          rows={2}
          className="w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus resize-none"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Output Format</label>
          <select
            value={prompt.output || 'research_brief'}
            onChange={(e) =>
              onChange({ ...prompt, output: e.target.value as ResearchOutputFormat })
            }
            className="w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
          >
            <option value="research_brief">Research Brief</option>
            <option value="change_report">Change Report</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Related Entities</label>
          <input
            type="text"
            value={entities}
            onChange={(e) => handleEntitiesChange(e.target.value)}
            placeholder="Comma-separated KG entities"
            className="w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
          />
        </div>
      </div>

      {prompt.type === 'periodic' && (
        <div className="p-3 bg-vscode-widget-bg rounded border border-vscode-border">
          <label className="block text-sm font-medium mb-2">Schedule</label>
          <div className="grid grid-cols-2 gap-4">
            <select
              value={prompt.schedule?.type || 'once'}
              onChange={(e) =>
                onChange({
                  ...prompt,
                  schedule: {
                    ...prompt.schedule,
                    type: e.target.value as ResearchSchedule['type'],
                  },
                })
              }
              className="px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
            >
              <option value="once">One-time</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>

            <input
              type="time"
              value={prompt.schedule?.time || '09:00'}
              onChange={(e) =>
                onChange({
                  ...prompt,
                  schedule: {
                    ...prompt.schedule,
                    type: prompt.schedule?.type || 'once',
                    time: e.target.value,
                  },
                })
              }
              className="px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
            />
          </div>

          {prompt.schedule?.type === 'weekly' && (
            <select
              value={prompt.schedule?.dayOfWeek ?? 1}
              onChange={(e) =>
                onChange({
                  ...prompt,
                  schedule: {
                    ...prompt.schedule,
                    type: 'weekly',
                    dayOfWeek: Number(e.target.value),
                  },
                })
              }
              className="mt-2 w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
            >
              <option value={0}>Sunday</option>
              <option value={1}>Monday</option>
              <option value={2}>Tuesday</option>
              <option value={3}>Wednesday</option>
              <option value={4}>Thursday</option>
              <option value={5}>Friday</option>
              <option value={6}>Saturday</option>
            </select>
          )}

          {prompt.schedule?.type === 'monthly' && (
            <select
              value={prompt.schedule?.dayOfMonth ?? 1}
              onChange={(e) =>
                onChange({
                  ...prompt,
                  schedule: {
                    ...prompt.schedule,
                    type: 'monthly',
                    dayOfMonth: Number(e.target.value),
                  },
                })
              }
              className="mt-2 w-full px-3 py-2 bg-vscode-input-bg border border-vscode-border rounded focus:outline-none focus:border-vscode-focus"
            >
              {Array.from({ length: 28 }, (_, i) => i + 1).map((day) => (
                <option key={day} value={day}>
                  {day}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <button
          onClick={onCancel}
          className="px-4 py-2 rounded bg-vscode-btn2-bg text-vscode-btn2-fg hover:opacity-80 transition-opacity"
        >
          Cancel
        </button>
        <button
          onClick={onSave}
          disabled={!prompt.name || !prompt.topic}
          className="px-4 py-2 rounded bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isNew ? 'Create' : 'Save'}
        </button>
      </div>
    </div>
  );
}

interface PromptCardProps {
  prompt: ResearchPrompt;
  onEdit: () => void;
  onDelete: () => void;
  onRun: () => void;
}

function PromptCard({ prompt, onEdit, onDelete, onRun }: PromptCardProps) {
  return (
    <div className="p-4 bg-vscode-widget-bg rounded border border-vscode-border">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium truncate">{prompt.name}</h4>
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${STATUS_COLORS[prompt.status]}`}>
              {prompt.status}
            </span>
          </div>
          <p className="text-xs text-vscode-muted truncate">{prompt.topic}</p>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onRun}
            disabled={prompt.status === 'in_progress'}
            className="p-1.5 hover:bg-vscode-hover rounded transition-colors disabled:opacity-50"
            title="Run now"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
          <button
            onClick={onEdit}
            className="p-1.5 hover:bg-vscode-hover rounded transition-colors"
            title="Edit"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 hover:bg-red-500/20 text-red-400 rounded transition-colors"
            title="Delete"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-vscode-muted">
        <span className="flex items-center gap-1">
          <span className={prompt.type === 'periodic' ? 'text-blue-400' : 'text-purple-400'}>
            {prompt.type === 'periodic' ? 'Periodic' : 'Exploratory'}
          </span>
        </span>
        <span>
          Model: <span className="text-vscode-fg">{prompt.modelHint}</span>
        </span>
        {prompt.schedule && (
          <span>
            {SCHEDULE_LABELS[prompt.schedule.type]}
            {prompt.schedule.time && ` @ ${prompt.schedule.time}`}
          </span>
        )}
      </div>

      {prompt.lastResult && (
        <div
          className={`mt-3 p-2 rounded text-xs ${prompt.lastResult.success ? 'bg-green-500/10' : 'bg-red-500/10'}`}
        >
          <div className="flex items-center justify-between">
            <span className={prompt.lastResult.success ? 'text-green-400' : 'text-red-400'}>
              {prompt.lastResult.success ? 'Last run successful' : 'Last run failed'}
            </span>
            <span className="text-vscode-muted">
              {new Date(prompt.lastResult.timestamp).toLocaleDateString()}
            </span>
          </div>
          {prompt.lastResult.summary && (
            <p className="mt-1 text-vscode-muted">{prompt.lastResult.summary}</p>
          )}
        </div>
      )}
    </div>
  );
}

export function ResearchPromptsPanel() {
  const { showResearchPrompts, setShowResearchPrompts, researchPrompts, sendMessage } =
    useDashboard();
  const [editingPrompt, setEditingPrompt] = useState<Partial<ResearchPrompt> | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [filterType, setFilterType] = useState<'all' | ResearchType>('all');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Load prompts when panel opens
  useEffect(() => {
    if (showResearchPrompts) {
      sendMessage({ type: 'listResearchPrompts' });
    }
  }, [showResearchPrompts, sendMessage]);

  if (!showResearchPrompts) {
    return null;
  }

  const handleNew = () => {
    setEditingPrompt(getEmptyPrompt());
    setIsNew(true);
  };

  const handleEdit = (prompt: ResearchPrompt) => {
    setEditingPrompt({ ...prompt });
    setIsNew(false);
  };

  const handleSave = () => {
    if (!editingPrompt || !editingPrompt.name || !editingPrompt.topic) return;

    const now = new Date().toISOString();
    const fullPrompt: ResearchPrompt = {
      id: editingPrompt.id || generateId(),
      name: editingPrompt.name,
      type: editingPrompt.type || 'exploratory',
      topic: editingPrompt.topic,
      context: editingPrompt.context || '',
      scope: editingPrompt.scope || '',
      modelHint: editingPrompt.modelHint || 'auto',
      output: editingPrompt.output || 'research_brief',
      relatedEntities: editingPrompt.relatedEntities || [],
      schedule: editingPrompt.schedule,
      status: editingPrompt.status || 'pending',
      createdAt: editingPrompt.createdAt || now,
      updatedAt: now,
      lastResult: editingPrompt.lastResult,
    };

    sendMessage({ type: 'saveResearchPrompt', prompt: fullPrompt });
    setEditingPrompt(null);
    setIsNew(false);
  };

  const handleDelete = (id: string) => {
    sendMessage({ type: 'deleteResearchPrompt', id });
    setDeleteConfirm(null);
  };

  const handleRun = (id: string) => {
    sendMessage({ type: 'runResearchPrompt', id });
  };

  const filteredPrompts = researchPrompts.filter(
    (p) => filterType === 'all' || p.type === filterType,
  );

  const periodicCount = researchPrompts.filter((p) => p.type === 'periodic').length;
  const exploratoryCount = researchPrompts.filter((p) => p.type === 'exploratory').length;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
      <div className="w-full max-w-lg bg-vscode-bg border-l border-vscode-border shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-vscode-border">
          <div>
            <h2 className="text-lg font-semibold">Research Prompts</h2>
            <p className="text-xs text-vscode-muted">
              {researchPrompts.length} prompt{researchPrompts.length !== 1 ? 's' : ''}
            </p>
          </div>
          <button
            onClick={() => setShowResearchPrompts(false)}
            className="p-1 hover:bg-vscode-widget-bg rounded transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-vscode-border bg-vscode-widget-bg/50">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setFilterType('all')}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                filterType === 'all'
                  ? 'bg-vscode-btn-bg text-vscode-btn-fg'
                  : 'hover:bg-vscode-hover'
              }`}
            >
              All ({researchPrompts.length})
            </button>
            <button
              onClick={() => setFilterType('periodic')}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                filterType === 'periodic' ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-vscode-hover'
              }`}
            >
              Periodic ({periodicCount})
            </button>
            <button
              onClick={() => setFilterType('exploratory')}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                filterType === 'exploratory'
                  ? 'bg-purple-500/20 text-purple-400'
                  : 'hover:bg-vscode-hover'
              }`}
            >
              Exploratory ({exploratoryCount})
            </button>
          </div>
          <button
            onClick={handleNew}
            className="flex items-center gap-1 px-3 py-1.5 bg-vscode-btn-bg text-vscode-btn-fg rounded hover:opacity-80 transition-opacity text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            New
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {editingPrompt ? (
            <div className="bg-vscode-widget-bg/50 rounded-lg p-4 border border-vscode-border">
              <h3 className="font-medium mb-4">
                {isNew ? 'New Research Prompt' : 'Edit Research Prompt'}
              </h3>
              <PromptEditor
                prompt={editingPrompt}
                onChange={setEditingPrompt}
                onSave={handleSave}
                onCancel={() => {
                  setEditingPrompt(null);
                  setIsNew(false);
                }}
                isNew={isNew}
              />
            </div>
          ) : filteredPrompts.length === 0 ? (
            <div className="text-center py-12 text-vscode-muted">
              <svg
                className="w-12 h-12 mx-auto mb-4 opacity-50"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <p className="mb-2">No research prompts yet</p>
              <p className="text-xs">
                Create prompts to track external changes or research new features
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredPrompts.map((prompt) => (
                <PromptCard
                  key={prompt.id}
                  prompt={prompt}
                  onEdit={() => handleEdit(prompt)}
                  onDelete={() => setDeleteConfirm(prompt.id)}
                  onRun={() => handleRun(prompt.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-3 border-t border-vscode-border text-xs text-vscode-muted">
          <p>
            <span className="text-blue-400">Periodic</span> prompts track external changes.{' '}
            <span className="text-purple-400">Exploratory</span> prompts inform new development.
          </p>
        </div>
      </div>

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/50">
          <div className="bg-vscode-bg border border-vscode-border rounded-lg p-6 max-w-sm mx-4 shadow-2xl">
            <h3 className="font-semibold mb-2">Delete Research Prompt?</h3>
            <p className="text-sm text-vscode-muted mb-4">This action cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 rounded bg-vscode-btn2-bg text-vscode-btn2-fg hover:opacity-80 transition-opacity"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="px-4 py-2 rounded bg-red-500 text-white hover:opacity-80 transition-opacity"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
