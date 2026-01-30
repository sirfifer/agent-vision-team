import * as vscode from 'vscode';
import { Entity, ProtectionTier } from '../models/Entity';

const TIER_ORDER: ProtectionTier[] = ['vision', 'architecture', 'quality'];
const TIER_LABELS: Record<ProtectionTier, string> = {
  vision: 'Vision Standards (immutable)',
  architecture: 'Architecture (human-approved)',
  quality: 'Quality (automated)',
};

export class MemoryTreeProvider implements vscode.TreeDataProvider<MemoryTreeItem | TierGroupItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<MemoryTreeItem | TierGroupItem | undefined>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private entities: Entity[] = [];

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  updateEntities(entities: Entity[]): void {
    this.entities = entities;
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: MemoryTreeItem | TierGroupItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: MemoryTreeItem | TierGroupItem): (MemoryTreeItem | TierGroupItem)[] {
    if (!element) {
      return TIER_ORDER.map(tier => {
        const count = this.entities.filter(e =>
          e.observations.some(o => o.includes(`protection_tier: ${tier}`))
        ).length;
        return new TierGroupItem(tier, count);
      });
    }

    if (element instanceof TierGroupItem) {
      return this.entities
        .filter(e =>
          e.observations.some(o => o.includes(`protection_tier: ${element.tier}`))
        )
        .map(e => new MemoryTreeItem(e));
    }

    return [];
  }
}

class TierGroupItem extends vscode.TreeItem {
  constructor(
    public readonly tier: ProtectionTier,
    count: number
  ) {
    super(
      `${TIER_LABELS[tier]} (${count})`,
      vscode.TreeItemCollapsibleState.Collapsed
    );
    this.contextValue = 'memoryTierGroup';
  }
}

class MemoryTreeItem extends vscode.TreeItem {
  constructor(public readonly entity: Entity) {
    super(entity.name, vscode.TreeItemCollapsibleState.None);

    this.description = `[${entity.entityType}] ${entity.observations.length} observations, ${entity.relations.length} relations`;
    this.tooltip = new vscode.MarkdownString(
      `**${entity.name}** (${entity.entityType})\n\n` +
      `**Observations:**\n${entity.observations.map(o => `- ${o}`).join('\n')}\n\n` +
      `**Relations:**\n${entity.relations.map(r => `- ${r.relationType} → ${r.to}`).join('\n')}`
    );
    this.contextValue = 'memoryEntity';
  }
}
