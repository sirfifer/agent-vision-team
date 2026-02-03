export type AgentRole = 'orchestrator' | 'worker' | 'quality-reviewer' | 'kg-librarian' | 'governance-reviewer' | 'researcher';
export type AgentStatusValue = 'active' | 'idle' | 'not-configured';
export type ActivityType = 'finding' | 'guidance' | 'response' | 'status' | 'drift' | 'decision' | 'review' | 'research';

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
  tier?: 'vision' | 'architecture' | 'quality';
  summary: string;
  detail?: string;
  governanceRef?: string;
}
