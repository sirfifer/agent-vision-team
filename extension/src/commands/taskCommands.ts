import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getCollabRoot } from '../utils/config';
import { logSystem } from '../utils/logger';

const TASK_BRIEF_TEMPLATE = `# Task Brief: {{TASK_ID}}

## Goal
<!-- What should be accomplished -->

## Acceptance Criteria
- [ ] <!-- Criterion 1 -->
- [ ] <!-- Criterion 2 -->

## Constraints
- <!-- Scope limitations -->
- <!-- Files that may be modified -->

## Context
<!-- Relevant architectural patterns, vision standards, or prior work -->

## Notes
<!-- Additional context for the worker session -->
`;

export function registerTaskCommands(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('collab.createTaskBrief', async () => {
      const taskId = await vscode.window.showInputBox({
        prompt: 'Enter task ID',
        placeHolder: 'e.g., 001-auth-fix',
      });
      if (!taskId) {
        return;
      }

      const collabRoot = getCollabRoot();
      if (!collabRoot) {
        vscode.window.showErrorMessage('No workspace folder open.');
        return;
      }

      const briefsDir = path.join(collabRoot, 'task-briefs');
      if (!fs.existsSync(briefsDir)) {
        fs.mkdirSync(briefsDir, { recursive: true });
      }

      const briefPath = path.join(briefsDir, `task-${taskId}.md`);
      const content = TASK_BRIEF_TEMPLATE.replace('{{TASK_ID}}', taskId);

      fs.writeFileSync(briefPath, content, 'utf-8');
      logSystem(`Task brief created: ${briefPath}`);

      const doc = await vscode.workspace.openTextDocument(briefPath);
      await vscode.window.showTextDocument(doc);
    })
  );
}
