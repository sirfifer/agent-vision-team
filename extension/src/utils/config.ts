import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export interface McpServerConfig {
  command: string;
  args: string[];
  port: number;
  env: Record<string, string>;
}

export interface CollabConfig {
  servers: {
    'knowledge-graph': McpServerConfig;
    quality: McpServerConfig;
  };
}

const DEFAULT_CONFIG: CollabConfig = {
  servers: {
    'knowledge-graph': {
      command: 'python',
      args: ['-m', 'collab_kg.server'],
      port: 3101,
      env: {},
    },
    quality: {
      command: 'python',
      args: ['-m', 'collab_quality.server'],
      port: 3102,
      env: {},
    },
  },
};

export function getCollabRoot(): string | undefined {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    return undefined;
  }
  return path.join(workspaceFolder.uri.fsPath, '.claude', 'collab');
}

export function loadConfig(): CollabConfig {
  const collabRoot = getCollabRoot();
  if (!collabRoot) {
    return DEFAULT_CONFIG;
  }

  const configPath = path.join(collabRoot, 'mcp-config.json');
  if (!fs.existsSync(configPath)) {
    return DEFAULT_CONFIG;
  }

  try {
    const raw = fs.readFileSync(configPath, 'utf-8');
    return JSON.parse(raw) as CollabConfig;
  } catch {
    return DEFAULT_CONFIG;
  }
}
