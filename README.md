# Collaborative Intelligence System

A platform-native collaborative intelligence system for software development, leveraging Claude Code's native subagent capabilities with tier-protected institutional memory, deterministic quality verification, and standalone remote operation.

## Overview

This system provides:

- **Tier-Protected Knowledge Graph**: Persistent institutional memory with vision/architecture/quality protection tiers
- **Transparent Governance**: PostToolUse hooks automatically pair every task with a rapid governance review. Holistic review evaluates task groups collectively, typically completing in seconds -- no agent cooperation required
- **Quality Verification**: Deterministic tool wrapping (linters, formatters, tests, build checks) with trust engine
- **Governed Task System**: "Intercept early, redirect early" -- tasks are verified against vision standards before work begins, with minimal introduced latency
- **Safe Multi-Agent Parallelism**: Six specialized subagents (worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward) operate in isolated worktrees. Governance verification means you can confidently scale to more parallel agents without risking architectural drift
- **AVT Gateway**: Standalone FastAPI backend with 35 REST endpoints, WebSocket push, and job runner for remote operation from any browser or phone
- **Dual-Mode Dashboard**: Same React dashboard runs in VS Code (local) or standalone browser (remote) via transport abstraction
- **Container Deployment**: Docker, docker-compose, and GitHub Codespaces support for persistent remote operation
- **E2E Testing Harness**: Autonomous test suite generating unique projects per run across 14 scenarios with 292+ structural assertions
- **VS Code Extension**: Observability layer for monitoring system state (optional)

## Architecture

The system follows a **platform-native** philosophy (Principle P9: "Build Only What the Platform Cannot Do"):

```
┌─────────────────────────────────────────────────────────────┐
│          Claude Code (Native Orchestration)                 │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PostToolUse Hook: TaskCreate                        │   │
│  │  → governance-task-intercept.py                      │   │
│  │  Every task is governed from creation automatically  │   │
│  │  Rapid review via settle checker + holistic review   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PreToolUse Hook: Write|Edit|Bash|Task               │   │
│  │  → holistic-review-gate.sh                           │   │
│  │  Coordinates work during holistic review (~1ms)      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PreToolUse Hook: ExitPlanMode                       │   │
│  │  → verify-governance-review.sh                       │   │
│  │  Plans are verified before presentation               │   │
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
- **Lifecycle hooks** that provide automatic governance verification at the platform level
- Custom subagent definitions (`.claude/agents/*.md`)
- Orchestration instructions (`CLAUDE.md`)
- AVT Gateway for remote operation (FastAPI, 35 REST endpoints, WebSocket, job runner)
- Dual-mode React dashboard (VS Code + standalone web)
- Container packaging (Docker, Codespaces)
- E2E testing harness (`e2e/`)
- VS Code extension for local observability

**What Claude Code provides natively:**
- Subagent spawning and coordination (Task tool)
- **PostToolUse / PreToolUse hooks** -- the coordination mechanism we hook into
- Session persistence and resume
- Git worktree management
- Model routing (Opus 4.6/Sonnet 4.5/Haiku 4.5)
- Tool restrictions and permissions
- Background execution

## Hook-Based Governance: How It Works

The key architectural insight: **we don't ask agents to call custom governance tools**. That approach is not tenable -- agents would need to remember to call `create_governed_task()` instead of using Claude Code's native task system, and there's no guarantee they will.

Instead, **we hook directly into what Claude does natively**. After Claude writes each task (via `TaskCreate`), a PostToolUse hook fires automatically, pairs it with a rapid governance review, and triggers holistic review of all tasks as a group:

```
Claude creates a task (TaskCreate)
        │
        ▼
PostToolUse hook fires (governance-task-intercept.py)
        │
        ├── Extracts task info from hook payload
        ├── Creates a [GOVERNANCE] review task
        ├── Pairs it with the implementation task (governed from creation)
        ├── Records governance state in SQLite (with session_id)
        ├── Creates .avt/.holistic-review-pending flag file
        └── Spawns background settle checker (3s debounce)
        │
        ▼
Task is governed from creation -- work begins once review completes
        │
        ▼
After all tasks created (settle period elapses):
        │
        ├── Holistic review evaluates collective intent
        ├── If approved: flag cleared, individual reviews queued
        └── If issues found: flag updated with guidance for revision
```

### The Three Hooks

**1. PostToolUse → `TaskCreate`** (governance-task-intercept.py)

Fires after every task creation. The hook:
- Reads the hook payload from stdin (tool_name, tool_input, tool_result, session_id)
- Pairs the implementation task with a governance review (100% interception rate)
- Stores governance records in SQLite (`.avt/governance.db`) with session_id
- Creates/updates the holistic review flag file (`.avt/.holistic-review-pending`)
- Spawns a background settle checker that waits 3s for more tasks
- Returns `additionalContext` to Claude explaining the governance pairing
- Loop prevention: skips tasks prefixed with `[GOVERNANCE]`, `[REVIEW]`, `[SECURITY]`, `[ARCHITECTURE]`

**2. PreToolUse → `Write|Edit|Bash|Task`** (holistic-review-gate.sh)

Coordinates work sequencing while holistic review completes. Fast path (~1ms): checks if `.avt/.holistic-review-pending` exists. If the flag exists, reads its status and returns appropriate feedback. Stale flags (older than 5 minutes) are auto-cleared.

**3. PreToolUse → `ExitPlanMode`** (verify-governance-review.sh)

Ensures plans are verified before presentation. If an agent tries to present a plan without having called `submit_plan_for_review`, this hook redirects the agent to submit the review first.

### Why Hooks Instead of Custom Tools

| Approach | Problem |
|----------|---------|
| Custom `create_governed_task()` tool | Agents must remember to use it; nothing catches it if they forget |
| PostToolUse hook on TaskCreate | **Every task is verified automatically** -- agents use Claude's native tools and governance happens behind the scenes |

The hook approach means governance is **transparent and universal**. Agents don't need to know about governance -- they just create tasks normally, and the hook ensures every task gets reviewed individually AND collectively. This reliability is what makes it safe to scale to more parallel agents: you know nothing reaches the codebase without passing through verification.

### Configuration

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "TaskCreate",
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
      },
      {
        "matcher": "Write|Edit|Bash|Task",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/hooks/holistic-review-gate.sh",
            "timeout": 5
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
# Everything at once (recommended)
npm run setup

# Or manually:
# MCP Servers
cd mcp-servers/knowledge-graph && uv sync --dev
cd mcp-servers/quality && uv sync --dev
cd mcp-servers/governance && uv sync --dev

# Gateway (optional, for remote mode)
cd server && uv sync

# Extension (optional, for VS Code mode)
cd extension && npm install
```

#### 2. Run Tests

```bash
# All tests via unified script
npm test

# Or individually:
npm run test -- --component knowledge-graph   # 18 tests
npm run test -- --component quality           # 26 tests
npm run test -- --component hooks             # 37 assertions

# E2E (exercises all 3 servers, 14 scenarios, 292 assertions)
npm run test:e2e

# Full quality check (lint + typecheck + build + test + coverage)
npm run check
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
│   ├── ci/                     # CI/CD and local quality scripts (backbone of all checks)
│   │   ├── setup.sh            # Install all dependencies (npm + uv)
│   │   ├── lint.sh             # ESLint + Prettier + Ruff (--fix flag supported)
│   │   ├── typecheck.sh        # tsc --noEmit for extension + webview
│   │   ├── build.sh            # Build extension + webview dashboard
│   │   ├── test.sh             # Run unit tests (--component flag for individual)
│   │   ├── coverage.sh         # Coverage with threshold enforcement (--skip-extension)
│   │   ├── test-e2e.sh         # E2E test wrapper
│   │   ├── test-hooks.sh       # Hook unit test wrapper
│   │   └── check-all.sh        # Full pipeline: lint → typecheck → build → test → coverage
│   └── hooks/                  # Claude Code lifecycle hooks
│       ├── governance-task-intercept.py  # PostToolUse: auto-governance on task creation
│       ├── holistic-review-gate.sh      # PreToolUse: coordinate work during holistic review
│       ├── _holistic-settle-check.py    # Background: settle detection + holistic review
│       ├── _run-governance-review.sh    # Background: individual AI-powered review
│       └── verify-governance-review.sh  # PreToolUse: verify plans before presentation
├── e2e/                        # Autonomous E2E testing harness
│   ├── generator/              # Unique project generation per run (8 domains)
│   ├── scenarios/              # 14 test scenarios (s01-s14)
│   ├── parallel/               # ThreadPoolExecutor + per-scenario isolation
│   └── validation/             # Assertion engine + report generator
├── .claude/
│   ├── agents/                 # 6 custom subagent definitions
│   ├── skills/                 # User-invocable skills (/e2e)
│   └── settings.json           # MCP server config + hooks (governance verification)
├── .avt/                       # Project config, task briefs, memory, research, data stores
│   ├── knowledge-graph.jsonl   # KG persistence (JSONL)
│   ├── trust-engine.db         # Trust engine (SQLite)
│   ├── governance.db           # Governance decisions + holistic reviews (SQLite)
│   ├── .holistic-review-pending # Flag file (transient, coordinates work during review)
│   └── seen-todos.json         # TodoWrite hash tracking (for hook diffing)
├── .github/workflows/ci.yml    # GitHub Actions CI pipeline
├── .husky/                     # Git hooks (Husky v9)
│   ├── pre-commit              # Lint + format staged files via lint-staged (~2-5s)
│   └── pre-push                # Typecheck + build + test + coverage (~30-60s)
├── .devcontainer/              # GitHub Codespaces configuration
├── extension/                  # VS Code extension (local mode, optional)
├── templates/                  # Installation templates for target projects
├── docs/
│   ├── project-overview.md     # Project overview
│   └── v1-full-architecture/   # Archived v1 design documents
├── .eslintrc.json              # ESLint config for TypeScript (in extension/)
├── .prettierrc.json            # Prettier config (root)
├── ruff.toml                   # Ruff config for Python (root)
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

The system implements "intercept early, redirect early" through **Claude Code lifecycle hooks**:

1. **Claude creates a task** -- using its native `TaskCreate` or `TodoWrite` tools (no special action required)
2. **PostToolUse hook fires** -- `governance-task-intercept.py` intercepts the tool call
3. **Governance review is paired** -- the implementation task is governed from creation, with rapid automated review queued
4. **Automated review runs** -- async AI-powered review checks vision standards, architecture patterns, KG memory
5. **Review completes** -- approved tasks proceed; tasks with issues receive constructive guidance
6. **Worker picks up verified task** -- guaranteed to be reviewed before execution

Multiple review checkpoints can be stacked (governance + security + architecture). The task proceeds only when ALL reviews are complete. This is what makes it safe to run many agents in parallel: every task is verified before any code reaches the codebase.

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
- PostToolUse / PreToolUse hooks for automatic governance verification
- session-state.md for persistent session state
- Git tags for checkpoints

## Implementation Status

### Phase 1: MCP Servers (Complete)

3 servers: KG (11 tools), Quality (8 tools), Governance (10 tools) = **29 tools total**. JSONL persistence, tier protection, SQLite trust engine, transactional governance review.

### Phase 2: Subagents + Validation (Complete)

6 agents (worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward). Full CLAUDE.md orchestration. E2E testing harness with 14 scenarios and 292 structural assertions.

### Phase 3: Extension (Complete)

Dashboard webview, 9-step wizard, 10-step tutorial, VS Code walkthrough, governance panel, decision explorer, quality gates panel, findings panel, research prompts panel, job submission. 3 MCP clients, 4 TreeViews, 12 commands.

### Phase 4: Governance + E2E (Complete)

- Governed task lifecycle (every task verified before work begins)
- **PostToolUse hook** intercepting `TaskCreate` for automatic governance verification (100% interception rate)
- **PreToolUse hook** on `Write|Edit|Bash|Task` coordinating work during holistic review
- **PreToolUse hook** on `ExitPlanMode` ensuring plans are verified before presentation
- **Holistic review**: collective intent detection with settle/debounce pattern, completing in seconds
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

### CI/CD and Local Quality (Complete)

- Unified CI scripts (`scripts/ci/`) as the backbone for all checks
- ESLint + Prettier (TypeScript) and Ruff (Python) for linting/formatting
- Pre-commit hooks (Husky + lint-staged) for lint on commit
- Pre-push hooks for typecheck + build + test + coverage on push
- GitHub Actions CI pipeline on every push to every branch
- Coverage enforcement (30% threshold, target 80%)

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

- **Automatic Verification**: PostToolUse hook intercepts every `TaskCreate` with 100% reliability -- governance is automatic, not opt-in
- **Holistic Review**: Tasks from the same session are evaluated collectively before work begins, catching architectural shifts that individual reviews would miss. Typically completes in seconds
- **Two-Layer Assurance**: PostToolUse detection (settle/debounce) + PreToolUse coordination (`Write|Edit|Bash|Task` sequenced around review)
- **Transactional Review**: Every decision receives a synchronous round-trip review
- **AI-Powered Review**: Uses `claude --print` with governance-reviewer agent for full reasoning
- **Decision Categories**: `pattern_choice`, `component_design`, `api_design`, `deviation`, `scope_change`
- **Verdicts**: `approved`, `blocked`, `needs_human_review` -- with constructive guidance and standards verified
- **Governed Tasks**: Atomic creation of review + implementation task pairs, governed from creation
- **Multi-Review Stacking**: Layer multiple reviews (governance, security, architecture) on a single task
- **Audit Trail**: All decisions, verdicts, holistic reviews, and task reviews stored in SQLite
- **Safe Scaling**: Reliable interception and hard quality gates mean you can confidently run more parallel agents -- nothing reaches the codebase without passing verification
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
- **Structural Assertions**: 292+ domain-agnostic assertions that verify behavioral contracts
- **Full Isolation**: Per-scenario KG, SQLite, and task directory -- scenarios never interfere
- **Parallel Execution**: Library-mode scenarios run concurrently via `ThreadPoolExecutor`
- **Reproducibility**: `--seed` flag for deterministic domain selection; `--keep` preserves workspace
- **Comprehensive Coverage**: 14 scenarios spanning KG, Governance, Quality, and cross-server integration

See [e2e/README.md](e2e/README.md) for complete documentation.

## CI/CD and Local Quality Infrastructure

The same scripts run locally and in CI. Pre-commit hooks catch lint/format issues before they leave your machine. Pre-push hooks run the full quality pipeline. GitHub Actions mirrors everything on every push.

```
Developer writes code
  → Pre-commit (lint + format on staged files, ~2-5s)
  → Pre-push (typecheck + build + test + coverage, ~30-60s)
  → GitHub Actions CI on every push (same scripts + E2E)
  → PR review (should have minimal issues by this point)
```

### Local Quality Scripts

All scripts live in `scripts/ci/` and are aliased in `package.json`:

| Command | What It Does |
|---------|-------------|
| `npm run setup` | Install all dependencies (npm ci + uv sync --dev) |
| `npm run lint` | ESLint (TypeScript) + Prettier + Ruff (Python) |
| `npm run lint:fix` | Auto-fix lint and format issues |
| `npm run typecheck` | tsc --noEmit for extension + webview |
| `npm run build` | Build webview dashboard + extension |
| `npm test` | Run all unit tests (Python + hooks) |
| `npm run coverage` | Coverage with threshold enforcement |
| `npm run check` | Full pipeline: lint, typecheck, build, test, coverage |
| `npm run test:e2e` | E2E test suite (14 scenarios, 292+ assertions) |

### Git Hooks (Husky + lint-staged)

- **Pre-commit**: Runs `lint-staged` on staged files only. ESLint + Prettier for TypeScript, Ruff for Python. Fast (~2-5s).
- **Pre-push**: Runs typecheck, build, Python tests, hook tests, and coverage. Blocks push on failure with clear error reporting. Extension tests are skipped locally (require xvfb) and run in CI.

### GitHub Actions

The CI pipeline (`.github/workflows/ci.yml`) runs on every push to every branch:
- **Parallel jobs**: lint, typecheck, test-python (matrix: 3 servers), test-hooks
- **Sequential**: build (after typecheck), extension tests (after build, with xvfb), coverage (after all tests), E2E (after build + Python tests)
- Coverage artifacts uploaded with 30-day retention

### Linting and Formatting

| Tool | Scope | Config |
|------|-------|--------|
| ESLint | `extension/src/**/*.ts` | `extension/.eslintrc.json` |
| Prettier | TypeScript, JSON | `.prettierrc.json` |
| Ruff | All Python code | `ruff.toml` (target py312, line-length 120) |

## Test Coverage

### Summary

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| Knowledge Graph | 18 | 36% | All passing |
| Quality Server | 26 | 41% | All passing |
| Hook Unit Tests | 37 assertions | N/A | All passing |
| E2E Harness | 14 scenarios / 292 assertions | N/A | All passing |
| **Total** | **44 unit + 37 hook + 14 E2E scenarios** | -- | **All passing** |

### Detailed Coverage

**Knowledge Graph (36% overall)**:
- graph.py: 98% (core logic)
- storage.py: 98% (persistence)
- models.py: 100%
- tier_protection.py: 84%
- server.py, ingestion.py, archival.py, curation.py: 0% (MCP integration/CLI entry points)

**Quality Server (41% overall)**:
- trust_engine.py: 89%
- models.py: 100%
- formatting.py: 72%
- linting.py: 58%
- config.py: 41%
- testing.py: 13% (branches requiring external tools)
- coverage.py: 22% (branches requiring external tools)
- server.py, gates.py, storage.py: 0% (MCP integration points)

**Hook Unit Tests (37 assertions)**:
- teammate-idle-gate.sh: 7 checks
- task-completed-gate.sh: 9 checks
- holistic-review-gate.sh: 12 checks
- verify-governance-review.sh: 4 checks
- governance-task-intercept.py parsing: 5 checks

### Coverage Notes

- **Current threshold**: 30% (enforced in CI and pre-push hook). Target: 80%.
- **Server.py files**: 0% coverage is expected; these are MCP FastMCP server entry points tested via E2E
- **Governance server**: 0% unit test coverage; tested exclusively via E2E scenarios (s02, s03, s05, s08, s09, s10, s12)
- **Core Business Logic**: 98%+ coverage for graph logic, storage, and models

See individual server READMEs for detailed test documentation:
- [Knowledge Graph Testing](mcp-servers/knowledge-graph/README.md#testing)
- [Quality Testing](mcp-servers/quality/README.md#testing)
- [Extension Testing](extension/TESTING.md)

## Validation

Complete end-to-end validation guide: [.claude/VALIDATION.md](.claude/VALIDATION.md)

### Quick Validation

```bash
# Full quality pipeline (lint + typecheck + build + test + coverage)
npm run check

# Or step by step:
npm run lint          # ESLint + Prettier + Ruff
npm run typecheck     # tsc --noEmit
npm run build         # Build extension + webview
npm test              # Unit tests + hook tests
npm run coverage      # Coverage with threshold enforcement

# E2E tests (exercises all 3 MCP servers via library import)
npm run test:e2e
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
