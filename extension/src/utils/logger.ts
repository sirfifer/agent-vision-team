import * as vscode from 'vscode';

let systemChannel: vscode.OutputChannel;
let qualityChannel: vscode.OutputChannel;
let memoryChannel: vscode.OutputChannel;

export function initializeLoggers(): void {
  systemChannel = vscode.window.createOutputChannel('Collab Intelligence: System');
  qualityChannel = vscode.window.createOutputChannel('Collab Intelligence: Quality');
  memoryChannel = vscode.window.createOutputChannel('Collab Intelligence: Memory');
}

export function logSystem(message: string): void {
  systemChannel?.appendLine(`[${new Date().toISOString()}] ${message}`);
}

export function logQuality(message: string): void {
  qualityChannel?.appendLine(`[${new Date().toISOString()}] ${message}`);
}

export function logMemory(message: string): void {
  memoryChannel?.appendLine(`[${new Date().toISOString()}] ${message}`);
}

export function disposeLoggers(): void {
  systemChannel?.dispose();
  qualityChannel?.dispose();
  memoryChannel?.dispose();
}
