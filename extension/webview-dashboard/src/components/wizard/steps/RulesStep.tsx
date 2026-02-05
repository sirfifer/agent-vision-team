import { useState } from 'react';
import type { ProjectConfig, RuleEntry, RuleCategory, RuleEnforcement, RuleScope, RulesConfig } from '../../../types';

interface RulesStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

// Rule definitions matching extension/src/models/ProjectConfig.ts
const DEFAULT_RULES: RuleEntry[] = [
  {
    id: 'no-mocks',
    statement: 'Write real integration and unit tests — never use mocks or stubs unless testing external service boundaries',
    rationale: 'Mocks hide integration bugs and create false confidence in test suites',
    category: 'testing',
    enforcement: 'enforce',
    scope: ['worker'],
    enabled: true,
    isDefault: true,
  },
  {
    id: 'test-coverage',
    statement: 'All new code must have test coverage. Target near-full coverage for business logic',
    rationale: 'Untested code is a liability — agents should not ship code they cannot prove works',
    category: 'testing',
    enforcement: 'enforce',
    scope: ['worker'],
    enabled: true,
    isDefault: true,
  },
  {
    id: 'build-before-done',
    statement: 'Run the build and all tests before reporting task completion',
    rationale: 'Broken builds waste review cycles and erode trust in agent output',
    category: 'testing',
    enforcement: 'enforce',
    scope: ['worker'],
    enabled: true,
    isDefault: true,
  },
  {
    id: 'follow-patterns',
    statement: 'Follow existing patterns in the codebase. Search for similar implementations before creating new patterns',
    rationale: 'Consistency reduces cognitive load; new patterns require justification',
    category: 'code-quality',
    enforcement: 'enforce',
    scope: ['worker'],
    enabled: true,
    isDefault: true,
  },
  {
    id: 'no-suppress-warnings',
    statement: 'Never suppress linter or compiler warnings without a documented justification',
    rationale: 'Suppressed warnings hide real issues and accumulate technical debt',
    category: 'code-quality',
    enforcement: 'enforce',
    scope: ['worker', 'quality-reviewer'],
    enabled: true,
    isDefault: true,
  },
  {
    id: 'focused-changes',
    statement: 'Keep changes focused. Don\'t refactor surrounding code unless it\'s part of the task',
    rationale: 'Scope creep makes reviews harder and introduces unrelated risk',
    category: 'workflow',
    enforcement: 'prefer',
    scope: ['worker'],
    enabled: true,
    isDefault: true,
  },
  {
    id: 'read-before-modify',
    statement: 'Read relevant code before modifying it. Never propose changes to code you haven\'t read',
    rationale: 'Blind modifications break assumptions and miss existing constraints',
    category: 'workflow',
    enforcement: 'enforce',
    scope: ['worker'],
    enabled: true,
    isDefault: true,
  },
  {
    id: 'reassess-on-failure',
    statement: 'When encountering repeated failures (3+ attempts), stop and reassess the approach rather than continuing to iterate',
    rationale: 'Repeated failures signal a wrong approach — iteration without reflection wastes resources',
    category: 'workflow',
    enforcement: 'prefer',
    scope: ['worker'],
    enabled: true,
    isDefault: true,
  },
];

const OPTIONAL_RULES: RuleEntry[] = [
  {
    id: 'no-singletons',
    statement: 'No singletons in production code',
    rationale: 'Singletons create hidden coupling and make testing difficult',
    category: 'patterns',
    enforcement: 'enforce',
    scope: ['worker'],
    enabled: false,
    isDefault: true,
  },
  {
    id: 'api-integration-tests',
    statement: 'All public APIs must have integration tests',
    rationale: 'Public APIs are contracts — integration tests verify the contract holds',
    category: 'testing',
    enforcement: 'enforce',
    scope: ['worker'],
    enabled: false,
    isDefault: true,
  },
  {
    id: 'result-types',
    statement: 'Error handling uses Result/Either types, not exceptions',
    rationale: 'Result types make error paths explicit and compiler-checked',
    category: 'patterns',
    enforcement: 'prefer',
    scope: ['worker'],
    enabled: false,
    isDefault: true,
  },
  {
    id: 'function-length',
    statement: 'Every function over 30 lines should be considered for decomposition',
    rationale: 'Long functions are harder to understand, test, and maintain',
    category: 'code-quality',
    enforcement: 'guide',
    scope: ['quality-reviewer'],
    enabled: false,
    isDefault: true,
  },
  {
    id: 'security-governance',
    statement: 'Security-sensitive operations require governance review',
    rationale: 'Authentication, authorization, and data handling need human oversight',
    category: 'security',
    enforcement: 'enforce',
    scope: ['worker'],
    enabled: false,
    isDefault: true,
  },
];

const CATEGORY_LABELS: Record<RuleCategory, string> = {
  testing: 'Testing',
  'code-quality': 'Code Quality',
  security: 'Security',
  performance: 'Performance',
  patterns: 'Patterns',
  workflow: 'Workflow',
  custom: 'Custom',
};

const ENFORCEMENT_LABELS: Record<RuleEnforcement, { label: string; color: string }> = {
  enforce: { label: 'Enforce', color: 'bg-tier-vision text-white' },
  prefer: { label: 'Prefer', color: 'bg-tier-architecture text-white' },
  guide: { label: 'Guide', color: 'bg-vscode-btn2-bg text-vscode-btn2-fg' },
};

const SCOPE_LABELS: Record<RuleScope, string> = {
  all: 'All Agents',
  worker: 'Worker',
  'quality-reviewer': 'Quality Reviewer',
  researcher: 'Researcher',
  steward: 'Steward',
};

const CATEGORY_ORDER: RuleCategory[] = ['testing', 'code-quality', 'workflow', 'patterns', 'security', 'performance', 'custom'];

// Rough estimate: ~4 tokens per word, average rule ~12 words
function estimateTokens(rules: RuleEntry[]): number {
  const enabledRules = rules.filter(r => r.enabled);
  // Header + structure overhead (~30 tokens) + ~4 tokens per word per rule
  const headerTokens = 30;
  const ruleTokens = enabledRules.reduce((sum, r) => {
    const words = r.statement.split(/\s+/).length;
    return sum + (words * 4) + 8; // +8 for bullet formatting
  }, 0);
  return headerTokens + ruleTokens;
}

function getTokenBudgetColor(tokens: number): string {
  if (tokens < 300) return 'text-tier-quality';
  if (tokens < 500) return 'text-amber-400';
  return 'text-red-400';
}

function getTokenBudgetBarColor(tokens: number): string {
  if (tokens < 300) return 'bg-tier-quality';
  if (tokens < 500) return 'bg-amber-400';
  return 'bg-red-400';
}

export function RulesStep({ config, updateConfig }: RulesStepProps) {
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [customStatement, setCustomStatement] = useState('');
  const [customRationale, setCustomRationale] = useState('');
  const [customCategory, setCustomCategory] = useState<RuleCategory>('custom');
  const [customEnforcement, setCustomEnforcement] = useState<RuleEnforcement>('enforce');
  const [customScope, setCustomScope] = useState<RuleScope[]>(['worker']);

  // Initialize rules from config or defaults
  const currentRules: RuleEntry[] = config.rules?.entries ?? [...DEFAULT_RULES, ...OPTIONAL_RULES];

  const updateRules = (entries: RuleEntry[]) => {
    const rulesConfig: RulesConfig = {
      version: 1,
      entries,
      injectionMode: config.rules?.injectionMode ?? 'compact',
      maxTokenBudget: config.rules?.maxTokenBudget ?? 400,
    };
    updateConfig({ rules: rulesConfig });
  };

  const handleToggle = (ruleId: string) => {
    const updated = currentRules.map(r =>
      r.id === ruleId ? { ...r, enabled: !r.enabled } : r
    );
    updateRules(updated);
  };

  const handleAddCustomRule = () => {
    if (!customStatement.trim()) return;

    const newRule: RuleEntry = {
      id: `custom-${Date.now()}`,
      statement: customStatement.trim(),
      rationale: customRationale.trim() || 'Custom project rule',
      category: customCategory,
      enforcement: customEnforcement,
      scope: customScope,
      enabled: true,
      isDefault: false,
    };

    updateRules([...currentRules, newRule]);

    // Reset form
    setCustomStatement('');
    setCustomRationale('');
    setCustomCategory('custom');
    setCustomEnforcement('enforce');
    setCustomScope(['worker']);
    setShowCustomForm(false);
  };

  const handleRemoveCustomRule = (ruleId: string) => {
    const updated = currentRules.filter(r => r.id !== ruleId);
    updateRules(updated);
  };

  const handleScopeToggle = (scope: RuleScope) => {
    setCustomScope(prev =>
      prev.includes(scope) ? prev.filter(s => s !== scope) : [...prev, scope]
    );
  };

  // Group rules by category for display
  const groupedRules = CATEGORY_ORDER.map(category => ({
    category,
    label: CATEGORY_LABELS[category],
    rules: currentRules.filter(r => r.category === category),
  })).filter(g => g.rules.length > 0);

  const enabledCount = currentRules.filter(r => r.enabled).length;
  const estimatedTokens = estimateTokens(currentRules);
  const tokenBudget = config.rules?.maxTokenBudget ?? 400;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-2">Project Rules</h3>
        <p className="text-vscode-muted">
          Rules guide agent behavior during sessions. They are injected into every agent's
          context at spawn time as concise imperatives.
        </p>
      </div>

      {/* Warning banner */}
      <div className="p-3 rounded bg-amber-500/10 border border-amber-500/30 text-sm">
        <strong>Balance matters.</strong> Too many rules reduce agent effectiveness — agents focus on
        compliance instead of problem-solving. We recommend 8-12 high-impact rules.
        Deterministic checks (linting, formatting, build) are enforced by quality gates, not rules.
        Rules are for behavioral guidance that tools can't check.
      </div>

      {/* Token budget meter */}
      <div className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm">
            <span className="font-medium">{enabledCount}</span>
            <span className="text-vscode-muted"> rules enabled</span>
          </div>
          <div className={`text-sm font-medium ${getTokenBudgetColor(estimatedTokens)}`}>
            ~{estimatedTokens} / {tokenBudget} tokens
          </div>
        </div>
        <div className="w-full h-2 bg-vscode-bg rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${getTokenBudgetBarColor(estimatedTokens)}`}
            style={{ width: `${Math.min(100, (estimatedTokens / tokenBudget) * 100)}%` }}
          />
        </div>
        <p className="text-xs text-vscode-muted mt-1">
          Estimated context cost of enabled rules. Each rule consumes tokens from the agent's context window.
        </p>
      </div>

      {/* Rules by category */}
      <div className="space-y-4">
        {groupedRules.map(group => (
          <div key={group.category} className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
            <h4 className="font-medium mb-3">{group.label}</h4>
            <div className="space-y-3">
              {group.rules.map(rule => (
                <label
                  key={rule.id}
                  className="flex items-start gap-3 cursor-pointer group"
                >
                  <input
                    type="checkbox"
                    checked={rule.enabled}
                    onChange={() => handleToggle(rule.id)}
                    className="mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm">{rule.statement}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase whitespace-nowrap ${ENFORCEMENT_LABELS[rule.enforcement].color}`}>
                        {ENFORCEMENT_LABELS[rule.enforcement].label}
                      </span>
                      {!rule.isDefault && (
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            handleRemoveCustomRule(rule.id);
                          }}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30"
                          title="Remove custom rule"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    <p className="text-xs text-vscode-muted mt-0.5">{rule.rationale}</p>
                    <div className="flex gap-1 mt-1">
                      {rule.scope.map(s => (
                        <span key={s} className="text-[10px] px-1 py-0.5 rounded bg-vscode-bg text-vscode-muted">
                          {SCOPE_LABELS[s]}
                        </span>
                      ))}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Add Custom Rule */}
      {!showCustomForm ? (
        <button
          onClick={() => setShowCustomForm(true)}
          className="px-4 py-2 rounded border border-dashed border-vscode-border text-vscode-muted hover:border-vscode-btn-bg hover:text-vscode-fg transition-colors w-full"
        >
          + Add Custom Rule
        </button>
      ) : (
        <div className="p-4 rounded-lg border border-vscode-btn-bg bg-vscode-widget-bg space-y-4">
          <h4 className="font-medium">New Custom Rule</h4>

          <div>
            <label className="block text-sm font-medium mb-1">Statement</label>
            <input
              type="text"
              value={customStatement}
              onChange={e => setCustomStatement(e.target.value)}
              placeholder="Concise imperative, e.g., 'All database queries must use parameterized statements'"
              className="w-full px-3 py-2 rounded bg-vscode-bg border border-vscode-border text-sm focus:border-vscode-btn-bg outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Rationale</label>
            <input
              type="text"
              value={customRationale}
              onChange={e => setCustomRationale(e.target.value)}
              placeholder="One sentence explaining why (shown here, not injected into agent context)"
              className="w-full px-3 py-2 rounded bg-vscode-bg border border-vscode-border text-sm focus:border-vscode-btn-bg outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <select
                value={customCategory}
                onChange={e => setCustomCategory(e.target.value as RuleCategory)}
                className="w-full px-3 py-2 rounded bg-vscode-bg border border-vscode-border text-sm"
              >
                {CATEGORY_ORDER.map(cat => (
                  <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Enforcement</label>
              <select
                value={customEnforcement}
                onChange={e => setCustomEnforcement(e.target.value as RuleEnforcement)}
                className="w-full px-3 py-2 rounded bg-vscode-bg border border-vscode-border text-sm"
              >
                <option value="enforce">Enforce (must follow)</option>
                <option value="prefer">Prefer (explain deviation)</option>
                <option value="guide">Guide (awareness only)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Applies to</label>
            <div className="flex flex-wrap gap-2">
              {(['worker', 'quality-reviewer', 'researcher', 'steward'] as RuleScope[]).map(scope => (
                <label key={scope} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={customScope.includes(scope)}
                    onChange={() => handleScopeToggle(scope)}
                  />
                  <span className="text-sm">{SCOPE_LABELS[scope]}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setShowCustomForm(false)}
              className="px-3 py-1.5 rounded bg-vscode-btn2-bg text-vscode-btn2-fg text-sm hover:opacity-80"
            >
              Cancel
            </button>
            <button
              onClick={handleAddCustomRule}
              disabled={!customStatement.trim()}
              className="px-3 py-1.5 rounded bg-vscode-btn-bg text-vscode-btn-fg text-sm hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Add Rule
            </button>
          </div>
        </div>
      )}

      <div className="p-3 rounded bg-blue-500/10 border border-blue-500/30 text-sm">
        <strong>How it works:</strong> Enabled rules are compiled into a concise preamble and injected
        into every agent session at spawn time. The preamble groups rules by enforcement level
        (Enforce, then Prefer). Rationale is not injected — it stays in the Knowledge Graph for agents
        that need deeper context.
      </div>
    </div>
  );
}
