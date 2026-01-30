import * as vscode from 'vscode';
import { McpClientService } from './services/McpClientService';
import { FileWatcherService } from './services/FileWatcherService';
import { StatusBarService } from './services/StatusBarService';
import { KnowledgeGraphClient } from './mcp/KnowledgeGraphClient';
import { QualityClient } from './mcp/QualityClient';
import { FindingsTreeProvider } from './providers/FindingsTreeProvider';
import { TasksTreeProvider } from './providers/TasksTreeProvider';
import { MemoryTreeProvider } from './providers/MemoryTreeProvider';
import { DashboardWebviewProvider } from './providers/DashboardWebviewProvider';
import { registerSystemCommands } from './commands/systemCommands';
import { registerMemoryCommands } from './commands/memoryCommands';
import { registerTaskCommands } from './commands/taskCommands';
import { initializeLoggers, disposeLoggers } from './utils/logger';

export function activate(context: vscode.ExtensionContext): void {
  // Initialize logging
  initializeLoggers();

  // Initialize services
  const mcpClient = new McpClientService();
  const fileWatcher = new FileWatcherService();
  const statusBar = new StatusBarService();

  // Initialize typed MCP clients
  const kgClient = new KnowledgeGraphClient(mcpClient);
  const qualityClient = new QualityClient(mcpClient);

  // Initialize tree view providers
  const findingsProvider = new FindingsTreeProvider();
  const tasksProvider = new TasksTreeProvider();
  const memoryProvider = new MemoryTreeProvider();
  const dashboardProvider = new DashboardWebviewProvider(context.extensionUri);

  // Register tree views
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider('collab.findings', findingsProvider),
    vscode.window.registerTreeDataProvider('collab.tasks', tasksProvider),
    vscode.window.registerTreeDataProvider('collab.memory', memoryProvider)
  );

  // Register commands
  registerSystemCommands(context, mcpClient, statusBar);
  registerMemoryCommands(context, kgClient);
  registerTaskCommands(context);

  // Dashboard command
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.viewDashboard', () => {
      dashboardProvider.openPanel();
    })
  );

  // Validate all gates command
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.validateAll', async () => {
      try {
        const result = await qualityClient.validate();
        if (result.all_passed) {
          vscode.window.showInformationMessage('All quality gates passed.');
        } else {
          vscode.window.showWarningMessage(`Quality gates: ${result.summary}`);
        }
      } catch (error) {
        vscode.window.showErrorMessage(`Validation failed: ${error}`);
      }
    })
  );

  // Initialize file watchers
  fileWatcher.initialize();
  fileWatcher.onDidChangeTaskBriefs(() => tasksProvider.refresh());
  fileWatcher.onDidChangeSessionState(() => {
    // TODO: Refresh dashboard
  });

  // Set initial status
  statusBar.setHealth('inactive');
  statusBar.setSummary(0, 0, 'inactive');
  statusBar.show();

  // Register disposables
  context.subscriptions.push(
    { dispose: () => fileWatcher.dispose() },
    { dispose: () => statusBar.dispose() },
    { dispose: () => findingsProvider.dispose() },
    { dispose: () => disposeLoggers() }
  );
}

export function deactivate(): void {
  // Cleanup handled by disposables
}
