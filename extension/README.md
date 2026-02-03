# Collab Intelligence Extension

Observability dashboard for the Collaborative Intelligence System — view knowledge graph entities, governance decisions, quality findings, agent status, and task progress in real time.

## Overview

This VS Code extension provides read-only observability into the Collaborative Intelligence System. It **does not orchestrate** agents or sessions; it **displays state** from three MCP servers that Claude Code subagents use.

**Key Principle**: Claude Code orchestrates, the extension observes.

### What You See

- **Session Bar** — Connection status, orchestration phase, active task count, and action buttons
- **Agent Cards** — Live status of all configured agents (orchestrator, workers, reviewers, librarian)
- **Governance Panel** — Vision standards and architectural elements from the Knowledge Graph, with observations and cross-references
- **Activity Feed** — Chronological log of findings, decisions, reviews, guidance, status updates, and drift alerts

All UI elements have tooltips. Hover over any element to see what it represents, what data it shows, and how to interact with it.

## Quick Start

### 1. Install Dependencies

```bash
# Extension
cd extension
npm install
cd webview-dashboard && npm install && cd ..

# MCP servers (each needs its own venv)
cd ../mcp-servers/knowledge-graph && uv sync
cd ../quality && uv sync
cd ../governance && uv sync
```

### 2. Build

```bash
cd extension
npm run build
```

### 3. Launch

Press **F5** in VS Code to open the Extension Development Host. The extension:

1. Auto-starts all three MCP servers as child processes
2. Waits for each server to become ready (up to 15 seconds per server)
3. Connects to all servers via SSE
4. Loads initial data (KG entities, governance status, task counts)
5. Displays the dashboard

No manual server startup required.

### 4. Open the Dashboard

- Click the **Collab Intelligence** icon in the Activity Bar, or
- Run command: **Collab Intelligence: View Dashboard**

## MCP Servers

The extension manages three MCP servers that run as child processes:

| Server | Port | Purpose |
|--------|------|---------|
| **Knowledge Graph** | 3101 | Persistent institutional memory with tier-protected entities |
| **Quality** | 3102 | Deterministic quality verification (build, lint, tests, coverage) |
| **Governance** | 3103 | Transactional review checkpoints for agent decisions |

All three servers are **required**. The extension will report an error if any server fails to start or connect.

### Auto-Start Behavior

On extension activation:
1. The `McpServerManager` spawns each server using `uv run python -m <module>` in the appropriate working directory
2. Each server is polled on its port until it responds (500ms intervals, 15s timeout)
3. If a port is already responding (server already running), the manager skips spawning that server
4. On extension deactivation, all managed server processes receive SIGTERM

### Manual Control

If auto-start fails, you can start servers manually:

```bash
# Terminal 1
cd mcp-servers/knowledge-graph && uv run python -m collab_kg.server

# Terminal 2
cd mcp-servers/quality && uv run python -m collab_quality.server

# Terminal 3
cd mcp-servers/governance && uv run python -m collab_governance.server
```

Then click **Connect** in the dashboard Session Bar.

## Dashboard Components

### Session Bar

The top bar shows system-wide status and provides action buttons.

| Element | Description |
|---------|-------------|
| **Phase** | Current orchestration phase (planning, implementing, reviewing, inactive) |
| **Tasks** | Active task briefs / total task briefs in `.claude/collab/task-briefs/` |
| **Status dot** | Green = connected, gray = disconnected, red = error |
| **Connect** | Start all MCP servers and establish connections |
| **Refresh** | Reload KG entities, governance decisions, and task counts from servers |
| **Validate** | Run all quality gates (build, lint, tests, coverage, findings) via the Quality server |

### Agent Cards

Shows the status of each configured agent in the system.

| Agent | Role | What It Does |
|-------|------|--------------|
| **Orchestrator** | `orchestrator` | Coordinates workers, enforces governance, manages session lifecycle |
| **Worker** (1-N) | `worker` | Implements scoped task briefs under governance checkpoints |
| **Quality Reviewer** | `quality-reviewer` | Runs deterministic quality gates |
| **KG Librarian** | `kg-librarian` | Curates Knowledge Graph entities and observations |
| **Governance Reviewer** | `governance-reviewer` | Evaluates decisions against vision and architecture standards |

Status values:
- **Active** (green) — Currently executing work
- **Idle** (gray) — Configured but not currently active
- **Not Configured** (muted) — Not set up in this session

Click an active/idle agent card to filter the Activity Feed to show only that agent's entries.

### Governance Panel

Displays Knowledge Graph entities organized into two sections:

**Vision Standards** — Core principles and invariants. Human-only modifiable. Violations block all related work. Examples:
- "All services use protocol-based dependency injection"
- "No singletons in production code"

**Architectural Elements** — Design rules, patterns, components, problems, and solution patterns. Includes:
- `architectural_standard` — Design rules enforced across the codebase
- `pattern` — Established implementation patterns agents should follow
- `component` — Tracked system components with state observations
- `problem` — Tracked issues needing attention
- `solution_pattern` — Proven approaches promoted from recurring successes

Each entity shows:
- **Name** — The entity identifier
- **Type badge** — Color-coded by tier (red = vision, blue = architecture, green = quality)
- **Activity count** — Number of Activity Feed entries referencing this entity
- **Observations** — Expand to see all observations recorded against the entity
- **Filter button** — Click to filter the Activity Feed to entries referencing this entity

### Activity Feed

Chronological log of all system activity. Each entry shows:

| Element | Description |
|---------|-------------|
| **Agent badge** | Color-coded circle with agent initials (OR, W1, QR, KG, GV) |
| **Timestamp** | When the activity occurred |
| **Type icon** | Visual indicator of activity type |
| **Summary** | One-line description |
| **Governance ref** | Link to related KG entity (if applicable) |
| **Detail** | Click to expand and see full detail text |

Activity types:

| Type | Icon | Meaning |
|------|------|---------|
| Finding | Warning sign | Quality or governance issue detected |
| Guidance | Info circle | Actionable recommendation from a reviewer |
| Response | Checkmark | Agent acted on a finding or guidance |
| Status | Dot | Operational update from an agent |
| Drift | Cycle arrows | Deviation from expected behavior or timeline |
| Decision | Scales | Governance checkpoint submitted by an agent |
| Review | Ballot check | Governance verdict returned for a decision or plan |

**Filtering**: Use the filter buttons at the top of the feed to show only specific activity types. You can also filter by agent (click an Agent Card) or by governance entity (click the filter button in a Governance Panel item).

The left border color indicates protection tier:
- **Red** — Vision tier (highest priority)
- **Blue** — Architecture tier
- **Green** — Quality tier
- **Gray** — No tier assigned

## Commands

All commands are available via the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`):

| Command | Description |
|---------|-------------|
| `Collab Intelligence: View Dashboard` | Open the observability dashboard |
| `Collab Intelligence: Connect to MCP Servers` | Start servers and connect |
| `Collab Intelligence: Validate All Quality Gates` | Run build, lint, tests, coverage checks |
| `Collab Intelligence: Refresh Memory Browser` | Re-fetch KG entities |
| `Collab Intelligence: Refresh Findings Panel` | Re-fetch quality findings |
| `Collab Intelligence: Refresh Tasks Panel` | Reload task briefs from filesystem |
| `Collab Intelligence: Search Memory` | Full-text search across KG entities |

## Workspace Structure

The extension expects this directory structure in your workspace:

```
.claude/
├── agents/                          # Subagent definitions
│   ├── worker.md
│   ├── quality-reviewer.md
│   ├── kg-librarian.md
│   └── governance-reviewer.md
├── collab/
│   ├── task-briefs/                 # Task brief files
│   ├── session-state.md             # Current session progress
│   ├── memory/                      # Archival memory files
│   │   ├── architectural-decisions.md
│   │   ├── troubleshooting-log.md
│   │   └── solution-patterns.md
│   ├── knowledge-graph.jsonl        # KG persistence (managed by KG server)
│   ├── trust-engine.db              # Trust engine DB (managed by Quality server)
│   └── governance.db                # Governance decisions/reviews (managed by Governance server)
└── settings.json                    # Claude Code settings, hooks, and MCP server config
```

## Configuration

### Default Ports

| Server | Default Port |
|--------|-------------|
| Knowledge Graph | 3101 |
| Quality | 3102 |
| Governance | 3103 |

### Custom Configuration

Create `.claude/collab/mcp-config.json` to override defaults:

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
    },
    "governance": {
      "command": "python",
      "args": ["-m", "collab_governance.server"],
      "port": 3103,
      "env": {}
    }
  }
}
```

## How the Governance System Works

The Governance MCP server provides **transactional review checkpoints** for agent decisions. When an agent calls a governance tool, the call **blocks** until the review completes. This is synchronous, not fire-and-forget.

### Decision Flow

1. Agent reaches a decision point (pattern choice, component design, API design, etc.)
2. Agent calls `submit_decision()` on the Governance server
3. The server stores the decision, loads KG standards, runs `claude --print` with the governance-reviewer agent
4. The server returns a verdict: `approved`, `blocked`, or `needs_human_review`
5. Agent acts on the verdict — proceeds, revises, or flags for human review

### Checkpoint Types

| Tool | When Used | What It Does |
|------|-----------|--------------|
| `submit_decision` | Before implementing any key decision | AI review against vision/architecture standards |
| `submit_plan_for_review` | Before presenting a plan to the human | Full plan review with all accumulated decisions |
| `submit_completion_review` | When a worker finishes its task | Final check for unreviewed or blocked decisions |

### Auto-Flagging

Decisions with category `deviation` or `scope_change` are automatically assigned `needs_human_review` — they always require human sign-off.

### Safety Net

A `PreToolUse` hook on `ExitPlanMode` checks the governance database for plan reviews. If an agent tries to exit plan mode without submitting a plan for governance review, the hook blocks the action.

## Tooltips Reference

Every interactive element in the dashboard has a tooltip. Here's what you'll find:

### Session Bar Tooltips
- **Phase**: "Current orchestration phase. Tracks where the session is in its lifecycle."
- **Tasks**: Dynamic count of active/total task briefs
- **Status dot**: Connection status explanation
- **Connect**: "Start all MCP servers and establish connections"
- **Refresh**: "Reload Knowledge Graph entities, governance decision history, and task counts"
- **Validate**: "Run all quality gates via the Quality MCP server"

### Agent Card Tooltips
- Each card shows role description, current status, and interaction hint
- Status dots explain what each status means

### Governance Panel Tooltips
- Section headers explain the tier and its modification rules
- Toggle buttons explain show/hide behavior
- Entity counts show how many items are in each section
- Entity type badges show full type descriptions
- Observation bullets show full text on hover

### Activity Entry Tooltips
- Agent badges show full role descriptions
- Timestamps show full ISO timestamp
- Type icons show activity type descriptions
- Summaries show full text (useful when truncated)
- Governance refs explain the cross-reference
- Left border colors indicate protection tier

## Troubleshooting

### Extension doesn't activate
- **Check**: Does workspace contain `.claude/collab/` directory?
- **Fix**: Create the directory structure (see Workspace Structure above)

### "Failed to connect to MCP servers"
- **Check**: Are all three servers running? The error message names which server(s) failed.
- **Fix**: Check server logs in the Output panel. Servers may have failed to start due to missing dependencies.
- **Verify ports**:
  ```bash
  curl http://localhost:3101/sse
  curl http://localhost:3102/sse
  curl http://localhost:3103/sse
  ```

### Servers fail to auto-start
- **Check**: Is `uv` installed and on PATH?
- **Check**: Are Python virtual environments initialized?
  ```bash
  cd mcp-servers/knowledge-graph && uv sync
  cd ../quality && uv sync
  cd ../governance && uv sync
  ```
- **Check**: The Output panel for "Collab Intelligence" channel shows server startup logs

### Dashboard shows "disconnected"
- Click **Connect** in the Session Bar to retry
- If servers crashed, they need to be restarted (deactivate and reactivate the extension, or restart VS Code)

### Governance Panel is empty
- **Check**: Does the Knowledge Graph have entities? Run `search_nodes("*")` via Claude Code.
- **Fix**: Populate the KG with vision standards and architectural entities via Claude Code subagents

### Activity Feed shows no entries
- Activity entries are generated when agents perform work (findings, decisions, reviews, etc.)
- In a fresh session with no agent activity, the feed will be empty
- Click **Refresh** to load historical governance decisions

### Status bar shows "Error"
- One or more MCP servers lost connection
- Check server processes are still running
- Click **Connect** to re-establish connections

## Development

### Project Structure

```
extension/
├── src/
│   ├── commands/                    # Command handlers
│   ├── mcp/                        # Typed MCP client wrappers
│   │   ├── KnowledgeGraphClient.ts # KG entity operations
│   │   ├── QualityClient.ts        # Quality gate operations
│   │   └── GovernanceClient.ts     # Governance status/history
│   ├── models/                     # Data models
│   │   ├── Entity.ts               # KG entity types
│   │   └── Activity.ts             # Activity entry types
│   ├── providers/                   # View providers
│   │   ├── MemoryTreeProvider.ts    # KG entity tree view
│   │   ├── FindingsTreeProvider.ts  # Quality findings tree view
│   │   ├── TasksTreeProvider.ts     # Task briefs tree view
│   │   └── DashboardWebviewProvider.ts # Webview dashboard
│   ├── services/                    # Core services
│   │   ├── McpClientService.ts      # SSE connections to MCP servers
│   │   ├── McpServerManager.ts      # Server lifecycle (spawn, poll, stop)
│   │   ├── FileWatcherService.ts    # File system watchers
│   │   └── StatusBarService.ts      # Status bar item
│   ├── utils/                       # Utilities
│   │   ├── config.ts                # Configuration loading
│   │   └── logger.ts                # Logging
│   ├── test/                        # Tests
│   └── extension.ts                 # Entry point (activation, commands, wiring)
├── webview-dashboard/               # React + Vite + Tailwind dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── SessionBar.tsx       # Top status bar with actions
│   │   │   ├── AgentCards.tsx       # Agent status grid
│   │   │   ├── GovernancePanel.tsx  # KG entities by tier
│   │   │   ├── GovernanceItem.tsx   # Individual entity display
│   │   │   ├── ActivityFeed.tsx     # Chronological activity log
│   │   │   └── ActivityEntry.tsx    # Individual activity display
│   │   ├── context/
│   │   │   └── DashboardContext.tsx # Shared state and VS Code messaging
│   │   ├── types.ts                 # TypeScript types (mirrors extension models)
│   │   ├── App.tsx                  # Root layout
│   │   └── main.tsx                 # Entry point
│   └── tailwind.config.js          # VS Code theme variable integration
├── package.json                     # Extension manifest
├── tsconfig.json
└── esbuild.config.js
```

### Build Commands

```bash
npm run build          # Build webview + extension
npm run build:webview  # Build only the React dashboard
npm run watch          # Watch mode for extension TypeScript
npm run lint           # ESLint
```

### Testing

```bash
npm run test           # Run all tests
```

See [TESTING.md](./TESTING.md) for comprehensive test documentation.

## See Also

- [Governance Server README](../mcp-servers/governance/README.md) — Full governance server documentation
- [CLAUDE.md](../CLAUDE.md) — Orchestrator instructions and system overview
- [docs/v1-full-architecture/](../docs/v1-full-architecture/) — Archived original architecture documents
