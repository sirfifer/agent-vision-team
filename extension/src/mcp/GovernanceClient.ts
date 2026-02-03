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
}
