import type { ProjectConfig, PermissionEntry, PermissionCategory } from '../../../types';

interface PermissionsStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

// Permission definitions matching extension/src/models/ProjectConfig.ts
const RECOMMENDED_PERMISSIONS: PermissionEntry[] = [
  // Build
  { pattern: 'Bash(npm run build:*)', description: 'Build TypeScript/JavaScript projects', recommended: true, category: 'build' },
  { pattern: 'Bash(npx tsc:*)', description: 'Run TypeScript compiler directly', recommended: true, category: 'build' },
  // Test
  { pattern: 'Bash(npm run test:*)', description: 'Run JavaScript/TypeScript tests', recommended: true, category: 'test' },
  { pattern: 'Bash(uv run pytest:*)', description: 'Run Python tests', recommended: true, category: 'test' },
  { pattern: 'Bash(./e2e/run-e2e.sh:*)', description: 'Run the E2E testing harness', recommended: true, category: 'test' },
  // Lint & Format
  { pattern: 'Bash(npm run lint:*)', description: 'Run ESLint', recommended: true, category: 'lint' },
  { pattern: 'Bash(npx eslint:*)', description: 'Run ESLint directly', recommended: true, category: 'lint' },
  { pattern: 'Bash(uv run ruff:*)', description: 'Run Python linter/formatter', recommended: true, category: 'lint' },
  { pattern: 'Bash(npx prettier:*)', description: 'Run Prettier code formatter', recommended: true, category: 'lint' },
  // Dependencies
  { pattern: 'Bash(uv sync:*)', description: 'Sync Python dependencies', recommended: true, category: 'deps' },
  { pattern: 'Bash(npm ci:*)', description: 'Clean install npm dependencies', recommended: true, category: 'deps' },
  // MCP Servers
  { pattern: 'mcp__collab-kg__*', description: 'Knowledge Graph: entities, relations, observations, search', recommended: true, category: 'mcp' },
  { pattern: 'mcp__collab-quality__*', description: 'Quality: lint, test, format, coverage, gates, trust engine', recommended: true, category: 'mcp' },
  { pattern: 'mcp__collab-governance__*', description: 'Governance: decisions, reviews, governed tasks, status', recommended: true, category: 'mcp' },
  // Git (core)
  { pattern: 'Bash(git status:*)', description: 'Check git status', recommended: true, category: 'git' },
  { pattern: 'Bash(git diff:*)', description: 'View git diffs', recommended: true, category: 'git' },
  { pattern: 'Bash(git add:*)', description: 'Stage files', recommended: true, category: 'git' },
  { pattern: 'Bash(git commit:*)', description: 'Create commits', recommended: true, category: 'git' },
  { pattern: 'Bash(git log:*)', description: 'View git history', recommended: true, category: 'git' },
  { pattern: 'Bash(git branch:*)', description: 'List and manage branches', recommended: true, category: 'git' },
  // Git (worker isolation & checkpoints)
  { pattern: 'Bash(git worktree:*)', description: 'Create/remove worktrees for parallel worker isolation', recommended: true, category: 'git' },
  { pattern: 'Bash(git tag:*)', description: 'Create checkpoint tags for recovery', recommended: true, category: 'git' },
  { pattern: 'Bash(git merge:*)', description: 'Merge worker branches after review', recommended: true, category: 'git' },
  // Other (required by system)
  { pattern: 'Bash(sqlite3:*)', description: 'Query governance DB (used by verification hooks)', recommended: true, category: 'other' },
  { pattern: 'Bash(uv run python:*)', description: 'Run Python scripts and MCP servers', recommended: true, category: 'other' },
];

const OPTIONAL_PERMISSIONS: PermissionEntry[] = [
  { pattern: 'Bash(git push:*)', description: 'Push to remote (requires review)', recommended: false, category: 'git' },
  { pattern: 'Bash(git checkout:*)', description: 'Switch branches', recommended: false, category: 'git' },
  { pattern: 'Bash(npm install:*)', description: 'Install npm packages (modifies lockfile)', recommended: false, category: 'deps' },
  { pattern: 'Bash(pip install:*)', description: 'Install Python packages', recommended: false, category: 'deps' },
  { pattern: 'Bash(docker:*)', description: 'Run Docker commands', recommended: false, category: 'other' },
  { pattern: 'Bash(curl:*)', description: 'Make HTTP requests', recommended: false, category: 'other' },
  { pattern: 'Bash(pkill:*)', description: 'Kill processes (e.g., stop MCP servers)', recommended: false, category: 'other' },
];

const CATEGORY_LABELS: Record<PermissionCategory, string> = {
  build: 'Build',
  test: 'Testing',
  lint: 'Linting & Formatting',
  deps: 'Dependencies',
  mcp: 'MCP Servers',
  git: 'Git Operations',
  other: 'Other',
};

const CATEGORY_ORDER: PermissionCategory[] = ['build', 'test', 'lint', 'deps', 'mcp', 'git', 'other'];

export function PermissionsStep({ config, updateConfig }: PermissionsStepProps) {
  const allPermissions = [...RECOMMENDED_PERMISSIONS, ...OPTIONAL_PERMISSIONS];

  const handleToggle = (pattern: string) => {
    const current = config.permissions;
    const newPermissions = current.includes(pattern)
      ? current.filter(p => p !== pattern)
      : [...current, pattern];
    updateConfig({ permissions: newPermissions });
  };

  const handleSelectAll = (recommended: boolean) => {
    const perms = recommended ? RECOMMENDED_PERMISSIONS : OPTIONAL_PERMISSIONS;
    const patterns = perms.map(p => p.pattern);
    const current = new Set(config.permissions);

    // Check if all are selected
    const allSelected = patterns.every(p => current.has(p));

    if (allSelected) {
      // Deselect all
      updateConfig({
        permissions: config.permissions.filter(p => !patterns.includes(p)),
      });
    } else {
      // Select all
      updateConfig({
        permissions: [...new Set([...config.permissions, ...patterns])],
      });
    }
  };

  const groupedPermissions = CATEGORY_ORDER.map(category => ({
    category,
    label: CATEGORY_LABELS[category],
    permissions: allPermissions.filter(p => p.category === category),
  })).filter(g => g.permissions.length > 0);

  const recommendedCount = RECOMMENDED_PERMISSIONS.filter(p =>
    config.permissions.includes(p.pattern)
  ).length;
  const optionalCount = OPTIONAL_PERMISSIONS.filter(p =>
    config.permissions.includes(p.pattern)
  ).length;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-2">Claude Code Permissions</h3>
        <p className="text-vscode-muted">
          Select which operations Claude Code can perform autonomously.
          These are written to <code className="bg-vscode-widget-bg px-1 rounded">.claude/settings.local.json</code>.
        </p>
      </div>

      {/* Summary */}
      <div className="flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded bg-tier-quality" />
          <span>Recommended: {recommendedCount}/{RECOMMENDED_PERMISSIONS.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded bg-vscode-btn2-bg" />
          <span>Optional: {optionalCount}/{OPTIONAL_PERMISSIONS.length}</span>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex gap-2">
        <button
          onClick={() => handleSelectAll(true)}
          className="px-3 py-1.5 rounded bg-tier-quality text-white text-sm hover:opacity-80 transition-opacity"
        >
          {recommendedCount === RECOMMENDED_PERMISSIONS.length ? 'Deselect' : 'Select'} All Recommended
        </button>
        <button
          onClick={() => handleSelectAll(false)}
          className="px-3 py-1.5 rounded bg-vscode-btn2-bg text-vscode-btn2-fg text-sm hover:opacity-80 transition-opacity"
        >
          {optionalCount === OPTIONAL_PERMISSIONS.length ? 'Deselect' : 'Select'} All Optional
        </button>
      </div>

      {/* Permissions by category */}
      <div className="space-y-4">
        {groupedPermissions.map(group => (
          <div key={group.category} className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
            <h4 className="font-medium mb-3">{group.label}</h4>
            <div className="space-y-2">
              {group.permissions.map(perm => (
                <label
                  key={perm.pattern}
                  className="flex items-start gap-3 cursor-pointer group"
                >
                  <input
                    type="checkbox"
                    checked={config.permissions.includes(perm.pattern)}
                    onChange={() => handleToggle(perm.pattern)}
                    className="mt-0.5"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <code className="text-sm bg-vscode-bg px-1 rounded group-hover:bg-vscode-border transition-colors">
                        {perm.pattern}
                      </code>
                      {perm.recommended && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-tier-quality text-white uppercase">
                          Recommended
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-vscode-muted">{perm.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="p-3 rounded bg-blue-500/10 border border-blue-500/30 text-sm">
        <strong>Note:</strong> These permissions allow Claude Code to run commands without asking for confirmation.
        You can always change them later in the settings panel or by editing <code>.claude/settings.local.json</code>.
      </div>
    </div>
  );
}
