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

### 2. Run Tests

```bash
# Knowledge Graph (8 tests, 74% coverage)
cd mcp-servers/knowledge-graph
uv run pytest

# Quality (26 tests, 48% coverage)
cd mcp-servers/quality
uv run pytest
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
- [x] 74% test coverage (KG), 48% (Quality)

### 🔄 Phase 2: Subagents + Validation (Next)

- [ ] Write `.claude/agents/worker.md`
- [ ] Write `.claude/agents/quality-reviewer.md`
- [ ] Write `.claude/agents/kg-librarian.md`
- [ ] Write orchestrator `CLAUDE.md`
- [ ] Write `.claude/settings.json` with lifecycle hooks
- [ ] **Critical validation test**: End-to-end from CLI without extension

### 📋 Phase 3: Extension (After Phase 2 validation)

- [ ] MCP client service (read-only)
- [ ] Memory Browser TreeView
- [ ] Findings Panel TreeView
- [ ] Dashboard webview
- [ ] Diagnostics integration

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

## Contributing

This is an experimental system exploring platform-native architecture. The v1 full-infrastructure design is preserved in `docs/v1-full-architecture/` and may be revisited based on what we learn from this approach.

## License

[Specify license]

## Related Documents

- [Collaborative Intelligence Vision](COLLABORATIVE_INTELLIGENCE_VISION.md)
- [Technical Architecture](ARCHITECTURE.md)
- [V1 Architecture (Archived)](docs/v1-full-architecture/README.md)
