# Collaborative Intelligence System: Architecture Document

This document specifies the engineering-level architecture for the Collaborative Intelligence System. It translates the conceptual design in `COLLABORATIVE_INTELLIGENCE_VISION.md` into concrete component designs, interfaces, data flows, and build instructions.

**Relationship to the Vision Document**: The vision doc answers *why this system exists, what it's shaped like, and what principles govern it*. This document answers *how to build it*. Every architectural decision here traces back to a principle or capability defined in the vision doc.

**Relationship to the V1 Architecture**: The original full-infrastructure architecture is preserved in `docs/v1-full-architecture/`. That design included three MCP servers (Hub, KG, Quality), a VS Code extension as orchestration engine, and custom session management. This document reflects the platform-native pivot: Claude Code's subagent system handles orchestration, only two MCP servers remain (KG + Quality), and the extension is reduced to observability.

---

## Table of Contents

1. [System Boundaries and Glossary](#1-system-boundaries-and-glossary)
2. [System Overview](#2-system-overview)
3. [Claude Code as Orchestration Platform](#3-claude-code-as-orchestration-platform)
4. [Knowledge Graph MCP Server](#4-knowledge-graph-mcp-server)
5. [Quality MCP Server](#5-quality-mcp-server)
6. [Custom Subagent Definitions](#6-custom-subagent-definitions)
7. [CLAUDE.md Orchestration](#7-claudemd-orchestration)
8. [VS Code Extension (Observability)](#8-vs-code-extension-observability)
9. [File System Layout](#9-file-system-layout)
10. [Data Flow Architecture](#10-data-flow-architecture)
11. [Technology Stack](#11-technology-stack)
12. [Implementation Phases](#12-implementation-phases)
13. [What We're Deliberately Not Building (Yet)](#13-what-were-deliberately-not-building-yet)
14. [Verification](#14-verification)

---

## 1. System Boundaries and Glossary

### In Scope

- Two MCP servers: Knowledge Graph, Quality
- Claude Code custom subagent definitions (`.claude/agents/`)
- Orchestrator CLAUDE.md instructions
- Tier-aware institutional memory
- File system conventions for task briefs, artifacts, and archival memory
- VS Code extension (observability and monitoring only)

### Out of Scope

- The target project being developed (the codebase agents work on)
- CI/CD pipelines for target projects
- External service internals (CodeRabbit, GitHub Actions)
- External orchestration frameworks (no Goose, LangGraph, AutoGen, CrewAI)
- API keys of any kind — the system runs entirely on Claude Code Max
- Custom inter-agent messaging infrastructure (Claude Code handles this natively)

### Glossary

| Term | Definition |
|------|-----------|
| **Orchestrator** | The human developer working through a primary Claude Code session. The strategic decision-maker. |
| **Worker Subagent** | A Claude Code subagent spawned via the Task tool, implementing a specific task. Defined in `.claude/agents/worker.md`. |
| **Quality Reviewer Subagent** | A Claude Code subagent that evaluates work through the three-lens model. Defined in `.claude/agents/quality-reviewer.md`. |
| **KG Librarian Subagent** | A Claude Code subagent that curates institutional memory. Defined in `.claude/agents/kg-librarian.md`. |
| **Knowledge Graph (KG)** | The MCP server providing persistent institutional memory as entities, relations, and observations. |
| **Quality Server** | The MCP server wrapping deterministic verification tools (linters, formatters, test runners) behind a unified interface. |
| **Finding** | A structured result from the quality reviewer identifying an issue, tagged with tier and severity. |
| **Tier** | One of three oversight levels: T1 Vision (immutable), T2 Architecture (human-gated), T3 Quality (automated). |
| **Protection Tier** | The mutability level of a Knowledge Graph entity: `vision` (human-only), `architecture` (human-approved), `quality` (automated). |
| **Task Brief** | A structured markdown document defining a worker's assignment: goals, acceptance criteria, constraints, scope. |
| **Checkpoint** | A known-good state: a git tag + session-state.md update, resumable after failures. |
| **Drift** | Deviation from session goals — time drift, loop drift, scope drift, or quality drift. |

---

## 2. System Overview

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                  HUMAN + PRIMARY SESSION                         │
│            Interactive Claude Code (Opus 4.5)                    │
│            Reads: CLAUDE.md, session-state.md                    │
│            Uses: Task tool to spawn subagents                    │
└──────┬────────────────┬────────────────┬────────────────────────┘
       │                │                │
       │ Task tool      │ Task tool      │ Task tool
       │                │                │
┌──────▼──────┐  ┌──────▼──────────┐  ┌──▼────────────────┐
│   WORKER    │  │ QUALITY         │  │ KG LIBRARIAN      │
│   SUBAGENT  │  │ REVIEWER        │  │ SUBAGENT          │
│             │  │ SUBAGENT        │  │                   │
│  worker.md  │  │ quality-        │  │ kg-librarian.md   │
│             │  │ reviewer.md     │  │                   │
└──────┬──────┘  └──────┬──────────┘  └──────┬────────────┘
       │                │                     │
       │ MCP            │ MCP                 │ MCP
       │                │                     │
┌──────▼──────┐  ┌──────▼──────────┐  ┌──────▼────────────┐
│ Knowledge   │  │ Quality         │  │ Knowledge         │
│ Graph       │  │ Server          │  │ Graph             │
│ Server      │  │                 │  │ Server            │
│ :3101       │  │ :3102           │  │ :3101             │
└─────────────┘  └─────────────────┘  └───────────────────┘
       │                │
       │                │
┌──────▼────────────────▼──────────────────────────────────┐
│                    PERSISTENT STATE                       │
│  .claude/collab/knowledge-graph.jsonl  (KG data)         │
│  .avt/session-state.md                 (goals, progress) │
│  .avt/task-briefs/                     (assignments)     │
│  .avt/memory/                          (archival files)  │
│  Git                                   (code state)      │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│          VS CODE EXTENSION (observability only)          │
│  Reads from: KG server, Quality server, filesystem       │
│  Displays: TreeViews, diagnostics, dashboard             │
│  Does NOT: spawn agents, manage sessions, orchestrate    │
└──────────────────────────────────────────────────────────┘
```

### Component Interaction Summary

| From \ To | KG Server | Quality Server | Git | Filesystem |
|-----------|-----------|----------------|-----|-----------|
| **Orchestrator** | Query constraints | — | Merge, tag | Write briefs, update session state |
| **Worker** | Query patterns, write observations | Run checks | Branch, commit (in worktree) | Read briefs |
| **Quality Reviewer** | Query vision/arch standards | Run all gates | Read diffs | — |
| **KG Librarian** | Full CRUD (curate) | — | — | Sync to archival files |
| **Extension** | Browse entities (read-only) | Display results (read-only) | — | Watch `.avt/` |

### Deployment Topology

All components run on a single developer machine (macOS):

- **Claude Code Sessions**: Interactive terminal sessions and subagents
- **MCP Servers**: Separate local processes, communicating via stdio or HTTP/SSE
- **Git/Filesystem**: Local, standard filesystem access
- **VS Code Extension**: Runs in VS Code Extension Host (observability only)

No network services, no cloud dependencies, no API keys.

---

## 3. Claude Code as Orchestration Platform

Claude Code provides the orchestration primitives that the v1 design built from scratch. This section maps each orchestration concern to the native capability that handles it.

### 3.1 Custom Subagents

Subagents are defined as markdown files in `.claude/agents/` with YAML frontmatter specifying tools, model, and prompt.

```
.claude/agents/
├── worker.md              # Implementation subagent
├── quality-reviewer.md    # Three-lens evaluation subagent
└── kg-librarian.md        # Memory curation subagent
```

When the orchestrator uses the Task tool to spawn a subagent, Claude Code:
1. Reads the subagent definition file
2. Creates a new context with the specified system prompt
3. Grants access to the specified tools
4. Routes to the specified model
5. Returns the subagent's output to the orchestrator

### 3.2 Task Tool Patterns

**Sequential review pattern** (worker then reviewer):
```
Orchestrator
  → spawns Worker (Task tool, foreground)
  ← Worker returns: completed code + diff summary
  → spawns Quality Reviewer (Task tool, foreground, passes diff)
  ← Reviewer returns: structured findings [{tier, severity, component, rationale, suggestion}]
  → if findings: spawns Worker again with findings context
  ← Worker returns: fixes applied
  → spawns Quality Reviewer again to verify
  ← Reviewer returns: all clear
```

**Parallel worker pattern** (multiple workers):
```
Orchestrator
  → spawns Worker A (Task tool, background, worktree-a)
  → spawns Worker B (Task tool, background, worktree-b)
  ← Worker A returns: completed task A
  ← Worker B returns: completed task B
  → spawns Quality Reviewer for Worker A's diff
  → spawns Quality Reviewer for Worker B's diff
```

**Note**: Background subagents cannot use MCP tools. Workers needing KG/Quality MCP access must run in foreground, or the orchestrator pre-fetches context for them.

### 3.3 Lifecycle Hooks

Hooks in `.claude/settings.json` respond to subagent and tool events:

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "*",
        "command": "echo \"$(date -u +%Y-%m-%dT%H:%M:%SZ) START $SUBAGENT_NAME\" >> .avt/agent-events.jsonl"
      }
    ],
    "SubagentStop": [
      {
        "matcher": "*",
        "command": "echo \"$(date -u +%Y-%m-%dT%H:%M:%SZ) STOP $SUBAGENT_NAME\" >> .avt/agent-events.jsonl"
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit",
        "command": "# Validate edit targets are within scope"
      }
    ]
  }
}
```

These hooks provide the event tracking that the v1 Hub server's agent registry handled.

### 3.4 Worktree Management

Worker subagents operating on code changes use isolated git worktrees:

**Creation** (orchestrator creates before spawning worker):
```bash
git worktree add ../project-name-worker-1 -b task/001-auth-fix
```

**Worker operates** in the worktree directory, making changes on the feature branch.

**Cleanup** (orchestrator handles after review and merge):
```bash
git merge task/001-auth-fix    # In main branch
git worktree remove ../project-name-worker-1
git branch -d task/001-auth-fix
```

### 3.5 Session Persistence

- **Claude Code `--resume`**: Continues a session with full conversation context
- **Session IDs**: Each session gets a stable ID for later resume
- **Git checkpoints**: Tag known-good states for code-level resume
- **session-state.md**: Human-readable session state that persists across everything

---

## 4. Knowledge Graph MCP Server

**Purpose**: Persistent institutional memory with tier-aware protection. Stores entities (components, patterns, decisions, problems, vision standards), relations, and observations. All sessions share the same graph. (Vision doc: Section 5)

**Transport**: stdio (default for single-client Claude Code) or HTTP/SSE (when extension also connects)

**Storage**: JSONL file at `.claude/collab/knowledge-graph.jsonl` (matching Anthropic's KG Memory server format)

### 4.1 Tool Interface

```
create_entities(
  entities: [{
    name: string,
    entityType: string,          # "component" | "vision_standard" | "architectural_standard" | "pattern" | "problem" | "solution_pattern"
    observations: string[]       # Must include "protection_tier: <tier>" for tier-protected entities
  }]
) → { created: number }

create_relations(
  relations: [{
    from: string,                # Entity name
    to: string,                  # Entity name
    relationType: string         # "depends_on" | "follows_pattern" | "governed_by" | "fixed_by" | "exemplified_by" | "rejected_in_favor_of"
  }]
) → { created: number }

add_observations(
  entityName: string,
  observations: string[],
  callerRole: string,            # "human" | "orchestrator" | "worker" | "quality"
  changeApproved: boolean        # Required for architecture-tier writes
) → { added: number, error?: string }
  # REJECTS if entity has protection_tier: vision and caller is not human
  # REJECTS if entity has protection_tier: architecture and change_approved is false

delete_observations(
  entityName: string,
  observations: string[],
  callerRole: string,
  changeApproved: boolean
) → { deleted: number, error?: string }
  # Same tier protection as add_observations

delete_entity(
  entityName: string,
  callerRole: string
) → { deleted: boolean, error?: string }
  # REJECTS if entity has protection_tier: vision or architecture

delete_relations(
  relations: [{
    from: string,
    to: string,
    relationType: string
  }]
) → { deleted: number }

search_nodes(
  query: string                  # Search term (substring match)
) → EntityWithRelations[]

get_entity(
  name: string
) → EntityWithRelations          # Full entity with observations and relations

get_entities_by_tier(
  tier: string                   # "vision" | "architecture" | "quality"
) → EntityWithRelations[]
```

### 4.2 Data Models

```python
class EntityType(str, Enum):
    COMPONENT = "component"
    VISION_STANDARD = "vision_standard"
    ARCHITECTURAL_STANDARD = "architectural_standard"
    PATTERN = "pattern"
    PROBLEM = "problem"
    SOLUTION_PATTERN = "solution_pattern"

class ProtectionTier(str, Enum):
    VISION = "vision"
    ARCHITECTURE = "architecture"
    QUALITY = "quality"

@dataclass
class Entity:
    name: str
    entityType: EntityType
    observations: list[str]

@dataclass
class Relation:
    from_entity: str   # "from" in JSON
    to: str
    relationType: str

@dataclass
class EntityWithRelations:
    name: str
    entityType: EntityType
    observations: list[str]
    relations: list[Relation]
```

### 4.3 Tier Protection Enforcement

The server enforces tier protection at the tool level, not by convention. This is critical — a misbehaving subagent cannot accidentally corrupt vision-tier data.

| Entity Tier | Read | Write (add observations) | Delete (entity/observations) |
|-------------|------|--------------------------|------------------------------|
| `vision` | All callers | Human only | Human only |
| `architecture` | All callers | Requires `changeApproved: true` | Human only |
| `quality` | All callers | All callers | All callers |

The `callerRole` is passed as a tool parameter. In the native subagent architecture, the subagent definition specifies the role, and the CLAUDE.md instructions tell each subagent to pass its role in all KG calls.

### 4.4 JSONL Persistence

The KG persists to a JSONL file where each line is a complete operation:

```jsonl
{"type": "entity", "name": "hands_free_first_design", "entityType": "vision_standard", "observations": ["protection_tier: vision", "mutability: human_only", "Voice is PRIMARY interaction mode"]}
{"type": "relation", "from": "KBOralSessionView", "to": "hands_free_first_design", "relationType": "governed_by"}
{"type": "entity", "name": "KBOralSessionView", "entityType": "component", "observations": ["protection_tier: architecture", "Uses protocol-based DI"]}
```

On startup, the server reads the entire file to reconstruct the in-memory graph. Writes append to the file. Periodic compaction rewrites the file with only current state.

### 4.5 Current Implementation Status

The KG server scaffold exists with:
- `graph.py`: Entity/relation/observation CRUD with tier protection
- `tier_protection.py`: `get_entity_tier()` and `validate_write_access()` enforcement
- `models.py`: Pydantic models for Entity, Relation, EntityWithRelations, ProtectionTier
- `server.py`: FastMCP server definition exposing tools
- 8 passing tests covering tier protection, CRUD operations, search

**Remaining work**: JSONL persistence (currently in-memory only), `delete_entity` and `delete_relations` tools, compaction logic.

---

## 5. Quality MCP Server

**Purpose**: Wraps all quality tools (linters, formatters, test runners, coverage checkers) behind a unified MCP interface. Implements the Tool Trust Engine. Provides quality gate aggregation. (Vision doc: Section 6 — deterministic verification as the primary trust mechanism)

**Transport**: stdio or HTTP/SSE

**Storage**: SQLite for Tool Trust Engine history and quality gate state.

### 5.1 Tool Interface

```
auto_format(
  files?: string[],              # Specific files, or all changed files if omitted
  language?: string              # "swift" | "python" | "rust" | "typescript"
) → { formatted: string[], unchanged: string[] }

run_lint(
  files?: string[],
  language?: string
) → { findings: LintFinding[], auto_fixable: number, total: number }

run_tests(
  scope?: string,                # "all" | "changed" | specific test path
  language?: string
) → { passed: number, failed: number, skipped: number, failures: TestFailure[] }

check_coverage(
  language?: string
) → { percentage: number, target: number, met: boolean, uncovered_files: string[] }

check_all_gates() → {
  build: { passed: boolean },
  lint: { passed: boolean, violations: number },
  tests: { passed: boolean, failures: number },
  coverage: { passed: boolean, percentage: number },
  findings: { passed: boolean, critical: number },
  all_passed: boolean
}

validate() → {                   # Comprehensive validation (all gates + summary)
  gates: GateResults,
  summary: string,
  all_passed: boolean
}

get_trust_decision(
  finding_id: string
) → { decision: "BLOCK" | "INVESTIGATE" | "TRACK", rationale: string }

record_dismissal(
  finding_id: string,
  justification: string,         # Required — no silent dismissals
  dismissed_by: string           # Agent or human identifier
) → { recorded: boolean }
```

### 5.2 Specialist Routing

The Quality Server routes checks to the best available tool per language:

| Language | Formatter | Linter | Test Runner |
|----------|-----------|--------|-------------|
| Swift | swiftformat | SwiftLint | xcodebuild test |
| Python | ruff format | ruff check | pytest |
| Rust | rustfmt | clippy | cargo test |
| TypeScript | prettier | eslint | vitest / jest |

The routing is configured in the Quality Server's config, not hardcoded. New languages/tools can be added by updating the config.

### 5.3 Tool Trust Engine

The trust engine provides structured decisions on findings:

```python
class TrustDecision(str, Enum):
    BLOCK = "BLOCK"           # Cannot proceed until resolved
    INVESTIGATE = "INVESTIGATE"  # Needs human or orchestrator review
    TRACK = "TRACK"            # Note it, don't block on it

# Trust engine schema (SQLite)
"""
CREATE TABLE findings (
    id TEXT PRIMARY KEY,
    tool TEXT NOT NULL,
    severity TEXT NOT NULL,
    component TEXT,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'open',       -- open, fixed, dismissed
    dismissed_by TEXT,
    dismissal_justification TEXT,
    dismissed_at TEXT
);
"""
```

Key principle: **No silent dismissals.** Every dismissed finding requires a justification string and the identity of who dismissed it. This creates an auditable trail.

### 5.4 Current Implementation Status

The Quality server scaffold exists with:
- `server.py`: FastMCP server exposing quality tools
- `tools/`: Stubs for formatting, linting, testing, coverage
- `gates.py`: Quality gate aggregation logic
- `trust_engine.py`: Trust decision framework (stub)
- 7 passing tests

**Remaining work**: Replace stubs with real tool invocations (`subprocess.run` wrapping `ruff`, `eslint`, `pytest`, etc.), implement SQLite persistence for trust engine, add configurable specialist routing.

---

## 6. Custom Subagent Definitions

Three custom subagents are defined as markdown files in `.claude/agents/`. Each file contains YAML frontmatter (model, tools, permissions) and a system prompt.

### 6.1 Worker Subagent

**File**: `.claude/agents/worker.md`

```markdown
---
model: opus
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - mcp:collab-kg
  - mcp:collab-quality
---

You are a Worker subagent in the Collaborative Intelligence System. You implement specific tasks assigned by the orchestrator.

## Startup Protocol

1. Read your task brief (provided in the task prompt or in `.avt/task-briefs/`)
2. Query the Knowledge Graph for vision standards governing your task's components:
   - `get_entities_by_tier("vision")` — load all vision constraints
   - `search_nodes("<component name>")` — find architectural patterns and past solutions
3. Note any `governed_by` relations linking your components to vision standards
4. Check for solution patterns matching your task type

## During Work

- Stay within the scope defined in your task brief
- Follow established patterns discovered in the KG (especially `follows_pattern` relations)
- Run quality checks via the Quality MCP server before reporting completion
- If you encounter an architectural question, note it in your response for the orchestrator

## On Completion

- Run `check_all_gates()` via the Quality server
- Return a structured summary: what was done, what files changed, gate results, any concerns
- Pass your `callerRole` as "worker" in all KG operations

## Constraints

- Do not modify files outside your task brief's scope
- Do not modify vision-tier or architecture-tier KG entities
- If a vision standard conflicts with your task, stop and report the conflict
```

### 6.2 Quality Reviewer Subagent

**File**: `.claude/agents/quality-reviewer.md`

```markdown
---
model: opus
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - mcp:collab-kg
  - mcp:collab-quality
---

You are the Quality Reviewer subagent in the Collaborative Intelligence System. You evaluate work through three ordered lenses: vision alignment, architectural conformance, and quality compliance.

## Review Protocol

Apply the three-lens model in strict order:

### Lens 1: Vision (Highest Priority)
- Query KG: `get_entities_by_tier("vision")` to load all vision standards
- Check if the work aligns with every applicable vision standard
- If there is a vision conflict, this is the ONLY finding you report — it overrides everything else
- Severity: `vision_conflict`

### Lens 2: Architecture
- Query KG: `search_nodes("<affected components>")` for architectural entities
- Check for adherence to established patterns (`follows_pattern` relations)
- Detect "ad-hoc pattern drift": new code that reinvents something an existing pattern handles
- Severity: `architectural`

### Lens 3: Quality
- Run `check_all_gates()` via the Quality server
- Run `run_lint()` for specific language violations
- Check test coverage via `check_coverage()`
- Severity: `logic`, `style`, or `formatting`

## Finding Format

Return findings as a structured list:
```json
[
  {
    "tier": "architecture",
    "severity": "architectural",
    "component": "AuthService",
    "finding": "New service bypasses established DI pattern",
    "rationale": "ServiceRegistry pattern (KG entity: protocol_based_di_pattern) requires all services to be injected via init. AuthService uses a singleton instead.",
    "suggestion": "Refactor AuthService to accept dependencies via init injection, register in ServiceRegistry."
  }
]
```

Every finding MUST include:
- Project-specific rationale (not generic advice)
- A concrete suggestion for how to fix it
- Reference to the KG entity or standard being violated

## Constraints

- You are read-focused: review code, do not write production code
- Pass your `callerRole` as "quality" in all KG operations
- Do not modify vision-tier or architecture-tier KG entities
- Be constructive: you're a teammate, not a gatekeeper
```

### 6.3 KG Librarian Subagent

**File**: `.claude/agents/kg-librarian.md`

```markdown
---
model: sonnet
tools:
  - Read
  - Write
  - Glob
  - Grep
  - mcp:collab-kg
---

You are the KG Librarian subagent in the Collaborative Intelligence System. You curate institutional memory after work sessions.

## Curation Protocol

1. **Review recent activity**: Query KG for recently added entities and observations
2. **Consolidate**: Merge redundant observations on the same entity into coherent entries
3. **Promote patterns**: When the same fix or approach appears 3+ times, create a `solution_pattern` entity
4. **Remove stale entries**: Delete observations that are no longer accurate (outdated component descriptions, resolved problems)
5. **Validate tier consistency**: Ensure no vision-tier entities have been modified by agents. If found, report the violation.
6. **Sync to archival files**: Update `.avt/memory/` files with important KG entries:
   - `architectural-decisions.md` — significant decisions and their rationale
   - `troubleshooting-log.md` — problems, what was tried, what worked
   - `solution-patterns.md` — promoted patterns with steps and reference implementations

## Curation Principles

- Don't save everything — failed approaches get brief notes; successful patterns get detailed entries
- Quality over quantity — 10 well-curated entities are worth more than 100 raw observations
- Protect the tier hierarchy — never modify vision or architecture entities without explicit human approval
- Pass your `callerRole` as "quality" in all KG operations (librarian operates at the quality tier)

## Constraints

- Do not create or modify vision-tier entities
- Do not create or modify architecture-tier entities without `changeApproved: true`
- Do not delete entities that have `governed_by` relations pointing to them
```

---

## 7. CLAUDE.md Orchestration

The project's root `CLAUDE.md` instructs the orchestrator session on how to manage the collaborative intelligence workflow.

### Key Directives

```markdown
# CLAUDE.md — Orchestrator Instructions

## Collaborative Intelligence System

This project uses a collaborative intelligence system with:
- Knowledge Graph MCP server (persistent institutional memory)
- Quality MCP server (deterministic quality verification)
- Custom subagents: worker, quality-reviewer, kg-librarian

## Task Decomposition

When given a complex task:
1. Break it into discrete, scopeable units of work
2. Write a task brief for each unit in `.avt/task-briefs/`
3. Create a git worktree for each worker: `git worktree add ../project-worker-N -b task/NNN-description`
4. Spawn worker subagents via Task tool, one per task brief
5. After each worker completes, spawn quality-reviewer with the worker's diff
6. Route findings back to workers for resolution
7. When all findings are resolved and gates pass, merge and clean up

## Quality Review Protocol

After any significant code change:
1. Spawn the quality-reviewer subagent with the diff context
2. Review findings by tier (vision first, then architecture, then quality)
3. Vision conflicts: stop all related work, address immediately
4. Architecture findings: route to worker with context, require resolution
5. Quality findings: route to worker, auto-fixable issues can be fixed inline

## Memory Protocol

- Before starting work on a component, query the KG for related entities
- After completing a significant piece of work, spawn the kg-librarian
- The librarian curates observations, promotes patterns, syncs archival files

## Checkpoints

After each meaningful unit of work:
1. Update `.avt/session-state.md` with progress
2. Git tag the state: `git tag checkpoint-NNN`
3. If resuming after a failure, start from the last checkpoint

## Drift Detection

Monitor for:
- Time drift: worker on a single task too long without progress
- Loop drift: repeated failures on the same issue
- Scope drift: work outside the task brief's defined scope
- Quality drift: findings accumulating faster than resolution
```

---

## 8. VS Code Extension (Observability)

The extension's role has changed fundamentally from v1. It is now an **observability layer** — it monitors and displays system state but does not orchestrate, spawn agents, or manage sessions.

### 8.1 What the Extension Does

| Capability | Implementation |
|-----------|----------------|
| Display KG entities (Memory Browser) | MCP client → KG server `search_nodes`, `get_entities_by_tier` |
| Display quality findings | MCP client → Quality server `check_all_gates` |
| Display task briefs | FileSystemWatcher on `.avt/task-briefs/` |
| Display session state | FileSystemWatcher on `.avt/session-state.md` |
| Map findings to diagnostics | Quality findings → `vscode.Diagnostic` (squigglies in editor) |
| Status bar summary | Aggregated health from MCP servers + filesystem |
| Dashboard webview | React-based overview of all system state |

### 8.2 What the Extension Does NOT Do

- Spawn Claude Code sessions or terminals
- Manage MCP server lifecycles (servers are started separately)
- Route messages between agents
- Manage git worktrees
- Make decisions about task decomposition or quality enforcement

### 8.3 Coexistence with Claude Code Extension

The Collaborative Intelligence extension works alongside the official Claude Code VS Code extension. The division:

| Concern | Collab Intelligence Extension | Claude Code Extension |
|---------|-------------------------------|----------------------|
| AI interaction | No | Yes |
| System monitoring / dashboards | Yes | No |
| Finding display and triage | Yes | No |
| Memory browsing | Yes | No |
| Code editing | No | Yes (via Claude Code) |

### 8.4 UI Components

**Activity Bar View Container**: "Collab Intelligence" sidebar with panels:

1. **Memory Browser (TreeView)**: KG entities grouped by protection tier, expandable to show observations and relations
2. **Findings Panel (TreeView)**: Quality findings grouped by tier (Vision → Architecture → Quality), mapped to VS Code diagnostics
3. **Tasks Panel (TreeView)**: Task briefs from filesystem, showing status
4. **Session Dashboard (Webview)**: React-based overview with session state, quality gates, activity timeline

**Status Bar Items**:
- Left: `$(shield) Collab: Active` — green/yellow/red based on system health
- Center: `N findings · Phase: implementation` — summary counts

**Diagnostics**:
- Vision findings → `DiagnosticSeverity.Error` (red squiggly)
- Architecture findings → `DiagnosticSeverity.Warning` (yellow squiggly)
- Quality findings → `DiagnosticSeverity.Information` (blue squiggly)

### 8.5 Extension MCP Connectivity

The extension connects to the same MCP servers that Claude Code sessions use, but in **read-only mode**:

- Polls KG server for entity data (or subscribes via SSE if HTTP transport)
- Polls Quality server for gate status
- Watches filesystem for task brief and session state changes

The extension does NOT need to connect to a Hub server (which no longer exists).

---

## 9. File System Layout

### Product Repository

```
agent-vision-team/                       # This repo — the standalone product
├── .claude/
│   └── agents/                          # Custom subagent definitions
│       ├── worker.md
│       ├── quality-reviewer.md
│       └── kg-librarian.md
├── extension/                           # VS Code extension source (observability)
│   ├── src/
│   │   ├── extension.ts                 # Activation, command registration
│   │   ├── providers/
│   │   │   ├── MemoryTreeProvider.ts    # KG entity browser
│   │   │   ├── FindingsTreeProvider.ts  # Tier-grouped findings
│   │   │   ├── TasksTreeProvider.ts     # Task brief display
│   │   │   └── DashboardWebviewProvider.ts
│   │   ├── services/
│   │   │   ├── McpClientService.ts      # MCP connection management
│   │   │   ├── FileWatcherService.ts    # .avt/ watchers
│   │   │   └── StatusBarService.ts      # Status bar management
│   │   ├── mcp/
│   │   │   ├── KnowledgeGraphClient.ts  # Typed client for KG server
│   │   │   └── QualityClient.ts         # Typed client for Quality server
│   │   ├── models/
│   │   │   ├── Finding.ts
│   │   │   ├── Task.ts
│   │   │   └── Entity.ts
│   │   └── utils/
│   │       ├── config.ts
│   │       └── logger.ts
│   ├── webview-dashboard/
│   │   └── src/
│   │       ├── App.tsx
│   │       └── components/
│   ├── media/
│   ├── package.json
│   ├── tsconfig.json
│   └── esbuild.config.js
├── mcp-servers/
│   ├── knowledge-graph/                 # Knowledge Graph MCP server
│   │   ├── collab_kg/
│   │   │   ├── __init__.py
│   │   │   ├── server.py
│   │   │   ├── graph.py
│   │   │   ├── models.py
│   │   │   ├── tier_protection.py
│   │   │   └── storage.py               # JSONL persistence
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── quality/                         # Quality MCP server
│       ├── collab_quality/
│       │   ├── __init__.py
│       │   ├── server.py
│       │   ├── tools/
│       │   │   ├── formatting.py
│       │   │   ├── linting.py
│       │   │   ├── testing.py
│       │   │   └── coverage.py
│       │   ├── trust_engine.py
│       │   ├── gates.py
│       │   └── storage.py               # SQLite persistence
│       ├── tests/
│       ├── pyproject.toml
│       └── README.md
├── templates/                           # Per-project installation templates
│   ├── claude-md/
│   │   └── CLAUDE.md                    # Orchestrator CLAUDE.md template
│   └── collab/
│       ├── session-state.md
│       ├── task-briefs/
│       ├── artifacts/
│       ├── memory/
│       │   ├── architectural-decisions.md
│       │   ├── troubleshooting-log.md
│       │   └── solution-patterns.md
│       └── mcp-config.json
├── docs/
│   └── v1-full-architecture/            # Archived v1 design documents
│       ├── README.md
│       ├── COLLABORATIVE_INTELLIGENCE_VISION.md
│       └── ARCHITECTURE.md
├── COLLABORATIVE_INTELLIGENCE_VISION.md # Vision document (current)
├── ARCHITECTURE.md                      # This document
├── package.json
└── README.md
```

### Target Project (After Installation)

When the Collaborative Intelligence system is installed into a target project:

```
target-project/
├── .claude/
│   ├── agents/
│   │   ├── worker.md
│   │   ├── quality-reviewer.md
│   │   └── kg-librarian.md
│   ├── collab/
│   │   └── knowledge-graph.jsonl        # KG persistence (managed by server)
│   └── settings.json                    # Hooks configuration
├── .avt/
│   ├── session-state.md
│   ├── task-briefs/
│   ├── memory/
│   │   ├── architectural-decisions.md
│   │   ├── troubleshooting-log.md
│   │   ├── solution-patterns.md
│   │   └── research-findings.md
│   ├── research-prompts/
│   ├── research-briefs/
│   ├── vision/
│   ├── architecture/
│   └── project-config.json
├── .mcp.json                            # MCP server registration
├── CLAUDE.md                            # Orchestrator instructions
└── (project files...)
```

---

## 10. Data Flow Architecture

### 10.1 Task Execution Flow

```
Human gives orchestrator a complex task
  │
  ├── Orchestrator decomposes into subtasks
  ├── Writes task briefs to .avt/task-briefs/
  ├── Creates git worktrees for workers
  │
  ├── Orchestrator spawns Worker subagent (Task tool)
  │     ├── Worker reads task brief
  │     ├── Worker queries KG for constraints + patterns
  │     ├── Worker implements in worktree
  │     ├── Worker runs check_all_gates() via Quality server
  │     └── Worker returns: summary + diff + gate results
  │
  ├── Orchestrator spawns Quality Reviewer subagent (Task tool)
  │     ├── Reviewer reads worker's diff
  │     ├── Reviewer queries KG for vision + architecture standards
  │     ├── Reviewer applies three-lens model
  │     ├── Reviewer runs quality gates
  │     └── Reviewer returns: structured findings list
  │
  ├── If findings exist:
  │     ├── Orchestrator spawns Worker again with findings
  │     ├── Worker addresses each finding
  │     ├── Orchestrator spawns Reviewer again to verify
  │     └── Repeat until clean
  │
  ├── Orchestrator merges worktree branch
  ├── Orchestrator cleans up worktree
  ├── Orchestrator updates session-state.md
  ├── Orchestrator creates checkpoint (git tag)
  │
  └── Orchestrator spawns KG Librarian (Task tool)
        ├── Librarian reviews what was learned
        ├── Librarian curates KG entries
        └── Librarian syncs to archival files
```

### 10.2 Memory Flow

```
Worker queries KG before starting
  └── search_nodes("ComponentName")
      └── Returns: entity + relations + observations
          └── Worker discovers: governed_by vision standards,
              follows_pattern architectural patterns,
              past troubleshooting history

Worker adds observation during work
  └── add_observations("ComponentName", ["Fixed auth race condition"],
                       callerRole="worker")

KG Librarian curates after session
  ├── Consolidates redundant observations
  ├── Promotes recurring patterns to solution_pattern entities
  ├── Removes stale entries
  ├── Validates tier consistency
  └── Syncs to .avt/memory/ files
```

### 10.3 Vision Conflict Flow

```
Quality Reviewer detects vision conflict
  └── Returns finding: {tier: "vision", severity: "vision_conflict", ...}
      │
      Orchestrator receives finding
        ├── STOPS all related work
        ├── Escalates to human if ambiguous
        └── Routes finding to worker with directive to conform
            │
            Worker reworks to align with vision
              └── Returns fixed implementation
                  │
                  Orchestrator spawns reviewer again
                    └── Reviewer confirms vision alignment
```

---

## 11. Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Orchestration** | Claude Code CLI + subagents | Latest | Native orchestration platform |
| **MCP Servers** | Python + FastMCP | Python 3.9+, FastMCP 2.x | Consistent language; FastMCP simplifies server creation |
| **KG Storage** | JSONL | — | Simple, portable, matches Anthropic's KG Memory format |
| **Quality Storage** | SQLite | — | Reliable, zero-config for trust engine history |
| **VS Code Extension** | TypeScript | 5.x | Only option for VS Code extensions |
| **Extension Build** | esbuild | Latest | Fast bundling for extension code |
| **Dashboard Webview** | React + TypeScript | React 19 | Rich reactive UI |
| **Webview Build** | Vite | Latest | Fast dev server + build |
| **AI Models** | Opus 4.5 (default), Sonnet 4.5 (routine), Haiku (mechanical) | — | Per vision doc model routing table |
| **Version Control** | Git + worktrees | — | Code state, worker isolation |
| **Package Management** | npm (extension), uv (Python servers) | — | Standard per ecosystem |
| **OS** | macOS (Darwin) | — | Developer platform |

---

## 12. Implementation Phases

### Phase 1: Make MCP Servers Real

Stand up the two MCP servers with actual functionality (not stubs).

**Knowledge Graph Server:**
- [ ] JSONL persistence (load on startup, append on write)
- [ ] `delete_entity` tool with tier protection
- [ ] `delete_relations` tool
- [ ] Compaction logic (periodic rewrite of JSONL)
- [ ] Pre-populate with example vision/architecture entities for testing
- [ ] Verify: 8 existing tests pass + new tests for persistence and deletion

**Quality Server:**
- [ ] Replace formatting stubs with real `subprocess.run` calls (`ruff format`, `prettier`)
- [ ] Replace linting stubs with real calls (`ruff check`, `eslint`)
- [ ] Replace test stubs with real calls (`pytest`, `npm test`)
- [ ] Replace coverage stubs with real calls
- [ ] Implement SQLite persistence for trust engine
- [ ] Configurable specialist routing (language → tool mapping)
- [ ] Verify: 7 existing tests pass + new integration tests

### Phase 2: Create Subagents + Validate End-to-End

Create Claude Code subagent definitions and validate the full loop from CLI.

- [ ] Write `.claude/agents/worker.md` with system prompt
- [ ] Write `.claude/agents/quality-reviewer.md` with three-lens protocol
- [ ] Write `.claude/agents/kg-librarian.md` with curation protocol
- [ ] Write orchestrator `CLAUDE.md` with task decomposition instructions
- [ ] Write `.claude/settings.json` with lifecycle hooks
- [ ] Start KG + Quality MCP servers
- [ ] Open Claude Code as orchestrator
- [ ] **Validation test**: Orchestrator spawns worker → worker queries KG → worker implements → quality reviewer evaluates → findings flow back → worker fixes → quality gates pass → KG librarian curates → done

**If this works end-to-end without any extension code, the core architecture is validated.**

### Phase 3: Build Extension as Monitoring Layer

Only after Phase 2 proves the loop works:

- [ ] Implement MCP client service (connect to KG + Quality via HTTP)
- [ ] Wire MemoryTreeProvider to real KG data
- [ ] Wire FindingsTreeProvider to real quality data
- [ ] Add filesystem watchers for session state and task briefs
- [ ] Diagnostics integration (findings → VS Code squigglies)
- [ ] Build dashboard webview with real data sources
- [ ] Status bar with aggregated health

### Phase 4: Expand and Harden

- [ ] Event logging via lifecycle hooks (simplified audit trail)
- [ ] Cross-project memory (KG entities that travel between projects)
- [ ] Multi-worker parallelism patterns and best practices
- [ ] FastMCP 3.0 migration when stable
- [ ] Installation script for target projects

---

## 13. What We're Deliberately Not Building (Yet)

| Component | V1 Status | Why We're Skipping It | When to Revisit |
|-----------|-----------|----------------------|-----------------|
| **Communication Hub MCP Server** | Fully scaffolded (6 tests passing) | Claude Code's Task tool + subagent returns handle coordination natively. | If we need persistent cross-session messaging, an audit trail beyond JSONL, or real-time event streaming between independent sessions. |
| **Extension-Driven Session Management** | Fully scaffolded | Claude Code spawns and manages subagents natively via Task tool. | If declarative orchestration (CLAUDE.md + subagent definitions) proves insufficient for complex multi-step workflows. |
| **Custom Agent Registry** | Part of Hub server | The orchestrator knows who it spawned. SubagentStart/SubagentStop hooks track lifecycle. | If we need to query agent state from outside the orchestrator session (e.g., from the extension or from other sessions). |
| **Inter-Agent Message Routing** | Part of Hub server | Orchestrator routes all communication as the natural hub. | If we need peer-to-peer agent communication or asynchronous messaging that doesn't flow through the orchestrator. |
| **Active Extension Orchestration** | Fully scaffolded | Claude Code IS the orchestrator. Extension monitors only. | If we need UI-driven workflow control (human clicking "start review" in the extension rather than typing it in Claude Code). |

The v1 scaffolding for these components is preserved in the codebase (Hub server, extension session management code) and in `docs/v1-full-architecture/`. It can be reactivated if the experiment reveals that native primitives are insufficient.

---

## 14. Verification

### 14.1 Component Verification

| Component | How to Verify |
|-----------|--------------|
| KG server | Create entities at each tier. Attempt to write to a vision-tier entity as "worker" — verify rejection. Search nodes, verify results. Test JSONL persistence (restart server, verify state survives). |
| Quality server | Run `check_all_gates()` against a real codebase. Verify lint findings, test results, coverage numbers match direct tool output. Test trust engine dismissal tracking. |
| Worker subagent | Spawn via Task tool. Verify it reads the task brief, queries KG, implements within scope, runs quality gates. |
| Quality reviewer subagent | Spawn with a diff that contains a vision violation. Verify it catches the violation and returns a structured finding with tier, severity, and project-specific rationale. |
| KG librarian subagent | Spawn after a work session. Verify it consolidates observations, removes stale entries, syncs to archival files. |
| Extension TreeViews | Connect to running MCP servers. Verify TreeView renders correct KG entities, findings, and task briefs. |

### 14.2 Integration Verification (Phase 2 Validation Test)

This is the critical test that validates the platform-native architecture works end-to-end:

**Setup:**
1. Start KG MCP server with pre-populated vision/architecture entities
2. Start Quality MCP server configured for Python (ruff + pytest)
3. Open Claude Code in a project with `.claude/agents/` subagent definitions and `CLAUDE.md`

**Test scenario:**
1. Give the orchestrator a task: "Add input validation to the UserService"
2. Orchestrator writes a task brief
3. Orchestrator creates a worktree and spawns a worker subagent
4. Worker queries KG, discovers the `protocol_based_di_pattern` governing UserService
5. Worker implements validation following the pattern
6. Orchestrator spawns quality reviewer with worker's diff
7. Quality reviewer runs three-lens review:
   - Vision: no conflicts
   - Architecture: confirms pattern adherence
   - Quality: runs lint + tests via Quality server
8. If findings exist, orchestrator routes them to worker, worker fixes, reviewer re-verifies
9. When clean: orchestrator merges, cleans worktree, updates session state
10. Orchestrator spawns KG librarian to curate observations

**Expected outcome**: The entire workflow completes using only Claude Code native primitives + two MCP servers. No extension code involved. No Hub server involved.

### 14.3 End-to-End Verification (Full System)

After Phase 3, the full system includes the extension:

1. All Phase 2 verification steps pass
2. Extension connects to KG and Quality servers
3. Memory Browser shows pre-populated entities with correct tier grouping
4. When quality reviewer returns findings, they appear in the Findings panel
5. Findings map to VS Code diagnostics (red/yellow/blue squigglies)
6. Task briefs created by the orchestrator appear in the Tasks panel
7. Session state changes reflect in the dashboard
8. Status bar shows correct health indicator

---

*This architecture document specifies how to build the system described in `COLLABORATIVE_INTELLIGENCE_VISION.md`. The vision doc governs principles and priorities. This doc governs implementation. When in doubt, the vision doc's principles take precedence. The v1 full-infrastructure architecture is preserved in `docs/v1-full-architecture/` and may be revisited as we learn from this platform-native approach.*
