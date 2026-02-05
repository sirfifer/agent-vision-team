/**
 * Project configuration types for the AVT system.
 * Configuration is stored in .avt/project-config.json
 */

export interface PermissionEntry {
  pattern: string;
  description: string;
  recommended: boolean;
  category: 'build' | 'test' | 'lint' | 'deps' | 'mcp' | 'git' | 'other';
}

export interface QualityGatesConfig {
  build: boolean;
  lint: boolean;
  tests: boolean;
  coverage: boolean;
  findings: boolean;
}

export interface ProjectSettings {
  mockTests: boolean;
  mockTestsForCostlyOps: boolean;
  coverageThreshold: number;
  autoGovernance: boolean;
  qualityGates: QualityGatesConfig;
  kgAutoCuration: boolean;
}

export interface QualityConfig {
  testCommands: Record<string, string>;
  lintCommands: Record<string, string>;
  buildCommands: Record<string, string>;
  formatCommands: Record<string, string>;
}

export interface IngestionStatus {
  lastVisionIngest: string | null;
  lastArchitectureIngest: string | null;
  visionDocCount: number;
  architectureDocCount: number;
}

export interface ProjectMetadata {
  name?: string;
  description?: string;
  isOpenSource: boolean;
  license?: string;
}

export interface ProjectConfig {
  version: number;
  setupComplete: boolean;
  languages: string[];
  metadata: ProjectMetadata;
  settings: ProjectSettings;
  quality: QualityConfig;
  permissions: string[];
  ingestion: IngestionStatus;
}

export interface SetupReadiness {
  hasVisionDocs: boolean;
  hasArchitectureDocs: boolean;
  hasProjectConfig: boolean;
  hasKgIngestion: boolean;
  isComplete: boolean;
}

export const DEFAULT_PROJECT_SETTINGS: ProjectSettings = {
  mockTests: false,
  mockTestsForCostlyOps: true,
  coverageThreshold: 80,
  autoGovernance: true,
  qualityGates: {
    build: true,
    lint: true,
    tests: true,
    coverage: true,
    findings: true,
  },
  kgAutoCuration: true,
};

export const DEFAULT_QUALITY_CONFIG: QualityConfig = {
  testCommands: {
    python: 'uv run pytest',
    typescript: 'npm run test',
    javascript: 'npm run test',
  },
  lintCommands: {
    python: 'uv run ruff check',
    typescript: 'npm run lint',
    javascript: 'npm run lint',
  },
  buildCommands: {
    typescript: 'npm run build',
    javascript: 'npm run build',
  },
  formatCommands: {
    python: 'uv run ruff format',
    typescript: 'npx prettier --write',
    javascript: 'npx prettier --write',
  },
};

export const DEFAULT_PROJECT_METADATA: ProjectMetadata = {
  isOpenSource: false,
};

export const DEFAULT_PROJECT_CONFIG: ProjectConfig = {
  version: 1,
  setupComplete: false,
  languages: [],
  metadata: DEFAULT_PROJECT_METADATA,
  settings: DEFAULT_PROJECT_SETTINGS,
  quality: DEFAULT_QUALITY_CONFIG,
  permissions: [],
  ingestion: {
    lastVisionIngest: null,
    lastArchitectureIngest: null,
    visionDocCount: 0,
    architectureDocCount: 0,
  },
};

/**
 * Recommended permissions - checked by default in the wizard.
 *
 * These cover the core operations that agents need to function:
 * - Build, test, lint, format toolchains
 * - Git operations for worktree isolation, checkpoints, and merges
 * - MCP server tool calls (Knowledge Graph, Quality, Governance)
 * - E2E testing harness
 * - Governance hook dependencies (sqlite3)
 */
export const RECOMMENDED_PERMISSIONS: PermissionEntry[] = [
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
  // Git (core operations)
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
  // Other (required by governance hooks)
  { pattern: 'Bash(sqlite3:*)', description: 'Query governance DB (used by verification hooks)', recommended: true, category: 'other' },
  { pattern: 'Bash(uv run python:*)', description: 'Run Python scripts and MCP servers', recommended: true, category: 'other' },
];

/**
 * Optional permissions - unchecked by default in the wizard.
 *
 * These are potentially destructive or have side-effects that
 * warrant explicit opt-in by the user.
 */
export const OPTIONAL_PERMISSIONS: PermissionEntry[] = [
  { pattern: 'Bash(git push:*)', description: 'Push to remote (requires review)', recommended: false, category: 'git' },
  { pattern: 'Bash(git checkout:*)', description: 'Switch branches', recommended: false, category: 'git' },
  { pattern: 'Bash(npm install:*)', description: 'Install npm packages (modifies lockfile)', recommended: false, category: 'deps' },
  { pattern: 'Bash(pip install:*)', description: 'Install Python packages', recommended: false, category: 'deps' },
  { pattern: 'Bash(docker:*)', description: 'Run Docker commands', recommended: false, category: 'other' },
  { pattern: 'Bash(curl:*)', description: 'Make HTTP requests', recommended: false, category: 'other' },
  { pattern: 'Bash(pkill:*)', description: 'Kill processes (e.g., stop MCP servers)', recommended: false, category: 'other' },
];

export const ALL_PERMISSIONS: PermissionEntry[] = [...RECOMMENDED_PERMISSIONS, ...OPTIONAL_PERMISSIONS];
