import * as vscode from 'vscode';
import { Finding, Tier } from '../models/Finding';

const TIER_ORDER: Tier[] = ['vision', 'architecture', 'quality'];
const TIER_ICONS: Record<Tier, string> = {
  vision: 'error',
  architecture: 'warning',
  quality: 'info',
};

export class FindingsTreeProvider implements vscode.TreeDataProvider<
  FindingTreeItem | TierGroupItem
> {
  private _onDidChangeTreeData = new vscode.EventEmitter<
    FindingTreeItem | TierGroupItem | undefined
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private findings: Finding[] = [];
  private diagnosticCollections: Map<Tier, vscode.DiagnosticCollection> = new Map();

  constructor() {
    this.diagnosticCollections.set(
      'vision',
      vscode.languages.createDiagnosticCollection('collab-vision'),
    );
    this.diagnosticCollections.set(
      'architecture',
      vscode.languages.createDiagnosticCollection('collab-architecture'),
    );
    this.diagnosticCollections.set(
      'quality',
      vscode.languages.createDiagnosticCollection('collab-quality'),
    );
  }

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  updateFindings(findings: Finding[]): void {
    this.findings = findings;
    this._onDidChangeTreeData.fire(undefined);
    // TODO: Update diagnostics from findings
  }

  getTreeItem(element: FindingTreeItem | TierGroupItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: FindingTreeItem | TierGroupItem): (FindingTreeItem | TierGroupItem)[] {
    if (!element) {
      return TIER_ORDER.map((tier) => {
        const count = this.findings.filter((f) => f.tier === tier).length;
        return new TierGroupItem(tier, count);
      }).filter((group) => group.count > 0);
    }

    if (element instanceof TierGroupItem) {
      return this.findings
        .filter((f) => f.tier === element.tier)
        .map((f) => new FindingTreeItem(f));
    }

    return [];
  }

  dispose(): void {
    this.diagnosticCollections.forEach((dc) => dc.dispose());
  }
}

export class TierGroupItem extends vscode.TreeItem {
  constructor(
    public readonly tier: Tier,
    public readonly count: number,
  ) {
    super(
      `${tier.charAt(0).toUpperCase() + tier.slice(1)} (${count})`,
      vscode.TreeItemCollapsibleState.Expanded,
    );
    this.iconPath = new vscode.ThemeIcon(TIER_ICONS[tier]);
    this.contextValue = 'tierGroup';
  }
}

export class FindingTreeItem extends vscode.TreeItem {
  constructor(public readonly finding: Finding) {
    super(finding.payload.finding, vscode.TreeItemCollapsibleState.None);

    this.description = finding.payload.component;
    this.tooltip = new vscode.MarkdownString(
      `**${finding.severity}** — ${finding.payload.component}\n\n` +
        `${finding.payload.finding}\n\n` +
        `**Rationale:** ${finding.payload.rationale}\n\n` +
        (finding.payload.suggestion ? `**Suggestion:** ${finding.payload.suggestion}` : ''),
    );
    this.contextValue = 'finding';
    this.iconPath = new vscode.ThemeIcon(TIER_ICONS[finding.tier]);
  }
}
