// Mirrors extension/src/models/* — keep in sync manually

export type ProtectionTier = 'vision' | 'architecture' | 'quality';

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
}

// Message types between extension host and webview
export type ExtensionMessage =
  | { type: 'update'; data: DashboardData }
  | { type: 'activityAdd'; entry: ActivityEntry };

export type WebviewMessage =
  | { type: 'connect' }
  | { type: 'refresh' }
  | { type: 'validate' };
