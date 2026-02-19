import * as vscode from 'vscode';
import { KnowledgeGraphClient } from '../mcp/KnowledgeGraphClient';
import { logMemory } from '../utils/logger';

export function registerMemoryCommands(
  context: vscode.ExtensionContext,
  kgClient: KnowledgeGraphClient,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.searchMemory', async () => {
      const query = await vscode.window.showInputBox({
        prompt: 'Search knowledge graph',
        placeHolder: 'e.g., KBOralSessionView',
      });
      if (!query) {
        return;
      }

      try {
        const results = await kgClient.searchNodes(query);
        logMemory(`Search for '${query}' returned ${results.length} results`);
        // TODO: Display results in Memory Browser or quick pick
        vscode.window.showInformationMessage(
          `Found ${results.length} entities matching '${query}'.`,
        );
      } catch (error) {
        vscode.window.showErrorMessage(`Memory search failed: ${error}`);
      }
    }),
  );
}
