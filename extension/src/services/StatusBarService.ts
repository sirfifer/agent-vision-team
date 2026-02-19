import * as vscode from 'vscode';

export type SystemHealth = 'active' | 'warning' | 'error' | 'inactive';

export class StatusBarService {
  private statusItem: vscode.StatusBarItem;
  private summaryItem: vscode.StatusBarItem;

  constructor() {
    this.statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    this.statusItem.command = 'collab.viewDashboard';

    this.summaryItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 99);
    this.summaryItem.command = 'collab.viewDashboard';
  }

  show(): void {
    this.statusItem.show();
    this.summaryItem.show();
  }

  hide(): void {
    this.statusItem.hide();
    this.summaryItem.hide();
  }

  setHealth(health: SystemHealth): void {
    switch (health) {
      case 'active':
        this.statusItem.text = '$(shield) Collab: Active';
        this.statusItem.backgroundColor = undefined;
        break;
      case 'warning':
        this.statusItem.text = '$(warning) Collab: Warning';
        this.statusItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        break;
      case 'error':
        this.statusItem.text = '$(error) Collab: Error';
        this.statusItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
        break;
      case 'inactive':
        this.statusItem.text = '$(circle-outline) Collab: Inactive';
        this.statusItem.backgroundColor = undefined;
        break;
    }
  }

  setSummary(workers: number, findings: number, phase: string): void {
    this.summaryItem.text = `${workers} workers · ${findings} findings · Phase: ${phase}`;
  }

  dispose(): void {
    this.statusItem.dispose();
    this.summaryItem.dispose();
  }
}
