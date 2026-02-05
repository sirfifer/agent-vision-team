export type AgentRole = 'orchestrator' | 'worker' | 'quality-reviewer' | 'kg-librarian' | 'governance-reviewer' | 'researcher' | 'project-steward';
export type AgentStatusValue = 'active' | 'idle' | 'blocked' | 'reviewing' | 'not-configured';
export type ActivityType = 'finding' | 'guidance' | 'response' | 'status' | 'drift' | 'decision' | 'review' | 'research';

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
  tier?: 'vision' | 'architecture' | 'quality';
  summary: string;
  detail?: string;
  governanceRef?: string;
}

// Governed task types for dashboard display
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
}
