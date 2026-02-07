# Collaborative Intelligence System

A platform-native collaborative intelligence system for software development, leveraging Claude Code's native subagent capabilities with tier-protected institutional memory, deterministic quality verification, and standalone remote operation.

## Overview

This system provides:

- **Tier-Protected Knowledge Graph**: Persistent institutional memory with vision/architecture/quality protection tiers
- **Hook-Based Governance Enforcement**: PostToolUse hooks intercept every task Claude creates, automatically pairing it with a governance review -- no agent cooperation required
- **Quality Verification**: Deterministic tool wrapping (linters, formatters, tests, build checks) with trust engine
- **Governed Task System**: "Intercept early, redirect early" -- implementation tasks are blocked from birth until governance review approves them
- **Claude Code Integration**: Custom subagents (worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward) that leverage native orchestration
- **AVT Gateway**: Standalone FastAPI backend with 35 REST endpoints, WebSocket push, and job runner for remote operation from any browser or phone
- **Dual-Mode Dashboard**: Same React dashboard runs in VS Code (local) or standalone browser (remote) via transport abstraction
- **Container Deployment**: Docker, docker-compose, and GitHub Codespaces support for persistent remote operation
- **E2E Testing Harness**: Autonomous test suite generating unique projects per run across 13 scenarios with 221 structural assertions
- **VS Code Extension**: Observability layer for monitoring system state (optional)

## Architecture

The system follows a **platform-native** philosophy (Principle P9: "Build Only What the Platform Cannot Do"):

```
┌─────────────────────────────────────────────────────────────┐
│          Claude Code (Native Orchestration)                 │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PostToolUse Hook: TaskCreate|TodoWrite              │   │
│  │  → governance-task-intercept.py                      │   │
│  │  Every task is "blocked from birth" automatically    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PreToolUse Hook: ExitPlanMode                       │   │
│  │  → verify-governance-review.sh                       │   │
│  │  Plans cannot be presented without governance review  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  Task tool for subagent coordination                        │
│  Git worktree management                                    │
│  Model routing (Opus 4.6/Sonnet 4.5/Haiku 4.5)             │
└───────┬──────────────────┬──────────────────┬───────────────┘
        │                  │                  │
┌───────▼───────┐  ┌───────▼────────┐  ┌─────▼──────────┐
│ Knowledge     │  │ Governance     │  │ Quality        │
│ Graph MCP     │  │ MCP            │  │ MCP            │
│ Server        │  │ Server         │  │ Server         │
│ (port 3101)   │  │ (port 3103)    │  │ (port 3102)    │
└───────────────┘  └────────────────┘  └────────────────┘
```

**What we build:**
- Three MCP servers providing capabilities Claude Code lacks
- **Lifecycle hooks** that enforce governance at the platform level
- Custom subagent definitions (`.claude/agents/*.md`)
- Orchestration instructions (`CLAUDE.md`)
- AVT Gateway for remote operation (FastAPI, 35 REST endpoints, WebSocket, job runner)
- Dual-mode React dashboard (VS Code + standalone web)
- Container packaging (Docker, Codespaces)
- E2E testing harness (`e2e/`)
- VS Code extension for local observability

**What Claude Code provides natively:**
- Subagent spawning and coordination (Task tool)
- **PostToolUse / PreToolUse hooks** -- the enforcement mechanism we hook into
- Session persistence and resume
- Git worktree management
- Model routing (Opus 4.6/Sonnet 4.5/Haiku 4.5)
- Tool restrictions and permissions
- Background execution

## Hook-Based Governance: How It Works

The key architectural insight: **we don't ask agents to call custom governance tools**. That approach is not tenable — agents would need to remember to call `create_governed_task()` instead of using Claude Code's native task system, and there's no enforcement if they forget.

Instead, **we hook directly into what Claude does natively**. After Claude writes each task (via `TaskCreate` or `TodoWrite`), a PostToolUse hook fires automatically and creates the governance artifacts:

```
Claude creates a task (TaskCreate or TodoWrite)
        │
        ▼
PostToolUse hook fires (governance-task-intercept.py)
        │
        ├── Extracts task info from hook payload
        ├── Creates a [GOVERNANCE] review task
        ├── Adds blockedBy to the implementation task
        ├── Records governance state in SQLite
        └── Queues async automated review (background)
        │
        ▼
Task is "blocked from birth" — cannot execute until review approves
```

### The Two Hooks

**1. PostToolUse → `TaskCreate|TodoWrite`** (governance-task-intercept.py)

Fires after every task creation. The hook:
- Reads the hook payload from stdin (tool_name, tool_input, tool_result)
- For `TodoWrite`: diffs against a seen-todos hash file (`.avt/seen-todos.json`) to detect genuinely new items — since TodoWrite sends the full list each time
- Creates a governance review task that blocks the implementation task
- Stores governance records in SQLite (`.avt/governance.db`)
- Queues an async AI-powered review via `claude --print` with the governance-reviewer agent
- Returns `additionalContext` to Claude explaining the governance pairing
- Loop prevention: skips tasks prefixed with `[GOVERNANCE]`, `[REVIEW]`, `[SECURITY]`, `[ARCHITECTURE]`

**2. PreToolUse → `ExitPlanMode`** (verify-governance-review.sh)

Safety net: if an agent tries to present a plan without having called `submit_plan_for_review`, this hook blocks the action. This ensures governance review cannot be bypassed.

### Why Hooks Instead of Custom Tools

| Approach | Problem |
|----------|---------|
| Custom `create_governed_task()` tool | Agents must remember to use it; no enforcement if they forget |
| PostToolUse hook on TaskCreate/TodoWrite | **Every task is intercepted automatically** — agents use Claude's native tools and governance happens behind the scenes |

The hook approach means governance is **transparent and mandatory**. Agents don't need to know about governance — they just create tasks normally, and the hook ensures every task gets reviewed.

### Configuration

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "TaskCreate|TodoWrite",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory \"$CLAUDE_PROJECT_DIR/mcp-servers/governance\" python \"$CLAUDE_PROJECT_DIR/scripts/hooks/governance-task-intercept.py\"",
            "timeout": 15
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/hooks/verify-governance-review.sh"
          }
        ]
      }
    ]
  }
}
```

## Quick Start

### Option A: Local Development

#### 1. Install Dependencies

```bash
# MCP Servers
cd mcp-servers/knowledge-graph && uv sync
cd mcp-servers/quality && uv sync
cd mcp-servers/governance && uv sync

# Gateway (optional, for remote mode)
cd server && uv sync

# Extension (optional, for VS Code mode)
cd extension && npm install
```

#### 2. Run Tests

```bash
# Unit tests
cd mcp-servers/knowledge-graph && uv run pytest   # 18 tests, 74% coverage
cd mcp-servers/quality && uv run pytest            # 26 tests, 48% coverage
cd extension && npm test                           # 9 unit tests

# E2E (exercises all 3 servers, 13 scenarios, 221 assertions)
./e2e/run-e2e.sh
```

See [E2E Testing Harness documentation](e2e/README.md) for details, options, and debugging guidance.

#### 3. Start MCP Servers

```bash
# Knowledge Graph (port 3101)
cd mcp-servers/knowledge-graph && uv run python -m collab_kg.server

# Quality (port 3102)
cd mcp-servers/quality && uv run python -m collab_quality.server

# Governance (port 3103)
cd mcp-servers/governance && uv run python -m collab_governance.server
```

#### 4. Install Extension (Optional)

```bash
cd extension
npm install && npm run build
# Then: Open in VS Code and press F5 to launch Extension Development Host
```

### Option B: Remote / Container Deployment

#### Docker Compose

```bash
export ANTHROPIC_API_KEY=your-key-here
docker compose up -d
# Access the dashboard at https://localhost
# API key is displayed in container logs
```

The container runs all 3 MCP servers, the AVT Gateway, and Nginx in a single image. Mount your project repo and persist state:

```yaml
services:
  avt:
    build: server/
    ports: ["443:443"]
    volumes:
      - ./my-project:/project
      - avt-state:/project/.avt
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

#### GitHub Codespaces

Open this repository in GitHub Codespaces. The `.devcontainer/devcontainer.json` starts all services automatically with port forwarding. Access from any device including phones via the Codespaces URL.

#### Cloud VPS

Deploy on any machine with Docker (DigitalOcean, Hetzner, AWS Lightsail, $5-20/month). Use `docker compose up -d` and configure Let's Encrypt for public TLS.

## Project Structure

```
agent-vision-team/
├── mcp-servers/
│   ├── knowledge-graph/       # Tier-protected institutional memory (port 3101)
│   ├── governance/             # Transactional governance review (port 3103)
│   └── quality/                # Deterministic quality verification (port 3102)
├── server/                     # AVT Gateway (remote mode)
│   ├── avt_gateway/            # FastAPI app, services, routers, WebSocket
│   ├── static/                 # Vite web build output (generated)
│   ├── Dockerfile              # Container image definition
│   ├── entrypoint.sh           # Multi-service startup script
│   └── nginx.conf              # Reverse proxy configuration
├── scripts/
│   └── hooks/                  # Claude Code lifecycle hooks
│       ├── governance-task-intercept.py  # PostToolUse: auto-governance on task creation
│       └── verify-governance-review.sh   # PreToolUse: block plans without review
├── e2e/                        # Autonomous E2E testing harness
│   ├── generator/              # Unique project generation per run (8 domains)
│   ├── scenarios/              # 13 test scenarios (s01-s13)
│   ├── parallel/               # ThreadPoolExecutor + per-scenario isolation
│   └── validation/             # Assertion engine + report generator
├── .claude/
│   ├── agents/                 # 6 custom subagent definitions
│   ├── skills/                 # User-invocable skills (/e2e)
│   └── settings.json           # MCP server config + hooks (governance enforcement)
├── .avt/                       # Project config, task briefs, memory, research, data stores
│   ├── knowledge-graph.jsonl   # KG persistence (JSONL)
│   ├── trust-engine.db         # Trust engine (SQLite)
│   ├── governance.db           # Governance decisions (SQLite)
│   └── seen-todos.json         # TodoWrite hash tracking (for hook diffing)
├── .devcontainer/              # GitHub Codespaces configuration
├── extension/                  # VS Code extension (local mode, optional)
├── templates/                  # Installation templates for target projects
├── docs/
│   ├── project-overview.md     # Project overview
│   └── v1-full-architecture/   # Archived v1 design documents
├── docker-compose.yml          # Container deployment config
├── COLLABORATIVE_INTELLIGENCE_VISION.md  # System vision (principles, topology)
├── ARCHITECTURE.md             # Technical architecture specification
└── CLAUDE.md                   # Orchestrator instructions
```

## Documentation

- **[Vision Document](COLLABORATIVE_INTELLIGENCE_VISION.md)**: Principles, agent topology, communication architecture
- **[Architecture Document](ARCHITECTURE.md)**: Technical specifications, data flow, implementation phases
- **[Orchestrator Instructions](CLAUDE.md)**: How Claude Code coordinates subagents, governance protocol, E2E testing
- **[E2E Testing Harness](e2e/README.md)**: Autonomous test suite — architecture, scenario reference, writing new tests, debugging
- **[Knowledge Graph Server README](mcp-servers/knowledge-graph/README.md)**: KG server API and tier protection
- **[Quality Server README](mcp-servers/quality/README.md)**: Quality tools and trust engine
- **[Governance Server README](mcp-servers/governance/README.md)**: Governance tools and governed task system
- **[V1 Architecture (Archived)](docs/v1-full-architecture/README.md)**: Original full-infrastructure design

## Core Concepts

### Protection Tiers

Three levels of oversight:

1. **T1 Vision** (Immutable): Fundamental identity and purpose. Human-only modification.
2. **T2 Architecture** (Human-Gated): Established patterns. Requires approval for changes.
3. **T3 Quality** (Automated): Code quality, tests, coverage. Freely modifiable.

### Governed Task Execution

The system enforces "intercept early, redirect early" through **Claude Code lifecycle hooks**:

1. **Claude creates a task** — using its native `TaskCreate` or `TodoWrite` tools (no special action required)
2. **PostToolUse hook fires** — `governance-task-intercept.py` intercepts the tool call
3. **Governance review task is created** — paired with the implementation task, which is blocked from birth
4. **Automated review runs** — async AI-powered review checks vision standards, architecture patterns, KG memory
5. **Review completes** — approved tasks unblock; blocked tasks stay with guidance
6. **Worker picks up unblocked task** — guaranteed to be reviewed before execution

Multiple review blockers can be stacked (governance + security + architecture). The task is released only when ALL blockers are approved.

### Custom Subagents

Defined in `.claude/agents/*.md`:

- **worker.md**: Implements tasks, queries KG for constraints, runs quality checks, uses governed task protocol
- **quality-reviewer.md**: Three-lens evaluation (vision → architecture → quality)
- **kg-librarian.md**: Curates institutional memory after sessions
- **governance-reviewer.md**: AI-powered decision review against vision and architecture standards
- **researcher.md**: External monitoring and design research (periodic + exploratory)
- **project-steward.md**: Project hygiene — naming conventions, folder organization, cruft detection

### Orchestrator-as-Hub

The human + primary Claude Code session acts as orchestrator, using:
- Task tool to spawn subagents
- CLAUDE.md for task decomposition and governance protocol
- Governance MCP server for transactional decision review
- PostToolUse / PreToolUse hooks for automatic governance enforcement
- session-state.md for persistent session state
- Git tags for checkpoints

## Implementation Status

### Phase 1: MCP Servers (Complete)

3 servers: KG (11 tools), Quality (8 tools), Governance (10 tools) = **29 tools total**. JSONL persistence, tier protection, SQLite trust engine, transactional governance review.

### Phase 2: Subagents + Validation (Complete)

6 agents (worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward). Full CLAUDE.md orchestration. E2E testing harness with 13 scenarios and 221 structural assertions.

### Phase 3: Extension (Complete)

Dashboard webview, 9-step wizard, 10-step tutorial, VS Code walkthrough, governance panel, decision explorer, quality gates panel, findings panel, research prompts panel, job submission. 3 MCP clients, 4 TreeViews, 12 commands.

### Phase 4: Governance + E2E (Complete)

- Governed task lifecycle (blocked from birth until review approves)
- **PostToolUse hook** intercepting `TaskCreate|TodoWrite` for automatic governance enforcement
- **PreToolUse hook** on `ExitPlanMode` ensuring plans are reviewed before presentation
- AI-powered review via `claude --print` with governance-reviewer agent
- Multi-blocker support (stack governance + security + architecture reviews)
- Quality gates fully operational: build, lint, tests, coverage, findings

### Phase 5: Remote Operation (Complete)

- AVT Gateway: FastAPI backend with 35 REST endpoints, WebSocket push, job runner
- Dual-mode React dashboard via transport abstraction (VS Code postMessage + HTTP/WebSocket)
- Container packaging: Dockerfile, docker-compose.yml, entrypoint.sh, nginx.conf
- GitHub Codespaces: .devcontainer/devcontainer.json with port forwarding
- Mobile-responsive layout with stacked panels on small screens
- API-key authentication (auto-generated bearer token)
- Zero changes to MCP servers, hooks, or agents

### Phase 6: Expand

- [ ] Cross-project memory
- [ ] Installation script for target projects

## Key Features

### Knowledge Graph Server

- **Persistent Memory**: JSONL storage matching Anthropic's KG Memory format
- **Tier Protection**: Enforced at tool level (no accidental corruption)
- **Relations**: `depends_on`, `follows_pattern`, `governed_by`, `fixed_by`
- **Entity Types**: `component`, `vision_standard`, `architectural_standard`, `pattern`, `problem`, `solution_pattern`
- **Compaction**: Automatic after 1000 writes

### Governance Server

- **Hook-Based Enforcement**: PostToolUse hook intercepts every `TaskCreate`/`TodoWrite` — governance is automatic, not opt-in
- **Transactional Review**: Every decision blocks until review completes (synchronous round-trip)
- **AI-Powered Review**: Uses `claude --print` with governance-reviewer agent for full reasoning
- **Decision Categories**: `pattern_choice`, `component_design`, `api_design`, `deviation`, `scope_change`
- **Verdicts**: `approved`, `blocked`, `needs_human_review` — with guidance and standards verified
- **Governed Tasks**: Atomic creation of review + implementation task pairs, blocked from birth
- **Multi-Blocker**: Stack multiple reviews (governance, security, architecture) on a single task
- **Audit Trail**: All decisions, verdicts, and task reviews stored in SQLite
- **Loop Prevention**: Review tasks (prefixed `[GOVERNANCE]`, `[REVIEW]`, etc.) are skipped to prevent infinite recursion

### Quality Server

- **Multi-Language Support**: Python (ruff), TypeScript (eslint/prettier), Swift (swiftlint), Rust (clippy)
- **Unified Interface**: Single MCP tools for format, lint, test, coverage
- **Trust Engine**: SQLite-backed finding tracking with dismissal audit trail
- **Quality Gates**: All 5 gates operational — build (runs configured build command), lint, tests, coverage, findings (checks trust engine for unresolved critical/high findings)
- **No Silent Dismissals**: Every dismissal requires justification and identity

### AVT Gateway (Remote Operation)

- **35 REST Endpoints**: Full API coverage mapping every VS Code `postMessage` type to HTTP
- **WebSocket Push**: Real-time dashboard updates, governance status, job progress at `/api/ws`
- **Job Runner**: Submit work from any device (prompt, agent type, model). Executes via Claude CLI with temp-file I/O. Persists to `.avt/jobs/`
- **API-Key Auth**: Auto-generated bearer token. All endpoints authenticated
- **Dual-Mode Dashboard**: Same React components in VS Code (postMessage) or browser (HTTP + WebSocket) via transport abstraction
- **Container Ready**: Dockerfile with all services, docker-compose for deployment, Codespaces for zero-setup cloud access
- **Mobile Responsive**: Stacked panels on small screens for phone access

### E2E Testing Harness

- **Autonomous Execution**: Single command (`./e2e/run-e2e.sh`) runs the full suite
- **Domain Randomization**: Each run randomly selects from 8 project domains
- **Structural Assertions**: 221 domain-agnostic assertions that verify behavioral contracts
- **Full Isolation**: Per-scenario KG, SQLite, and task directory -- scenarios never interfere
- **Parallel Execution**: Library-mode scenarios run concurrently via `ThreadPoolExecutor`
- **Reproducibility**: `--seed` flag for deterministic domain selection; `--keep` preserves workspace
- **Comprehensive Coverage**: 13 scenarios spanning KG, Governance, Quality, and cross-server integration

See [e2e/README.md](e2e/README.md) for complete documentation.

## Test Coverage

### Summary

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| Knowledge Graph | 18 | 74% | All passing |
| Quality Server | 26 | 48% | All passing |
| Extension (Unit) | 9 | N/A | All passing |
| E2E Harness | 13 scenarios / 221 assertions | N/A | All passing |
| **Total** | **53 unit + 13 E2E scenarios** | -- | **All passing** |

### Detailed Coverage

**Knowledge Graph (74% overall)**:
- graph.py: 98% (core logic)
- storage.py: 98% (persistence)
- models.py: 100%
- tier_protection.py: 84%
- server.py: 0% (MCP integration points, expected)

**Quality Server (48% overall)**:
- trust_engine.py: 100%
- models.py: 100%
- formatting.py: 72%
- linting.py: 58%
- testing.py: 13% (branches requiring external tools)
- coverage.py: 18% (branches requiring external tools)
- server.py: 0% (MCP integration points, expected)
- gates.py: 0% (would require pytest recursion)

**Extension (Unit Tests)**:
- McpClientService: 3 unit tests + 3 integration (skipped)
- MemoryTreeProvider: 4 tests (100% coverage)
- KnowledgeGraphClient: 1 unit + 7 integration (skipped)
- QualityClient: 1 unit + 8 integration (skipped)

**Integration Tests**: 18 integration tests defined but skipped by default (require live servers).

### Coverage Notes

- **Server.py files**: 0% coverage is expected - these are MCP FastMCP server entry points tested via integration tests
- **Tool execution branches**: Lower coverage for quality tools is due to branches requiring external tools (ruff, eslint, pytest) to be installed
- **Gates.py**: 0% coverage to avoid pytest recursion in tests
- **Core Business Logic**: 98%+ coverage for graph logic, storage, trust engine, and models

See individual server READMEs for detailed test documentation:
- [Knowledge Graph Testing](mcp-servers/knowledge-graph/README.md#testing)
- [Quality Testing](mcp-servers/quality/README.md#testing)
- [Extension Testing](extension/TESTING.md)

## Validation

Complete end-to-end validation guide: [.claude/VALIDATION.md](.claude/VALIDATION.md)

### Quick Validation

```bash
# 1. Run unit tests
cd mcp-servers/knowledge-graph && uv run pytest
cd mcp-servers/quality && uv run pytest
cd extension && npm test

# 2. Run E2E tests (exercises all 3 MCP servers via library import)
./e2e/run-e2e.sh

# 3. Start MCP servers (for live usage)
cd mcp-servers/knowledge-graph && uv run python -m collab_kg.server &
cd mcp-servers/quality && uv run python -m collab_quality.server &
cd mcp-servers/governance && uv run python -m collab_governance.server &

# 4. Verify server health
curl http://localhost:3101/health
curl http://localhost:3102/health
curl http://localhost:3103/health
```

## Contributing

This is an experimental system exploring platform-native architecture. The v1 full-infrastructure design is preserved in `docs/v1-full-architecture/` and may be revisited based on what we learn from this approach.

## License

[Specify license]

## Related Documents

- [Collaborative Intelligence Vision](COLLABORATIVE_INTELLIGENCE_VISION.md)
- [Technical Architecture](ARCHITECTURE.md)
- [Project Overview](docs/project-overview.md)
- [Orchestrator Instructions (CLAUDE.md)](CLAUDE.md)
- [E2E Testing Harness](e2e/README.md)
- [Knowledge Graph Server](mcp-servers/knowledge-graph/README.md)
- [Quality Server](mcp-servers/quality/README.md)
- [Governance Server](mcp-servers/governance/README.md)
- [V1 Architecture (Archived)](docs/v1-full-architecture/README.md)
