import * as vscode from 'vscode';
import * as crypto from 'crypto';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { spawn } from 'child_process';
import { createInterface } from 'readline';
import { Entity } from '../models/Entity';
import { AgentStatus, ActivityEntry, GovernedTask, GovernanceStats } from '../models/Activity';
import { ProjectConfig, SetupReadiness } from '../models/ProjectConfig';
import { ResearchPrompt } from '../models/ResearchPrompt';
import { ProjectConfigService } from '../services/ProjectConfigService';

interface DocumentInfo {
  name: string;
  path: string;
  title?: string;
}

interface GateResult {
  name: string;
  passed: boolean;
  detail?: string;
}

interface QualityGateResults {
  build: GateResult;
  lint: GateResult;
  tests: GateResult;
  coverage: GateResult;
  findings: GateResult;
  all_passed: boolean;
  timestamp?: string;
}

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

interface TrustFinding {
  id: string;
  tool: string;
  severity: string;
  component?: string;
  description: string;
  createdAt: string;
  status: 'open' | 'dismissed';
}

interface HookGovernanceStatus {
  totalInterceptions: number;
  lastInterceptionAt?: string;
  recentInterceptions: Array<{ timestamp: string; subject: string }>;
}

interface SessionState {
  phase: string;
  lastCheckpoint?: string;
  activeWorktrees?: string[];
}

interface ResearchBriefInfo {
  name: string;
  path: string;
  modifiedAt: string;
}

interface DashboardData {
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
}

function getNonce(): string {
  return crypto.randomBytes(16).toString('hex');
}

export class DashboardWebviewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'collab.dashboard';

  private view?: vscode.WebviewView;
  private panel?: vscode.WebviewPanel;
  private configService?: ProjectConfigService;
  private data: DashboardData = {
    connectionStatus: 'disconnected',
    serverPorts: { kg: 3101, quality: 3102, governance: 3103 },
    agents: [],
    visionStandards: [],
    architecturalElements: [],
    activities: [],
    tasks: { active: 0, total: 0 },
    sessionPhase: 'inactive',
    governedTasks: [],
    governanceStats: {
      totalDecisions: 0,
      approved: 0,
      blocked: 0,
      pending: 0,
      pendingReviews: 0,
      totalGovernedTasks: 0,
    },
  };

  // Bootstrap streaming state
  private bootstrapActivities: Array<{ tool: string; summary: string; timestamp: number }> = [];
  private currentBootstrapPhase: string = 'Starting';
  private subAgentCount: number = 0;

  constructor(private readonly extensionUri: vscode.Uri) {}

  /**
   * Set the project config service. Called after workspace is determined.
   */
  setConfigService(configService: ProjectConfigService): void {
    this.configService = configService;
    this.refreshConfigData();
  }

  /**
   * Refresh setup readiness and config data
   */
  refreshConfigData(): void {
    if (!this.configService) return;

    const setupReadiness = this.configService.getReadiness();
    const projectConfig = this.configService.load();
    const visionDocs = this.getDocumentInfoList('vision');
    const architectureDocs = this.getDocumentInfoList('architecture');

    this.updateData({
      setupReadiness,
      projectConfig,
      visionDocs,
      architectureDocs,
    });
  }

  private getDocumentInfoList(tier: 'vision' | 'architecture'): DocumentInfo[] {
    if (!this.configService) return [];

    const docs =
      tier === 'vision'
        ? this.configService.listVisionDocs()
        : this.configService.listArchitectureDocs();

    const docsRoot = this.configService.getDocsRoot();
    return docs.map((name) => ({
      name,
      path: path.join(docsRoot, tier, name),
    }));
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;
    const distUri = vscode.Uri.joinPath(this.extensionUri, 'webview-dashboard', 'dist');
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [distUri],
    };
    webviewView.webview.html = this.getHtmlContent(webviewView.webview);
    this.registerMessageHandler(webviewView.webview);
  }

  public openPanel(): void {
    if (this.panel) {
      this.panel.reveal();
      return;
    }

    const distUri = vscode.Uri.joinPath(this.extensionUri, 'webview-dashboard', 'dist');
    this.panel = vscode.window.createWebviewPanel(
      'collab.dashboard',
      'Agent Operations Center',
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        localResourceRoots: [distUri],
        retainContextWhenHidden: true,
      },
    );

    this.panel.webview.html = this.getHtmlContent(this.panel.webview);
    this.registerMessageHandler(this.panel.webview);
    this.panel.onDidDispose(() => {
      this.panel = undefined;
    });
  }

  public updateData(update: Partial<DashboardData>): void {
    Object.assign(this.data, update);
    const msg = { type: 'update', data: this.data };
    this.panel?.webview.postMessage(msg);
    this.view?.webview.postMessage(msg);
  }

  public addActivity(entry: ActivityEntry): void {
    this.data.activities.unshift(entry);
    const msg = { type: 'activityAdd', entry };
    this.panel?.webview.postMessage(msg);
    this.view?.webview.postMessage(msg);
  }

  public showSetupWizard(): void {
    const msg = { type: 'showWizard' };
    this.panel?.webview.postMessage(msg);
    this.view?.webview.postMessage(msg);
  }

  public showTutorial(): void {
    const msg = { type: 'showTutorial' };
    this.panel?.webview.postMessage(msg);
    this.view?.webview.postMessage(msg);
  }

  public toggleDemo(): void {
    const msg = { type: 'toggleDemo' };
    this.panel?.webview.postMessage(msg);
    this.view?.webview.postMessage(msg);
  }

  private postMessage(msg: unknown): void {
    this.panel?.webview.postMessage(msg);
    this.view?.webview.postMessage(msg);
  }

  private registerMessageHandler(webview: vscode.Webview): void {
    webview.onDidReceiveMessage(async (message) => {
      switch (message.type) {
        case 'refresh':
          vscode.commands.executeCommand('collab.refreshMemory');
          break;

        case 'connect':
          vscode.commands.executeCommand('collab.connectMcpServers');
          break;

        case 'validate':
          vscode.commands.executeCommand('collab.validateAll');
          break;

        case 'checkSetup':
          this.handleCheckSetup();
          break;

        case 'saveProjectConfig':
          this.handleSaveProjectConfig(message.config);
          break;

        case 'createVisionDoc':
          this.handleCreateVisionDoc(message.name, message.content);
          break;

        case 'createArchDoc':
          this.handleCreateArchDoc(message.name, message.content);
          break;

        case 'ingestDocs':
          await this.handleIngestDocs(message.tier);
          break;

        case 'listVisionDocs':
          this.handleListDocs('vision');
          break;

        case 'listArchDocs':
          this.handleListDocs('architecture');
          break;

        case 'openSettings':
          this.handleOpenSettings();
          break;

        case 'savePermissions':
          this.handleSavePermissions(message.permissions);
          break;

        case 'listResearchPrompts':
          this.handleListResearchPrompts();
          break;

        case 'saveResearchPrompt':
          this.handleSaveResearchPrompt(message.prompt);
          break;

        case 'deleteResearchPrompt':
          this.handleDeleteResearchPrompt(message.id);
          break;

        case 'requestGovernedTasks':
          // Governed tasks are pushed via polling — send current state
          this.postMessage({ type: 'governedTasks', tasks: this.data.governedTasks });
          this.postMessage({ type: 'governanceStats', stats: this.data.governanceStats });
          break;

        case 'runResearchPrompt':
          this.handleRunResearchPrompt(message.id);
          break;

        case 'formatDocContent':
          this.handleFormatDocContent(message.tier, message.rawContent, message.requestId);
          break;

        case 'dismissFinding':
          this.handleDismissFinding(message.findingId, message.justification, message.dismissedBy);
          break;

        case 'requestFindings':
          this.postMessage({ type: 'findingsUpdate', findings: this.data.findings ?? [] });
          break;

        case 'readResearchBrief':
          this.handleReadResearchBrief(message.briefPath);
          break;

        case 'listResearchBriefs':
          this.handleListResearchBriefs();
          break;

        case 'bootstrapScaleCheck':
          this.handleBootstrapScaleCheck();
          break;

        case 'runBootstrap':
          this.handleRunBootstrap(message.context, message.focusAreas);
          break;

        case 'loadBootstrapReview':
          this.handleLoadBootstrapReview();
          break;

        case 'finalizeBootstrapReview':
          this.handleFinalizeBootstrapReview(message.items);
          break;

        case 'requestUsageReport':
          this.handleRequestUsageReport(message.period, message.groupBy);
          break;

        case 'requestAuditHealth':
          this.handleRequestAuditHealth();
          break;

        case 'requestAuditRecommendations':
          this.handleRequestAuditRecommendations();
          break;

        case 'requestAuditEvents':
          this.handleRequestAuditEvents(message.limit);
          break;

        case 'dismissAuditRecommendation':
          this.handleDismissAuditRecommendation(message.id, message.reason);
          break;
      }
    });
  }

  private handleCheckSetup(): void {
    if (!this.configService) return;

    const readiness = this.configService.getReadiness();
    this.postMessage({ type: 'setupReadiness', readiness });
  }

  private handleSaveProjectConfig(config: ProjectConfig): void {
    if (!this.configService) return;

    this.configService.save(config);

    // Sync permissions to .claude/settings.local.json
    if (config.permissions && config.permissions.length > 0) {
      this.configService.syncPermissionsToClaudeSettings(config.permissions);
    }

    // Update dashboard data
    this.refreshConfigData();

    // Notify webview
    this.postMessage({ type: 'projectConfig', config });
  }

  private handleCreateVisionDoc(name: string, content: string): void {
    if (!this.configService) return;

    const filepath = this.configService.createVisionDoc(name, content);
    const doc: DocumentInfo = {
      name: path.basename(filepath),
      path: filepath,
    };

    this.postMessage({ type: 'documentCreated', docType: 'vision', doc });

    // Refresh doc lists
    this.refreshConfigData();
  }

  private handleCreateArchDoc(name: string, content: string): void {
    if (!this.configService) return;

    const filepath = this.configService.createArchitectureDoc(name, content);
    const doc: DocumentInfo = {
      name: path.basename(filepath),
      path: filepath,
    };

    this.postMessage({ type: 'documentCreated', docType: 'architecture', doc });

    // Refresh doc lists
    this.refreshConfigData();
  }

  private async handleIngestDocs(tier: 'vision' | 'architecture'): Promise<void> {
    // This will call the KG server's ingest_documents tool
    // For now, we'll execute a command that the extension.ts can handle
    try {
      const result = await vscode.commands.executeCommand<{
        ingested: number;
        entities: string[];
        errors: string[];
        skipped: string[];
      }>('collab.ingestDocuments', tier);

      if (result) {
        this.postMessage({
          type: 'ingestionResult',
          result: { tier, ...result },
        });

        // Update ingestion status in config
        if (this.configService) {
          const config = this.configService.load();
          const now = new Date().toISOString();
          if (tier === 'vision') {
            config.ingestion.lastVisionIngest = now;
            config.ingestion.visionDocCount = result.ingested;
          } else {
            config.ingestion.lastArchitectureIngest = now;
            config.ingestion.architectureDocCount = result.ingested;
          }
          this.configService.save(config);
          this.refreshConfigData();
        }
      }
    } catch (err) {
      this.postMessage({
        type: 'ingestionResult',
        result: {
          tier,
          ingested: 0,
          entities: [],
          errors: [String(err)],
          skipped: [],
        },
      });
    }
  }

  private handleListDocs(tier: 'vision' | 'architecture'): void {
    const docs = this.getDocumentInfoList(tier);
    this.postMessage({
      type: tier === 'vision' ? 'visionDocs' : 'architectureDocs',
      docs,
    });
  }

  private handleOpenSettings(): void {
    if (!this.configService) return;

    const config = this.configService.load();
    this.postMessage({ type: 'projectConfig', config });
  }

  private handleSavePermissions(permissions: string[]): void {
    if (!this.configService) return;

    this.configService.syncPermissionsToClaudeSettings(permissions);

    // Also update the project config
    const config = this.configService.load();
    config.permissions = permissions;
    this.configService.save(config);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Research Prompts Handlers
  // ─────────────────────────────────────────────────────────────────────────────

  private handleListResearchPrompts(): void {
    if (!this.configService) return;

    const prompts = this.configService.listResearchPrompts();
    this.postMessage({ type: 'researchPrompts', prompts });
  }

  private handleSaveResearchPrompt(prompt: ResearchPrompt): void {
    if (!this.configService) return;

    this.configService.saveResearchPrompt(prompt);
    this.postMessage({ type: 'researchPromptUpdated', prompt });

    // Also add activity entry
    this.addActivity({
      id: `activity-${Date.now()}`,
      timestamp: new Date().toISOString(),
      agent: 'orchestrator',
      type: 'research',
      summary: `Research prompt "${prompt.name}" ${prompt.createdAt === prompt.updatedAt ? 'created' : 'updated'}`,
      detail: `Type: ${prompt.type}, Topic: ${prompt.topic}`,
    });
  }

  private handleDeleteResearchPrompt(id: string): void {
    if (!this.configService) return;

    const prompt = this.configService.getResearchPrompt(id);
    this.configService.deleteResearchPrompt(id);
    this.postMessage({ type: 'researchPromptDeleted', id });

    if (prompt) {
      this.addActivity({
        id: `activity-${Date.now()}`,
        timestamp: new Date().toISOString(),
        agent: 'orchestrator',
        type: 'research',
        summary: `Research prompt "${prompt.name}" deleted`,
      });
    }
  }

  private async handleRunResearchPrompt(id: string): Promise<void> {
    if (!this.configService) return;

    const prompt = this.configService.getResearchPrompt(id);
    if (!prompt) return;

    // Update status to in_progress
    this.configService.updateResearchPromptStatus(id, 'in_progress');
    const updatedPrompt = this.configService.getResearchPrompt(id);
    if (updatedPrompt) {
      this.postMessage({ type: 'researchPromptUpdated', prompt: updatedPrompt });
    }

    // Add activity entry
    this.addActivity({
      id: `activity-${Date.now()}`,
      timestamp: new Date().toISOString(),
      agent: 'researcher',
      type: 'research',
      summary: `Starting research: "${prompt.name}"`,
      detail: `Topic: ${prompt.topic}\nModel: ${prompt.modelHint}`,
    });

    // Execute the research via a command (to be implemented in extension.ts)
    try {
      const result = await vscode.commands.executeCommand<{
        success: boolean;
        summary?: string;
        briefPath?: string;
        error?: string;
      }>('collab.runResearch', id);

      const timestamp = new Date().toISOString();
      if (result) {
        this.configService.updateResearchPromptStatus(id, result.success ? 'completed' : 'failed', {
          timestamp,
          ...result,
        });
      } else {
        this.configService.updateResearchPromptStatus(id, 'completed', {
          timestamp,
          success: true,
          summary: 'Research completed (no detailed result available)',
        });
      }

      const finalPrompt = this.configService.getResearchPrompt(id);
      if (finalPrompt) {
        this.postMessage({ type: 'researchPromptUpdated', prompt: finalPrompt });
      }

      this.addActivity({
        id: `activity-${Date.now()}`,
        timestamp,
        agent: 'researcher',
        type: 'research',
        summary: `Research "${prompt.name}" ${result?.success !== false ? 'completed' : 'failed'}`,
        detail: result?.summary || result?.error,
      });
    } catch (err) {
      const timestamp = new Date().toISOString();
      this.configService.updateResearchPromptStatus(id, 'failed', {
        timestamp,
        success: false,
        error: String(err),
      });

      const failedPrompt = this.configService.getResearchPrompt(id);
      if (failedPrompt) {
        this.postMessage({ type: 'researchPromptUpdated', prompt: failedPrompt });
      }

      this.addActivity({
        id: `activity-${Date.now()}`,
        timestamp,
        agent: 'researcher',
        type: 'research',
        summary: `Research "${prompt.name}" failed`,
        detail: String(err),
      });
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Document Content Formatting (Claude CLI)
  // ─────────────────────────────────────────────────────────────────────────────

  private async handleFormatDocContent(
    tier: 'vision' | 'architecture',
    rawContent: string,
    requestId: string,
  ): Promise<void> {
    try {
      const formatted = await this.invokeClaudeFormat(tier, rawContent);
      this.postMessage({
        type: 'formatDocContentResult',
        requestId,
        success: true,
        formattedContent: formatted,
      });
    } catch (err) {
      this.postMessage({
        type: 'formatDocContentResult',
        requestId,
        success: false,
        error: String(err),
      });
    }
  }

  private async invokeClaudeFormat(
    tier: 'vision' | 'architecture',
    rawContent: string,
  ): Promise<string> {
    // Size gate — catch unreasonably large content before sending to model
    const MAX_CONTENT_BYTES = 100 * 1024; // 100KB
    if (Buffer.byteLength(rawContent, 'utf-8') > MAX_CONTENT_BYTES) {
      throw new Error(
        `Content too large (${Math.round(Buffer.byteLength(rawContent, 'utf-8') / 1024)}KB). ` +
          'Please reduce to under 100KB.',
      );
    }

    const prompt = tier === 'vision' ? VISION_FORMAT_PROMPT : ARCHITECTURE_FORMAT_PROMPT;
    const fullPrompt = `${prompt}\n\n---\n\nHere is the raw content to format:\n\n${rawContent}`;

    // Use temp files for input/output — avoids CLI arg limits and pipe buffering issues
    const stamp = `avt-fmt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const inputPath = path.join(os.tmpdir(), `${stamp}-input.md`);
    const outputPath = path.join(os.tmpdir(), `${stamp}-output.md`);

    try {
      // Write prompt to temp input file
      fs.writeFileSync(inputPath, fullPrompt, 'utf-8');

      // Run claude with file-descriptor-based I/O (no shell, no pipes)
      await new Promise<void>((resolve, reject) => {
        const inputFd = fs.openSync(inputPath, 'r');
        const outputFd = fs.openSync(outputPath, 'w');

        const proc = spawn('claude', ['--print', '--model', 'sonnet'], {
          stdio: [inputFd, outputFd, 'pipe'],
          timeout: 60000,
        });

        // Close parent copies of fds — child process has its own
        fs.closeSync(inputFd);
        fs.closeSync(outputFd);

        let stderr = '';
        proc.stderr!.on('data', (data: Buffer) => {
          stderr += data.toString();
        });

        proc.on('error', (err: NodeJS.ErrnoException) => {
          if (err.code === 'ENOENT') {
            reject(
              new Error('Claude CLI not found. Ensure "claude" is installed and on your PATH.'),
            );
          } else {
            reject(new Error(`Claude CLI failed to start: ${err.message}`));
          }
        });

        proc.on('close', (code: number | null) => {
          if (code !== 0) {
            reject(
              new Error(
                `Claude CLI exited with code ${code}${stderr ? `: ${stderr.trim().slice(0, 500)}` : ''}`,
              ),
            );
          } else {
            resolve();
          }
        });
      });

      // Read formatted output from temp file
      const output = fs.readFileSync(outputPath, 'utf-8').trim();
      if (!output) {
        throw new Error('Claude CLI returned empty output');
      }
      return output;
    } finally {
      // Clean up temp files
      try {
        fs.unlinkSync(inputPath);
      } catch {
        /* ignore */
      }
      try {
        fs.unlinkSync(outputPath);
      } catch {
        /* ignore */
      }
    }
  }

  private async handleDismissFinding(
    findingId: string,
    justification: string,
    dismissedBy: string,
  ): Promise<void> {
    try {
      // Call quality server's record_dismissal via MCP
      const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      if (!root) return;

      // Use the quality MCP port to call record_dismissal
      const response = await fetch('http://localhost:3102/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'record_dismissal',
          arguments: { finding_id: findingId, justification, dismissed_by: dismissedBy },
        }),
      });

      if (response.ok) {
        this.postMessage({ type: 'findingDismissed', findingId, success: true });
      } else {
        this.postMessage({ type: 'findingDismissed', findingId, success: false });
      }
    } catch {
      this.postMessage({ type: 'findingDismissed', findingId, success: false });
    }
  }

  private handleReadResearchBrief(briefPath: string): void {
    try {
      const content = fs.readFileSync(briefPath, 'utf-8');
      this.postMessage({ type: 'researchBriefContent', briefPath, content });
    } catch (err) {
      this.postMessage({
        type: 'researchBriefContent',
        briefPath,
        content: '',
        error: String(err),
      });
    }
  }

  private handleListResearchBriefs(): void {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!root) {
      this.postMessage({ type: 'researchBriefsList', briefs: [] });
      return;
    }

    const briefsDir = path.join(root, '.avt', 'research-briefs');
    if (!fs.existsSync(briefsDir)) {
      this.postMessage({ type: 'researchBriefsList', briefs: [] });
      return;
    }

    try {
      const files = fs
        .readdirSync(briefsDir)
        .filter((f) => f.endsWith('.md'))
        .map((f) => {
          const fullPath = path.join(briefsDir, f);
          const stat = fs.statSync(fullPath);
          return {
            name: f,
            path: fullPath,
            modifiedAt: stat.mtime.toISOString(),
          };
        })
        .sort((a, b) => b.modifiedAt.localeCompare(a.modifiedAt));

      this.postMessage({ type: 'researchBriefsList', briefs: files });
    } catch {
      this.postMessage({ type: 'researchBriefsList', briefs: [] });
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Bootstrap Handlers
  // ─────────────────────────────────────────────────────────────────────────────

  private async handleBootstrapScaleCheck(): Promise<void> {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!root) return;

    const scriptPath = path.join(root, 'scripts', 'bootstrap-scale-check.py');
    if (!fs.existsSync(scriptPath)) {
      vscode.window.showErrorMessage('Bootstrap scale check script not found.');
      return;
    }

    try {
      const result = await new Promise<string>((resolve, reject) => {
        const proc = spawn('uv', ['run', 'python', scriptPath, root], {
          cwd: root,
          timeout: 30000,
        });

        let stdout = '';
        let stderr = '';
        proc.stdout.on('data', (data: Buffer) => {
          stdout += data.toString();
        });
        proc.stderr.on('data', (data: Buffer) => {
          stderr += data.toString();
        });

        proc.on('error', (err: NodeJS.ErrnoException) => {
          reject(new Error(`Failed to run scale check: ${err.message}`));
        });

        proc.on('close', (code: number | null) => {
          if (code !== 0) {
            reject(new Error(`Scale check exited with code ${code}: ${stderr.trim()}`));
          } else {
            resolve(stdout.trim());
          }
        });
      });

      const profile = JSON.parse(result);
      this.postMessage({ type: 'bootstrapScaleResult', profile });
    } catch (err) {
      vscode.window.showErrorMessage(`Scale check failed: ${err}`);
    }
  }

  private async handleRunBootstrap(
    context: string,
    focusAreas: Record<string, boolean>,
  ): Promise<void> {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!root) return;

    // Build the bootstrap prompt
    const areas: string[] = [];
    if (focusAreas.visionStandards) areas.push('vision standards');
    if (focusAreas.architectureDocs) areas.push('architecture documentation');
    if (focusAreas.conventions) areas.push('coding conventions and style guide');
    if (focusAreas.projectRules) areas.push('project rules');

    let prompt = `Bootstrap the project at ${root}.`;
    if (areas.length < 4) {
      prompt += ` Focus on: ${areas.join(', ')}.`;
    }
    if (context.trim()) {
      prompt += `\n\nProject context from user:\n${context.trim()}`;
    }

    // Reset bootstrap streaming state
    this.bootstrapActivities = [];
    this.currentBootstrapPhase = 'Starting';
    this.subAgentCount = 0;

    // Notify webview that bootstrap has started (transitions dialog to progress view)
    this.postMessage({ type: 'bootstrapStarted' });

    // Add activity entry
    this.addActivity({
      id: `activity-${Date.now()}`,
      timestamp: new Date().toISOString(),
      agent: 'project-bootstrapper',
      type: 'status',
      summary: 'Bootstrap started',
      detail: areas.length < 4 ? `Focus: ${areas.join(', ')}` : 'Full bootstrap (all focus areas)',
    });

    this.postMessage({
      type: 'bootstrapProgress',
      phase: 'Initializing',
      detail: 'Preparing bootstrap agent...',
      activities: [],
    });

    // Write prompt to temp file for stdin
    const stamp = `avt-bootstrap-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const inputPath = path.join(os.tmpdir(), `${stamp}-input.md`);

    try {
      fs.writeFileSync(inputPath, prompt, 'utf-8');

      await new Promise<void>((resolve, reject) => {
        const inputFd = fs.openSync(inputPath, 'r');

        // Build env: inherit process.env but remove CLAUDECODE to avoid nested session detection
        const env = { ...process.env };
        delete env.CLAUDECODE;

        const proc = spawn(
          'claude',
          [
            '--print',
            '--output-format',
            'stream-json',
            '--verbose',
            '--model',
            'opus',
            '--agent',
            'project-bootstrapper',
          ],
          {
            stdio: [inputFd, 'pipe', 'pipe'],
            cwd: root,
            env,
            timeout: 3600000, // 1 hour timeout for large projects
          },
        );

        fs.closeSync(inputFd);

        // Parse stdout as stream-json: one JSON object per line
        const rl = createInterface({ input: proc.stdout! });
        rl.on('line', (line: string) => {
          try {
            const event = JSON.parse(line);
            this.handleBootstrapStreamEvent(event);
          } catch {
            // Skip non-JSON lines (e.g., blank lines, warnings)
          }
        });

        // Capture stderr for error reporting
        let stderr = '';
        proc.stderr!.on('data', (data: Buffer) => {
          stderr += data.toString();
        });

        // Heartbeat: if no stream events for 30s, send a pulse so UI doesn't look frozen
        let lastEventTime = Date.now();
        const heartbeat = setInterval(() => {
          if (Date.now() - lastEventTime > 30000) {
            const elapsed = Math.round((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
            this.postMessage({
              type: 'bootstrapProgress',
              phase: this.currentBootstrapPhase,
              detail: `Agent is thinking... (${timeStr} elapsed)`,
              activities: this.bootstrapActivities.slice(0, 8),
            });
          }
        }, 10000);
        const startTime = Date.now();

        // Patch lastEventTime on each stream event
        const origHandler = this.handleBootstrapStreamEvent.bind(this);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        this.handleBootstrapStreamEvent = (event: any) => {
          lastEventTime = Date.now();
          origHandler(event);
        };

        proc.on('error', (err: NodeJS.ErrnoException) => {
          clearInterval(heartbeat);
          this.handleBootstrapStreamEvent = origHandler; // restore
          if (err.code === 'ENOENT') {
            reject(
              new Error('Claude CLI not found. Ensure "claude" is installed and on your PATH.'),
            );
          } else {
            reject(new Error(`Bootstrap failed to start: ${err.message}`));
          }
        });

        proc.on('close', (code: number | null) => {
          clearInterval(heartbeat);
          this.handleBootstrapStreamEvent = origHandler; // restore
          if (code !== 0) {
            reject(
              new Error(
                `Bootstrap exited with code ${code}${stderr ? `: ${stderr.trim().slice(0, 500)}` : ''}`,
              ),
            );
          } else {
            resolve();
          }
        });
      });

      // Check if bootstrap report was created
      const reportPath = path.join(root, '.avt', 'bootstrap-report.md');
      const hasReport = fs.existsSync(reportPath);

      this.addActivity({
        id: `activity-${Date.now()}`,
        timestamp: new Date().toISOString(),
        agent: 'project-bootstrapper',
        type: 'status',
        summary: 'Bootstrap completed',
        detail: hasReport
          ? 'Review the bootstrap report in .avt/bootstrap-report.md'
          : 'Bootstrap completed. Check .avt/ for generated artifacts.',
      });

      this.postMessage({
        type: 'bootstrapComplete',
        success: true,
        reportPath: hasReport ? '.avt/bootstrap-report.md' : undefined,
      });

      // Refresh config data to pick up any new docs
      this.refreshConfigData();
    } catch (err) {
      this.addActivity({
        id: `activity-${Date.now()}`,
        timestamp: new Date().toISOString(),
        agent: 'project-bootstrapper',
        type: 'status',
        summary: 'Bootstrap failed',
        detail: String(err),
      });
      this.postMessage({
        type: 'bootstrapComplete',
        success: false,
        error: String(err),
      });
    } finally {
      // Clean up temp files
      try {
        fs.unlinkSync(inputPath);
      } catch {
        /* ignore */
      }
    }
  }

  /**
   * Handle a single stream-json event from the bootstrap claude CLI process.
   * Parses tool calls and text to send real-time progress to the webview.
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private handleBootstrapStreamEvent(event: any): void {
    switch (event.type) {
      case 'system':
        this.currentBootstrapPhase = 'Analyzing';
        this.postMessage({
          type: 'bootstrapProgress',
          phase: 'Analyzing',
          detail: 'Bootstrap agent initialized',
          activities: [],
        });
        break;

      case 'assistant':
        for (const block of event.message?.content || []) {
          if (block.type === 'tool_use') {
            const summary = this.summarizeToolCall(block.name, block.input);
            this.bootstrapActivities.unshift({ tool: block.name, summary, timestamp: Date.now() });
            if (this.bootstrapActivities.length > 20) this.bootstrapActivities.pop();

            const phase = this.deriveBootstrapPhase(block.name, block.input);
            this.currentBootstrapPhase = phase;

            this.postMessage({
              type: 'bootstrapProgress',
              phase,
              detail: summary,
              activities: this.bootstrapActivities.slice(0, 8),
            });
          }
          if (block.type === 'text' && block.text?.trim()) {
            const snippet = block.text.trim().slice(0, 120);
            this.postMessage({
              type: 'bootstrapProgress',
              phase: this.currentBootstrapPhase || 'Working',
              detail: snippet,
              activities: this.bootstrapActivities.slice(0, 8),
            });
          }
        }
        break;

      // 'user' events (tool results) and 'result' events are ignored for progress display
    }
  }

  /**
   * Translate a raw tool call into a human-readable summary.
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private summarizeToolCall(tool: string, input: any): string {
    try {
      switch (tool) {
        case 'Read':
          return `Reading ${this.shortenPath(input?.file_path)}`;
        case 'Glob':
          return `Searching for ${input?.pattern || 'files'}`;
        case 'Grep':
          return `Searching for "${(input?.pattern || '').slice(0, 40)}"`;
        case 'Bash':
          return `Running: ${(input?.command || '').slice(0, 60)}`;
        case 'Write':
          return `Writing ${this.shortenPath(input?.file_path)}`;
        case 'Edit':
          return `Editing ${this.shortenPath(input?.file_path)}`;
        case 'Task':
          return `Sub-agent: ${input?.description || 'analysis task'}`;
        case 'TodoWrite':
          return 'Updating task list';
        default:
          if (tool.startsWith('mcp__')) {
            const parts = tool.split('__');
            return `MCP: ${parts.slice(1).join('.')}`;
          }
          return `Using ${tool}`;
      }
    } catch {
      return `Using ${tool}`;
    }
  }

  /**
   * Derive the current bootstrap phase from the tool being called.
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private deriveBootstrapPhase(tool: string, input: any): string {
    try {
      if (tool === 'Bash') {
        const cmd = input?.command || '';
        if (cmd.includes('find') || cmd.includes('wc') || cmd.includes('ls')) return 'Scanning';
      }
      if (tool === 'Task') {
        this.subAgentCount++;
        return `Working (${this.subAgentCount} sub-agents)`;
      }
      if (tool === 'Write') {
        const fp = input?.file_path || '';
        if (
          fp.includes('docs/architecture') ||
          fp.includes('docs/vision') ||
          fp.includes('docs/style')
        )
          return 'Writing Docs';
        if (fp.includes('bootstrap-report')) return 'Writing Report';
        return 'Writing';
      }
      if (tool === 'Glob' || tool === 'Grep') return 'Analyzing';
      if (tool === 'Read') return 'Reading';
      if (tool.startsWith('mcp__')) return 'Recording';
    } catch {
      /* ignore */
    }
    return this.currentBootstrapPhase || 'Working';
  }

  /**
   * Shorten a file path for display (show last 2-3 segments).
   */
  private shortenPath(filePath: string | undefined): string {
    if (!filePath) return 'file';
    const parts = filePath.replace(/\\/g, '/').split('/');
    return parts.length <= 3 ? parts.join('/') : '...' + '/' + parts.slice(-3).join('/');
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Bootstrap Review Handlers
  // ─────────────────────────────────────────────────────────────────────────────

  /**
   * Load bootstrap discoveries for review. Reads from the structured
   * bootstrap-discoveries.json staging file (preferred) or falls back
   * to the legacy knowledge-graph.jsonl path for backward compatibility.
   */
  private async handleLoadBootstrapReview(): Promise<void> {
    try {
      const projectDir = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      if (!projectDir) {
        this.postMessage({ type: 'bootstrapReviewLoaded', items: [] });
        return;
      }

      // Preferred: structured discoveries file (staging, not yet in KG)
      const discoveriesPath = path.join(projectDir, '.avt', 'bootstrap-discoveries.json');
      if (fs.existsSync(discoveriesPath)) {
        const data = JSON.parse(fs.readFileSync(discoveriesPath, 'utf-8'));
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const items = (data.discoveries || []).map((d: any) => ({
          id: d.id || '',
          name: d.name || d.id || '',
          description: d.description || d.observations?.[0]?.slice(0, 120) || d.entityType || '',
          tier: d.tier || 'quality',
          entityType: d.entityType || 'observation',
          observations: d.observations || [],
          status: 'pending' as const,
          confidence: d.confidence,
          sourceFiles: d.sourceFiles,
          sourceEvidence: d.sourceEvidence,
          isContradiction: d.isContradiction || false,
          contradiction: d.contradiction,
        }));
        this.postMessage({ type: 'bootstrapReviewLoaded', items });
        return;
      }

      // Fallback: legacy JSONL path (backward compatibility)
      const jsonlPath = path.join(projectDir, '.avt', 'knowledge-graph.jsonl');
      if (!fs.existsSync(jsonlPath)) {
        this.postMessage({ type: 'bootstrapReviewLoaded', items: [] });
        return;
      }

      const content = fs.readFileSync(jsonlPath, 'utf-8');
      const lines = content.split('\n').filter((l) => l.trim());

      const items: Array<{
        id: string;
        name: string;
        description: string;
        tier: 'vision' | 'architecture' | 'quality';
        entityType: string;
        observations: string[];
        status: 'pending';
      }> = [];

      for (const line of lines) {
        try {
          const entity = JSON.parse(line);
          if (!entity.name || !entity.entityType) continue;

          let tier: 'vision' | 'architecture' | 'quality' = 'quality';
          const pt = (entity.protectionTier || '').toLowerCase();
          if (pt === 'vision') tier = 'vision';
          else if (pt === 'architecture') tier = 'architecture';

          const observations: string[] = entity.observations || [];
          const description = observations[0]?.slice(0, 120) || entity.entityType;

          const humanName = entity.name
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (c: string) => c.toUpperCase());

          items.push({
            id: entity.name,
            name: humanName,
            description,
            tier,
            entityType: entity.entityType,
            observations,
            status: 'pending' as const,
          });
        } catch {
          // Skip malformed lines
        }
      }

      this.postMessage({ type: 'bootstrapReviewLoaded', items });
    } catch (err: unknown) {
      console.error('Failed to load bootstrap review:', err);
      this.postMessage({ type: 'bootstrapReviewLoaded', items: [] });
    }
  }

  /**
   * Finalize bootstrap review: write approved/edited items to the Knowledge Graph.
   * Rejected items are simply not written. This is the moment items become permanent.
   */
  private async handleFinalizeBootstrapReview(
    items: Array<{
      id: string;
      name: string;
      tier: string;
      entityType: string;
      observations: string[];
      status: string;
      editedObservations?: string[];
      isUserCreated?: boolean;
    }>,
  ): Promise<void> {
    try {
      const projectDir = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      if (!projectDir) {
        this.postMessage({
          type: 'bootstrapReviewFinalized',
          result: {
            success: false,
            approved: 0,
            rejected: 0,
            edited: 0,
            errors: ['No workspace folder'],
          },
        });
        return;
      }

      let approved = 0;
      let rejected = 0;
      let edited = 0;
      const newLines: string[] = [];

      for (const item of items) {
        if (item.status === 'rejected') {
          rejected++;
          continue;
        }

        // Approved, edited, and pending items all get written
        if (item.status === 'approved' || item.status === 'edited' || item.status === 'pending') {
          if (item.status === 'edited') edited++;
          else approved++;

          const observations = item.editedObservations || item.observations;

          // Ensure protection_tier observation exists
          if (!observations.some((o) => o.startsWith('protection_tier:'))) {
            observations.unshift(`protection_tier: ${item.tier}`);
          }

          const entity: Record<string, unknown> = {
            type: 'entity',
            name: item.id,
            entityType: item.entityType,
            observations,
          };

          // Preserve protectionTier for KG server compatibility
          if (item.tier) {
            entity.protectionTier = item.tier;
          }

          newLines.push(JSON.stringify(entity));
        }
      }

      // Append approved items to the Knowledge Graph JSONL
      const avtDir = path.join(projectDir, '.avt');
      if (!fs.existsSync(avtDir)) {
        fs.mkdirSync(avtDir, { recursive: true });
      }

      const jsonlPath = path.join(avtDir, 'knowledge-graph.jsonl');
      if (newLines.length > 0) {
        fs.appendFileSync(jsonlPath, newLines.join('\n') + '\n', 'utf-8');
      }

      // Archive the discoveries staging file
      const discoveriesPath = path.join(avtDir, 'bootstrap-discoveries.json');
      if (fs.existsSync(discoveriesPath)) {
        const archivePath = path.join(avtDir, 'bootstrap-discoveries.finalized.json');
        fs.renameSync(discoveriesPath, archivePath);
      }

      // Add activity entry
      this.addActivity({
        id: `activity-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: 'bootstrap',
        agent: 'dashboard',
        summary: `Bootstrap review finalized: ${approved} approved, ${edited} edited, ${rejected} rejected`,
        tier: 'quality',
      });

      this.postMessage({
        type: 'bootstrapReviewFinalized',
        result: { success: true, approved, rejected, edited, errors: [] },
      });
    } catch (err: unknown) {
      console.error('Failed to finalize bootstrap review:', err);
      this.postMessage({
        type: 'bootstrapReviewFinalized',
        result: { success: false, approved: 0, rejected: 0, edited: 0, errors: [String(err)] },
      });
    }
  }

  private async handleRequestUsageReport(period: string, groupBy: string): Promise<void> {
    try {
      const response = await fetch('http://localhost:3103/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'get_usage_report',
          arguments: { period, group_by: groupBy },
        }),
      });

      if (response.ok) {
        const result = (await response.json()) as { content?: Array<{ text?: string }> };
        // FastMCP wraps tool results in content array
        const report = result?.content?.[0]?.text ? JSON.parse(result.content[0].text) : result;
        this.postMessage({ type: 'usageReport', report });
      } else {
        this.postMessage({ type: 'usageReport', report: null });
      }
    } catch {
      this.postMessage({ type: 'usageReport', report: null });
    }
  }

  private async handleRequestAuditHealth(): Promise<void> {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!root) {
      this.postMessage({
        type: 'auditHealth',
        data: {
          enabled: false,
          total_events: 0,
          events_last_hour: 0,
          active_recommendations: 0,
          recent_anomalies: 0,
          last_processed_at: null,
          event_types: {},
        },
      });
      return;
    }

    try {
      const auditDir = path.join(root, '.avt', 'audit');
      const configPath = path.join(root, '.avt', 'project-config.json');

      // Check if audit is enabled
      let enabled = false;
      if (fs.existsSync(configPath)) {
        const cfg = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
        enabled = cfg?.settings?.audit?.enabled === true;
      }

      // Count events
      const eventsPath = path.join(auditDir, 'events.jsonl');
      let totalEvents = 0;
      let eventsLastHour = 0;
      const eventTypes: Record<string, number> = {};
      const oneHourAgo = Date.now() / 1000 - 3600;

      if (fs.existsSync(eventsPath)) {
        const lines = fs.readFileSync(eventsPath, 'utf-8').split('\n').filter(Boolean);
        totalEvents = lines.length;
        for (const line of lines) {
          try {
            const evt = JSON.parse(line);
            const etype = evt.type || 'unknown';
            eventTypes[etype] = (eventTypes[etype] || 0) + 1;
            if (evt.ts > oneHourAgo) eventsLastHour++;
          } catch {
            /* skip */
          }
        }
      }

      // Count active recommendations
      const recsPath = path.join(auditDir, 'recommendations.json');
      let activeRecs = 0;
      if (fs.existsSync(recsPath)) {
        const data = JSON.parse(fs.readFileSync(recsPath, 'utf-8'));
        activeRecs = (data.recommendations || []).filter(
          (r: { status: string }) => r.status === 'active',
        ).length;
      }

      // Count recent anomalies from checkpoint
      const checkpointPath = path.join(auditDir, 'checkpoint.json');
      let lastProcessedAt: number | null = null;
      if (fs.existsSync(checkpointPath)) {
        const cp = JSON.parse(fs.readFileSync(checkpointPath, 'utf-8'));
        lastProcessedAt = cp.last_processed_ts || null;
      }

      this.postMessage({
        type: 'auditHealth',
        data: {
          enabled,
          total_events: totalEvents,
          events_last_hour: eventsLastHour,
          active_recommendations: activeRecs,
          recent_anomalies: activeRecs,
          last_processed_at: lastProcessedAt,
          event_types: eventTypes,
        },
      });
    } catch {
      this.postMessage({
        type: 'auditHealth',
        data: {
          enabled: false,
          total_events: 0,
          events_last_hour: 0,
          active_recommendations: 0,
          recent_anomalies: 0,
          last_processed_at: null,
          event_types: {},
        },
      });
    }
  }

  private async handleRequestAuditRecommendations(): Promise<void> {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!root) {
      this.postMessage({ type: 'auditRecommendations', recommendations: [] });
      return;
    }
    try {
      const recsPath = path.join(root, '.avt', 'audit', 'recommendations.json');
      if (fs.existsSync(recsPath)) {
        const data = JSON.parse(fs.readFileSync(recsPath, 'utf-8'));
        this.postMessage({
          type: 'auditRecommendations',
          recommendations: data.recommendations || [],
        });
      } else {
        this.postMessage({ type: 'auditRecommendations', recommendations: [] });
      }
    } catch {
      this.postMessage({ type: 'auditRecommendations', recommendations: [] });
    }
  }

  private async handleRequestAuditEvents(limit?: number): Promise<void> {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!root) {
      this.postMessage({ type: 'auditEvents', events: [] });
      return;
    }
    try {
      const eventsPath = path.join(root, '.avt', 'audit', 'events.jsonl');
      if (!fs.existsSync(eventsPath)) {
        this.postMessage({ type: 'auditEvents', events: [] });
        return;
      }
      const lines = fs.readFileSync(eventsPath, 'utf-8').split('\n').filter(Boolean);
      const maxEvents = limit || 50;
      const recentLines = lines.slice(-maxEvents);
      const events = [];
      for (const line of recentLines) {
        try {
          events.push(JSON.parse(line));
        } catch {
          /* skip corrupt lines */
        }
      }
      // Reverse so newest first
      events.reverse();
      this.postMessage({ type: 'auditEvents', events });
    } catch {
      this.postMessage({ type: 'auditEvents', events: [] });
    }
  }

  private async handleDismissAuditRecommendation(id: string, reason: string): Promise<void> {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!root) return;
    try {
      const recsPath = path.join(root, '.avt', 'audit', 'recommendations.json');
      if (!fs.existsSync(recsPath)) return;
      const data = JSON.parse(fs.readFileSync(recsPath, 'utf-8'));
      const recs = data.recommendations || [];
      for (const rec of recs) {
        if (rec.id === id) {
          rec.status = 'dismissed';
          rec.dismissed_reason = reason;
          break;
        }
      }
      data.recommendations = recs;
      data.updated_at = Date.now() / 1000;
      fs.writeFileSync(recsPath, JSON.stringify(data, null, 2));
      this.postMessage({ type: 'auditRecommendations', recommendations: recs });
    } catch (err) {
      console.error('Failed to dismiss audit recommendation:', err);
    }
  }

  private getHtmlContent(webview: vscode.Webview): string {
    const distPath = vscode.Uri.joinPath(this.extensionUri, 'webview-dashboard', 'dist');
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(distPath, 'assets', 'index.js'));
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(distPath, 'assets', 'index.css'));
    const nonce = getNonce();

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <link rel="stylesheet" href="${styleUri}">
  <title>Agent Operations Center</title>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}">
    window.__INITIAL_DATA__ = ${JSON.stringify(this.data)};
  </script>
  <script nonce="${nonce}" type="module" src="${scriptUri}"></script>
</body>
</html>`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Document Formatting Prompts
// ─────────────────────────────────────────────────────────────────────────────

const VISION_FORMAT_PROMPT = `You are a technical writing assistant. Your task is to take raw, unstructured notes about a software project's vision standards and format them into a clean, well-organized markdown document.

Vision standards are the highest-level principles and invariants for a project. They are immutable rules that all development must follow. Examples include "All services use protocol-based dependency injection" or "No singletons in production code."

Instructions:
- Extract individual standards/principles from the raw content
- For each standard, create a section with:
  - A clear, concise Statement (one sentence, imperative)
  - A Rationale explaining why this standard exists
  - Optionally, Examples showing compliant and violating code/behavior
- Use proper markdown formatting with ## headings for each standard
- Add a top-level # heading summarizing the document
- Remove redundancy, fix grammar, and organize logically
- If the content is vague, do your best to extract actionable standards
- Output ONLY the formatted markdown document, no preamble or explanation
- Do not wrap the output in markdown code fences`;

const ARCHITECTURE_FORMAT_PROMPT = `You are a technical writing assistant. Your task is to take raw, unstructured notes about a software project's architecture and format them into a clean, well-organized markdown document.

Architecture documents describe patterns, components, technical standards, and design decisions. They inform AI agents and developers about how the system is built.

Instructions:
- Categorize content into sections as appropriate: Architectural Standards, Patterns, and Components
- For each element, create a section with:
  - A Type (standard, pattern, or component)
  - A clear Description of what it is and its purpose
  - Usage guidance (when and how to use it)
  - Optionally, Examples with code snippets
  - Optionally, Related links to other architectural elements
- Use proper markdown formatting with ## headings for each element
- Add a top-level # heading summarizing the document
- Remove redundancy, fix grammar, and organize logically
- If the content is vague, do your best to extract actionable architecture guidance
- Output ONLY the formatted markdown document, no preamble or explanation
- Do not wrap the output in markdown code fences`;
