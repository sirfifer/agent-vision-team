import * as vscode from 'vscode';
import { Task, TaskStatus } from '../models/Task';

const STATUS_ICONS: Record<TaskStatus, string> = {
  pending: 'circle-outline',
  in_progress: 'sync~spin',
  review: 'eye',
  complete: 'check',
};

export class TasksTreeProvider implements vscode.TreeDataProvider<TaskTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<TaskTreeItem | undefined>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private tasks: Task[] = [];

  refresh(): void {
    // TODO: Read task briefs from filesystem
    this._onDidChangeTreeData.fire(undefined);
  }

  updateTasks(tasks: Task[]): void {
    this.tasks = tasks;
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: TaskTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(): TaskTreeItem[] {
    return this.tasks.map((task) => new TaskTreeItem(task));
  }
}

export class TaskTreeItem extends vscode.TreeItem {
  constructor(public readonly task: Task) {
    super(task.title, vscode.TreeItemCollapsibleState.None);

    this.description = task.assigned_worker
      ? `${task.status} (${task.assigned_worker})`
      : task.status;

    this.tooltip = new vscode.MarkdownString(
      `**${task.title}**\n\n${task.description}\n\n` +
        `**Status:** ${task.status}\n` +
        (task.assigned_worker ? `**Worker:** ${task.assigned_worker}\n` : '') +
        `\n**Acceptance Criteria:**\n${task.acceptance_criteria.map((c) => `- ${c}`).join('\n')}`,
    );

    this.contextValue = 'task';
    this.iconPath = new vscode.ThemeIcon(STATUS_ICONS[task.status]);
  }
}
