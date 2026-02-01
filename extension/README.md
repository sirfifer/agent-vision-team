# Collab Intelligence Extension

Observability dashboard for the Collaborative Intelligence System — view knowledge graph, quality findings, and task status.

## Overview

This VS Code extension provides read-only observability into the Collaborative Intelligence System. It **does not orchestrate** agents or sessions; it **displays state** from the MCP servers that Claude Code subagents use.

**Key Principle**: Claude Code orchestrates, the extension observes.

## Features

### 1. Memory Browser (TreeView)
- Displays Knowledge Graph entities grouped by protection tier
- **Vision Standards** (immutable) - Core principles and invariants
- **Architecture** (human-approved) - Patterns and major components
- **Quality** (automated) - Observations and troubleshooting notes
- Shows entity type, observation count, relation count
- Tooltip displays full observations and relations
- Refresh and search capabilities

### 2. Findings Panel (TreeView)
- Displays quality findings from lint/test runs
- Groups findings by severity or component
- Updates via Quality MCP server
- Refresh to get latest findings

### 3. Tasks Panel (TreeView)
- Watches `.claude/collab/task-briefs/` directory
- Shows task brief files from filesystem
- Auto-refreshes on file changes

### 4. Status Bar
- **Health Indicator**: $(shield) Collab: Active/Inactive/Error
- **Finding Count**: N findings · Phase: active/inactive
- Click to open dashboard

### 5. Commands

| Command | Description |
|---------|-------------|
| `Refresh Memory Browser` | Re-fetch KG entities from server |
| `Refresh Findings Panel` | Re-fetch quality findings from server |
| `Refresh Tasks Panel` | Reload task briefs from filesystem |
| `Search Memory` | Full-text search across KG entities |
| `View Dashboard` | Open dashboard webview |
| `Validate All Quality Gates` | Run all quality gates and show results |
| `Connect to MCP Servers` | Manually connect to MCP servers |

## Prerequisites

### 1. MCP Servers Running

The extension connects to two MCP servers:
- **Knowledge Graph**: `http://localhost:3101`
- **Quality**: `http://localhost:3102`

Start them before using the extension:

```bash
# Terminal 1: Knowledge Graph server
cd mcp-servers/knowledge-graph
uv run python -m collab_kg.server

# Terminal 2: Quality server
cd mcp-servers/quality
uv run python -m collab_quality.server
```

### 2. Workspace Structure

Your workspace must contain:
```
.claude/
├── collab/
│   ├── task-briefs/           # Task brief files
│   ├── memory/                 # Archival memory files
│   ├── session-state.md        # Session progress
│   ├── knowledge-graph.jsonl   # KG persistence (created by server)
│   └── trust-engine.db         # Trust engine DB (created by server)
└── agents/                     # Subagent definitions
    ├── worker.md
    ├── quality-reviewer.md
    └── kg-librarian.md
```

The extension activates when it detects `.claude/collab/` in the workspace.

## Installation

### From Source (Development)

```bash
cd extension
npm install
npm run build

# Launch Extension Development Host
# Press F5 in VS Code
```

### Package as VSIX

```bash
npm install -g @vscode/vsce
cd extension
vsce package
# Installs extension/collab-intelligence-0.1.0.vsix
```

Then install via:
- VS Code → Extensions → ... → Install from VSIX

## Usage

### 1. Start MCP Servers

```bash
cd mcp-servers/knowledge-graph && uv run python -m collab_kg.server &
cd mcp-servers/quality && uv run python -m collab_quality.server &
```

### 2. Open Workspace

Open a workspace containing `.claude/collab/` directory.

### 3. Extension Activates

- Activity bar shows "Collab Intelligence" icon
- Extension auto-connects to MCP servers
- Initial data load:
  - Memory Browser fetches all KG entities
  - Findings Panel fetches lint results
  - Tasks Panel watches task-briefs directory

### 4. Interact with UI

**Memory Browser:**
- Expand tier groups to see entities
- Hover over entities to see observations and relations
- Click refresh button to reload from server
- Click search button to search KG

**Findings Panel:**
- View quality findings grouped by severity
- Click refresh to get latest findings
- Findings update when quality checks run

**Tasks Panel:**
- View task briefs from filesystem
- Auto-refreshes when files change

**Status Bar:**
- Shows connection health
- Displays finding count
- Click to open dashboard

## Architecture

### MCP Client Service

`McpClientService` provides read-only access to MCP servers:

```typescript
// Connect to servers
await mcpClient.connect();

// Call tools via HTTP JSON-RPC
const result = await mcpClient.callTool(
  'knowledge-graph',
  'search_nodes',
  { query: 'auth' }
);
```

Endpoints:
- `GET /health` - Health check
- `POST /mcp/call` - Tool invocation

### Typed MCP Clients

**KnowledgeGraphClient** (`mcp/KnowledgeGraphClient.ts`):
- `createEntities(entities)` - Create KG entities
- `createRelations(relations)` - Create relations
- `addObservations(entityName, observations)` - Add observations
- `searchNodes(query)` - Full-text search
- `getEntity(name)` - Get single entity
- `getEntitiesByTier(tier)` - Get all entities at tier
- `validateTierAccess(entityName, operation, callerRole)` - Check tier access

**QualityClient** (`mcp/QualityClient.ts`):
- `autoFormat(files, language)` - Format code
- `runLint(files, language)` - Lint code
- `runTests(scope, language)` - Run tests
- `checkCoverage(language)` - Check test coverage
- `checkAllGates()` - Run all quality gates
- `validate()` - Comprehensive validation
- `getTrustDecision(findingId)` - Get trust decision for finding
- `recordDismissal(findingId, justification, dismissedBy)` - Dismiss finding

### Tree View Providers

**MemoryTreeProvider** (`providers/MemoryTreeProvider.ts`):
- Implements `vscode.TreeDataProvider<MemoryTreeItem>`
- Groups entities by protection tier
- Updates via `updateEntities(entities: Entity[])`
- Refreshes via `refresh()`

**FindingsTreeProvider** (`providers/FindingsTreeProvider.ts`):
- Displays quality findings
- Updates via `updateFindings(findings: LintFinding[])`

**TasksTreeProvider** (`providers/TasksTreeProvider.ts`):
- Filesystem-based (watches `.claude/collab/task-briefs/`)
- Auto-refreshes on file changes

### Data Flow

1. **Extension Activation**
   - `McpClientService` connects to servers (ports 3101, 3102)
   - Initial data fetch:
     - `kgClient.getEntitiesByTier('vision')` → Memory Browser
     - `kgClient.getEntitiesByTier('architecture')` → Memory Browser
     - `kgClient.getEntitiesByTier('quality')` → Memory Browser
     - `qualityClient.runLint()` → Findings Panel
   - File watchers start

2. **User Refresh**
   - Click refresh button
   - Re-fetch data from MCP servers
   - Update tree views

3. **File Changes**
   - Task brief added/modified
   - File watcher triggers refresh
   - Tasks Panel updates

## Configuration

The extension uses default MCP server ports:
- **Knowledge Graph**: 3101
- **Quality**: 3102

To customize, create `.claude/collab/mcp-config.json`:

```json
{
  "servers": {
    "knowledge-graph": {
      "command": "python",
      "args": ["-m", "collab_kg.server"],
      "port": 3101,
      "env": {}
    },
    "quality": {
      "command": "python",
      "args": ["-m", "collab_quality.server"],
      "port": 3102,
      "env": {}
    }
  }
}
```

## Testing

See [TESTING.md](./TESTING.md) for comprehensive test documentation.

### Unit Tests

```bash
npm run test
```

Tests cover:
- MCP client service (connection, tool calling)
- Tree view providers (data grouping, updates)
- KG and Quality clients (method signatures)

### Integration Tests

Integration tests require live MCP servers. They are skipped by default (marked with `test.skip`).

To run integration tests:
1. Start both MCP servers
2. Remove `.skip` from integration test cases
3. Run `npm test`

## Troubleshooting

### Extension doesn't activate
- **Check**: Does workspace contain `.claude/collab/` directory?
- **Fix**: Create directory structure (see Prerequisites)

### "MCP servers not available" warning
- **Check**: Are servers running on ports 3101 and 3102?
- **Fix**: Start servers (see Usage step 1)
- **Verify**: `curl http://localhost:3101/health` and `curl http://localhost:3102/health`

### Memory Browser shows empty tiers
- **Check**: Does KG have entities?
- **Fix**: Populate KG via Claude Code subagents or manually:
  ```typescript
  kgClient.createEntities([{
    name: "test_standard",
    entityType: "vision_standard",
    observations: ["protection_tier: vision", "Description"]
  }]);
  ```

### Findings Panel shows no findings
- **Check**: Have you run lint?
- **Fix**: Run `qualityClient.runLint()` or use Claude Code worker to make changes

### Status bar shows "Error"
- **Check**: MCP server health endpoints
- **Fix**: Restart servers, check logs

## Development

### Project Structure

```
extension/
├── src/
│   ├── commands/               # Command handlers
│   ├── mcp/                    # MCP client wrappers
│   │   ├── KnowledgeGraphClient.ts
│   │   └── QualityClient.ts
│   ├── models/                 # Data models
│   │   └── Entity.ts
│   ├── providers/              # TreeView providers
│   │   ├── MemoryTreeProvider.ts
│   │   ├── FindingsTreeProvider.ts
│   │   ├── TasksTreeProvider.ts
│   │   └── DashboardWebviewProvider.ts
│   ├── services/               # Core services
│   │   ├── McpClientService.ts
│   │   ├── FileWatcherService.ts
│   │   └── StatusBarService.ts
│   ├── test/                   # Unit and integration tests
│   ├── utils/                  # Utilities (logger, config)
│   └── extension.ts            # Entry point
├── webview-dashboard/          # React dashboard
├── package.json                # Extension manifest
├── tsconfig.json               # TypeScript config
└── esbuild.config.js           # Build config
```

### Build Commands

```bash
npm run build        # Build once
npm run watch        # Build and watch for changes
npm run lint         # Run ESLint
npm run pretest      # Build before testing
```

### Adding New Features

1. **New MCP Tool**:
   - Add method to `KnowledgeGraphClient` or `QualityClient`
   - Update TypeScript interfaces
   - Add tests in `src/test/`

2. **New Tree View**:
   - Create provider in `src/providers/`
   - Register in `extension.ts` via `registerTreeDataProvider`
   - Add view to `package.json` contributes

3. **New Command**:
   - Implement handler
   - Register in `extension.ts` via `registerCommand`
   - Add to `package.json` contributes

## See Also

- [TESTING.md](./TESTING.md) - Test documentation
- [../../ARCHITECTURE.md](../../ARCHITECTURE.md) - System architecture
- [../../CLAUDE.md](../../CLAUDE.md) - Orchestrator instructions
- [../../.claude/VALIDATION.md](../../.claude/VALIDATION.md) - Validation guide

## License

See root [LICENSE](../LICENSE) file.
