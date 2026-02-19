import { McpClientService } from '../services/McpClientService';

export interface GateResult {
  passed: boolean;
  detail?: string;
}

export interface GateResults {
  build: GateResult;
  lint: GateResult & { violations?: number };
  tests: GateResult & { failures?: number };
  coverage: GateResult & { percentage?: number };
  findings: GateResult & { critical?: number };
  all_passed: boolean;
}

export class QualityClient {
  constructor(private mcp: McpClientService) {}

  async autoFormat(params?: {
    files?: string[];
    language?: string;
  }): Promise<{ formatted: string[]; unchanged: string[] }> {
    return (await this.mcp.callTool('quality', 'auto_format', params ?? {})) as {
      formatted: string[];
      unchanged: string[];
    };
  }

  async runLint(params?: {
    files?: string[];
    language?: string;
  }): Promise<{ findings: unknown[]; auto_fixable: number; total: number }> {
    return (await this.mcp.callTool('quality', 'run_lint', params ?? {})) as {
      findings: unknown[];
      auto_fixable: number;
      total: number;
    };
  }

  async runTests(params?: {
    scope?: string;
    language?: string;
  }): Promise<{ passed: number; failed: number; skipped: number; failures: unknown[] }> {
    return (await this.mcp.callTool('quality', 'run_tests', params ?? {})) as {
      passed: number;
      failed: number;
      skipped: number;
      failures: unknown[];
    };
  }

  async checkCoverage(params?: {
    language?: string;
  }): Promise<{ percentage: number; target: number; met: boolean; uncovered_files: string[] }> {
    return (await this.mcp.callTool('quality', 'check_coverage', params ?? {})) as {
      percentage: number;
      target: number;
      met: boolean;
      uncovered_files: string[];
    };
  }

  async checkAllGates(): Promise<GateResults> {
    return (await this.mcp.callTool('quality', 'check_all_gates', {})) as GateResults;
  }

  async validate(): Promise<{ gates: GateResults; summary: string; all_passed: boolean }> {
    return (await this.mcp.callTool('quality', 'validate', {})) as {
      gates: GateResults;
      summary: string;
      all_passed: boolean;
    };
  }

  async getTrustDecision(findingId: string): Promise<{
    decision: 'BLOCK' | 'INVESTIGATE' | 'TRACK';
    rationale: string;
  }> {
    return (await this.mcp.callTool('quality', 'get_trust_decision', {
      finding_id: findingId,
    })) as { decision: 'BLOCK' | 'INVESTIGATE' | 'TRACK'; rationale: string };
  }

  async recordDismissal(
    findingId: string,
    justification: string,
    dismissedBy: string,
  ): Promise<{ recorded: boolean }> {
    return (await this.mcp.callTool('quality', 'record_dismissal', {
      finding_id: findingId,
      justification,
      dismissed_by: dismissedBy,
    })) as { recorded: boolean };
  }

  async getAllFindings(status?: string): Promise<{
    findings: Array<{
      id: string;
      tool: string;
      severity: string;
      component: string | null;
      description: string;
      created_at: string;
      status: string;
    }>;
  }> {
    return (await this.mcp.callTool('quality', 'get_all_findings', {
      ...(status ? { status } : {}),
    })) as {
      findings: Array<{
        id: string;
        tool: string;
        severity: string;
        component: string | null;
        description: string;
        created_at: string;
        status: string;
      }>;
    };
  }

  async getDismissalHistory(findingId: string): Promise<{
    history: Array<{
      dismissed_by: string;
      justification: string;
      dismissed_at: string;
    }>;
  }> {
    return (await this.mcp.callTool('quality', 'get_dismissal_history', {
      finding_id: findingId,
    })) as {
      history: Array<{ dismissed_by: string; justification: string; dismissed_at: string }>;
    };
  }
}
