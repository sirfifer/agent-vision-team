import * as vscode from 'vscode';
import * as path from 'path';
import { ChildProcess, spawn } from 'child_process';
import { logSystem } from '../utils/logger';

interface ServerDef {
  name: string;
  module: string;
  cwd: string;       // relative to workspace root
  port: number;
}

const SERVERS: ServerDef[] = [
  { name: 'Knowledge Graph', module: 'collab_kg.server', cwd: 'mcp-servers/knowledge-graph', port: 3101 },
  { name: 'Quality',         module: 'collab_quality.server', cwd: 'mcp-servers/quality',    port: 3102 },
  { name: 'Governance',      module: 'collab_governance.server', cwd: 'mcp-servers/governance', port: 3103 },
];

const READY_POLL_INTERVAL = 500;
const READY_TIMEOUT = 15000;

export class McpServerManager {
  private processes: Map<string, ChildProcess> = new Map();
  private outputChannel: vscode.OutputChannel;

  constructor(outputChannel: vscode.OutputChannel) {
    this.outputChannel = outputChannel;
  }

  async startAll(): Promise<void> {
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!workspaceRoot) {
      throw new Error('No workspace folder open.');
    }

    logSystem('Starting all MCP servers...');
    this.outputChannel.appendLine('Starting MCP servers...');

    const startPromises = SERVERS.map(server => this.startServer(server, workspaceRoot));
    const results = await Promise.allSettled(startPromises);

    const failed: string[] = [];
    for (let i = 0; i < results.length; i++) {
      if (results[i].status === 'rejected') {
        failed.push(`${SERVERS[i].name}: ${(results[i] as PromiseRejectedResult).reason}`);
      }
    }

    if (failed.length > 0) {
      const msg = `Failed to start servers:\n${failed.join('\n')}`;
      logSystem(msg);
      this.outputChannel.appendLine(msg);
      throw new Error(msg);
    }

    logSystem('All MCP servers started.');
    this.outputChannel.appendLine('All MCP servers started and ready.');
  }

  private async startServer(server: ServerDef, workspaceRoot: string): Promise<void> {
    // Check if already running on that port
    if (await this.isPortReady(server.port)) {
      logSystem(`${server.name} already running on port ${server.port}.`);
      this.outputChannel.appendLine(`${server.name} already running on port ${server.port}.`);
      return;
    }

    const cwd = path.join(workspaceRoot, server.cwd);
    const proc = spawn('uv', ['run', 'python', '-m', server.module], {
      cwd,
      stdio: ['ignore', 'pipe', 'pipe'],
      detached: false,
    });

    this.processes.set(server.name, proc);

    proc.stdout?.on('data', (data: Buffer) => {
      this.outputChannel.appendLine(`[${server.name}] ${data.toString().trim()}`);
    });

    proc.stderr?.on('data', (data: Buffer) => {
      this.outputChannel.appendLine(`[${server.name}] ${data.toString().trim()}`);
    });

    proc.on('exit', (code) => {
      logSystem(`${server.name} server exited with code ${code}`);
      this.processes.delete(server.name);
    });

    proc.on('error', (err) => {
      logSystem(`${server.name} server error: ${err.message}`);
      this.processes.delete(server.name);
    });

    this.outputChannel.appendLine(`${server.name} starting on port ${server.port}...`);

    // Wait until the port is accepting connections
    await this.waitForReady(server.name, server.port);
  }

  private async waitForReady(name: string, port: number): Promise<void> {
    const start = Date.now();
    while (Date.now() - start < READY_TIMEOUT) {
      if (await this.isPortReady(port)) {
        logSystem(`${name} ready on port ${port}.`);
        this.outputChannel.appendLine(`${name} ready on port ${port}.`);
        return;
      }
      await new Promise(r => setTimeout(r, READY_POLL_INTERVAL));
    }
    throw new Error(`${name} did not become ready on port ${port} within ${READY_TIMEOUT / 1000}s`);
  }

  private async isPortReady(port: number): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2000);
      const response = await fetch(`http://localhost:${port}/sse`, {
        signal: controller.signal,
      });
      clearTimeout(timeout);
      // The SSE endpoint returns 200 with a streaming body — that means it's up
      // We don't need the stream, just abort after confirming it's alive
      response.body?.cancel();
      return true;
    } catch {
      return false;
    }
  }

  stopAll(): void {
    logSystem('Stopping all MCP servers...');
    for (const [name, proc] of this.processes) {
      logSystem(`Stopping ${name}...`);
      proc.kill('SIGTERM');
    }
    this.processes.clear();
  }

  isRunning(name: string): boolean {
    return this.processes.has(name);
  }

  get runningCount(): number {
    return this.processes.size;
  }
}
