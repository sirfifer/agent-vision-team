import * as vscode from 'vscode';

export class DashboardWebviewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'collab.dashboard';

  private view?: vscode.WebviewView;

  constructor(private readonly extensionUri: vscode.Uri) {}

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this.getHtmlContent();

    webviewView.webview.onDidReceiveMessage((message) => {
      // TODO: Handle messages from webview
      switch (message.type) {
        case 'ready':
          // Webview is ready, send initial data
          break;
      }
    });
  }

  public openPanel(): void {
    const panel = vscode.window.createWebviewPanel(
      'collab.dashboard',
      'Collab Intelligence Dashboard',
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        localResourceRoots: [this.extensionUri],
      }
    );

    panel.webview.html = this.getHtmlContent();
  }

  private getHtmlContent(): string {
    // TODO: Load built React webview from webview-dashboard/dist
    return `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Collab Intelligence Dashboard</title>
        <style>
          body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            padding: 16px;
          }
          h1 { font-size: 1.4em; margin-bottom: 16px; }
          .placeholder {
            padding: 24px;
            text-align: center;
            color: var(--vscode-descriptionForeground);
            border: 1px dashed var(--vscode-widget-border);
            border-radius: 4px;
            margin-bottom: 16px;
          }
        </style>
      </head>
      <body>
        <h1>Collab Intelligence Dashboard</h1>
        <div class="placeholder">Session Timeline (coming soon)</div>
        <div class="placeholder">Message Feed (coming soon)</div>
        <div class="placeholder">Quality Gates (coming soon)</div>
        <div class="placeholder">Agent Cards (coming soon)</div>
      </body>
      </html>
    `;
  }
}
