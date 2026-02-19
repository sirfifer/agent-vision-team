import * as vscode from 'vscode';
import { McpClientService } from '../services/McpClientService';
import { StatusBarService } from '../services/StatusBarService';
import { logSystem } from '../utils/logger';

export function registerSystemCommands(
  context: vscode.ExtensionContext,
  mcpClient: McpClientService,
  statusBar: StatusBarService,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.startSystem', async () => {
      logSystem('Starting Collab Intelligence system...');

      try {
        // TODO: Start KG and Quality MCP server child processes
        await mcpClient.connect();
        statusBar.setHealth('active');
        statusBar.setSummary(0, 0, 'ready');
        statusBar.show();
        vscode.window.showInformationMessage('Collab Intelligence system started.');
      } catch (error) {
        statusBar.setHealth('error');
        vscode.window.showErrorMessage(`Failed to start system: ${error}`);
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('collab.stopSystem', async () => {
      logSystem('Stopping Collab Intelligence system...');

      try {
        await mcpClient.disconnect();
        // TODO: Terminate KG and Quality MCP server child processes
        statusBar.setHealth('inactive');
        vscode.window.showInformationMessage('Collab Intelligence system stopped.');
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to stop system: ${error}`);
      }
    }),
  );
}
