import * as vscode from 'vscode';
import * as crypto from 'crypto';
import * as path from 'path';
import { Entity } from '../models/Entity';
import { AgentStatus, ActivityEntry } from '../models/Activity';
import { ProjectConfig, SetupReadiness } from '../models/ProjectConfig';
import { ResearchPrompt } from '../models/ResearchPrompt';
import { ProjectConfigService } from '../services/ProjectConfigService';

interface DocumentInfo {
  name: string;
  path: string;
  title?: string;
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
  // Setup wizard and config
  setupReadiness?: SetupReadiness;
  projectConfig?: ProjectConfig;
  visionDocs?: DocumentInfo[];
  architectureDocs?: DocumentInfo[];
  // Research prompts
  researchPrompts?: ResearchPrompt[];
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
  };

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

    const docs = tier === 'vision'
      ? this.configService.listVisionDocs()
      : this.configService.listArchitectureDocs();

    const docsRoot = this.configService.getDocsRoot();
    return docs.map(name => ({
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
      }
    );

    this.panel.webview.html = this.getHtmlContent(this.panel.webview);
    this.registerMessageHandler(this.panel.webview);
    this.panel.onDidDispose(() => { this.panel = undefined; });
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

        case 'runResearchPrompt':
          this.handleRunResearchPrompt(message.id);
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
        this.configService.updateResearchPromptStatus(
          id,
          result.success ? 'completed' : 'failed',
          { timestamp, ...result }
        );
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

  private getHtmlContent(webview: vscode.Webview): string {
    const distPath = vscode.Uri.joinPath(this.extensionUri, 'webview-dashboard', 'dist');
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(distPath, 'assets', 'index.js')
    );
    const styleUri = webview.asWebviewUri(
      vscode.Uri.joinPath(distPath, 'assets', 'index.css')
    );
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
