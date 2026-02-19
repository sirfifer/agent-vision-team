# Style Guide: Agent Vision Team

## Languages

The project uses three primary languages:
- **TypeScript** (VS Code extension, React dashboard)
- **Python** (MCP servers, AVT Gateway, E2E tests, hook scripts)
- **Bash** (hook scripts, build scripts, test harnesses)

---

## Naming Conventions

### Files

| Language | Convention | Examples |
|----------|-----------|----------|
| Python packages | snake_case | `collab_kg`, `collab_quality`, `avt_gateway` |
| Python modules | snake_case | `tier_protection.py`, `trust_engine.py`, `task_integration.py` |
| TypeScript source | PascalCase | `McpClientService.ts`, `DashboardWebviewProvider.ts` |
| React components | PascalCase | `AgentCards.tsx`, `GovernancePanel.tsx`, `SessionBar.tsx` |
| Agent definitions | kebab-case | `quality-reviewer.md`, `kg-librarian.md`, `project-bootstrapper.md` |
| Hook scripts | kebab-case | `governance-task-intercept.py`, `holistic-review-gate.sh` |
| Test files (Python) | `test_*.py` | `test_knowledge_graph.py`, `test_governance.py` |
| Config files | kebab-case or standard names | `tsconfig.json`, `pyproject.toml`, `vite.config.ts` |

### Code

| Scope | Convention | Examples |
|-------|-----------|----------|
| Python classes | PascalCase | `KnowledgeGraph`, `GovernanceStore`, `GovernanceReviewer` |
| Python functions | snake_case | `create_entities`, `submit_decision`, `check_all_gates` |
| Python constants | UPPER_SNAKE_CASE | `MIN_TASKS_FOR_REVIEW`, `PROJECT_DIR` |
| TypeScript classes | PascalCase | `McpClientService`, `DashboardWebviewProvider` |
| TypeScript functions | camelCase | `getEntity`, `handleMessage`, `registerCommands` |
| React components | PascalCase | `EntitiesPanel`, `GovernancePanel`, `AgentCards` |
| MCP tool names | snake_case | `create_entities`, `submit_decision`, `check_all_gates` |
| JSON/config keys | camelCase | `entityType`, `relationType`, `setupComplete` |

---

## Import Organization

### Python

Order: standard library, then third-party, then local. Use relative imports within packages.

```python
import os
import json
from pathlib import Path

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from .models import Entity, Relation
from .storage import Storage
```

### TypeScript

Order: VS Code API, Node.js built-ins, third-party, local.

```typescript
import * as vscode from 'vscode';
import * as path from 'path';

import { Entity, Relation } from '../models/Entity';
import { McpClientService } from '../services/McpClientService';
```

---

## Error Handling

### Python MCP Servers

Return error dicts rather than raising exceptions:

```python
def some_tool(param: str) -> dict:
    if not param:
        return {"error": "param is required"}
    # ... do work
    return {"result": "success"}
```

### TypeScript Extension

Try-catch with VS Code error display:

```typescript
try {
    const result = await mcpClient.callTool(...);
} catch (err) {
    vscode.window.showErrorMessage(`Operation failed: ${err}`);
}
```

### Hook Scripts

Never crash. Exit silently on parse errors. Log to `.avt/hook-governance.log`:

```python
try:
    data = json.loads(sys.stdin.read())
except:
    sys.exit(0)  # Silent exit on parse error
```

---

## Documentation

### Python

Use triple-quote docstrings with Args/Returns sections:

```python
def create_entity(name: str, entity_type: str) -> dict:
    """Create a new entity in the knowledge graph.

    Args:
        name: Unique entity name
        entity_type: One of 'vision', 'architecture', 'quality'

    Returns:
        Dict with created entity or error
    """
```

### TypeScript

Use JSDoc for public functions:

```typescript
/**
 * Fetches entity by name from the Knowledge Graph.
 * @param name - The entity name to look up
 * @returns The entity object or undefined if not found
 */
async getEntity(name: string): Promise<Entity | undefined> {
```

### General

- No em dashes in any prose (use commas, semicolons, colons, or parentheses)
- Inline comments only for non-obvious logic
- README.md per MCP server with tool listings and usage examples

---

## Formatting

### Python

- Indentation: 4 spaces
- Line length: 120 characters (soft limit)
- Quotes: double quotes for strings
- Package manager: `uv` (not pip directly)
- Minimum version: Python 3.12+
- Build backend: hatchling

### TypeScript

- Indentation: 2 spaces (configured in tsconfig)
- Semicolons: yes
- Quotes: single quotes
- Package manager: `npm`

### Bash

- Indentation: 2 spaces
- Shebang: `#!/usr/bin/env bash` or `#!/usr/bin/env python3`
- Set flags: `set -euo pipefail` for strict mode (when appropriate)
- Quote all variables: `"$var"` not `$var`

---

## Testing

### Python (pytest)

- Test files: `test_*.py` in `tests/` directory per package
- Fixtures: Pydantic model fixtures, fresh instances per test
- E2E: Scenario-based with `BaseScenario`, structural assertions
- Coverage threshold: 80%

### TypeScript (Mocha)

- Test files: `*.test.ts` (note: some pre-existing type errors in test setup)
- Framework: Mocha with assertion libraries

### Hook Tests

- Multi-level testing: mock (Level 1), real AI (Level 2), subagent (Level 3), session-scoped (Level 4)
- Test script: `scripts/hooks/test-hook-live.sh --level {1,2,3,4}`

---

## Build Commands

| Component | Command |
|-----------|---------|
| Extension backend | `cd extension && node esbuild.config.js` |
| Webview dashboard | `cd extension/webview-dashboard && npm run build` |
| MCP servers | `cd mcp-servers/<name> && uv run python -m collab_<name>.server` |
| Gateway | `cd server && uv run uvicorn avt_gateway.app:app` |
| E2E tests | `python e2e/run-e2e.py` |
| Hook unit tests | `scripts/hooks/test-hook-unit.sh` |

**Important**: Extension backend build uses `node esbuild.config.js`, NOT `npm run compile`.
