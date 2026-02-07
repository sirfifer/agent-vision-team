import { McpClientService } from '../services/McpClientService';

export interface GovernanceFinding {
  tier: string;
  severity: string;
  description: string;
  suggestion: string;
}

export interface DecisionVerdict {
  verdict: 'approved' | 'blocked' | 'needs_human_review';
  decision_id: string;
  findings: GovernanceFinding[];
  guidance: string;
  standards_verified: string[];
}

export interface PlanVerdict {
  verdict: 'approved' | 'blocked' | 'needs_human_review';
  review_id: string;
  findings: GovernanceFinding[];
  guidance: string;
  decisions_reviewed: number;
  standards_verified: string[];
}

export interface CompletionVerdict {
  verdict: 'approved' | 'blocked' | 'needs_human_review';
  review_id: string;
  unreviewed_decisions: string[];
  findings: GovernanceFinding[];
  guidance: string;
}

export interface DecisionHistoryEntry {
  id: string;
  task_id: string;
  sequence: number;
  agent: string;
  category: string;
  summary: string;
  confidence: string;
  verdict: string | null;
  guidance: string;
  created_at: string;
}

export interface GovernanceStatus {
  total_decisions: number;
  approved: number;
  blocked: number;
  needs_human_review: number;
  pending: number;
  recent_activity: Array<{
    summary: string;
    agent: string;
    category: string;
    verdict: string | null;
  }>;
  task_governance?: TaskGovernanceStats;
}

export interface TaskGovernanceStats {
  total_governed_tasks: number;
  pending_review: number;
  approved: number;
  blocked: number;
  pending_reviews: number;
}

export interface PendingReviewEntry {
  id: string;
  review_task_id: string;
  implementation_task_id: string;
  type: string;
  context: string;
  created_at: string;
}

export interface GovernedTaskEntry {
  task_id: string;
  subject: string;
  status: string;
  is_blocked: boolean;
  can_execute: boolean;
  reviews: Array<{
    id: string;
    review_task_id: string;
    type: string;
    status: string;
    verdict: string | null;
    guidance: string;
    created_at: string;
    completed_at: string | null;
  }>;
  blockers_from_files: Array<{
    id: string;
    subject: string;
    status: string;
    review_type: string;
  }>;
}

export class GovernanceClient {
  constructor(private mcp: McpClientService) {}

  async getGovernanceStatus(): Promise<GovernanceStatus> {
    return (await this.mcp.callTool('governance', 'get_governance_status', {})) as GovernanceStatus;
  }

  async getDecisionHistory(params?: {
    task_id?: string;
    agent?: string;
    verdict?: string;
  }): Promise<{ decisions: DecisionHistoryEntry[] }> {
    return (await this.mcp.callTool('governance', 'get_decision_history', params ?? {})) as {
      decisions: DecisionHistoryEntry[];
    };
  }

  async getPendingReviews(): Promise<{ pending_reviews: PendingReviewEntry[]; count: number }> {
    return (await this.mcp.callTool('governance', 'get_pending_reviews', {})) as {
      pending_reviews: PendingReviewEntry[];
      count: number;
    };
  }

  async getTaskReviewStatus(implementationTaskId: string): Promise<GovernedTaskEntry> {
    return (await this.mcp.callTool('governance', 'get_task_review_status', {
      implementation_task_id: implementationTaskId,
    })) as GovernedTaskEntry;
  }

  async listGovernedTasks(params?: {
    status?: string;
    limit?: number;
  }): Promise<{ governed_tasks: GovernedTaskListEntry[]; total: number }> {
    return (await this.mcp.callTool('governance', 'list_governed_tasks', params ?? {})) as {
      governed_tasks: GovernedTaskListEntry[];
      total: number;
    };
  }
}

export interface GovernedTaskListEntry {
  id: string;
  implementation_task_id: string;
  subject: string;
  description: string;
  current_status: string;
  created_at: string;
  released_at: string | null;
  reviews: Array<{
    id: string;
    review_task_id: string;
    review_type: string;
    status: string;
    verdict: string | null;
    guidance: string;
    findings: unknown[];
    created_at: string;
    completed_at: string | null;
  }>;
}
