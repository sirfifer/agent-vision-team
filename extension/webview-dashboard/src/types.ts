// Mirrors extension/src/models/* — keep in sync manually

export type ProtectionTier = 'vision' | 'architecture' | 'quality';

// ─────────────────────────────────────────────────────────────────────────────
// Project Configuration Types (mirrors extension/src/models/ProjectConfig.ts)
// ─────────────────────────────────────────────────────────────────────────────

export type PermissionCategory = 'build' | 'test' | 'lint' | 'mcp' | 'git' | 'other';

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

export interface ProjectConfig {
  version: number;
  setupComplete: boolean;
  languages: string[];
  settings: ProjectSettings;
  quality: QualityConfig;
  permissions: string[];
  ingestion: IngestionStatus;
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
  | 'permissions'
  | 'settings'
  | 'ingestion'
  | 'complete';

export const WIZARD_STEPS: WizardStep[] = [
  'welcome',
  'vision-docs',
  'architecture-docs',
  'quality-config',
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
  'permissions': 'Permissions',
  'settings': 'Settings',
  'ingestion': 'Ingestion',
  'complete': 'Complete',
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

export type AgentRole = 'orchestrator' | 'worker' | 'quality-reviewer' | 'kg-librarian' | 'governance-reviewer';
export type AgentStatusValue = 'active' | 'idle' | 'not-configured';
export type ActivityType = 'finding' | 'guidance' | 'response' | 'status' | 'drift' | 'decision' | 'review';

export interface AgentStatus {
  id: string;
  name: string;
  role: AgentRole;
  status: AgentStatusValue;
  currentTask?: string;
  lastActivity?: string;
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
  // Setup wizard and config
  setupReadiness?: SetupReadiness;
  projectConfig?: ProjectConfig;
  visionDocs?: DocumentInfo[];
  architectureDocs?: DocumentInfo[];
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
  | { type: 'documentCreated'; docType: 'vision' | 'architecture'; doc: DocumentInfo };

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
  | { type: 'listArchDocs' };

export interface IngestionResult {
  tier: 'vision' | 'architecture';
  ingested: number;
  entities: string[];
  errors: string[];
  skipped: string[];
}
