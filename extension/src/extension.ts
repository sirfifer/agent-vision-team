import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { McpClientService } from './services/McpClientService';
import { FileWatcherService } from './services/FileWatcherService';
import { StatusBarService } from './services/StatusBarService';
import { ProjectConfigService } from './services/ProjectConfigService';
import { KnowledgeGraphClient } from './mcp/KnowledgeGraphClient';
import { QualityClient } from './mcp/QualityClient';
import { GovernanceClient } from './mcp/GovernanceClient';
import { McpServerManager } from './services/McpServerManager';
import { FindingsTreeProvider } from './providers/FindingsTreeProvider';
import { TasksTreeProvider } from './providers/TasksTreeProvider';
import { MemoryTreeProvider } from './providers/MemoryTreeProvider';
import { DashboardWebviewProvider } from './providers/DashboardWebviewProvider';
import { registerSystemCommands } from './commands/systemCommands';
import { registerMemoryCommands } from './commands/memoryCommands';
import { registerTaskCommands } from './commands/taskCommands';
import { initializeLoggers, disposeLoggers } from './utils/logger';
import { Entity } from './models/Entity';
import { AgentStatus, ActivityEntry, GovernedTask, GovernanceStats } from './models/Activity';
import type { GovernanceStatus, PendingReviewEntry } from './mcp/GovernanceClient';

let activityCounter = 0;
function makeActivity(
  agent: string,
  type: ActivityEntry['type'],
  summary: string,
  opts?: { tier?: ActivityEntry['tier']; detail?: string; governanceRef?: string }
): ActivityEntry {
  return {
    id: `act-${++activityCounter}`,
    timestamp: new Date().toISOString(),
    agent,
    type,
    summary,
    ...opts,
  };
}

function getWorkspaceRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function detectAgents(root: string): AgentStatus[] {
  const agents: AgentStatus[] = [
    { id: 'orchestrator', name: 'Orchestrator', role: 'orchestrator', status: 'active' },
  ];

  const agentDefs: Array<{ file: string; id: string; name: string; role: AgentStatus['role'] }> = [
    { file: 'worker.md', id: 'worker', name: 'Worker', role: 'worker' },
    { file: 'quality-reviewer.md', id: 'quality-reviewer', name: 'Quality Reviewer', role: 'quality-reviewer' },
    { file: 'kg-librarian.md', id: 'kg-librarian', name: 'KG Librarian', role: 'kg-librarian' },
    { file: 'governance-reviewer.md', id: 'governance-reviewer', name: 'Governance Reviewer', role: 'governance-reviewer' },
    { file: 'researcher.md', id: 'researcher', name: 'Researcher', role: 'researcher' },
    { file: 'project-steward.md', id: 'project-steward', name: 'Project Steward', role: 'project-steward' },
  ];

  for (const def of agentDefs) {
    const agentPath = path.join(root, '.claude', 'agents', def.file);
    const exists = fs.existsSync(agentPath);
    agents.push({
      id: def.id,
      name: def.name,
      role: def.role,
      status: exists ? 'idle' : 'not-configured',
    });
  }

  return agents;
}

/**
 * Enrich agent status based on governance data.
 * Infers runtime state from pending reviews, governed tasks, and recent activity.
 */
function enrichAgentStatus(
  agents: AgentStatus[],
  govStatus: GovernanceStatus | null,
  pendingReviews: PendingReviewEntry[],
): AgentStatus[] {
  if (!govStatus) return agents;

  return agents.map(agent => {
    // Skip not-configured agents
    if (agent.status === 'not-configured') return agent;

    switch (agent.role) {
      case 'governance-reviewer': {
        if (pendingReviews.length > 0) {
          return {
            ...agent,
            status: 'reviewing',
            currentTask: `${pendingReviews.length} review(s) pending`,
          };
        }
        break;
      }
      case 'worker': {
        const taskStats = govStatus.task_governance;
        if (taskStats) {
          if (taskStats.blocked > 0) {
            return {
              ...agent,
              status: 'blocked',
              currentTask: `${taskStats.blocked} task(s) blocked`,
            };
          }
          if (taskStats.approved > 0) {
            return {
              ...agent,
              status: 'active',
              currentTask: `${taskStats.approved} task(s) approved`,
            };
          }
          if (taskStats.pending_review > 0) {
            return {
              ...agent,
              status: 'idle',
              currentTask: `${taskStats.pending_review} task(s) awaiting review`,
            };
          }
        }
        break;
      }
      case 'quality-reviewer': {
        // Check recent activity for quality review events
        const recentQR = govStatus.recent_activity.find(
          a => a.agent === 'quality-reviewer'
        );
        if (recentQR) {
          return {
            ...agent,
            status: 'active',
            currentTask: recentQR.summary,
            lastActivity: recentQR.summary,
          };
        }
        break;
      }
      default:
        break;
    }

    return agent;
  });
}

function getSessionPhase(root: string): string {
  try {
    const statePath = path.join(root, '.avt', 'session-state.md');
    if (fs.existsSync(statePath)) {
      const content = fs.readFileSync(statePath, 'utf-8');
      const match = content.match(/##\s*Current Phase[:\s]*(.+)/i)
        ?? content.match(/phase[:\s]*(.+)/i);
      if (match) return match[1].trim();
    }
  } catch { /* ignore */ }
  return 'inactive';
}

function getTaskCounts(root: string): { active: number; total: number } {
  try {
    const briefsDir = path.join(root, '.avt', 'task-briefs');
    if (fs.existsSync(briefsDir)) {
      const files = fs.readdirSync(briefsDir).filter(f => f.endsWith('.md'));
      return { active: 0, total: files.length };
    }
  } catch { /* ignore */ }
  return { active: 0, total: 0 };
}

function classifyEntities(allEntities: Entity[]): { vision: Entity[]; architecture: Entity[] } {
  const vision: Entity[] = [];
  const architecture: Entity[] = [];

  for (const entity of allEntities) {
    const isVision = entity.entityType === 'vision_standard'
      || entity.observations.some(o => o.includes('protection_tier: vision'));
    const isArch = entity.entityType === 'architectural_standard'
      || entity.entityType === 'pattern'
      || entity.entityType === 'component'
      || entity.observations.some(o => o.includes('protection_tier: architecture'));

    if (isVision) {
      vision.push(entity);
    } else if (isArch) {
      architecture.push(entity);
    }
  }

  return { vision, architecture };
}

/**
 * Fetch governance data and transform into dashboard-ready format.
 */
async function fetchGovernanceData(governanceClient: GovernanceClient): Promise<{
  govStatus: GovernanceStatus | null;
  pendingReviews: PendingReviewEntry[];
  governanceStats: GovernanceStats;
  governedTasks: GovernedTask[];
}> {
  const defaultStats: GovernanceStats = {
    totalDecisions: 0,
    approved: 0,
    blocked: 0,
    pending: 0,
    pendingReviews: 0,
    totalGovernedTasks: 0,
  };

  try {
    const [govStatus, pendingResult] = await Promise.all([
      governanceClient.getGovernanceStatus(),
      governanceClient.getPendingReviews(),
    ]);

    const taskGov = govStatus.task_governance;
    const governanceStats: GovernanceStats = {
      totalDecisions: govStatus.total_decisions,
      approved: govStatus.approved,
      blocked: govStatus.blocked,
      pending: govStatus.pending,
      pendingReviews: pendingResult.count,
      totalGovernedTasks: taskGov?.total_governed_tasks ?? 0,
    };

    // Transform pending reviews into governed task representations
    const governedTasks: GovernedTask[] = pendingResult.pending_reviews.map(r => ({
      id: r.id,
      implementationTaskId: r.implementation_task_id,
      subject: r.context.length > 80 ? r.context.substring(0, 80) + '...' : r.context,
      status: 'pending_review' as const,
      reviews: [{
        id: r.id,
        reviewType: r.type,
        status: 'pending' as const,
        createdAt: r.created_at,
      }],
      createdAt: r.created_at,
    }));

    return {
      govStatus,
      pendingReviews: pendingResult.pending_reviews,
      governanceStats,
      governedTasks,
    };
  } catch {
    return {
      govStatus: null,
      pendingReviews: [],
      governanceStats: defaultStats,
      governedTasks: [],
    };
  }
}

export function activate(context: vscode.ExtensionContext): void {
  console.log('>>> Collab Intelligence extension is activating...');
  const outputChannel = vscode.window.createOutputChannel('Collab Intelligence');
  outputChannel.appendLine('Collab Intelligence extension is activating...');
  outputChannel.show();

  // Initialize logging
  initializeLoggers();

  // Initialize services
  const serverManager = new McpServerManager(outputChannel);
  const mcpClient = new McpClientService();
  const fileWatcher = new FileWatcherService();
  const statusBar = new StatusBarService();

  // Initialize typed MCP clients
  const kgClient = new KnowledgeGraphClient(mcpClient);
  const qualityClient = new QualityClient(mcpClient);
  const governanceClient = new GovernanceClient(mcpClient);

  // Initialize tree view providers
  const findingsProvider = new FindingsTreeProvider();
  const tasksProvider = new TasksTreeProvider();
  const memoryProvider = new MemoryTreeProvider();
  const dashboardProvider = new DashboardWebviewProvider(context.extensionUri);

  // Polling state
  let pollInterval: ReturnType<typeof setInterval> | undefined;
  let isConnected = false;

  // Initialize project config service if workspace exists
  const workspaceRoot = getWorkspaceRoot();
  let configService: ProjectConfigService | undefined;
  if (workspaceRoot) {
    configService = new ProjectConfigService(workspaceRoot);
    configService.ensureFolderStructure();
    dashboardProvider.setConfigService(configService);

    // Push agent detection + session data immediately (before MCP connects)
    // so agent cards render even when servers aren't running
    const earlyAgents = detectAgents(workspaceRoot);
    const earlyPhase = getSessionPhase(workspaceRoot);
    const earlyTasks = getTaskCounts(workspaceRoot);
    dashboardProvider.updateData({
      agents: earlyAgents,
      sessionPhase: earlyPhase,
      tasks: earlyTasks,
    });
  }

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

  /**
   * Periodic dashboard refresh — fetches governance data and updates agent status.
   */
  async function pollDashboard(): Promise<void> {
    if (!isConnected) return;

    try {
      const root = getWorkspaceRoot();
      const baseAgents = root ? detectAgents(root) : [];
      const tasks = root ? getTaskCounts(root) : { active: 0, total: 0 };
      const sessionPhase = root ? getSessionPhase(root) : 'inactive';

      const { govStatus, pendingReviews, governanceStats, governedTasks } =
        await fetchGovernanceData(governanceClient);

      const agents = enrichAgentStatus(baseAgents, govStatus, pendingReviews);

      dashboardProvider.updateData({
        agents,
        tasks,
        sessionPhase,
        governedTasks,
        governanceStats,
      });
    } catch {
      // Polling failures are non-fatal — dashboard keeps last known state
    }
  }

  function startPolling(): void {
    stopPolling();
    isConnected = true;
    // Initial poll immediately
    pollDashboard();
    // Then every 10 seconds
    pollInterval = setInterval(pollDashboard, 10_000);
  }

  function stopPolling(): void {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = undefined;
    }
    isConnected = false;
  }

  // Connect to MCP Servers command
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.connectMcpServers', async () => {
      try {
        outputChannel.appendLine('Starting MCP servers...');
        await serverManager.startAll();
        outputChannel.appendLine('Connecting to MCP servers...');
        await mcpClient.connect();
        statusBar.setHealth('active');
        statusBar.setSummary(0, 0, 'ready');

        const root = getWorkspaceRoot();
        const agents = root ? detectAgents(root) : [];
        const sessionPhase = root ? getSessionPhase(root) : 'inactive';
        const tasks = root ? getTaskCounts(root) : { active: 0, total: 0 };

        dashboardProvider.updateData({
          connectionStatus: 'connected',
          agents,
          sessionPhase,
          tasks,
        });
        dashboardProvider.addActivity(
          makeActivity('orchestrator', 'status', 'Connected to MCP servers')
        );

        // Fetch governance data and enrich agents
        const { govStatus, pendingReviews, governanceStats, governedTasks } =
          await fetchGovernanceData(governanceClient);

        const enrichedAgents = enrichAgentStatus(agents, govStatus, pendingReviews);
        dashboardProvider.updateData({
          agents: enrichedAgents,
          governedTasks,
          governanceStats,
        });

        if (govStatus && govStatus.total_decisions > 0) {
          dashboardProvider.addActivity(
            makeActivity('governance-reviewer', 'review',
              `Governance: ${govStatus.approved} approved, ${govStatus.blocked} blocked, ${govStatus.pending} pending`,
              { tier: 'architecture' })
          );
        }

        // Start periodic polling
        startPolling();

        vscode.window.showInformationMessage('Connected to MCP servers.');
        outputChannel.appendLine('Connected to MCP servers successfully.');
      } catch (error) {
        statusBar.setHealth('error');
        stopPolling();
        dashboardProvider.updateData({ connectionStatus: 'error' });
        dashboardProvider.addActivity(
          makeActivity('orchestrator', 'status', `Connection failed: ${error}`)
        );
        vscode.window.showErrorMessage(`Failed to connect to MCP servers: ${error}`);
        outputChannel.appendLine(`Connection failed: ${error}`);
      }
    })
  );

  // Refresh commands
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.refreshMemory', async () => {
      try {
        const allEntities: Entity[] = [];
        for (const tier of ['vision', 'architecture', 'quality'] as const) {
          const entities = await kgClient.getEntitiesByTier(tier);
          allEntities.push(...entities);
        }
        memoryProvider.updateEntities(allEntities);

        const { vision, architecture } = classifyEntities(allEntities);
        const root = getWorkspaceRoot();
        const sessionPhase = root ? getSessionPhase(root) : 'inactive';
        const tasks = root ? getTaskCounts(root) : { active: 0, total: 0 };

        dashboardProvider.updateData({
          visionStandards: vision,
          architecturalElements: architecture,
          sessionPhase,
          tasks,
        });
        dashboardProvider.addActivity(
          makeActivity('orchestrator', 'status', `Memory refreshed: ${allEntities.length} entities (${vision.length} vision, ${architecture.length} architecture)`)
        );

        // Also fetch governance decision history
        try {
          const { decisions } = await governanceClient.getDecisionHistory();
          for (const d of decisions.slice(0, 10)) {
            dashboardProvider.addActivity(
              makeActivity(
                d.agent || 'governance-reviewer',
                d.verdict ? 'review' : 'decision',
                `[${d.category}] ${d.summary}`,
                {
                  tier: 'architecture',
                  detail: d.verdict ? `Verdict: ${d.verdict}. ${d.guidance}` : undefined,
                  governanceRef: d.id,
                }
              )
            );
          }
        } catch {
          // Governance server may not be running — non-fatal
        }

        // Also force a governance data refresh
        await pollDashboard();

        vscode.window.showInformationMessage(`Memory Browser refreshed: ${allEntities.length} entities.`);
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to refresh memory: ${error}`);
      }
    }),
    vscode.commands.registerCommand('collab.refreshFindings', async () => {
      try {
        const result = await qualityClient.validate();
        dashboardProvider.addActivity(
          makeActivity('quality-reviewer', 'finding', `Validation: ${result.summary}`, { tier: 'quality' })
        );
        vscode.window.showInformationMessage(`Validation: ${result.summary}`);
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to refresh findings: ${error}`);
      }
    }),
    vscode.commands.registerCommand('collab.refreshTasks', () => {
      tasksProvider.refresh();
      const root = getWorkspaceRoot();
      const tasks = root ? getTaskCounts(root) : { active: 0, total: 0 };
      dashboardProvider.updateData({ tasks });
      vscode.window.showInformationMessage('Tasks refreshed.');
    })
  );

  // Dashboard command
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.viewDashboard', () => {
      dashboardProvider.openPanel();
    })
  );

  // Open Setup Wizard command — opens dashboard then shows wizard overlay
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.openSetupWizard', () => {
      dashboardProvider.openPanel();
      // Small delay to let webview initialize if panel was just created
      setTimeout(() => dashboardProvider.showSetupWizard(), 300);
    })
  );

  // Open Walkthrough command
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.openWalkthrough', () => {
      vscode.commands.executeCommand(
        'workbench.action.openWalkthrough',
        'collab-intelligence.avt-getting-started',
        false
      );
    })
  );

  // Validate all gates command
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.validateAll', async () => {
      try {
        const result = await qualityClient.validate();
        dashboardProvider.addActivity(
          makeActivity('quality-reviewer', 'finding', `Quality gates: ${result.summary}`, {
            tier: 'quality',
            detail: result.summary,
          })
        );
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

  // Ingest documents command (called by dashboard wizard)
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.ingestDocuments', async (tier: 'vision' | 'architecture') => {
      try {
        const result = await kgClient.ingestDocuments(tier);
        dashboardProvider.addActivity(
          makeActivity('kg-librarian', 'status', `Ingested ${result.ingested} ${tier} documents into KG`, {
            tier: tier === 'vision' ? 'vision' : 'architecture',
          })
        );
        return result;
      } catch (error) {
        vscode.window.showErrorMessage(`Document ingestion failed: ${error}`);
        return {
          ingested: 0,
          entities: [],
          errors: [String(error)],
          skipped: [],
        };
      }
    })
  );

  // Initialize file watchers
  fileWatcher.initialize();
  fileWatcher.onDidChangeTaskBriefs(() => tasksProvider.refresh());
  fileWatcher.onDidChangeSessionState(() => {
    const root = getWorkspaceRoot();
    if (root) {
      dashboardProvider.updateData({ sessionPhase: getSessionPhase(root) });
    }
  });

  // Set initial status
  statusBar.setHealth('inactive');
  statusBar.setSummary(0, 0, 'inactive');
  statusBar.show();

  console.log('>>> Collab Intelligence extension activated successfully!');
  outputChannel.appendLine('Extension activated successfully!');

  // Register disposables
  context.subscriptions.push(
    { dispose: () => stopPolling() },
    { dispose: () => serverManager.stopAll() },
    { dispose: () => mcpClient.disconnect() },
    { dispose: () => fileWatcher.dispose() },
    { dispose: () => statusBar.dispose() },
    { dispose: () => findingsProvider.dispose() },
    { dispose: () => disposeLoggers() }
  );

  // Auto-start servers and connect on activation
  serverManager.startAll().then(async () => {
    try {
      await mcpClient.connect();
      statusBar.setHealth('active');
      statusBar.setSummary(0, 0, 'ready');

      const root = getWorkspaceRoot();
      const agents = root ? detectAgents(root) : [];
      const sessionPhase = root ? getSessionPhase(root) : 'inactive';
      const tasks = root ? getTaskCounts(root) : { active: 0, total: 0 };

      // Fetch governance data for enrichment
      const { govStatus, pendingReviews, governanceStats, governedTasks } =
        await fetchGovernanceData(governanceClient);

      const enrichedAgents = enrichAgentStatus(agents, govStatus, pendingReviews);

      dashboardProvider.updateData({
        connectionStatus: 'connected',
        agents: enrichedAgents,
        sessionPhase,
        tasks,
        governedTasks,
        governanceStats,
      });
      dashboardProvider.addActivity(
        makeActivity('orchestrator', 'status', 'MCP servers started and connected automatically')
      );

      // Start periodic polling
      startPolling();

      outputChannel.appendLine('Auto-connected to MCP servers on activation.');
    } catch (error) {
      outputChannel.appendLine(`Auto-connect failed: ${error}`);
      statusBar.setHealth('error');
      dashboardProvider.updateData({ connectionStatus: 'error' });
    }
  }).catch((error) => {
    outputChannel.appendLine(`Auto-start servers failed: ${error}`);
    outputChannel.appendLine('Use "Connect to MCP Servers" command to retry.');
    dashboardProvider.updateData({ connectionStatus: 'error' });
  });
}

export function deactivate(): void {
  // Cleanup handled by disposables (serverManager.stopAll + mcpClient.disconnect + stopPolling)
}
