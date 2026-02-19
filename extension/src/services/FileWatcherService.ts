import * as vscode from 'vscode';
import { logSystem } from '../utils/logger';

export class FileWatcherService {
  private watchers: vscode.FileSystemWatcher[] = [];
  private onTaskBriefChange: vscode.EventEmitter<void> = new vscode.EventEmitter();
  private onSessionStateChange: vscode.EventEmitter<void> = new vscode.EventEmitter();

  readonly onDidChangeTaskBriefs = this.onTaskBriefChange.event;
  readonly onDidChangeSessionState = this.onSessionStateChange.event;

  initialize(): void {
    const taskBriefWatcher = vscode.workspace.createFileSystemWatcher('**/.avt/task-briefs/**');
    taskBriefWatcher.onDidChange(() => {
      logSystem('Task brief changed');
      this.onTaskBriefChange.fire();
    });
    taskBriefWatcher.onDidCreate(() => {
      logSystem('Task brief created');
      this.onTaskBriefChange.fire();
    });
    taskBriefWatcher.onDidDelete(() => {
      logSystem('Task brief deleted');
      this.onTaskBriefChange.fire();
    });
    this.watchers.push(taskBriefWatcher);

    const sessionStateWatcher = vscode.workspace.createFileSystemWatcher(
      '**/.avt/session-state.md',
    );
    sessionStateWatcher.onDidChange(() => {
      logSystem('Session state changed');
      this.onSessionStateChange.fire();
    });
    this.watchers.push(sessionStateWatcher);
  }

  dispose(): void {
    this.watchers.forEach((w) => w.dispose());
    this.onTaskBriefChange.dispose();
    this.onSessionStateChange.dispose();
  }
}
