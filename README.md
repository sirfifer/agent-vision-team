# Collaborative Intelligence System

A platform-native collaborative intelligence system for software development, leveraging Claude Code's native subagent capabilities with tier-protected institutional memory and deterministic quality verification.

## Overview

This system provides:

- **Tier-Protected Knowledge Graph**: Persistent institutional memory with vision/architecture/quality protection tiers
- **Governance Server**: Transactional review checkpoints with AI-powered decision review and governed task execution
- **Quality Verification**: Deterministic tool wrapping (linters, formatters, tests) with trust engine
- **Governed Task System**: "Intercept early, redirect early" — implementation tasks are blocked from birth until governance review approves them
- **Claude Code Integration**: Custom subagents (worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward) that leverage native orchestration
- **E2E Testing Harness**: Autonomous test suite generating unique projects per run across 11 scenarios with 172+ structural assertions
- **VS Code Extension**: Observability layer for monitoring system state (optional)

## Architecture

The system follows a **platform-native** philosophy (Principle P9: "Build Only What the Platform Cannot Do"):

```
┌─────────────────────────────────────────────┐
│     Claude Code (Native Orchestration)      │
│     - Task tool for subagent coordination   │
│     - Lifecycle hooks for event tracking    │
│     - Git worktree management              │
└──────┬──────────────┬──────────────┬────────┘
       │              │              │
┌──────▼──────┐  ┌───▼────────┐  ┌──▼──────────┐
│ Knowledge   │  │ Governance │  │  Quality    │
│ Graph MCP   │  │ MCP        │  │  MCP        │
│ Server      │  │ Server     │  │  Server     │
│ (port 3101) │  │ (port 3103)│  │  (port 3102)│
└─────────────┘  └────────────┘  └─────────────┘
```

**What we build:**
- Three MCP servers providing capabilities Claude Code lacks
- Custom subagent definitions (`.claude/agents/*.md`)
- Orchestration instructions (`CLAUDE.md`)
- E2E testing harness (`e2e/`)
- VS Code extension for observability

**What Claude Code provides natively:**
- Subagent spawning and coordination (Task tool)
- Session persistence and resume
- Git worktree management
- Model routing (Opus/Sonnet/Haiku)
- Tool restrictions and permissions
- Background execution

## Quick Start

### 1. Install Dependencies

```bash
# Knowledge Graph Server
cd mcp-servers/knowledge-graph && uv sync

# Quality Server
cd mcp-servers/quality && uv sync

# Governance Server
cd mcp-servers/governance && uv sync

# Extension (optional)
cd extension && npm install
```

### 2. Run Unit Tests

```bash
# Knowledge Graph (18 tests, 74% coverage)
cd mcp-servers/knowledge-graph && uv run pytest

# Quality (26 tests, 48% coverage)
cd mcp-servers/quality && uv run pytest

# Extension (9 unit tests)
cd extension && npm test
```

### 3. Run E2E Tests

```bash
# Full autonomous E2E suite (11 scenarios, 172+ assertions)
./e2e/run-e2e.sh
```

See [E2E Testing Harness documentation](e2e/README.md) for details, options, and debugging guidance.

### 4. Start MCP Servers

```bash
# Knowledge Graph (port 3101)
cd mcp-servers/knowledge-graph && uv run python -m collab_kg.server

# Quality (port 3102)
cd mcp-servers/quality && uv run python -m collab_quality.server

# Governance (port 3103)
cd mcp-servers/governance && uv run python -m collab_governance.server
```

### 5. Install Extension (Optional)

```bash
cd extension
npm install && npm run build
# Then: Open in VS Code and press F5 to launch Extension Development Host
```

## Project Structure

```
agent-vision-team/
├── mcp-servers/
│   ├── knowledge-graph/       # Tier-protected institutional memory (port 3101)
│   ├── governance/             # Transactional governance review (port 3103)
│   └── quality/                # Deterministic quality verification (port 3102)
├── e2e/                        # Autonomous E2E testing harness
│   ├── generator/              # Unique project generation per run (8 domains)
│   ├── scenarios/              # 11 test scenarios (s01–s12)
│   ├── parallel/               # ThreadPoolExecutor + per-scenario isolation
│   └── validation/             # Assertion engine + report generator
├── .claude/
│   ├── agents/                 # 6 custom subagent definitions
│   ├── skills/                 # User-invocable skills (/e2e)
│   ├── collab/                 # KG, trust engine, governance databases
│   └── settings.json           # MCP server config + hooks
├── .avt/                       # Project config, task briefs, memory, research
├── extension/                  # VS Code extension (observability only)
├── templates/                  # Installation templates for target projects
├── docs/
│   └── v1-full-architecture/   # Archived v1 design documents
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
- **[V1 Architecture (Archived)](docs/v1-full-architecture/README.md)**: Original full-infrastructure design

## Core Concepts

### Protection Tiers

Three levels of oversight:

1. **T1 Vision** (Immutable): Fundamental identity and purpose. Human-only modification.
2. **T2 Architecture** (Human-Gated): Established patterns. Requires approval for changes.
3. **T3 Quality** (Automated): Code quality, tests, coverage. Freely modifiable.

### Governed Task Execution

The system enforces "intercept early, redirect early" through the governance-gated task system:

1. **Orchestrator calls `create_governed_task`** — atomically creates a review task AND an implementation task
2. **Implementation task is blocked from birth** — its `blockedBy` array references the review task
3. **Governance review runs** — checks vision standards, architecture patterns, KG memory
4. **Review completes** — approved tasks unblock; blocked tasks stay with guidance
5. **Worker picks up unblocked task** — guaranteed to be reviewed before execution

Multiple review blockers can be stacked (governance → security → architecture). The task is released only when ALL blockers are approved.

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
- session-state.md for persistent session state
- Git tags for checkpoints

## Implementation Status

### ✅ Phase 1: MCP Servers (Complete)

- [x] Knowledge Graph with JSONL persistence
- [x] Tier protection enforcement
- [x] `delete_entity` and `delete_relations` tools
- [x] Quality tool wrappers (format, lint, test, coverage)
- [x] SQLite trust engine with dismissal tracking
- [x] 18 tests (KG), 26 tests (Quality) - all passing
- [x] 74% test coverage (KG), 48% (Quality)
- [x] Complete API documentation

### ✅ Phase 2: Subagents + Validation (Complete)

- [x] Write `.claude/agents/worker.md`
- [x] Write `.claude/agents/quality-reviewer.md`
- [x] Write `.claude/agents/kg-librarian.md`
- [x] Write orchestrator `CLAUDE.md`
- [x] Write `.claude/settings.json` with lifecycle hooks
- [x] Create workspace structure (task-briefs, memory, session-state)
- [x] Example task brief and archival files
- [x] Validation documentation

### ✅ Phase 3: Extension (Complete)

- [x] MCP client service (read-only HTTP/JSON-RPC)
- [x] Memory Browser TreeView (KG entities by tier)
- [x] Findings Panel TreeView (quality findings)
- [x] Tasks Panel TreeView (filesystem-based)
- [x] Status bar integration
- [x] Observability commands (refresh, search, validate)
- [x] Extension builds successfully
- [x] Unit tests (9 test files)
- [x] Integration test suite (skipped by default)
- [x] Complete documentation (README, TESTING)

### ✅ Phase 4: Governance + E2E (Complete)

- [x] Governance MCP server with transactional decision review
- [x] AI-powered review via `claude --print` with governance-reviewer agent
- [x] Governed task system — tasks blocked from birth until review approves
- [x] Multi-blocker support (stack governance + security + architecture reviews)
- [x] 6 custom subagents (worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward)
- [x] E2E testing harness (11 scenarios, 172+ assertions, 8 random domains)
- [x] `/e2e` skill for easy test invocation
- [x] `GOVERNANCE_MOCK_REVIEW` env var for deterministic E2E testing

### 🚀 Phase 5: Expand

- [ ] Cross-project memory
- [ ] Multi-worker parallelism patterns
- [ ] Installation script for target projects

## Key Features

### Knowledge Graph Server

- **Persistent Memory**: JSONL storage matching Anthropic's KG Memory format
- **Tier Protection**: Enforced at tool level (no accidental corruption)
- **Relations**: `depends_on`, `follows_pattern`, `governed_by`, `fixed_by`
- **Entity Types**: `component`, `vision_standard`, `architectural_standard`, `pattern`, `problem`, `solution_pattern`
- **Compaction**: Automatic after 1000 writes

### Governance Server

- **Transactional Review**: Every decision blocks until review completes (synchronous round-trip)
- **AI-Powered Review**: Uses `claude --print` with governance-reviewer agent for full reasoning
- **Decision Categories**: `pattern_choice`, `component_design`, `api_design`, `deviation`, `scope_change`
- **Verdicts**: `approved`, `blocked`, `needs_human_review` — with guidance and standards verified
- **Governed Tasks**: Atomic creation of review + implementation task pairs, blocked from birth
- **Multi-Blocker**: Stack multiple reviews (governance, security, architecture) on a single task
- **Audit Trail**: All decisions, verdicts, and task reviews stored in SQLite

### Quality Server

- **Multi-Language Support**: Python (ruff), TypeScript (eslint/prettier), Swift (swiftlint), Rust (clippy)
- **Unified Interface**: Single MCP tools for format, lint, test, coverage
- **Trust Engine**: SQLite-backed finding tracking with dismissal audit trail
- **Quality Gates**: Aggregated gate results (build, lint, tests, coverage, findings)
- **No Silent Dismissals**: Every dismissal requires justification and identity

### E2E Testing Harness

- **Autonomous Execution**: Single command (`./e2e/run-e2e.sh`) runs the full suite
- **Domain Randomization**: Each run randomly selects from 8 project domains
- **Structural Assertions**: 172+ domain-agnostic assertions that verify behavioral contracts
- **Full Isolation**: Per-scenario KG, SQLite, and task directory — scenarios never interfere
- **Parallel Execution**: Library-mode scenarios run concurrently via `ThreadPoolExecutor`
- **Reproducibility**: `--seed` flag for deterministic domain selection; `--keep` preserves workspace
- **Comprehensive Coverage**: 11 scenarios spanning KG, Governance, Quality, and cross-server integration

See [e2e/README.md](e2e/README.md) for complete documentation.

## Test Coverage

### Summary

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| Knowledge Graph | 18 | 74% | ✅ All passing |
| Quality Server | 26 | 48% | ✅ All passing |
| Extension (Unit) | 9 | N/A | ✅ All passing |
| E2E Harness | 11 scenarios / 172+ assertions | N/A | ✅ All passing |
| **Total** | **53 unit + 11 E2E scenarios** | — | **✅ All passing** |

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
- [Orchestrator Instructions (CLAUDE.md)](CLAUDE.md)
- [E2E Testing Harness](e2e/README.md)
- [V1 Architecture (Archived)](docs/v1-full-architecture/README.md)
