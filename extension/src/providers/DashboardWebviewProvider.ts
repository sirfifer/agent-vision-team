import * as vscode from 'vscode';
import * as crypto from 'crypto';
import { Entity } from '../models/Entity';
import { AgentStatus, ActivityEntry } from '../models/Activity';

interface DashboardData {
  connectionStatus: 'connected' | 'disconnected' | 'error';
  serverPorts: { kg: number; quality: number; governance: number };
  agents: AgentStatus[];
  visionStandards: Entity[];
  architecturalElements: Entity[];
  activities: ActivityEntry[];
  tasks: { active: number; total: number };
  sessionPhase: string;
}

function getNonce(): string {
  return crypto.randomBytes(16).toString('hex');
}

export class DashboardWebviewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'collab.dashboard';

  private view?: vscode.WebviewView;
  private panel?: vscode.WebviewPanel;
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

  private registerMessageHandler(webview: vscode.Webview): void {
    webview.onDidReceiveMessage((message) => {
      if (message.type === 'refresh') {
        vscode.commands.executeCommand('collab.refreshMemory');
      } else if (message.type === 'connect') {
        vscode.commands.executeCommand('collab.connectMcpServers');
      } else if (message.type === 'validate') {
        vscode.commands.executeCommand('collab.validateAll');
      }
    });
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
