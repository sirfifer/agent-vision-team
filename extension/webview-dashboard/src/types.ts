// Mirrors extension/src/models/* — keep in sync manually

export type ProtectionTier = 'vision' | 'architecture' | 'quality';

// ─────────────────────────────────────────────────────────────────────────────
// Project Configuration Types (mirrors extension/src/models/ProjectConfig.ts)
// ─────────────────────────────────────────────────────────────────────────────

export type PermissionCategory = 'build' | 'test' | 'lint' | 'deps' | 'mcp' | 'git' | 'other';

export interface PermissionEntry {
  pattern: string;
  description: string;
  recommended: boolean;
  category: PermissionCategory;
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

export interface ProjectMetadata {
  name?: string;
  description?: string;
  isOpenSource: boolean;
  license?: string;
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

export type RuleCategory = 'testing' | 'code-quality' | 'security' | 'performance' | 'patterns' | 'workflow' | 'custom';
export type RuleEnforcement = 'enforce' | 'prefer' | 'guide';
export type RuleScope = 'all' | 'worker' | 'quality-reviewer' | 'researcher' | 'steward';

export interface RuleEntry {
  id: string;
  statement: string;
  rationale: string;
  category: RuleCategory;
  enforcement: RuleEnforcement;
  scope: RuleScope[];
  enabled: boolean;
  isDefault: boolean;
}

export interface RulesConfig {
  version: number;
  entries: RuleEntry[];
  injectionMode: 'compact' | 'verbose';
  maxTokenBudget: number;
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
  rules?: RulesConfig;
}

export interface SetupReadiness {
  isComplete: boolean;
  hasVisionDocs: boolean;
  hasArchitectureDocs: boolean;
  hasProjectConfig: boolean;
  hasKgIngestion: boolean;
  visionDocCount: number;
  architectureDocCount: number;
}

export interface DocumentInfo {
  name: string;
  path: string;
  title?: string;
}

export type WizardStep =
  | 'welcome'
  | 'vision-docs'
  | 'architecture-docs'
  | 'quality-config'
  | 'rules'
  | 'permissions'
  | 'settings'
  | 'ingestion'
  | 'complete';

export const WIZARD_STEPS: WizardStep[] = [
  'welcome',
  'vision-docs',
  'architecture-docs',
  'quality-config',
  'rules',
  'permissions',
  'settings',
  'ingestion',
  'complete',
];

export const WIZARD_STEP_LABELS: Record<WizardStep, string> = {
  'welcome': 'Welcome',
  'vision-docs': 'Vision Docs',
  'architecture-docs': 'Architecture Docs',
  'quality-config': 'Quality Config',
  'rules': 'Rules',
  'permissions': 'Permissions',
  'settings': 'Settings',
  'ingestion': 'Ingestion',
  'complete': 'Complete',
};

// ─────────────────────────────────────────────────────────────────────────────
// Tutorial Step Types
// ─────────────────────────────────────────────────────────────────────────────

export type TutorialStep =
  | 'welcome'
  | 'big-picture'
  | 'setup'
  | 'starting-work'
  | 'behind-scenes'
  | 'monitoring'
  | 'knowledge-graph'
  | 'quality-gates'
  | 'tips'
  | 'ready';

export const TUTORIAL_STEPS: TutorialStep[] = [
  'welcome',
  'big-picture',
  'setup',
  'starting-work',
  'behind-scenes',
  'monitoring',
  'knowledge-graph',
  'quality-gates',
  'tips',
  'ready',
];

export const TUTORIAL_STEP_LABELS: Record<TutorialStep, string> = {
  'welcome': 'Welcome',
  'big-picture': 'Big Picture',
  'setup': 'Run Setup',
  'starting-work': 'Start Work',
  'behind-scenes': 'Behind the Scenes',
  'monitoring': 'Monitoring',
  'knowledge-graph': 'Knowledge Graph',
  'quality-gates': 'Quality Gates',
  'tips': 'Tips',
  'ready': 'Ready!',
};

export const SUPPORTED_LANGUAGES = ['python', 'typescript', 'javascript', 'swift', 'rust'] as const;
export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number];

export type EntityType =
  | 'component'
  | 'vision_standard'
  | 'architectural_standard'
  | 'pattern'
  | 'problem'
  | 'solution_pattern';

export interface Entity {
  name: string;
  entityType: EntityType;
  observations: string[];
  relations: { from: string; to: string; relationType: string }[];
}

export type AgentRole = 'orchestrator' | 'worker' | 'quality-reviewer' | 'kg-librarian' | 'governance-reviewer' | 'researcher' | 'project-steward';
export type AgentStatusValue = 'active' | 'idle' | 'blocked' | 'reviewing' | 'not-configured';
export type ActivityType = 'finding' | 'guidance' | 'response' | 'status' | 'drift' | 'decision' | 'review' | 'research';

// ─────────────────────────────────────────────────────────────────────────────
// Governed Task Types
// ─────────────────────────────────────────────────────────────────────────────

export type GovernedTaskStatus = 'pending_review' | 'approved' | 'blocked' | 'in_progress' | 'completed';
export type TaskReviewStatusValue = 'pending' | 'approved' | 'blocked' | 'needs_human_review';

export interface TaskReviewInfo {
  id: string;
  reviewType: string;
  status: TaskReviewStatusValue;
  verdict?: string;
  guidance?: string;
  createdAt: string;
  completedAt?: string;
}

export interface GovernedTask {
  id: string;
  implementationTaskId: string;
  subject: string;
  status: GovernedTaskStatus;
  reviews: TaskReviewInfo[];
  createdAt: string;
  releasedAt?: string;
}

export interface GovernanceStats {
  totalDecisions: number;
  approved: number;
  blocked: number;
  pending: number;
  pendingReviews: number;
  totalGovernedTasks: number;
  needsHumanReview: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Quality Gate Types
// ─────────────────────────────────────────────────────────────────────────────

export interface GateResult {
  name: string;
  passed: boolean;
  detail?: string;
}

export interface QualityGateResults {
  build: GateResult;
  lint: GateResult;
  tests: GateResult;
  coverage: GateResult;
  findings: GateResult;
  all_passed: boolean;
  timestamp?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Decision History Types
// ─────────────────────────────────────────────────────────────────────────────

export interface DecisionHistoryEntry {
  id: string;
  taskId: string;
  agent: string;
  category: string;
  summary: string;
  confidence: string;
  verdict: string | null;
  guidance: string;
  createdAt: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Trust Engine / Findings Types
// ─────────────────────────────────────────────────────────────────────────────

export interface TrustFinding {
  id: string;
  tool: string;
  severity: string;
  component?: string;
  description: string;
  createdAt: string;
  status: 'open' | 'dismissed';
}

export interface DismissalHistoryEntry {
  dismissedBy: string;
  justification: string;
  dismissedAt: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Hook Governance Status Types
// ─────────────────────────────────────────────────────────────────────────────

export interface HookGovernanceStatus {
  totalInterceptions: number;
  lastInterceptionAt?: string;
  recentInterceptions: Array<{ timestamp: string; subject: string }>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Session State Types
// ─────────────────────────────────────────────────────────────────────────────

export interface SessionState {
  phase: string;
  lastCheckpoint?: string;
  activeWorktrees?: string[];
  driftStatus?: { type: string; description: string } | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Research Brief Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ResearchBriefInfo {
  name: string;
  path: string;
  modifiedAt: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Research Prompt Types
// ─────────────────────────────────────────────────────────────────────────────

export type ResearchType = 'periodic' | 'exploratory';
export type ResearchModelHint = 'opus' | 'sonnet' | 'auto';
export type ResearchOutputFormat = 'change_report' | 'research_brief' | 'custom';
export type ResearchStatus = 'pending' | 'scheduled' | 'in_progress' | 'completed' | 'failed';

export interface ResearchSchedule {
  type: 'once' | 'daily' | 'weekly' | 'monthly';
  dayOfWeek?: number;  // 0-6 for weekly
  dayOfMonth?: number; // 1-31 for monthly
  time?: string;       // HH:MM format
  lastRun?: string;    // ISO timestamp
  nextRun?: string;    // ISO timestamp
}

export interface ResearchPrompt {
  id: string;
  name: string;
  type: ResearchType;
  topic: string;
  context: string;
  scope: string;
  modelHint: ResearchModelHint;
  output: ResearchOutputFormat;
  relatedEntities: string[];
  schedule?: ResearchSchedule;
  status: ResearchStatus;
  createdAt: string;
  updatedAt: string;
  lastResult?: {
    timestamp: string;
    success: boolean;
    summary?: string;
    briefPath?: string;
    error?: string;
  };
}

export interface AgentStatus {
  id: string;
  name: string;
  role: AgentRole;
  status: AgentStatusValue;
  currentTask?: string;
  lastActivity?: string;
  governedTaskId?: string;
  blockedBy?: string[];
}

export interface ActivityEntry {
  id: string;
  timestamp: string;
  agent: string;
  type: ActivityType;
  tier?: ProtectionTier;
  summary: string;
  detail?: string;
  governanceRef?: string;
}

export interface DashboardData {
  connectionStatus: 'connected' | 'disconnected' | 'error';
  serverPorts: { kg: number; quality: number; governance: number };
  agents: AgentStatus[];
  visionStandards: Entity[];
  architecturalElements: Entity[];
  activities: ActivityEntry[];
  tasks: { active: number; total: number };
  sessionPhase: string;
  // Governed tasks and governance stats
  governedTasks: GovernedTask[];
  governanceStats: GovernanceStats;
  // Quality gates
  qualityGateResults?: QualityGateResults;
  // Decision history
  decisionHistory?: DecisionHistoryEntry[];
  // Trust engine findings
  findings?: TrustFinding[];
  // Hook governance
  hookGovernanceStatus?: HookGovernanceStatus;
  // Session state
  sessionState?: SessionState;
  // Setup wizard and config
  setupReadiness?: SetupReadiness;
  projectConfig?: ProjectConfig;
  visionDocs?: DocumentInfo[];
  architectureDocs?: DocumentInfo[];
  // Research prompts
  researchPrompts?: ResearchPrompt[];
  // Research briefs
  researchBriefs?: ResearchBriefInfo[];
  // Job summary for status bar
  jobSummary?: { running: number; queued: number; total: number };
}

// Message types between extension host and webview
export type ExtensionMessage =
  | { type: 'update'; data: DashboardData }
  | { type: 'activityAdd'; entry: ActivityEntry }
  | { type: 'setupReadiness'; readiness: SetupReadiness }
  | { type: 'projectConfig'; config: ProjectConfig }
  | { type: 'visionDocs'; docs: DocumentInfo[] }
  | { type: 'architectureDocs'; docs: DocumentInfo[] }
  | { type: 'ingestionResult'; result: IngestionResult }
  | { type: 'documentCreated'; docType: 'vision' | 'architecture'; doc: DocumentInfo }
  | { type: 'researchPrompts'; prompts: ResearchPrompt[] }
  | { type: 'researchPromptUpdated'; prompt: ResearchPrompt }
  | { type: 'researchPromptDeleted'; id: string }
  | { type: 'governedTasks'; tasks: GovernedTask[] }
  | { type: 'governanceStats'; stats: GovernanceStats }
  | { type: 'formatDocContentResult'; requestId: string; success: boolean; formattedContent?: string; error?: string }
  | { type: 'findingsUpdate'; findings: TrustFinding[] }
  | { type: 'findingDismissed'; findingId: string; success: boolean }
  | { type: 'researchBriefContent'; briefPath: string; content: string; error?: string }
  | { type: 'researchBriefsList'; briefs: ResearchBriefInfo[] }
  | { type: 'showWizard' }
  | { type: 'showTutorial' }
  | { type: 'toggleDemo' };

export type WebviewMessage =
  | { type: 'connect' }
  | { type: 'refresh' }
  | { type: 'validate' }
  | { type: 'checkSetup' }
  | { type: 'saveProjectConfig'; config: ProjectConfig }
  | { type: 'createVisionDoc'; name: string; content: string }
  | { type: 'createArchDoc'; name: string; content: string }
  | { type: 'ingestDocs'; tier: 'vision' | 'architecture' }
  | { type: 'openSettings' }
  | { type: 'savePermissions'; permissions: string[] }
  | { type: 'listVisionDocs' }
  | { type: 'listArchDocs' }
  | { type: 'listResearchPrompts' }
  | { type: 'saveResearchPrompt'; prompt: ResearchPrompt }
  | { type: 'deleteResearchPrompt'; id: string }
  | { type: 'runResearchPrompt'; id: string }
  | { type: 'requestGovernedTasks' }
  | { type: 'formatDocContent'; tier: 'vision' | 'architecture'; rawContent: string; requestId: string }
  | { type: 'dismissFinding'; findingId: string; justification: string; dismissedBy: string }
  | { type: 'requestFindings' }
  | { type: 'readResearchBrief'; briefPath: string }
  | { type: 'listResearchBriefs' };

export interface IngestionResult {
  tier: 'vision' | 'architecture';
  ingested: number;
  entities: string[];
  errors: string[];
  skipped: string[];
}
