# Collaborative Intelligence System

A platform-native collaborative intelligence system for software development, leveraging Claude Code's native subagent capabilities with tier-protected institutional memory and deterministic quality verification.

## Overview

This system provides:

- **Tier-Protected Knowledge Graph**: Persistent institutional memory with vision/architecture/quality protection tiers
- **Quality Verification**: Deterministic tool wrapping (linters, formatters, tests) with trust engine
- **Claude Code Integration**: Custom subagents (worker, quality-reviewer, kg-librarian) that leverage native orchestration
- **VS Code Extension**: Observability layer for monitoring system state (optional)

## Architecture

The system follows a **platform-native** philosophy (Principle P9: "Build Only What the Platform Cannot Do"):

```
┌─────────────────────────────────────────┐
│   Claude Code (Native Orchestration)    │
│   - Task tool for subagent coordination │
│   - Lifecycle hooks for event tracking  │
│   - Git worktree management            │
└──────────┬──────────────┬───────────────┘
           │              │
    ┌──────▼──────┐  ┌───▼────────┐
    │ Knowledge   │  │  Quality   │
    │ Graph MCP   │  │  MCP       │
    │ Server      │  │  Server    │
    └─────────────┘  └────────────┘
```

**What we build:**
- Two MCP servers providing capabilities Claude Code lacks
- Custom subagent definitions (`.claude/agents/*.md`)
- Orchestration instructions (`CLAUDE.md`)
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

**Knowledge Graph Server:**
```bash
cd mcp-servers/knowledge-graph
uv sync
```

**Quality Server:**
```bash
cd mcp-servers/quality
uv sync
```

**Extension (optional):**
```bash
cd extension
npm install
```

### 2. Run Tests

```bash
# Knowledge Graph (18 tests, 74% coverage)
cd mcp-servers/knowledge-graph
uv run pytest

# Quality (26 tests, 48% coverage)
cd mcp-servers/quality
uv run pytest

# Extension (9 unit tests)
cd extension
npm test
```

### 3. Start MCP Servers

**Knowledge Graph:**
```bash
cd mcp-servers/knowledge-graph
uv run python -m collab_kg.server
# Runs on port 3101 (SSE transport)
```

**Quality:**
```bash
cd mcp-servers/quality
uv run python -m collab_quality.server
# Runs on port 3102 (SSE transport)
```

### 4. Install Extension (Optional)

```bash
cd extension
npm install
npm run build
# Then: Open in VS Code and press F5 to launch Extension Development Host
```

## Project Structure

```
agent-vision-team/
├── mcp-servers/
│   ├── knowledge-graph/       # Tier-protected institutional memory
│   └── quality/                # Deterministic quality verification
├── extension/                  # VS Code extension (observability only)
├── templates/                  # Installation templates for target projects
│   ├── claude-md/              # CLAUDE.md orchestration template
│   └── collab/                 # .claude/collab/ file structure
├── docs/
│   └── v1-full-architecture/   # Archived v1 design documents
├── COLLABORATIVE_INTELLIGENCE_VISION.md  # System vision (principles, topology)
└── ARCHITECTURE.md             # Technical architecture specification
```

## Documentation

- **[Vision Document](COLLABORATIVE_INTELLIGENCE_VISION.md)**: Principles, agent topology, communication architecture
- **[Architecture Document](ARCHITECTURE.md)**: Technical specifications, data flow, implementation phases
- **[Knowledge Graph Server README](mcp-servers/knowledge-graph/README.md)**: KG server API and tier protection
- **[Quality Server README](mcp-servers/quality/README.md)**: Quality tools and trust engine
- **[V1 Architecture (Archived)](docs/v1-full-architecture/README.md)**: Original full-infrastructure design

## Core Concepts

### Protection Tiers

Three levels of oversight:

1. **T1 Vision** (Immutable): Fundamental identity and purpose. Human-only modification.
2. **T2 Architecture** (Human-Gated): Established patterns. Requires approval for changes.
3. **T3 Quality** (Automated): Code quality, tests, coverage. Freely modifiable.

### Custom Subagents

Defined in `.claude/agents/*.md` with YAML frontmatter:

- **worker.md**: Implements tasks, queries KG for constraints, runs quality checks
- **quality-reviewer.md**: Three-lens evaluation (vision → architecture → quality)
- **kg-librarian.md**: Curates institutional memory after sessions

### Orchestrator-as-Hub

The human + primary Claude Code session acts as orchestrator, using:
- Task tool to spawn subagents
- CLAUDE.md for task decomposition instructions
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

### 🚀 Phase 4: Expand

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

### Quality Server

- **Multi-Language Support**: Python (ruff), TypeScript (eslint/prettier), Swift (swiftlint), Rust (clippy)
- **Unified Interface**: Single MCP tools for format, lint, test, coverage
- **Trust Engine**: SQLite-backed finding tracking with dismissal audit trail
- **Quality Gates**: Aggregated gate results (build, lint, tests, coverage, findings)
- **No Silent Dismissals**: Every dismissal requires justification and identity

## Test Coverage

### Summary

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| Knowledge Graph | 18 | 74% | ✅ All passing |
| Quality Server | 26 | 48% | ✅ All passing |
| Extension (Unit) | 9 | N/A | ✅ All passing |
| **Total** | **53** | **61%** | **✅ All passing** |

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
# 1. Run all tests
cd mcp-servers/knowledge-graph && uv run pytest
cd mcp-servers/quality && uv run pytest
cd extension && npm test

# 2. Start MCP servers
cd mcp-servers/knowledge-graph && uv run python -m collab_kg.server &
cd mcp-servers/quality && uv run python -m collab_quality.server &

# 3. Verify server health
curl http://localhost:3101/health
curl http://localhost:3102/health

# 4. Test end-to-end flow (manual)
# - Open workspace with .claude/collab/ in Claude Code
# - Use Task tool to spawn worker subagent
# - Worker queries KG, runs quality checks
# - Quality reviewer evaluates work
# - KG librarian curates memory
```

## Contributing

This is an experimental system exploring platform-native architecture. The v1 full-infrastructure design is preserved in `docs/v1-full-architecture/` and may be revisited based on what we learn from this approach.

## License

[Specify license]

## Related Documents

- [Collaborative Intelligence Vision](COLLABORATIVE_INTELLIGENCE_VISION.md)
- [Technical Architecture](ARCHITECTURE.md)
- [V1 Architecture (Archived)](docs/v1-full-architecture/README.md)
