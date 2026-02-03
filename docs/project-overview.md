# Collaborative Intelligence System

> A platform-native multi-agent framework that enables teams of AI agents to work for extended autonomous sessions while protecting project vision and maintaining architectural integrity.

**Last Updated**: 2026-02-02

---

## The Vision

This system exists to solve a fundamental problem: how do you enable multiple AI agents to work together for hours without derailing, degrading in quality, or going unchecked?

The answer lies in a hierarchy of concerns. Vision (what the project IS) governs architecture (how we build it). Architecture governs quality (the standards we enforce). Every agent's work is measured against this hierarchy. A perfectly linted function that violates the project's design philosophy is a failure, not a success.

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Vision First** | Vision standards are immutable by agents. Only humans define the vision. Agents enforce it but never propose changes to it. |
| **Mutual Confidence** | The quality system and dev agents "have each other's back." Neither side "owns" quality; it's shared. |
| **Bidirectional Agency** | The quality system enables coding agents to do their best work. Support, not policing. |
| **Extended Autonomous Sessions** | Teams of agents work for hours without derailing, losing focus, or quality degradation. |
| **Build Only What the Platform Cannot Do** | Claude Code handles orchestration natively. We build only persistent memory and deterministic verification. |

### The Team Metaphor

This isn't a pipeline where hooks fire and tools run. This is a **team united by a shared mission**: realizing the project's vision through disciplined architecture and quality execution.

- Members have distinct expertise and genuinely different perspectives
- They communicate bidirectionally with rich context
- They develop working confidence through track record, not just permission scoping
- The quality of collective output exceeds what any individual could produce
- **Every member understands the project's vision and protects it**

---

## Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────┐
│            HUMAN + PRIMARY SESSION (Orchestrator)             │
│   Interactive Claude Code session directing the team          │
└──────────┬───────────────┬───────────────┬───────────────────┘
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   WORKER    │ │  QUALITY    │ │ KG LIBRARIAN│
    │  SUBAGENT   │ │  REVIEWER   │ │  SUBAGENT   │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
    ┌──────▼───────────────▼───────────────▼──────┐
    │              MCP SERVERS                     │
    │  ┌─────────────┐  ┌─────────────┐  ┌──────┐ │
    │  │ Knowledge   │  │  Quality    │  │Govern│ │
    │  │   Graph     │  │  Server     │  │ance  │ │
    │  │  :3101      │  │  :3102      │  │:3103 │ │
    │  └─────────────┘  └─────────────┘  └──────┘ │
    └─────────────────────────────────────────────┘
           │
    ┌──────▼──────────────────────────────────────┐
    │          VS CODE EXTENSION                   │
    │    (Observability Dashboard - Read Only)     │
    └─────────────────────────────────────────────┘
```

---

## Key Components

### 1. Three-Tier Governance Hierarchy

The system enforces a protection hierarchy that mirrors what matters most in a project:

| Tier | Contains | Who Can Modify | Examples |
|------|----------|----------------|----------|
| **Vision** | Core principles, design philosophy, fundamental purpose | Human only | "Voice is the primary interaction mode", "All services use protocol-based DI" |
| **Architecture** | Patterns, major components, established abstractions | Human or orchestrator with approval | "ServiceRegistry pattern", "AuthService component" |
| **Quality** | Observations, findings, troubleshooting notes | Any agent | "AuthService lacks error handling", "Login flow refactored" |

**Key principle**: Lower tiers cannot modify higher tiers. Vision conflicts override all other work.

### 2. Three MCP Servers

#### Knowledge Graph Server (Port 3101)
**Purpose**: Tier-protected persistent institutional memory

- Stores entities (components, patterns, decisions, vision standards)
- Relations map dependencies and pattern adherence
- Observations capture facts with timestamps and outcomes
- **Tier protection enforced at the server level** — agents cannot accidentally corrupt vision-tier data

**Tools**: `create_entities`, `create_relations`, `add_observations`, `search_nodes`, `get_entity`, `get_entities_by_tier`, `delete_observations`, `delete_entity`

#### Quality Server (Port 3102)
**Purpose**: Deterministic quality verification with trust engine

- Wraps real tools: `ruff` (Python), `eslint` (TypeScript), `swiftlint` (Swift), `clippy` (Rust)
- Unified interface to formatters, linters, test runners, coverage checkers
- **Trust engine** with SQLite-backed finding management
- **No silent dismissals** — every dismissed finding requires justification

**Tools**: `auto_format`, `run_lint`, `run_tests`, `check_coverage`, `check_all_gates`, `validate`, `get_trust_decision`, `record_dismissal`

#### Governance Server (Port 3103)
**Purpose**: Transactional review checkpoints for agent decisions

- Workers submit decisions and **block** until reviewed
- Verdicts: `approved`, `blocked`, or `needs_human_review`
- Automatic classification of deviations and scope changes
- Full decision history with audit trail

**Tools**: `submit_decision`, `submit_plan_for_review`, `submit_completion_review`, `get_decision_history`, `get_governance_status`

### 3. Four Custom Subagents

| Agent | Model | Role | Key Capabilities |
|-------|-------|------|------------------|
| **Worker** | Opus 4.5 | Implements scoped tasks | Queries KG for constraints, submits decisions for review, runs quality gates |
| **Quality Reviewer** | Opus 4.5 | Three-lens evaluation | Vision → Architecture → Quality review order; returns structured findings |
| **KG Librarian** | Sonnet 4.5 | Curates institutional memory | Consolidates observations, promotes patterns, syncs to archival files |
| **Governance Reviewer** | Sonnet 4.5 | Evaluates decisions against standards | Called internally by governance server via `claude --print` |

### 4. VS Code Extension

**Role**: Observability layer (read-only)

- **Memory Browser**: KG entities grouped by protection tier
- **Findings Panel**: Quality findings mapped to VS Code diagnostics
- **Tasks Panel**: Task briefs from filesystem
- **Dashboard Webview**: Real-time overview of session state, agents, and activity

The extension monitors and displays — it does NOT orchestrate, spawn agents, or manage sessions. The system works fully from CLI without the extension.

---

## How It Works

### Task Execution Flow

```
1. Human gives orchestrator a complex task
2. Orchestrator decomposes into subtasks, writes task briefs
3. Orchestrator creates git worktrees for parallel isolation
4. Worker queries KG for vision/architecture constraints
5. Worker submits key decisions to Governance server (blocks until verdict)
6. Worker implements, runs quality gates
7. Quality Reviewer applies three-lens review
8. Findings route back to Worker for resolution
9. On completion: merge, checkpoint, curate memory via KG Librarian
```

### The Three-Lens Review Model

The Quality Reviewer evaluates work in strict order:

1. **Vision Lens** (Highest Priority)
   - Does this work align with project identity?
   - Vision conflicts stop all related work immediately

2. **Architecture Lens**
   - Does this work follow established patterns?
   - Detects "ad-hoc pattern drift" — reinventing existing solutions

3. **Quality Lens**
   - Does the code pass automated checks?
   - Auto-fixes formatting; reports issues needing judgment

### Transactional Governance

Workers don't just implement and hope for the best. Before key decisions, they call the Governance server:

```
Worker: submit_decision(category="pattern_choice", summary="Using singleton for AuthService")
        ↓ BLOCKS
Governance Server: Loads KG vision standards → Runs governance-reviewer → Returns verdict
        ↓
Worker: Receives verdict (approved/blocked/needs_human_review)
        ↓
Worker: Acts on verdict (proceed, revise, or escalate)
```

Decision categories: `pattern_choice`, `component_design`, `api_design`, `deviation`, `scope_change`

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Orchestration | Claude Code CLI + native subagents | Platform-native, no API keys needed |
| MCP Servers | Python + FastMCP 2.x | SSE transport, simple server creation |
| KG Storage | JSONL | Matches Anthropic's KG Memory format |
| Quality Storage | SQLite | Zero-config for trust engine |
| VS Code Extension | TypeScript + React | Rich observability dashboard |
| AI Models | Opus 4.5 (judgment), Sonnet 4.5 (routine) | Capability-first model routing |

---

## What Makes This Different

### Platform-Native Philosophy

This system is built **on top of** Claude Code's native capabilities, not around them. Where other approaches require API keys and external orchestration frameworks (LangGraph, AutoGen, CrewAI), this runs entirely on Claude Code Max.

**What Claude Code provides natively** (we don't rebuild):
- Agent spawning via custom subagent definitions
- Parallel execution with `run_in_background`
- Lifecycle hooks for event tracking
- Session persistence and resume
- Model routing per subagent

**What we build** (Claude Code cannot do):
- Persistent, tier-protected institutional memory
- Deterministic quality verification with trust engine
- Transactional governance checkpoints

### Earned Trust, Not Blind Trust

Confidence between agents emerges from:
1. **Deterministic verification first** — Does it compile? Do tests pass?
2. **Track record second** — Did previous suggestions work?
3. **Explanation quality third** — Is the rationale project-specific?

Never from self-assessment.

### The Enabling Role

The quality system's primary purpose is making workers produce better work than they would alone:
- **Pattern Memory**: "In this codebase, new services always implement the protocol pattern. Here's TTSService as an example."
- **Architectural Guardrails as Navigation Aids**: Not "you violated the boundary" but "here's how SessionManager does it."
- **Coaching Over Replacement**: Explains WHY patterns exist, not just enforcing them.

---

## Current Status

### Completed
- Knowledge Graph MCP server with tier protection (18 tests, 74% coverage)
- Quality MCP server with trust engine (26 tests, 48% coverage)
- Governance MCP server with transactional checkpoints
- Four custom subagent definitions
- VS Code extension with TreeViews and dashboard
- PreToolUse hook for governance enforcement
- CLAUDE.md orchestrator instructions

### In Progress
- Dogfooding and validation testing
- Dashboard UX improvements

### Planned
- Cross-project memory (KG entities that travel between projects)
- Multi-worker parallelism patterns
- Installation script for target projects

---

## File Structure

```
agent-vision-team/
├── .claude/
│   ├── agents/                    # Custom subagent definitions
│   │   ├── worker.md
│   │   ├── quality-reviewer.md
│   │   ├── kg-librarian.md
│   │   └── governance-reviewer.md
│   ├── collab/                    # Collaboration workspace
│   │   ├── session-state.md
│   │   ├── task-briefs/
│   │   ├── memory/
│   │   ├── knowledge-graph.jsonl
│   │   ├── trust-engine.db
│   │   └── governance.db
│   └── settings.json              # Hooks and MCP configuration
├── mcp-servers/
│   ├── knowledge-graph/           # Tier-protected institutional memory
│   ├── quality/                   # Deterministic quality verification
│   └── governance/                # Transactional review checkpoints
├── extension/                     # VS Code extension (observability)
├── docs/
│   ├── project-overview.md        # This document
│   └── reports/                   # Intelligence reports
├── prompts/                       # Reusable prompts
├── COLLABORATIVE_INTELLIGENCE_VISION.md
├── ARCHITECTURE.md
└── CLAUDE.md                      # Orchestrator instructions
```

---

## Getting Started

### Prerequisites
- Claude Code with Max subscription
- Python 3.9+ with `uv` package manager
- Node.js 18+ (for VS Code extension)
- VS Code (optional, for extension)

### Starting the System

```bash
# Terminal 1: Knowledge Graph server
cd mcp-servers/knowledge-graph && uv run python -m collab_kg.server

# Terminal 2: Quality server
cd mcp-servers/quality && uv run python -m collab_quality.server

# Terminal 3: Governance server
cd mcp-servers/governance && uv run python -m collab_governance.server

# Terminal 4: Claude Code session
claude
```

The CLAUDE.md in the project root provides orchestrator instructions automatically.

---

## Learn More

- [COLLABORATIVE_INTELLIGENCE_VISION.md](../COLLABORATIVE_INTELLIGENCE_VISION.md) — Full vision document with principles and philosophy
- [ARCHITECTURE.md](../ARCHITECTURE.md) — Engineering-level architecture specification
- [CLAUDE.md](../CLAUDE.md) — Orchestrator instructions and protocols

---

*This document is maintained by the `/project-overview` skill. Run it to regenerate from current project state.*
