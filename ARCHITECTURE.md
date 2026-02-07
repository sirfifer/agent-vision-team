# ARCHITECTURE.md v2 — Agent Vision Team

This document is the authoritative architecture reference for the Agent Vision Team Collaborative Intelligence System. It describes the system as built: a Claude Code-based orchestration platform coordinating 6 custom subagents across 3 MCP servers, with transactional governance review, persistent institutional memory, deterministic quality verification, and a VS Code extension providing setup, monitoring, and management capabilities.

The system's orchestration infrastructure runs on the developer's machine: MCP servers communicate over stdio transport (spawned by Claude Code as child processes), and all persistent state (Knowledge Graph, governance database, trust engine) lives in the project directory. AI inference is cloud-based, handled by Anthropic's Claude models via Claude Code. Claude Code Max provides model access through a subscription (no API keys to manage), but an internet connection is required for all agent operations.


## Table of Contents

1. [System Boundaries and Glossary](#1-system-boundaries-and-glossary)
2. [System Overview](#2-system-overview)
3. [Claude Code as Orchestration Platform](#3-claude-code-as-orchestration-platform)
4. [Knowledge Graph MCP Server (Port 3101)](#4-knowledge-graph-mcp-server-port-3101)
5. [Quality MCP Server (Port 3102)](#5-quality-mcp-server-port-3102)
6. [Governance MCP Server (Port 3103)](#6-governance-mcp-server-port-3103)
7. [Custom Subagent Definitions](#7-custom-subagent-definitions)
8. [Governance Architecture](#8-governance-architecture)
9. [CLAUDE.md Orchestration](#9-claudemd-orchestration)
10. [VS Code Extension](#10-vs-code-extension)
11. [File System Layout](#11-file-system-layout)
12. [Data Flow Architecture](#12-data-flow-architecture)
13. [E2E Testing Architecture](#13-e2e-testing-architecture)
14. [Research System](#14-research-system)
15. [Project Rules System](#15-project-rules-system)
16. [Technology Stack](#16-technology-stack)
17. [Current Status and Evolution Path](#17-current-status-and-evolution-path)
18. [Verification](#18-verification)

---

## 1. System Boundaries and Glossary

### 1.1 In Scope

| Component | Description |
|-----------|-------------|
| **Knowledge Graph MCP Server** | Persistent institutional memory with tier-based access control (port 3101, 11 tools) |
| **Quality MCP Server** | Deterministic quality verification with trust engine (port 3102, 8 tools) |
| **Governance MCP Server** | Transactional review checkpoints and governed task lifecycle (port 3103, 10 tools) |
| **6 Custom Subagents** | Worker, Quality Reviewer, KG Librarian, Governance Reviewer, Researcher, Project Steward |
| **Governance Architecture** | PostToolUse hook on TaskCreate (core enforcement), governed tasks (blocked-from-birth), transactional decision review, multi-blocker support, AI-powered review via `claude --print` |
| **Three-Tier Protection Hierarchy** | Vision > Architecture > Quality — lower tiers cannot modify higher tiers |
| **Project Rules System** | Behavioral guidelines (enforce/prefer) injected into agent prompts from `.avt/project-config.json` |
| **E2E Testing Harness** | 14 scenarios, 292+ structural assertions, parallel execution with full isolation |
| **VS Code Extension** | Setup wizard (9 steps), workflow tutorial (10 steps), governance panel, document editor, research prompts panel, 3 MCP clients |
| **CLAUDE.md Orchestration Protocol** | Orchestrator instructions defining task decomposition, governance checkpoints, quality review, memory curation |
| **Research System** | Research prompts, researcher agent (dual-mode), research briefs |
| **Session Management** | Checkpoints via git tags, session state in `.avt/session-state.md`, worktree isolation |

### 1.2 Out of Scope

| Exclusion | Rationale |
|-----------|-----------|
| External CI/CD pipelines | All quality gates run locally via MCP servers |
| External cloud services (beyond Claude) | AI inference uses Anthropic's cloud via Claude Code Max; no additional cloud services |
| API key management | No API keys required (Claude Code Max subscription model) |
| External authentication | No multi-user system; single developer workflow |
| External frameworks or runtimes | MCP servers use Python/uv; extension uses Node/TypeScript — no additional frameworks |
| Production deployment | This is a development-time system, not a deployed service |

### 1.3 Glossary

| Term | Definition |
|------|------------|
| **Orchestrator** | The primary Claude Code session (Opus 4.6) that decomposes tasks, spawns subagents, and coordinates work. Defined by `CLAUDE.md`. |
| **Subagent** | A specialized Claude Code agent spawned via the Task tool, with a scoped system prompt from `.claude/agents/`. |
| **Worker** | Subagent (Opus 4.6, 9 tools) that implements scoped tasks within governance constraints. |
| **Quality Reviewer** | Subagent (Opus 4.6, 6 tools) that evaluates work through three ordered lenses: vision, architecture, quality. |
| **KG Librarian** | Subagent (Sonnet 4.5, 5 tools) that curates institutional memory — consolidates, promotes patterns, syncs archival files. |
| **Governance Reviewer** | Subagent (Sonnet 4.5, 4 tools) that evaluates decisions and plans for vision/architecture alignment. **Not spawned by the orchestrator** — called internally by the Governance Server via `claude --print`. |
| **Researcher** | Subagent (Opus 4.6, 7 tools) that gathers intelligence in two modes: periodic/maintenance monitoring and exploratory/design research. |
| **Project Steward** | Subagent (Sonnet 4.5, 7 tools) that maintains project hygiene: naming conventions, organization, documentation completeness, cruft detection. |
| **MCP Server** | Model Context Protocol server providing tools to Claude Code sessions. Spawned as child processes via stdio transport. |
| **Knowledge Graph (KG)** | Entity-relation graph stored in `.avt/knowledge-graph.jsonl`. Contains vision standards, architectural patterns, components, observations. |
| **Protection Tier** | Access control level on KG entities: **vision** (human-only modification), **architecture** (human or orchestrator with approval), **quality** (any agent). |
| **Finding** | A quality or conformance issue detected by a reviewer or quality gate. Classified by the trust engine as BLOCK, INVESTIGATE, or TRACK. |
| **Governed Task** | A task pair created atomically: a review task (pending) that blocks an implementation task. The implementation task cannot execute until all review blockers are completed with "approved" verdicts. |
| **Task Brief** | A scoped work definition stored in `.avt/task-briefs/`. Contains objective, scope, constraints, and references to research briefs or KG entities. |
| **Project Rules** | Behavioral guidelines in `.avt/project-config.json` with enforcement levels (`enforce` = non-negotiable, `prefer` = explain if deviating). Injected into agent prompts at spawn time. |
| **Research Prompt** | A structured research request defining topic, mode (periodic/exploratory), scope, model hint, and output format. Stored in `.avt/research-prompts/`. |
| **Research Brief** | The output of exploratory research — options evaluated, tradeoff analysis, recommendations. Stored in `.avt/research-briefs/` and referenced by task briefs. |
| **Governance Server** | MCP server (port 3103, 10 tools) providing transactional decision review, plan review, completion review, and governed task lifecycle management. |
| **Quality Gate** | A deterministic check that must pass before work is accepted: build, lint, test, coverage, findings. Run via `check_all_gates()` on the Quality server. |
| **Trust Engine** | Classification system within the Quality server that assigns findings a trust level (BLOCK, INVESTIGATE, TRACK) and maintains an audit trail for dismissals. |
| **Verdict** | The outcome of a governance review: `approved` (proceed), `blocked` (stop and revise), or `needs_human_review` (escalate). |
| **Decision Category** | Classification for governance decisions: `pattern_choice`, `component_design`, `api_design`, `deviation`, `scope_change`. |
| **Checkpoint** | A git tag (`checkpoint-NNN`) marking a recovery point after a meaningful unit of work. |

---

## 2. System Overview

### 2.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              HUMAN                                      │
│                         (Developer / Lead)                               │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ Directs
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRIMARY SESSION (Opus 4.6)                            │
│                         ORCHESTRATOR                                     │
│                                                                         │
│  Governed by: CLAUDE.md                                                 │
│  Capabilities: Task decomposition, subagent spawning,                   │
│                governance coordination, quality enforcement              │
│  Context: 1M tokens (beta)                                              │
└────┬──────┬──────┬──────┬──────┬──────┬─────────────────────────────────┘
     │      │      │      │      │      │
     │      │      │      │      │      │  Spawns via Task tool
     ▼      ▼      ▼      ▼      ▼      ▼
┌────────┐┌────────┐┌────────┐       ┌────────┐┌────────┐
│Worker  ││Quality ││  KG    │       │Research││Project │
│(Opus   ││Reviewer││Librar- │       │  -er   ││Steward │
│4.6)    ││(Opus   ││ian     │       │(Opus   ││(Sonnet │
│9 tools ││4.6)    ││(Sonnet │       │4.6)    ││4.5)    │
│        ││6 tools ││4.5)    │       │7 tools ││7 tools │
│        ││        ││5 tools │       │        ││        │
└───┬────┘└───┬────┘└───┬────┘       └───┬────┘└───┬────┘
    │         │         │                │         │
    │         │         │                │         │
    ▼         ▼         ▼                ▼         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MCP SERVER LAYER                                 │
│                                                                         │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐ │
│  │ Knowledge Graph   │ │ Quality          │ │ Governance               │ │
│  │ :3101 (11 tools)  │ │ :3102 (8 tools)  │ │ :3103 (10 tools)        │ │
│  │                   │ │                  │ │                          │ │
│  │ Entities, rels,   │ │ Format, lint,    │ │ Decisions, plans,        │ │
│  │ observations,     │ │ test, coverage,  │ │ governed tasks,          │ │
│  │ tier protection,  │ │ gates, trust     │ │ reviews, verdicts        │ │
│  │ search, ingest    │ │ engine           │ │                          │ │
│  └────────┬─────────┘ └────────┬─────────┘ └──────┬───────────────────┘ │
│           │                    │                   │                     │
└───────────┼────────────────────┼───────────────────┼─────────────────────┘
            │                    │                   │
            ▼                    ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       PERSISTENT STATE                                   │
│                                                                         │
│  .avt/                                                                  │
│  ├── knowledge-graph.jsonl      # KG entity/relation persistence        │
│  ├── trust-engine.db            # Quality finding audit trails           │
│  ├── governance.db              # Decision store with verdicts           │
│  ├── session-state.md           # Current session progress               │
│  ├── task-briefs/               # Worker assignments                     │
│  ├── memory/                                                             │
│  │   ├── architectural-decisions.md                                      │
│  │   ├── troubleshooting-log.md                                          │
│  │   ├── solution-patterns.md                                            │
│  │   └── research-findings.md                                            │
│  ├── research-prompts/          # Research prompt definitions             │
│  ├── research-briefs/           # Research output briefs                  │
│  └── project-config.json        # Project configuration                  │
│                                                                          │
│  ~/.claude/tasks/<list-id>/     # Claude Code native task files          │
│  └── *.json (task files)                                                 │
│                                                                          │
│  Git (worktrees, tags, branches)                                         │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────┐
                    │  GOVERNANCE REVIEWER             │
                    │  (Sonnet 4.5)                    │
                    │  4 tools | NOT spawned by         │
                    │  orchestrator — called internally │
                    │  by Governance Server via         │
                    │  `claude --print`                 │
                    └──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      VS CODE EXTENSION                                   │
│                                                                         │
│  Setup Wizard (9 steps)  │ Workflow Tutorial (10 steps)                 │
│  Governance Panel        │ Research Prompts Panel                       │
│  Document Editor         │ VS Code Walkthrough (6 steps)               │
│  Agent Cards / Activity  │ Settings Panel                              │
│                                                                         │
│  3 MCP Clients: KnowledgeGraphClient, QualityClient, GovernanceClient  │
│  4 Tree Providers + Actions view: Memory, Findings, Tasks, Actions     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 The Governance Reviewer: A Special Case

The Governance Reviewer differs from all other subagents in a fundamental way:

- **Other subagents**: Spawned by the orchestrator via the Task tool. They run as interactive sessions with full tool access.
- **Governance Reviewer**: Called internally by the Governance Server's `reviewer.py` via `claude --print --agent governance-reviewer`. It receives a structured prompt (decision or plan + standards), produces a JSON verdict, and exits. It is a **synchronous, non-interactive subprocess** of the Governance Server, not an orchestrator-managed agent.

This design makes governance review **transactional** — an agent calls `submit_decision()`, the Governance Server invokes the reviewer internally, and the verdict is returned in the same tool call. No orchestrator coordination needed.

### 2.3 Component Interaction Summary

This table shows which MCP servers each component interacts with and the nature of the interaction.

| Component | KG Server | Quality Server | Governance Server | Primary Role |
|-----------|-----------|----------------|-------------------|--------------|
| **Orchestrator** | Read (context loading) | -- | Read (status) | Decompose tasks, spawn subagents, coordinate |
| **Worker** | Read/Write (observations) | Run gates | Submit decisions, plans, completion reviews; create governed tasks | Implement scoped tasks |
| **Quality Reviewer** | Read (standards, patterns) | Run gates, lint, coverage | -- | Evaluate work through 3 lenses |
| **KG Librarian** | Read/Write (curate) | -- | -- | Consolidate, promote, sync memory |
| **Governance Reviewer** | Read (standards) | -- | -- (called BY the server) | Evaluate decisions/plans for alignment |
| **Researcher** | Read/Write (findings) | -- | Submit research decisions | Gather intelligence, produce briefs |
| **Project Steward** | Read/Write (conventions) | -- | -- | Maintain project hygiene |
| **Governance Server (internal)** | Read (standards via JSONL) | -- | N/A (is the server) | Store decisions, invoke reviewer, manage task pairs |
| **VS Code Extension** | Read (3 MCP clients) | Read | Read | Setup wizard, monitoring, management |

### 2.4 Deployment Topology

```
Developer Machine (macOS / Linux)
│
├── Claude Code (binary)
│   ├── Primary session (orchestrator, Opus 4.6)
│   └── Subagent sessions (spawned via Task tool)
│       ├── Workers (Opus 4.6)
│       ├── Quality Reviewer (Opus 4.6)
│       ├── KG Librarian (Sonnet 4.5)
│       ├── Researcher (Opus 4.6)
│       └── Project Steward (Sonnet 4.5)
│
├── MCP Servers (spawned as child processes via stdio)
│   ├── collab-kg (Python/uv)        ← knowledge-graph.jsonl
│   ├── collab-quality (Python/uv)   ← trust-engine.db
│   └── collab-governance (Python/uv) ← governance.db
│
├── VS Code Extension
│   ├── Extension backend (Node.js)
│   └── Webview dashboard (React/Vite)
│
└── Project directory
    ├── .claude/          ← Agent definitions, settings, collab state
    ├── .avt/             ← System config, task briefs, memory, research
    ├── e2e/              ← E2E testing harness
    ├── mcp-servers/      ← Server source code
    ├── extension/        ← VS Code extension source
    └── scripts/hooks/    ← Lifecycle hooks
```

**Key properties**:
- **Local orchestration, cloud inference**: MCP servers and persistent state are local. AI inference is cloud-based via Anthropic's Claude models through Claude Code Max (subscription, no API keys).
- **Stdio transport**: MCP servers are spawned as child processes by Claude Code, not network listeners. Port numbers in this document are logical identifiers for documentation, not TCP ports.
- **Single-user**: Designed for one developer per project directory. Multi-user coordination is out of scope.

---

## 3. Claude Code as Orchestration Platform

Claude Code is not a tool the system uses — it IS the orchestration platform. The system leverages Claude Code's native capabilities (subagents, Task tool, MCP integration, hooks, skills) and extends them with governance policy, institutional memory, and quality verification.

### 3.1 Custom Subagents

Six custom subagent definitions live in `.claude/agents/`:

```
.claude/agents/
├── worker.md                # Opus 4.6  | 9 tools | KG + Quality + Governance
├── quality-reviewer.md      # Opus 4.6  | 6 tools | KG + Quality
├── kg-librarian.md          # Sonnet 4.5 | 5 tools | KG
├── governance-reviewer.md   # Sonnet 4.5 | 4 tools | KG (called via claude --print)
├── researcher.md            # Opus 4.6  | 7 tools | KG + Governance + WebSearch + WebFetch
└── project-steward.md       # Sonnet 4.5 | 7 tools | KG + Write + Edit + Bash
```

Each definition contains:
- **YAML frontmatter**: Model selection and tool allowlist
- **System prompt**: Role description, protocols, constraints
- **Startup protocol**: KG queries to run before beginning work
- **Output format**: Structured response expected by the orchestrator

Model routing is configured in `.claude/settings.json`:

```json
{
  "agents": {
    "defaultModel": "sonnet",
    "worker": {
      "model": "opus",
      "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep",
                "mcp:collab-kg", "mcp:collab-quality", "mcp:collab-governance"]
    },
    "quality-reviewer": {
      "model": "opus",
      "tools": ["Read", "Glob", "Grep", "Bash", "mcp:collab-kg", "mcp:collab-quality"]
    },
    "kg-librarian": {
      "model": "sonnet",
      "tools": ["Read", "Write", "Glob", "Grep", "mcp:collab-kg"]
    },
    "governance-reviewer": {
      "model": "sonnet",
      "tools": ["Read", "Glob", "Grep", "mcp:collab-kg"]
    }
  }
}
```

Note: The `researcher` and `project-steward` agents define their tools in YAML frontmatter within their `.md` files. They are not duplicated in `settings.json` because the frontmatter definition is authoritative.

### 3.2 Task Tool Patterns

The orchestrator uses Claude Code's Task tool to spawn subagents. Three primary patterns:

#### Sequential Pattern

Used when tasks have dependencies:

```
Orchestrator
  └─ Task: Worker A (implement foundation)
       └─ completes
            └─ Task: Worker B (implement feature using A's output)
                 └─ completes
                      └─ Task: Quality Reviewer (review both)
```

#### Parallel Pattern

Used for independent work units:

```
Orchestrator
  ├─ Task: Worker A (implement service)     ← git worktree A
  ├─ Task: Worker B (implement other service) ← git worktree B
  └─ Task: Researcher (investigate dependency) ← read-only
       │
       ▼ (all complete)
  └─ Task: Quality Reviewer (review all work)
```

#### Governance-Gated Pattern

Used for all implementation work. This is the primary workflow. Tasks are automatically governed by the PostToolUse hook on `TaskCreate` (Section 3.3):

```
1. Orchestrator creates a task via TaskCreate or create_governed_task()
   │
   │  If TaskCreate: PostToolUse hook fires automatically
   │  If create_governed_task(): MCP server handles governance directly
   │
   │  Either way, the result is the same:
   │
   ├─→ Review Task (review-abc123)       Implementation Task (1.json)
   │   status: pending                    status: pending
   │   blocks: [1]                        blockedBy: [review-abc123]
   │                                      CANNOT EXECUTE
   │
2. Governance review runs (async, queued by the hook)
   │  (Governance Server invokes governance-reviewer via claude --print)
   │  Loads vision standards from KG, checks alignment, produces verdict
   │
3. On approval: complete_task_review(review-abc123, verdict="approved")
   │  Removes review-abc123 from implementation task's blockedBy
   │  Implementation task now executable
   │
4. Orchestrator spawns Worker with the task
   │
   Worker lifecycle:
   │  a. Check get_task_review_status() -- confirm unblocked
   │  b. Read task brief, query KG for context
   │  c. For each key decision: submit_decision() -- blocks until verdict
   │     - pattern_choice, component_design, api_design: standard review
   │     - deviation, scope_change: auto-flagged as needs_human_review
   │  d. Implement within scope
   │  e. submit_plan_for_review() before presenting plan
   │  f. check_all_gates() via Quality server
   │  g. submit_completion_review() before reporting done
   │
5. Orchestrator spawns Quality Reviewer with worker's diff
   │
6. Findings routed back to Worker if needed
   │
7. Orchestrator spawns KG Librarian to curate memory
```

If a governance review identifies the need for additional scrutiny:

```
add_review_blocker(implementation_task_id, "security", "Auth handling requires security review")
   │
   ├─→ New Review Task (review-security-def456)
   │   blocks: [implementation_task_id]
   │
   └─→ Implementation task blockedBy: [review-abc123, review-security-def456]
       BOTH must complete with "approved" before task can execute
```

### 3.3 Lifecycle Hooks

Hooks are configured in `.claude/settings.json` and execute shell scripts at specific points in the Claude Code lifecycle. Hooks are the **primary enforcement mechanism** for governance in this system, not a secondary safety net.

#### Current Hooks

| Hook Type | Matcher | Script | Purpose |
|-----------|---------|--------|---------|
| `PostToolUse` | `TaskCreate` | `scripts/hooks/governance-task-intercept.py` | **Core enforcement**: intercepts every task creation and pairs it with a governance review blocker |
| `PreToolUse` | `ExitPlanMode` | `scripts/hooks/verify-governance-review.sh` | Safety net: blocks plan presentation if `submit_plan_for_review` was not called |

#### PostToolUse Hook on TaskCreate (Core Enforcement)

This is the **architectural cornerstone** of the governance system. Every call to `TaskCreate`, by any agent at any level of the hierarchy, is intercepted by this hook. The hook creates a governance review task that blocks the implementation task from execution. This is how the "blocked from birth" invariant is enforced structurally, not by convention or documentation.

**How it works:**

```
Agent calls TaskCreate("Implement auth service")
    |
    v
Claude Code creates task file (1.json) in ~/.claude/tasks/<list-id>/
    |
    v
PostToolUse hook fires -> governance-task-intercept.py
    |
    v
Hook discovers the new task's ID by scanning the task directory
    |
    v
Hook creates review-{uuid}.json with blocks: ["1"]
Hook adds blockedBy: ["review-{uuid}"] to 1.json
Hook stores governance records in .avt/governance.db
Hook queues async AI review via _run-governance-review.sh
    |
    v
Hook returns additionalContext to Claude:
    "GOVERNANCE: Task 'Implement auth service' has been automatically
     paired with governance review review-abc123."
    |
    v
Agent receives the context and continues working
```

**Why this approach is essential:**

- **100% interception**: The hook fires on every `TaskCreate` call, regardless of which agent made it or whether the agent followed governance instructions. There is no way to create an ungoverned task.
- **Subagent inheritance**: Subagents spawned via the Task tool inherit PostToolUse hooks from the parent session. This has been empirically verified: a subagent's `TaskCreate` calls fire the same hook as the parent's. Full coverage across the entire agent hierarchy is guaranteed.
- **No protocol dependency**: Unlike the MCP-based `create_governed_task()` approach (which requires agents to call the right tool), the hook works even if an agent uses native `TaskCreate` directly. Governance is enforced by the platform, not by agent compliance.
- **Transparent to agents**: Agents use `TaskCreate` normally. They do not need special instructions or awareness of governance. The hook adds governance transparently.

**Key discovery: `TaskCreate` returns an empty `tool_result`**. The hook cannot extract the task ID from the tool's return value. Instead, it discovers the task by scanning the task directory for a subject match immediately after creation (`_discover_task_id()`). This is reliable because the hook fires synchronously after the task file is written.

**Environment requirements** (both must be set):

```bash
export CLAUDE_CODE_ENABLE_TASKS="true"      # Enables TaskCreate (replaces legacy TodoWrite)
export CLAUDE_CODE_TASK_LIST_ID="<name>"     # Enables cross-session persistence
```

Without `CLAUDE_CODE_ENABLE_TASKS="true"`, the native task tools (`TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet`) are not available. Claude Code falls back to the legacy `TodoWrite` tool, which is in-memory only, has no dependency tracking, and cannot be hooked for governance. Setting this variable replaces `TodoWrite` entirely with the native task system.

**Verified in live testing** (2026-02-07):
- Level 1 (mock review): 12/12 tasks intercepted, 100% rate
- Level 2 (real AI review): 10/10 tasks intercepted, reviews approved/blocked correctly
- Level 3 (subagent delegation): 13/13 tasks intercepted (10 main + 3 subagent)
- E2E: 13 scenarios, 221 assertions, no regression

#### ExitPlanMode Hook (Safety Net)

This hook is the **safety net** for plan review, not the primary governance mechanism. The primary plan review enforcement is the worker protocol itself; this hook catches cases where an agent skips or forgets the governance checkpoint.

```bash
# scripts/hooks/verify-governance-review.sh
# Checks governance SQLite DB for plan review records.
# Exit 0 = allow (review found or DB unavailable)
# Exit 2 = block with feedback JSON (no review found)
```

The hook blocks `ExitPlanMode` if no plan review records exist in the governance database. If the database does not exist (server not running), the hook allows the action to avoid blocking development when governance is intentionally disabled.

### 3.4 Worktree Management

For parallel worker isolation, the orchestrator creates git worktrees:

```bash
# Create isolated worktree for a task
git worktree add ../project-worker-1 -b task/001-add-auth
git worktree add ../project-worker-2 -b task/002-add-logging

# Workers operate in their worktrees
# On completion: merge back, clean up
git merge task/001-add-auth
git worktree remove ../project-worker-1
git branch -d task/001-add-auth
```

**Key properties**:
- Each worktree is a full working copy with its own branch
- Workers cannot interfere with each other's files
- MCP servers share state (KG, governance DB) across worktrees — this is intentional for governance consistency
- Worktrees are ephemeral; they are created per-task and removed after merge

### 3.5 Session Persistence

The system maintains continuity across sessions through multiple mechanisms:

| Mechanism | What Persists | Location |
|-----------|--------------|----------|
| Knowledge Graph | Entities, relations, observations, tier metadata | `.avt/knowledge-graph.jsonl` |
| Trust Engine | Finding records, dismissals, audit trail | `.avt/trust-engine.db` |
| Governance DB | Decisions, verdicts, review history | `.avt/governance.db` |
| Task List | Task states, blockers, DAG dependencies | `~/.claude/tasks/<list-id>/*.json` |
| Session State | Current progress, active tasks, checkpoint info | `.avt/session-state.md` |
| Archival Memory | Curated decisions, troubleshooting, patterns, research | `.avt/memory/*.md` |
| Git | Checkpoints (tags), branches, worktrees, commit history | `.git/` |

**Cross-session task sharing** is enabled via:

```bash
export CLAUDE_CODE_TASK_LIST_ID="agent-vision-team"
```

This causes all Claude Code sessions (orchestrator and subagents) to read/write task files from `~/.claude/tasks/agent-vision-team/`, enabling:
- Subagents to see governed task state
- Task blockers to persist across session restarts
- Multiple sessions to coordinate via the shared task list

### 3.6 Platform Features

The system leverages (or plans to leverage) these Claude Code capabilities:

#### Native Task List (ACTIVE)

Claude Code's native Task List provides the infrastructure layer for governed tasks:

- **DAG dependencies**: Tasks can block other tasks; blocked tasks auto-unblock when dependencies complete
- **File locking**: `fcntl.LOCK_EX` prevents race conditions when multiple agents claim tasks
- **Cross-session persistence**: Tasks stored as JSON files in `~/.claude/tasks/<list-id>/`
- **Terminal display**: Toggle with `Ctrl+T`, shows up to 10 tasks with status indicators

**Relationship to Governance**: Task List is the infrastructure layer; Governance is the policy layer.

```
Task List (infrastructure)          Governance (policy)
─────────────────────────           ────────────────────
DAG dependencies                    Whether a task should proceed
File locking                        What reviews are required
Cross-session persistence           What standards apply
Automatic unblocking                Verdict logic (approved/blocked/needs_human_review)
```

The system's `task_integration.py` (in `mcp-servers/governance/collab_governance/`) manipulates Claude Code's native task files directly. `create_governed_task_pair()` writes JSON task files with `blockedBy` arrays. `release_task()` removes blockers from those files. The Task List handles persistence and locking; Governance handles review policy.

#### MCP Tool Search (CONFIGURATION-ONLY)

When MCP tools exceed 10% of the context window, Claude Code auto lazy-loads only the 3-5 most relevant tools per task — an 85% reduction in MCP tool context overhead.

- **Enable**: `ENABLE_TOOL_SEARCH=auto:5` or rely on automatic activation
- **Requires**: Sonnet 4+ or Opus 4+
- **Impact**: Significant for this system (29 tools across 3 servers)

#### Effort Controls (OPPORTUNITY)

Four levels: `low`, `medium`, `high`, `max`. Adjustable per-agent to optimize cost and latency.

Recommended mapping:

| Agent | Effort | Rationale |
|-------|--------|-----------|
| Worker | `max` | Implementation requires thoroughness |
| Quality Reviewer | `high` | Review benefits from depth but is bounded |
| KG Librarian | `medium` | Curation is structured and repetitive |
| Governance Reviewer | `medium` | Review is structured with clear criteria |
| Researcher | `high` | Research requires depth and breadth |
| Project Steward | `low` | Hygiene checks are mechanical |

#### Context Compaction (AUTOMATIC)

Beta feature that auto-summarizes older context for long-running sessions. Active by default with Opus 4.6. Particularly beneficial for the orchestrator, which may coordinate many subagents in a single session.

#### 1M Context Window (AUTOMATIC)

Available with Opus 4.6 (beta). Enables:
- Extended code reviews spanning more files
- Longer orchestrator sessions without context overflow
- Larger research contexts for the researcher agent

#### Agent Teams (MONITORING ONLY)

Experimental Claude Code feature providing native multi-agent coordination:
- **Delegate mode**: Restricts lead to coordination-only tools (maps to our orchestrator pattern)
- **Shared task list**: Teammates share tasks via DAG (maps to our governed tasks)
- **Plan approval**: Lead approves/rejects teammate plans (maps to our governance review)
- **Peer messaging**: Teammates message each other directly (not available in current subagent model)

**Status**: Experimental with significant limitations (no session resumption with in-process teammates, one team per session, no nested teams).

**Assessment**: Aligns conceptually with our orchestration model. When stable, may replace custom subagent coordination while governance remains the policy layer. Potential future use: worker swarm teams for parallelizable implementation work. The system's governance guarantees (blocked-from-birth, multi-blocker, transactional review) are not provided by Agent Teams — governance remains essential regardless of coordination mechanism.

#### Plugins and Marketplaces (PLANNED FOR LATER)

Claude Code supports bundling skills, hooks, subagents, and MCP servers into distributable plugins with `/<plugin-name>:<skill>` namespacing.

**Natural plugin boundaries in this system**:
- 3 MCP servers (Python packages)
- 6 agent definitions (markdown files)
- Skills (`/e2e`) and commands (`/project-overview`)
- Lifecycle hooks (governance review verification)
- VS Code extension (separate distribution channel)

**Status**: APIs still maturing (Quality server has partial stubs, governance protocol may evolve). Document as a milestone in the system's evolution path. Packaging should wait until the system's interfaces stabilize.

#### Skills (ACTIVE)

Skills (`.claude/skills/`) and commands (`.claude/commands/`) are unified — both create `/<name>` invocations. Skills take precedence if both exist for the same name.

**Current skills and commands**:

| Name | Type | Purpose |
|------|------|---------|
| `/e2e` | Skill | Run E2E testing harness |
| `/project-overview` | Command | Display project context summary |

Skills are **model-invocable** by default — Claude auto-loads them based on task relevance, reducing manual invocation overhead. Common orchestrator workflows are candidates for conversion to auto-loaded skills.

#### Setup Hooks (OPPORTUNITY)

`--init` and `--maintenance` flags trigger project initialization automation:
- `--init`: First-time project setup (install dependencies, configure MCP servers, run setup wizard)
- `--maintenance`: Periodic maintenance (update dependencies, run steward review, refresh research)

These can be connected to scripts that automate onboarding and upkeep.

## 4. Knowledge Graph MCP Server (Port 3101)

**Purpose**: Persistent institutional memory with tier-aware protection. Stores entities (components, patterns, decisions, problems, vision standards), relations, and observations. All sessions and agents share the same graph. The KG is the system's single source of truth for what the project believes, what it has decided, and what it has learned.

**Transport**: SSE on port 3101 (FastMCP)

**Storage**: JSONL file at `.avt/knowledge-graph.jsonl`. Each line is a self-contained JSON record (entity or relation). The server loads the full file into memory on startup and appends new records on writes. Periodic compaction rewrites the file with only current state, discarding deleted entities and stale entries.

### 4.1 Tool Interface (11 tools)

```
create_entities(
  entities: list[dict]           # [{name, entityType, observations}]
                                 # entityType: "component" | "vision_standard" | "architectural_standard"
                                 #             | "pattern" | "problem" | "solution_pattern"
                                 # observations: include "protection_tier: <tier>" for tier-protected entities
) -> { created: int }

create_relations(
  relations: list[dict]          # [{from, to, relationType}]
                                 # relationType: "depends_on" | "follows_pattern" | "governed_by"
                                 #               | "fixed_by" | "exemplified_by" | "rejected_in_favor_of"
) -> { created: int }

add_observations(
  entity_name: str,
  observations: list[str],
  caller_role: str = "agent",    # "human" | "orchestrator" | "worker" | "agent" | "quality"
  change_approved: bool = False  # Required true for architecture-tier writes by non-humans
) -> { added: int }
  | { added: 0, error: str }
  # REJECTS if entity has protection_tier: vision and caller is not "human"
  # REJECTS if entity has protection_tier: architecture and change_approved is false
  #   and caller is not "human"

search_nodes(
  query: str                     # Substring match against entity names and observations
                                 # (case-insensitive)
) -> list[EntityWithRelations]

get_entity(
  name: str                      # Exact entity name
) -> EntityWithRelations
  | { error: "Entity '<name>' not found." }

get_entities_by_tier(
  tier: str                      # "vision" | "architecture" | "quality"
) -> list[EntityWithRelations]

delete_observations(
  entity_name: str,
  observations: list[str],       # Exact strings to remove
  caller_role: str = "agent",
  change_approved: bool = False
) -> { deleted: int }
  | { deleted: 0, error: str }
  # Same tier protection as add_observations

delete_entity(
  entity_name: str,
  caller_role: str = "agent"
) -> { deleted: bool }
  | { deleted: false, error: str }
  # REJECTS if entity has protection_tier: vision or architecture and caller is not "human"
  # Also removes all relations involving the deleted entity

delete_relations(
  relations: list[dict]          # [{from, to, relationType}] -- exact match required
) -> { deleted: int }

ingest_documents(
  folder: str,                   # Path to folder containing .md files
                                 # Defaults to "docs/vision/" or "docs/architecture/" based on tier
  tier: str                      # "vision" | "architecture"
) -> { ingested: int, entities: list[str], errors: list[str], skipped: list[str] }
  # Parses markdown files: extracts H1 title, Statement, Description, Rationale, Usage, Examples
  # Converts titles to snake_case entity names
  # Sets protection_tier observation automatically
  # Supports re-ingestion: deletes existing entities with same name before creating
  #   (uses caller_role="human")

validate_tier_access(
  entity_name: str,
  operation: str,                # "read" | "write" | "delete"
  caller_role: str               # "human" | "orchestrator" | "worker" | "agent"
) -> { allowed: bool, reason?: str }
  # Read operations always return allowed: true
  # Write/delete operations check tier protection via get_entity_tier + validate_write_access
```

### 4.2 Data Models

```python
class ProtectionTier(str, Enum):
    VISION = "vision"
    ARCHITECTURE = "architecture"
    QUALITY = "quality"

class Mutability(str, Enum):
    HUMAN_ONLY = "human_only"
    HUMAN_APPROVED_ONLY = "human_approved_only"
    AUTOMATED = "automated"

class EntityType(str, Enum):
    COMPONENT = "component"
    VISION_STANDARD = "vision_standard"
    ARCHITECTURAL_STANDARD = "architectural_standard"
    PATTERN = "pattern"
    PROBLEM = "problem"
    SOLUTION_PATTERN = "solution_pattern"

class Relation(BaseModel):
    from_entity: str              # Serialized as "from" in JSON (Field alias)
    to: str
    relation_type: str            # Serialized as "relationType" in JSON (Field alias)

class Entity(BaseModel):
    name: str
    entity_type: EntityType       # Serialized as "entityType" in JSON (Field alias)
    observations: list[str]

class EntityWithRelations(Entity):
    relations: list[Relation]     # All relations where this entity is "from" or "to"
```

### 4.3 Tier Protection Enforcement

The server enforces tier protection at the tool level, not by convention. A misbehaving subagent cannot accidentally corrupt vision-tier data.

Protection tier is determined by scanning the entity's observations for a `"protection_tier: <tier>"` string. If no such observation exists, the entity is unprotected and freely writable.

| Entity Tier | Read | Write (add/delete observations) | Delete Entity |
|-------------|------|--------------------------------|---------------|
| `vision` | All callers | Human only | Human only |
| `architecture` | All callers | Human, or agent with `change_approved: true` | Human only |
| `quality` | All callers | All callers | All callers |
| *(untiered)* | All callers | All callers | All callers |

### 4.4 JSONL Persistence Format

Each line in the JSONL file is one of two record types:

**Entity record**:
```json
{"type": "entity", "name": "hands_free_first_design", "entityType": "vision_standard", "observations": ["protection_tier: vision", "statement: Voice is PRIMARY interaction mode"]}
```

**Relation record**:
```json
{"type": "relation", "from": "KBOralSessionView", "to": "hands_free_first_design", "relationType": "governed_by"}
```

**Write strategy**: New entities and relations are appended. Mutations (add/delete observations, delete entity) trigger a full compaction: the entire in-memory graph is rewritten to a `.jsonl.tmp` file and atomically renamed over the original. Compaction also runs automatically after every 1,000 append operations.

**Startup**: The server reads every line, deserializes, and populates the in-memory `dict[str, Entity]` and `list[Relation]`. Duplicate entity names are resolved by last-write-wins (later lines overwrite earlier ones during sequential loading).

### 4.5 Document Ingestion Pipeline

The `ingest_documents` tool enables bulk population of the KG from markdown files in `docs/vision/` and `docs/architecture/`. The ingestion module (`ingestion.py`) performs the following:

1. **Scan**: Find all `.md` files in the target folder (excluding `README.md`)
2. **Parse**: Extract H1 title, then extract named sections (`## Statement`, `## Description`, `## Rationale`, `## Usage`, `## Examples`) using regex
3. **Name**: Convert the H1 title to a `snake_case` entity name, stripping common prefixes like "Vision Standard:" or "Pattern:"
4. **Type**: Determine entity type from the `## Type` section content or keywords: vision tier always maps to `vision_standard`; architecture tier maps to `pattern`, `component`, or `architectural_standard` based on content
5. **Observations**: Build from extracted sections, prepended with `"protection_tier: <tier>"`, plus `"title: ..."` and `"source_file: ..."` metadata
6. **Re-ingestion**: If an entity with the same name already exists, delete it first (using `caller_role="human"` since ingestion is human-initiated)
7. **Create**: Batch-create all parsed entities via `graph.create_entities()`

### 4.6 Current Implementation Status

All 11 tools are implemented and operational:

- `graph.py`: Full entity/relation/observation CRUD with tier protection enforcement
- `tier_protection.py`: `get_entity_tier()` scans observations, `validate_write_access()` enforces the tier table
- `models.py`: Pydantic models with JSON field aliases for serialization compatibility
- `storage.py`: JSONL persistence with append, load, and atomic compaction
- `ingestion.py`: Markdown-to-entity parser with section extraction and re-ingestion support
- `server.py`: FastMCP server definition exposing all 11 tools on port 3101

**Note**: The storage path defaults to `.avt/knowledge-graph.jsonl` (updated from the original `.claude/collab/knowledge-graph.jsonl`). Search is substring-based (case-insensitive), not full-text or semantic.

---

## 5. Quality MCP Server (Port 3102)

**Purpose**: Wraps all quality tools (linters, formatters, test runners, coverage checkers) behind a unified MCP interface. Implements the Tool Trust Engine for finding management. Provides quality gate aggregation via `check_all_gates()` and a human-readable summary via `validate()`.

**Transport**: SSE on port 3102 (FastMCP)

**Storage**: SQLite at `.avt/trust-engine.db` for the Trust Engine (findings and dismissal history). Quality gate configuration is read from `.avt/project-config.json`.

### 5.1 Tool Interface (8 tools)

```
auto_format(
  files: list[str] | None = None,   # Specific file paths to format; returns error if omitted
  language: str | None = None        # "swift" | "python" | "rust" | "typescript" | "javascript"
                                     # Auto-detected from file extension if omitted
) -> { formatted: list[str], unchanged: list[str] }
  | { formatted: [], unchanged: [], error: str }

run_lint(
  files: list[str] | None = None,   # Specific file paths to lint
  language: str | None = None
) -> { findings: list[dict], auto_fixable: int, total: int }
  | { findings: [], auto_fixable: 0, total: 0, error: str }

run_tests(
  scope: str | None = None,         # "all" | specific test path; defaults to full suite
  language: str | None = None        # Defaults to "python" if omitted
) -> { passed: int, failed: int, skipped: int, failures: list[str] }

check_coverage(
  language: str | None = None        # Defaults to "python" if omitted
) -> { percentage: float, target: float, met: bool, uncovered_files: list[str] }
  # Target threshold read from project-config.json (default: 80%)

check_all_gates() -> {
  build:    { name: "build",    passed: bool, detail: str },
  lint:     { name: "lint",     passed: bool, detail: str },
  tests:    { name: "tests",    passed: bool, detail: str },
  coverage: { name: "coverage", passed: bool, detail: str },
  findings: { name: "findings", passed: bool, detail: str },
  all_passed: bool
}
  # Each gate can be disabled via .avt/project-config.json -> settings.qualityGates
  # Disabled gates return passed: true with detail: "Skipped (disabled)"

validate() -> {
  gates: GateResults,                # Same structure as check_all_gates()
  summary: str,                      # "All quality gates passed." or "Failed gates: lint, tests"
  all_passed: bool
}

get_trust_decision(
  finding_id: str
) -> { decision: "BLOCK" | "INVESTIGATE" | "TRACK", rationale: str }
  # Default for unknown findings: BLOCK ("all tool findings presumed legitimate")
  # Previously dismissed findings: TRACK (with rationale from dismissal record)

record_dismissal(
  finding_id: str,
  justification: str,               # Required -- empty string is rejected (returns false)
  dismissed_by: str                  # Agent or human identifier
) -> { recorded: bool }
  # Updates finding status to "dismissed" in findings table
  # Appends to dismissal_history table for audit trail
```

### 5.2 Specialist Routing

The Quality Server routes to language-specific tools via subprocess:

| Language | Formatter | Linter | Test Runner | Coverage |
|----------|-----------|--------|-------------|----------|
| Swift | `swiftformat` | `swiftlint lint --reporter json` | `xcodebuild test` | *(not configured)* |
| Python | `ruff format` | `ruff check --output-format=json` | `pytest -v --tb=short` | `pytest --cov --cov-report=term` |
| Rust | `rustfmt` | `cargo clippy --message-format=json` | `cargo test` | *(not configured)* |
| TypeScript | `prettier --write` | `eslint --format=json` | `npm test` | `npm run coverage` |
| JavaScript | `prettier --write` | `eslint --format=json` | `npm test` | `npm run coverage` |

Language detection uses file extension mapping: `.swift`, `.py`, `.rs`, `.ts`/`.tsx`, `.js`/`.jsx`. Custom commands can be configured via `.avt/project-config.json` under `quality.testCommands`, `quality.lintCommands`, `quality.buildCommands`, and `quality.formatCommands`.

### 5.3 Tool Trust Engine

The trust engine manages the lifecycle of quality findings. It uses a "guilty until proven innocent" philosophy: all findings from deterministic tools are presumed legitimate (`BLOCK`) until explicitly dismissed with justification.

**Trust decision classifications**:

| Decision | Meaning | When Applied |
|----------|---------|-------------|
| `BLOCK` | Cannot proceed until resolved | Default for all new/unknown findings |
| `INVESTIGATE` | Needs human or orchestrator review | *(Reserved for future use)* |
| `TRACK` | Note it, do not block on it | Previously dismissed findings |

**SQLite schema** (`.avt/trust-engine.db`):

```sql
CREATE TABLE findings (
    id TEXT PRIMARY KEY,
    tool TEXT NOT NULL,
    severity TEXT NOT NULL,
    component TEXT,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'open',          -- 'open' | 'dismissed'
    dismissed_by TEXT,
    dismissal_justification TEXT,
    dismissed_at TEXT
);

CREATE TABLE dismissal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id TEXT NOT NULL REFERENCES findings(id),
    dismissed_by TEXT NOT NULL,
    justification TEXT NOT NULL,
    dismissed_at TEXT NOT NULL
);
```

**No silent dismissals**: Every call to `record_dismissal` requires a non-empty `justification` string and a `dismissed_by` identifier. The dismissal is recorded both in the `findings` table (updating status) and in the `dismissal_history` table (append-only audit trail). Future occurrences of the same finding are classified as `TRACK` rather than `BLOCK`.

### 5.4 Quality Gate Configuration

Gates can be individually enabled or disabled via `.avt/project-config.json`:

```json
{
  "settings": {
    "qualityGates": {
      "build": true,
      "lint": true,
      "tests": true,
      "coverage": true,
      "findings": true
    },
    "coverageThreshold": 80
  }
}
```

### 5.5 Current Implementation Status

All 8 tools are implemented and operational:

- `server.py`: FastMCP server exposing all tools on port 3102
- `tools/formatting.py`: Real subprocess calls to `swiftformat`, `ruff format`, `rustfmt`, `prettier`
- `tools/linting.py`: Real subprocess calls with JSON output parsing for `ruff`, `eslint`, `swiftlint`; cargo clippy support
- `tools/testing.py`: Real subprocess calls to `pytest`, `npm test`, `xcodebuild test`, `cargo test`; output parsing for pass/fail counts
- `tools/coverage.py`: Real subprocess calls to `pytest --cov`, `npm run coverage`; percentage extraction from output
- `gates.py`: Aggregates all gates, respects per-gate enable/disable from project config
- `trust_engine.py`: SQLite-backed finding management with `record_finding`, `record_dismissal`, `get_trust_decision`, `get_dismissal_history`, `get_all_findings`
- `config.py`: Project configuration loader with defaults, merging, and per-language command overrides

**Partial stubs**: The build gate in `check_all_gates()` always returns `passed: true` with `"Build check not yet implemented"`. The findings gate always returns `passed: true` with `"No critical findings"`. These are TODOs for connecting to actual build commands and the trust engine's finding store respectively. Tool subprocess calls are real but depend on the corresponding tools being installed in the environment (`ruff`, `prettier`, `eslint`, etc.).

---

## 6. Governance MCP Server (Port 3103)

**Purpose**: Transactional decision review, governed task lifecycle management, and AI-powered review against vision and architecture standards. The governance server ensures that every significant agent decision is reviewed before implementation, every task is blocked from birth until governance approves it, and every completed task passes a final compliance check.

**Transport**: SSE on port 3103 (FastMCP)

**Storage**: SQLite at `.avt/governance.db` for decisions, reviews, governed tasks, and task review records. Task files are stored in Claude Code's native task directory (`~/.claude/tasks/<CLAUDE_CODE_TASK_LIST_ID>/`).

### 6.1 Tool Interface (10 tools)

#### Decision Review Tools

```
submit_decision(
  task_id: str,                      # The task this decision belongs to
  agent: str,                        # Name of the calling agent (e.g. "worker-1")
  category: str,                     # "pattern_choice" | "component_design" | "api_design"
                                     # | "deviation" | "scope_change"
  summary: str,                      # Brief summary of the decision
  detail: str = "",                  # Detailed explanation
  components_affected: list[str] | None = None,
  alternatives_considered: list[dict] | None = None,  # [{option, reason_rejected}]
  confidence: str = "high"           # "high" | "medium" | "low"
) -> {
  verdict: str,                      # "approved" | "blocked" | "needs_human_review"
  decision_id: str,
  findings: list[Finding],
  guidance: str,
  standards_verified: list[str]
}
  # BLOCKS until review completes (synchronous round-trip)
  # "deviation" and "scope_change" categories auto-return "needs_human_review"
  #   without AI review

submit_plan_for_review(
  task_id: str,
  agent: str,
  plan_summary: str,                 # Brief summary of the plan
  plan_content: str,                 # Full plan content (markdown)
  components_affected: list[str] | None = None
) -> {
  verdict: str,
  review_id: str,
  findings: list[Finding],
  guidance: str,
  decisions_reviewed: int,           # Count of prior decisions checked
  standards_verified: list[str]
}

submit_completion_review(
  task_id: str,
  agent: str,
  summary_of_work: str,
  files_changed: list[str] | None = None
) -> {
  verdict: str,
  review_id: str,
  unreviewed_decisions: list[str],   # Decision IDs that were never reviewed
  findings: list[Finding],
  guidance: str
}
  # Automatically BLOCKS if:
  #   - Any decisions for this task were never reviewed
  #   - Any blocked decisions remain unresolved
  # Otherwise runs AI review for final compliance check
```

#### Decision History Tools

```
get_decision_history(
  task_id: str | None = None,        # Filter by task
  agent: str | None = None,          # Filter by agent
  verdict: str | None = None         # Filter by verdict
) -> {
  decisions: list[{id, task_id, sequence, agent, category, summary,
                    confidence, verdict, guidance, created_at}]
}

get_governance_status() -> {
  total_decisions: int,
  approved: int,
  blocked: int,
  needs_human_review: int,
  pending: int,
  recent_activity: list[{summary, agent, category, verdict}],
  task_governance: {
    total_governed_tasks: int,
    pending_review: int,
    approved: int,
    blocked: int,
    pending_reviews: int
  }
}
```

#### Task Governance Tools

```
create_governed_task(
  subject: str,                      # The implementation task subject
  description: str,                  # Detailed description
  context: str,                      # Context for the governance review
  review_type: str = "governance"    # "governance" | "security" | "architecture"
                                     # | "memory" | "vision" | "custom"
) -> {
  implementation_task_id: str,       # The task that will do the work (prefixed "impl-")
  review_task_id: str,               # The review task blocking it (prefixed "review-")
  review_record_id: str,             # Internal governance record ID
  status: "pending_review",
  message: str
}
  # Atomically creates TWO Claude Code task files:
  #   1. Review task (created first): blocks the implementation task
  #   2. Implementation task (created second): blockedBy the review task
  # The implementation task CANNOT be picked up until the review completes

add_review_blocker(
  implementation_task_id: str,       # The implementation task to add a blocker to
  review_type: str,                  # "security" | "architecture" | "memory" | "vision" | "custom"
  context: str
) -> {
  review_task_id: str,
  review_record_id: str,
  status: "pending_review",
  message: str
}
  | { error: str, status: "failed" }
  # Adds an additional review blocker: task now has N blockers, ALL must complete

complete_task_review(
  review_task_id: str,               # The review task ID (from create_governed_task)
  verdict: str,                      # "approved" | "blocked" | "needs_human_review"
  guidance: str = "",
  findings: list[dict] | None = None,      # [{tier, severity, description, suggestion}]
  standards_verified: list[str] | None = None
) -> {
  verdict: str,
  implementation_task_id: str,
  task_released: bool,               # True only if ALL blockers are resolved
  remaining_blockers: int,
  message: str
}
  # If verdict is "approved", removes this review from blockedBy list
  # If verdict is "blocked", keeps the blocker and adds guidance to task description
  # Task is only released when blockedBy list is empty

get_task_review_status(
  implementation_task_id: str
) -> {
  task_id: str,
  subject: str,
  status: str,                       # "pending_review" | "approved" | "blocked"
  is_blocked: bool,
  can_execute: bool,
  reviews: list[{id, review_task_id, type, status, verdict, guidance,
                  created_at, completed_at}],
  blockers_from_files: list[{id, subject, status, review_type}],
  message: str
}

get_pending_reviews() -> {
  pending_reviews: list[{id, review_task_id, implementation_task_id,
                          type, context, created_at}],
  count: int
}
```

### 6.2 Decision Categories

| Category | When Used | Auto-Verdict |
|----------|-----------|-------------|
| `pattern_choice` | Choosing an implementation pattern | AI-reviewed |
| `component_design` | Designing a component's interface | AI-reviewed |
| `api_design` | Designing an API surface | AI-reviewed |
| `deviation` | Deviating from established patterns | `needs_human_review` (automatic) |
| `scope_change` | Working outside task brief scope | `needs_human_review` (automatic) |

### 6.3 Verdicts

| Verdict | Meaning | Effect |
|---------|---------|--------|
| `approved` | Decision/plan aligns with standards | Agent proceeds; review blocker removed |
| `blocked` | Decision conflicts with standards | Agent must revise and resubmit; blocker remains |
| `needs_human_review` | Requires human judgment | Include review context when presenting to human; auto-assigned for `deviation` and `scope_change` |

### 6.4 Data Models

```python
class DecisionCategory(str, Enum):
    PATTERN_CHOICE = "pattern_choice"
    COMPONENT_DESIGN = "component_design"
    API_DESIGN = "api_design"
    DEVIATION = "deviation"
    SCOPE_CHANGE = "scope_change"

class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Verdict(str, Enum):
    APPROVED = "approved"
    BLOCKED = "blocked"
    NEEDS_HUMAN_REVIEW = "needs_human_review"

class ReviewType(str, Enum):
    GOVERNANCE = "governance"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    MEMORY = "memory"
    VISION = "vision"
    CUSTOM = "custom"

class TaskReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    BLOCKED = "blocked"
    NEEDS_HUMAN_REVIEW = "needs_human_review"

class Alternative(BaseModel):
    option: str
    reason_rejected: str

class Decision(BaseModel):
    id: str                          # Auto-generated 12-char hex
    task_id: str
    sequence: int                    # Auto-incremented per task
    agent: str
    category: DecisionCategory
    summary: str
    detail: str
    components_affected: list[str]
    alternatives_considered: list[Alternative]
    confidence: Confidence
    created_at: str                  # ISO 8601 UTC

class Finding(BaseModel):
    tier: str                        # "vision" | "architecture" | "quality"
    severity: str                    # "vision_conflict" | "architectural" | "logic"
    description: str
    suggestion: str

class ReviewVerdict(BaseModel):
    id: str                          # Auto-generated 12-char hex
    decision_id: str | None          # Set for decision reviews
    plan_id: str | None              # Set for plan/completion reviews
    verdict: Verdict
    findings: list[Finding]
    guidance: str
    standards_verified: list[str]
    reviewer: str                    # Default: "governance-reviewer"
    created_at: str

class GovernedTaskRecord(BaseModel):
    id: str
    implementation_task_id: str      # Claude Code task file ID
    subject: str
    description: str
    context: str
    reviews: list[str]               # TaskReviewRecord IDs
    current_status: str              # "pending_review" | "approved" | "blocked"
    created_at: str
    released_at: str | None

class TaskReviewRecord(BaseModel):
    id: str
    review_task_id: str              # Claude Code task file ID for the review
    implementation_task_id: str      # Claude Code task file ID for the implementation
    review_type: ReviewType
    status: TaskReviewStatus
    context: str
    verdict: Verdict | None
    guidance: str
    findings: list[Finding]
    standards_verified: list[str]
    created_at: str
    completed_at: str | None
    reviewer: str                    # Default: "governance-reviewer"
```

### 6.5 AI Review Pipeline

The `GovernanceReviewer` class (`reviewer.py`) powers the AI review process. It constructs structured prompts, invokes `claude --print` via subprocess with temp file I/O, and parses JSON verdicts from the response.

**Three review modes**:

| Mode | Method | Timeout | Prompt Context |
|------|--------|---------|----------------|
| Decision review | `review_decision()` | 60s | Decision + vision standards + architecture entities |
| Plan review | `review_plan()` | 120s | Plan + all prior decisions + all prior reviews + vision + architecture |
| Completion review | `review_completion()` | 90s | Summary of work + files changed + all decisions + all reviews + vision |

**Execution flow** (for each review):

```
1. Build prompt
   |-- Format vision standards from KG
   |-- Format architecture entities from KG
   |-- Include decision/plan/completion details
   +-- Append JSON response schema instructions

2. Write prompt to temp file (tempfile.mkstemp)
   |-- Input:  /tmp/avt-gov-XXXX-input.md
   +-- Output: /tmp/avt-gov-XXXX-output.md

3. Execute: subprocess.run(
       ["claude", "--print"],
       stdin=<input file>,
       stdout=<output file>,
       timeout=<varies>
   )

4. Read response from output temp file

5. Parse JSON from response
   |-- Try: raw string starts with "{"
   |-- Try: extract from ```json ... ``` code blocks
   |-- Try: extract from first "{" to last "}"
   +-- Fallback: return needs_human_review with raw text

6. Clean up temp files (in finally block)
```

**Prompt structure** (decision review example):

```markdown
You are a governance reviewer. Evaluate this decision against the project's
vision and architecture standards.

## Vision Standards
- **standard_name**: observation1; observation2

## Architecture Patterns
- **component_name** (component): observation1; observation2

## Decision to Review
- **Agent**: worker-1
- **Category**: pattern_choice
- **Summary**: Use protocol-based DI for auth service
- **Detail**: ...
- **Components affected**: AuthService, ServiceRegistry
- **Alternatives considered**: ...
- **Confidence**: high

## Instructions
1. Check if this decision CONFLICTS with any vision standard.
2. Check if this decision deviates from established architecture patterns.
3. If deviation/scope_change, verdict should be "needs_human_review".
4. If aligned with standards, verdict is "approved".

Respond with ONLY a JSON object:
{ "verdict": "...", "findings": [...], "guidance": "...", "standards_verified": [...] }
```

**Error handling**: If `claude` CLI is not found, times out, or returns non-zero, the reviewer returns `needs_human_review` with an error description. The system degrades gracefully to manual review.

**Mock mode**: When the `GOVERNANCE_MOCK_REVIEW` environment variable is set, the reviewer skips the `claude` subprocess entirely and returns a deterministic `"approved"` verdict. This is used by the E2E test harness to avoid live `claude` binary dependency.

### 6.6 KG Integration

The `KGClient` class (`kg_client.py`) reads the Knowledge Graph JSONL file directly from the filesystem. It does not communicate with the KG MCP server over SSE -- it reads `.avt/knowledge-graph.jsonl` synchronously for zero-latency standard loading during review.

**Methods**:

| Method | What It Loads | How It Filters |
|--------|--------------|----------------|
| `get_vision_standards()` | All vision-tier entities | `entityType == "vision_standard"` OR observations containing "vision" |
| `get_architecture_entities()` | All architecture-tier entities | `entityType in ("architectural_standard", "pattern", "component")` |
| `search_entities(names)` | Entities matching component names | Case-insensitive substring match on name and observations |
| `record_decision(...)` | *(writes)* | Appends a `solution_pattern` entity to the JSONL file |

**Design choice**: Direct JSONL file reads avoid the latency and complexity of an MCP round-trip during synchronous governance review. Since the governance server runs on the same machine as the KG server, they share the same filesystem. The tradeoff is that KG writes during a governance review could produce stale reads, but governance reviews are short-lived (60-120 seconds) and standards change rarely.

### 6.7 Task Integration

The `task_integration.py` module manipulates Claude Code's native task file system to implement governance-gated task execution. Tasks are stored as JSON files in `~/.claude/tasks/<CLAUDE_CODE_TASK_LIST_ID>/`.

**Core principle**: Implementation tasks are ALWAYS created with a governance review blocker already in place. There is no window where a task exists without a blocker -- the review task is created first, the implementation task is created second with `blockedBy: [review_task_id]`.

**Task file format** (Claude Code native):

```json
{
  "id": "impl-a1b2c3d4",
  "subject": "Implement authentication service",
  "description": "Create JWT-based auth with refresh tokens",
  "status": "pending",
  "owner": null,
  "activeForm": "Working on Implement authentication service",
  "blockedBy": ["review-e5f6g7h8"],
  "blocks": [],
  "createdAt": 1738764000.0,
  "updatedAt": 1738764000.0
}
```

**Atomic operations**: All task file reads and writes use `fcntl.flock()` (exclusive file locks) to prevent race conditions when multiple agents access the same task simultaneously.

**TaskFileManager operations**:

| Operation | What It Does | Locking |
|-----------|-------------|---------|
| `create_task(task)` | Write new task JSON file | Exclusive lock on `.{task_id}.lock` |
| `read_task(task_id)` | Read and parse task JSON | No lock (read-only) |
| `update_task(task)` | Overwrite task JSON | Exclusive lock |
| `add_blocker(task_id, blocker_id)` | Add to `blockedBy` array | Exclusive lock |
| `remove_blocker(task_id, blocker_id)` | Remove from `blockedBy` array | Exclusive lock |
| `complete_task(task_id)` | Set `status: "completed"` | Via `update_task` |
| `list_tasks()` | Read all `.json` files in task directory | No lock |
| `get_pending_unblocked_tasks()` | Filter: pending, no blockers, no owner | No lock |

**Governed task pair creation** (`create_governed_task_pair`):

```
1. Generate IDs: review-{uuid8}, impl-{uuid8}
2. Create review task FIRST:
   - subject: "[GOVERNANCE] Review: <subject>"
   - blocks: [impl-id]
3. Create implementation task SECOND:
   - blockedBy: [review-id]
   - status: "pending" (but cannot execute due to blocker)
4. Both written atomically to task directory
```

**Task release** (`release_task`):

```
1. Read review task -> get implementation task ID from metadata or blocks list
2. Mark review task as completed
3. If verdict is "approved":
   - Remove review-id from implementation task's blockedBy
   - If blockedBy is now empty -> task can execute
4. If verdict is "blocked":
   - Keep blocker in place
   - Append guidance to implementation task description
```

### 6.8 Internal Architecture

```
+------------------------------------------------------------------+
| Agent calls submit_decision() / submit_plan_for_review()          |
+-------------------------------+----------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| server.py                                                         |
|  1. Store decision in SQLite (store.py)                           |
|  2. Auto-flag deviation/scope_change for human review             |
|  3. Load vision standards from KG (kg_client.py reads JSONL)      |
|  4. Load architecture entities from KG                            |
|  5. Call reviewer.review_decision() / review_plan()               |
+-------------------------------+----------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| reviewer.py (GovernanceReviewer)                                  |
|  1. Build prompt: decision + standards -> JSON response expected  |
|  2. Write prompt to temp file (mkstemp)                           |
|  3. Run: claude --print < input_tempfile > output_tempfile        |
|  4. Read response from output temp file                           |
|  5. Parse JSON into ReviewVerdict                                 |
|  6. Cleanup temp files in finally block                           |
|  (Mock mode: GOVERNANCE_MOCK_REVIEW returns deterministic OK)     |
+-------------------------------+----------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| Back in server.py                                                 |
|  6. Store review verdict in SQLite                                |
|  7. Record decision in KG (kg_client.record_decision)             |
|  8. Return verdict to calling agent                               |
+------------------------------------------------------------------+
```

### 6.9 SQLite Schema

The governance database (`.avt/governance.db`) contains four tables:

```sql
-- Decisions submitted by agents
CREATE TABLE decisions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,       -- Auto-incremented per task
    agent TEXT NOT NULL,
    category TEXT NOT NULL,          -- DecisionCategory enum value
    summary TEXT NOT NULL,
    detail TEXT,
    components_affected TEXT,        -- JSON array of strings
    alternatives TEXT,               -- JSON array of {option, reason_rejected}
    confidence TEXT,                 -- "high" | "medium" | "low"
    created_at TEXT NOT NULL         -- ISO 8601 UTC
);

-- Review verdicts (linked to decisions or plans)
CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    decision_id TEXT REFERENCES decisions(id),
    plan_id TEXT,                    -- Task ID for plan/completion reviews
    verdict TEXT NOT NULL,           -- "approved" | "blocked" | "needs_human_review"
    findings TEXT,                   -- JSON array of Finding objects
    guidance TEXT,
    standards_verified TEXT,         -- JSON array of standard names
    reviewer TEXT NOT NULL,          -- Default: "governance-reviewer"
    created_at TEXT NOT NULL
);

-- Governed task tracking
CREATE TABLE governed_tasks (
    id TEXT PRIMARY KEY,
    implementation_task_id TEXT UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    description TEXT,
    context TEXT,
    current_status TEXT NOT NULL DEFAULT 'pending_review',
    created_at TEXT NOT NULL,
    released_at TEXT                 -- Set when all review blockers are resolved
);

-- Individual review records for governed tasks
CREATE TABLE task_reviews (
    id TEXT PRIMARY KEY,
    review_task_id TEXT NOT NULL,
    implementation_task_id TEXT NOT NULL
        REFERENCES governed_tasks(implementation_task_id),
    review_type TEXT NOT NULL DEFAULT 'governance',
    status TEXT NOT NULL DEFAULT 'pending',
    context TEXT,
    verdict TEXT,                    -- Null until completed
    guidance TEXT,
    findings TEXT,                   -- JSON array of Finding objects
    standards_verified TEXT,         -- JSON array of standard names
    reviewer TEXT NOT NULL DEFAULT 'governance-reviewer',
    created_at TEXT NOT NULL,
    completed_at TEXT
);

-- Indexes for common query patterns
CREATE INDEX idx_decisions_task ON decisions(task_id);
CREATE INDEX idx_reviews_decision ON reviews(decision_id);
CREATE INDEX idx_reviews_plan ON reviews(plan_id);
CREATE INDEX idx_governed_tasks_impl ON governed_tasks(implementation_task_id);
CREATE INDEX idx_task_reviews_impl ON task_reviews(implementation_task_id);
CREATE INDEX idx_task_reviews_review ON task_reviews(review_task_id);
```

### 6.10 Current Implementation Status

All 10 tools are implemented and operational:

- `server.py`: FastMCP server exposing all tools on port 3103, including both decision review (5 tools) and task governance (5 tools) groups
- `store.py`: Full SQLite persistence with 4 tables, connection pooling via `sqlite3.Row`, and comprehensive CRUD for decisions, reviews, governed tasks, and task reviews
- `reviewer.py`: AI review engine with three review modes (decision, plan, completion), temp file I/O pattern, JSON parsing with multiple extraction strategies, and mock mode for testing
- `kg_client.py`: Direct JSONL reader with `get_vision_standards()`, `get_architecture_entities()`, `search_entities()`, and `record_decision()` for institutional memory
- `task_integration.py`: Claude Code task file manipulation with `fcntl` file locking, atomic governed task pair creation, blocker add/remove, and task release on approval
- `models.py`: Complete Pydantic model hierarchy for decisions, reviews, findings, verdicts, governed tasks, and task review records

**Extension point**: The `_queue_governance_review()` function in `server.py` is currently a pass-through placeholder. It records the review request (already stored in the `task_reviews` table) and serves as the extension point for future async job queue integration. Currently, reviews for governed tasks are triggered manually via `complete_task_review()` or processed by a governance-reviewer agent polling `get_pending_reviews()`.

## 7. Custom Subagent Definitions

The system defines six specialized subagents in `.claude/agents/`. Each is a Markdown file with YAML frontmatter declaring the model, tool access, and MCP server bindings. The orchestrator spawns subagents via the Claude Code Task tool, injecting task-specific context and project rules into each invocation.

### Agent Comparison Table

| Agent | Model | Tool Count | MCP Access | Role | Spawned By |
|-------|-------|------------|------------|------|------------|
| **Worker** | Opus 4.6 | 9 | KG + Quality + Governance | Implement scoped tasks with full governance integration | Orchestrator |
| **Quality Reviewer** | Opus 4.6 | 6 | KG + Quality | Three-lens review (vision, architecture, quality) | Orchestrator |
| **KG Librarian** | Sonnet 4.5 | 5 | KG | Curate institutional memory, consolidate observations | Orchestrator |
| **Governance Reviewer** | Sonnet 4.5 | 4 | KG | AI-powered decision review against vision/architecture standards | Governance Server (via `claude --print`) |
| **Researcher** | Opus 4.6 | 7 | KG + Governance | Periodic monitoring + exploratory design research | Orchestrator |
| **Project Steward** | Sonnet 4.5 | 7 | KG | Project hygiene, naming conventions, cruft detection | Orchestrator |

> **Note on Governance Reviewer**: Unlike the other five agents, the governance-reviewer is NOT spawned by the orchestrator. It is invoked internally by the Governance MCP server via `claude --print` when `submit_decision()`, `submit_plan_for_review()`, or `submit_completion_review()` are called. It runs as a headless subprocess, not a Task tool subagent.

---

### 7.1 Worker

**File**: `.claude/agents/worker.md`

```yaml
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
  - mcp:collab-governance
---
```

**MCP Server Access**: Knowledge Graph (port 3101), Quality (port 3102), Governance (port 3103)

**Role**: Implements specific tasks assigned by the orchestrator. Workers are the only agents that write production code. They operate within strictly scoped task briefs and must pass all governance checkpoints before, during, and after implementation.

**Protocol**:

| Phase | Step | Detail |
|-------|------|--------|
| **Startup** | 1. Read task brief | From task prompt or `.avt/task-briefs/` |
| | 2. Check project rules | Injected in context under `## Project Rules`. `ENFORCE` rules are non-negotiable; `PREFER` rules require documented justification to deviate. |
| | 3. Query KG for vision standards | `get_entities_by_tier("vision")` to load all vision constraints |
| | 4. Query KG for patterns | `search_nodes("<component>")` to find architectural patterns and past solutions |
| | 5. Note governed relations | Check `governed_by` relations linking components to vision standards |
| **Task Creation** | 6. Create governed tasks | Use `TaskCreate` or `create_governed_task()`. The PostToolUse hook ensures governance regardless of which is used (Section 3.3). |
| | 7. Verify task unblocked | Call `get_task_review_status()` to confirm approval before starting work |
| **During Work** | 8. Submit decisions | Call `submit_decision()` for every key choice (pattern_choice, component_design, api_design, deviation, scope_change). **This call blocks until verdict returns.** |
| | 9. Act on verdicts | `approved`: proceed. `blocked`: revise and resubmit. `needs_human_review`: include context and wait. |
| | 10. Submit plans | Call `submit_plan_for_review()` before presenting any plan |
| | 11. Stay in scope | Follow patterns from KG, do not modify files outside task brief |
| **Completion** | 12. Submit completion review | Call `submit_completion_review()` with work summary and changed files |
| | 13. Run quality gates | Call `check_all_gates()` via Quality server |
| | 14. Return summary | Structured output: what was done, files changed, gate results, governance verdicts, concerns |

**Constraints**:
- Do not modify files outside the task brief's scope
- Do not modify vision-tier or architecture-tier KG entities
- If a vision standard conflicts with the task, stop and report the conflict
- Do not skip governance checkpoints -- every key decision must be submitted
- Pass `callerRole: "worker"` in all KG operations

---

### 7.2 Quality Reviewer

**File**: `.claude/agents/quality-reviewer.md`

```yaml
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
```

**MCP Server Access**: Knowledge Graph (port 3101), Quality (port 3102)

**Role**: Evaluates work through three ordered lenses: vision alignment, architectural conformance, and quality compliance. The quality reviewer is a read-focused agent -- it reviews code but does not write production code.

**Protocol -- Three-Lens Review (Strict Order)**:

| Lens | Priority | KG Query | What It Checks | Severity |
|------|----------|----------|----------------|----------|
| **1. Vision** | Highest | `get_entities_by_tier("vision")` | Alignment with every applicable vision standard. A vision conflict is the ONLY finding reported -- it overrides everything else. | `vision_conflict` |
| **2. Architecture** | Medium | `search_nodes("<affected components>")` | Adherence to established patterns (`follows_pattern` relations). Detection of ad-hoc pattern drift: new code that reinvents something an existing pattern handles. | `architectural` |
| **3. Quality** | Standard | `check_all_gates()`, `run_lint()`, `check_coverage()` | Quality gate results, lint violations, test coverage. Compliance with project rules injected in context. | `logic`, `style`, `formatting` |

**Finding Format**: Every finding must include:
- Project-specific rationale (not generic advice)
- Concrete suggestion for remediation
- Reference to the KG entity or standard being violated

**Constraints**:
- Read-focused: review code, do not write production code
- Pass `callerRole: "quality"` in all KG operations
- Do not modify vision-tier or architecture-tier KG entities
- Constructive tone: teammate, not gatekeeper

---

### 7.3 KG Librarian

**File**: `.claude/agents/kg-librarian.md`

```yaml
---
model: sonnet
tools:
  - Read
  - Write
  - Glob
  - Grep
  - mcp:collab-kg
---
```

**MCP Server Access**: Knowledge Graph (port 3101)

**Role**: Curates institutional memory after work sessions. The librarian consolidates raw observations into well-organized knowledge, promotes recurring solutions to patterns, and syncs important entries to archival files.

**Protocol**:

| Phase | Step | Detail |
|-------|------|--------|
| **Review** | 1. Query recent activity | Find recently added entities and observations in the KG |
| **Consolidate** | 2. Merge redundant observations | Combine overlapping observations on the same entity into coherent entries |
| **Promote** | 3. Create solution patterns | When the same fix or approach appears 3+ times, create a `solution_pattern` entity |
| **Clean** | 4. Remove stale entries | Delete observations that are no longer accurate (outdated descriptions, resolved problems) |
| **Validate** | 5. Check tier consistency | Ensure no vision-tier entities have been modified by agents; report violations |
| **Sync** | 6. Update archival files | Write important KG entries to `.avt/memory/` files |

**Archival File Mapping**:

| File | Contents |
|------|----------|
| `.avt/memory/architectural-decisions.md` | Significant decisions and their rationale |
| `.avt/memory/troubleshooting-log.md` | Problems, what was tried, what worked |
| `.avt/memory/solution-patterns.md` | Promoted patterns with steps and reference implementations |
| `.avt/memory/research-findings.md` | Key discoveries from research that establish new baselines |

**Constraints**:
- Do not create or modify vision-tier entities
- Do not create or modify architecture-tier entities without `changeApproved: true`
- Do not delete entities that have `governed_by` relations pointing to them
- Pass `callerRole: "quality"` in all KG operations (librarian operates at the quality tier)

---

### 7.4 Governance Reviewer

**File**: `.claude/agents/governance-reviewer.md`

```yaml
---
model: sonnet
tools:
  - Read
  - Glob
  - Grep
  - mcp:collab-kg
---
```

**MCP Server Access**: Knowledge Graph (port 3101)

**Role**: AI-powered decision evaluator invoked internally by the Governance MCP server. Evaluates agent decisions and plans through the lens of vision alignment and architectural conformance. Returns structured JSON verdicts.

**Invocation**: The governance-reviewer is NOT spawned by the orchestrator via the Task tool. Instead, the Governance server's `GovernanceReviewer` class invokes it via `claude --print` (headless subprocess) when processing `submit_decision()`, `submit_plan_for_review()`, or `submit_completion_review()` calls. This makes governance review a synchronous round-trip within the MCP tool call.

**Review Protocol (Strict Order)**:

| Check | Priority | Action on Failure |
|-------|----------|-------------------|
| **1. Vision Alignment** | Highest | Load standards via `get_entities_by_tier("vision")`. Any vision conflict produces a `blocked` verdict immediately -- overrides everything else. |
| **2. Architectural Conformance** | Medium | Search KG for patterns and components. Detect ad-hoc pattern drift. Unjustified deviation produces a `blocked` verdict. |
| **3. Consistency Check** | Standard | For plan reviews: verify blocked decisions were not reimplemented. For completion reviews: verify all decisions were reviewed. Inconsistencies produce a `blocked` verdict. |

**Response Format**:

```json
{
  "verdict": "approved | blocked | needs_human_review",
  "findings": [
    {
      "tier": "vision | architecture | quality",
      "severity": "vision_conflict | architectural | logic",
      "description": "specific finding with project context",
      "suggestion": "concrete fix"
    }
  ],
  "guidance": "brief guidance for the agent",
  "standards_verified": ["list of standards checked and passed"]
}
```

**Verdict Rules**:
- **approved**: Decision aligns with all applicable standards. Includes which standards were verified.
- **blocked**: Decision conflicts with vision or architecture. Includes specific findings with suggestions.
- **needs_human_review**: Decision involves deviation, scope change, or ambiguous interpretation. Includes context for the human.

**Constraints**:
- Read-only: evaluate, do not implement
- Do not modify any KG entities
- Pass `callerRole: "quality"` in all KG operations
- Every finding must reference the actual standard or pattern being violated
- Always include a suggestion for remediation

---

### 7.5 Researcher

**File**: `.claude/agents/researcher.md`

```yaml
---
model: opus
tools:
  - Read
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - mcp:collab-kg
  - mcp:collab-governance
---
```

**MCP Server Access**: Knowledge Graph (port 3101), Governance (port 3103)

**Role**: Gathers intelligence to inform development decisions and tracks external changes. The researcher is the only agent with web access (`WebSearch`, `WebFetch`). Workers should never do substantial research -- that is the researcher's job.

**Research Modes**:

| Mode | Trigger | Output | Stored In |
|------|---------|--------|-----------|
| **Periodic/Maintenance** | Scheduled or on-demand | Change reports (breaking changes, deprecations, security advisories) | KG + `.avt/memory/research-findings.md` |
| **Exploratory/Design** | Before architectural decisions | Research briefs with options, tradeoffs, recommendations | `.avt/research-briefs/` |

**Protocol**:

| Phase | Step | Detail |
|-------|------|--------|
| **Startup** | 1. Read research prompt | From task prompt or `.avt/research-prompts/` |
| | 2. Determine research mode | Periodic or exploratory |
| | 3. Query KG for existing knowledge | `search_nodes("<topic>")` to avoid rediscovering known information |
| | 4. Note dependency relations | Check `depends_on` and `integrates_with` relations |
| **Periodic Research** | 5. Identify scope | Which technologies, APIs, or dependencies to check |
| | 6. Gather intelligence | Use `WebSearch` and `WebFetch` for changelogs, release notes, advisories |
| | 7. Analyze relevance | Filter findings to what affects this project |
| | 8. Record findings | Add observations to relevant KG entities |
| | 9. Flag actionable items | Categorize: breaking changes, deprecations, new features, security advisories |
| **Exploratory Research** | 5. Survey the landscape | Search for patterns, best practices, case studies, documentation |
| | 6. Evaluate options | For each viable approach: how it works, pros/cons, integration cost, risks |
| | 7. Synthesize recommendations | Present options with analysis, not information dumps |
| | 8. Submit research conclusion | Call `submit_decision(category="research_complete")` on Governance server |

**Model Selection**: The orchestrator selects the model based on research complexity:

| Complexity | Model | Use When |
|------------|-------|----------|
| High | Opus 4.6 | Novel domains, architectural decisions, security analysis, ambiguous requirements |
| Routine | Sonnet 4.5 | Changelog monitoring, version updates, straightforward API documentation |

**Constraints**:
- Do not modify vision-tier or architecture-tier KG entities (observations only)
- Do not make implementation decisions -- provide options and analysis
- Do not skip governance checkpoints for research that informs architecture
- Cite sources for all significant claims
- Distinguish fact from interpretation; flag uncertainty

---

### 7.6 Project Steward

**File**: `.claude/agents/project-steward.md`

```yaml
---
model: sonnet
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - mcp:collab-kg
---
```

**MCP Server Access**: Knowledge Graph (port 3101)

**Role**: Maintains project hygiene, organization, naming conventions, and completeness across the codebase. The steward is the guardian of project-level quality -- not code logic, but everything that makes a project professional and maintainable.

**Review Areas**:

| Area | What It Checks |
|------|----------------|
| **Project-Level Files** | Presence and completeness of LICENSE, README, CONTRIBUTING, CHANGELOG, CODE_OF_CONDUCT, SECURITY, .gitignore |
| **Naming Conventions** | Consistent casing across files, directories, variables, types, constants, test files per language/framework norms |
| **Folder Organization** | Logical grouping, consistent depth, no orphaned files, separation of concerns |
| **Documentation Completeness** | README sections, API docs, configuration documentation, script header comments |
| **Cruft Detection** | Unused files, duplicates, empty directories, temp files, outdated configs, dead links, resolved TODOs |
| **Consistency** | Indentation style, line endings, file encoding, import ordering, export patterns |

**Protocol**:

| Phase | Step | Detail |
|-------|------|--------|
| **Startup** | 1. Query KG for standards | `search_nodes("naming convention")`, `search_nodes("project structure")`, `get_entities_by_tier("architecture")` |
| | 2. Scan project root | Check for essential project files |
| | 3. Map folder structure | Build a mental map of organization |
| **Review** | 4. Check essential files | Verify existence and completeness (not stubs or placeholders) |
| | 5. Analyze naming | Sample files across directories for casing consistency |
| | 6. Detect cruft | Look for orphaned, duplicate, or outdated files |
| | 7. Review documentation | Check README and key docs for accuracy |
| **Output** | 8. Produce structured report | Findings categorized by priority (immediate, short-term, long-term) |
| | 9. Record KG entities | Create `naming_convention` and `project_structure` entities |

**Direct Fix Policy**: The steward CAN fix issues directly when the fix is mechanical (renaming, cruft removal) and non-controversial. It must ask the orchestrator before deleting files that might still be in use, making structural changes, modifying legal files, or changing multi-developer workflows.

**Periodic Review Schedule**:
- **Weekly**: Cruft detection, dead link checking
- **Monthly**: Full naming consistency audit
- **Quarterly**: Deep documentation review, structure analysis

**Constraints**:
- Do not modify code logic -- only project organization and documentation
- Do not modify vision-tier or architecture-tier KG entities
- Pass `callerRole: "quality"` in all KG operations
- When uncertain if something is cruft, flag it rather than delete it
- Respect existing conventions even if different ones would be preferred
- Always explain rationale behind naming/organization recommendations

---

## 8. Governance Architecture

### 8.1 Philosophy: "Intercept Early, Redirect Early"

Every implementation task is blocked from birth until governance review approves it. This is the central invariant of the governance system. There are no race conditions where work could start before review, no optimistic execution paths, and no fire-and-forget review requests.

The design principle is deterministic ordering: **Review -> Approve/Block -> Execute**. This order is enforced structurally through the PostToolUse hook on `TaskCreate` (Section 3.3), which intercepts every task creation and pairs it with a governance blocker. There is no way for any agent, at any level of the hierarchy, to create an ungoverned task.

Why this matters:
- **Vision conflicts are caught before code is written**, not during code review
- **Failed approaches from institutional memory are flagged** before workers repeat them
- **Scope creep is detected at the decision level**, not the pull request level
- **Architectural drift is prevented**, not corrected after the fact

### 8.2 Governed Task Lifecycle

The "blocked from birth" invariant is enforced by two complementary mechanisms:

1. **PostToolUse hook on `TaskCreate`** (primary, automatic): Every `TaskCreate` call triggers the hook at `scripts/hooks/governance-task-intercept.py`, which creates a governance review blocker. This is the **core enforcement mechanism** -- it works regardless of which agent created the task or whether the agent was following governance instructions. See Section 3.3 for the detailed hook flow.

2. **`create_governed_task()` MCP tool** (explicit, protocol-based): Agents can also create governed tasks directly through the Governance MCP server. This provides a richer API (review type selection, structured context) and creates governance DB records in a single atomic call.

Both mechanisms produce the same result: a review task that blocks an implementation task.

```
                      TWO PATHS TO THE SAME INVARIANT

Path A (Automatic - PostToolUse Hook):         Path B (Explicit - MCP Tool):

Agent calls TaskCreate("Implement auth")       Agent calls create_governed_task(
    |                                              subject: "Implement auth",
    v                                              review_type: "governance")
Claude Code writes task file (1.json)              |
    |                                              v
    v                                          Governance Server creates both tasks
PostToolUse hook fires automatically               |
    |                                              |
    v                                              |
Hook creates review-{uuid}.json                   |
Hook adds blockedBy to 1.json                     |
Hook stores records in governance.db               |
    |                                              |
    v                                              v
+------------------------------+  +--------------------------------------+
| Review Task (review-abc123)  |  | Implementation Task (1 or impl-xyz) |
|                              |  |                                      |
| subject: [GOVERNANCE]        |  | subject: Implement auth service      |
|   Review: Implement auth     |  | status: pending                      |
|   service                    |  | blockedBy: [review-abc123]           |
| status: pending              |  |                                      |
| blocks: [1 or impl-xyz]     |  | XX CANNOT EXECUTE                    |
+------------------------------+  +--------------------------------------+
              |
              v
+---------------------------------------------------------------------+
| Governance Review Executes:                                         |
|   - Load vision standards from KG                                   |
|   - Load architecture patterns from KG                              |
|   - Check memory for failed approaches                              |
|   - AI review via governance-reviewer (claude --print)              |
+---------------------------------------------------------------------+
              |
   +----------+-------------------+
   v          v                   v
APPROVED    BLOCKED          NEEDS_HUMAN_REVIEW
   |          |                   |
   |          |                   v
   |          |          Human must resolve.
   |          |          Task stays blocked.
   |          |
   |          v
   |   Task stays blocked
   |   with guidance. Agent
   |   must revise approach.
   |
   v
complete_task_review(review-abc123, "approved", ...)
   |
   v
review-abc123 removed from implementation task's blockedBy
   |
   v
If no remaining blockers -> implementation task is AVAILABLE for execution
```

**Why the hook is the primary mechanism**: The `create_governed_task()` MCP tool requires agents to call the right tool. If an agent uses native `TaskCreate` directly (whether by mistake, because it was not instructed, or because it is a subagent without governance MCP access), the MCP tool cannot intercept it. The PostToolUse hook has no such gap: it fires on every `TaskCreate` call at every level of the agent hierarchy, including subagents. In practice, use `create_governed_task()` when you want the richer API and structured context; rely on the hook to guarantee that nothing slips through.

**Stacking Additional Reviews**:

If initial governance review passes but flags a need for specialized review, additional blockers can be added:

```
add_review_blocker(
    implementation_task_id: "impl-xyz789",
    review_type: "security",
    context: "Auth handling requires security review"
)
```

The implementation task now has TWO blockers. Both must be individually completed via `complete_task_review()` before the task unblocks:

```
impl-xyz789
  blockedBy: [review-abc123, review-security-def456]
                    |                    |
                    v                    v
         complete_task_review()  complete_task_review()
         verdict: approved       verdict: approved
                    |                    |
                    v                    v
            blocker removed       blocker removed
                    |                    |
                    +--------+-----------+
                             v
                  blockedBy: [] -> TASK AVAILABLE
```

**Implementation**: Two code paths create governed task pairs:
- **PostToolUse hook** (`scripts/hooks/governance-task-intercept.py`): Discovers the newly created task by subject match (`_discover_task_id()`), creates a `review-{uuid}.json` file, and modifies the implementation task to add `blockedBy`. Stores governance records in `governance.db`.
- **MCP tool** (`create_governed_task_pair()` in `task_integration.py`): Atomically creates both task files with `blockedBy`/`blocks` relationships. Review tasks are written before implementation tasks, ensuring the blocker reference is valid at creation time. File-level locking via `fcntl.flock()` prevents concurrent modification.

### 8.3 Transactional Decision Review

Worker agents call `submit_decision()` on the Governance MCP server before implementing any key choice. This is a **synchronous round-trip** -- the tool call blocks until the review completes and a verdict is returned. It is not fire-and-forget.

**Internal Flow of `submit_decision()`**:

```
Worker calls submit_decision(task_id, agent, category, summary, ...)
    |
    v
1. Decision stored in SQLite (.avt/governance.db)
    |
    v
2. Vision standards loaded from KG JSONL
    |
    v
3. Architecture entities loaded from KG
    |
    v
4. Category check:
    +-- deviation or scope_change -> auto-verdict: needs_human_review
    |
    +-- all other categories:
        |
        v
    5. claude --print invoked with governance-reviewer agent
       (full AI reasoning against standards)
        |
        v
    6. ReviewVerdict parsed from reviewer output
    |
    v
7. Review stored in SQLite
    |
    v
8. Decision recorded in KG for institutional memory
    |
    v
9. Verdict returned to the calling worker
```

**Decision Categories**:

| Category | When Used | Behavior |
|----------|-----------|----------|
| `pattern_choice` | Choosing an implementation pattern | AI review against standards |
| `component_design` | Designing a component's interface | AI review against standards |
| `api_design` | Designing an API surface | AI review against standards |
| `deviation` | Intentionally deviating from an established pattern | Auto-verdict: `needs_human_review` |
| `scope_change` | Working outside the task brief's defined scope | Auto-verdict: `needs_human_review` |

**Verdicts**:

| Verdict | Meaning | Agent Action |
|---------|---------|--------------|
| `approved` | Decision aligns with all applicable standards | Proceed with implementation. Response includes which standards were verified. |
| `blocked` | Decision conflicts with vision or architecture | Stop. Response includes `guidance` explaining what to change. Revise and resubmit. |
| `needs_human_review` | Ambiguous, deviation, or scope change | Include the review context when presenting to the human. Do not proceed with the blocked aspect until resolved. |

**Plan Review**: Workers must also call `submit_plan_for_review()` before presenting any plan. This reviews the complete plan against all standards and checks that blocked decisions were not reimplemented.

**Completion Review**: Workers must call `submit_completion_review()` before reporting task completion. This verifies:
- All decisions were reviewed (no unreviewed decisions)
- No blocked decisions remain unresolved
- Work aligns with standards

If unreviewed decisions or unresolved blocks are found, the completion review returns a `blocked` verdict.

### 8.4 Three-Tier Governance Hierarchy

The Knowledge Graph enforces a protection hierarchy via `protection_tier` metadata on entities. Lower tiers cannot modify higher tiers. This hierarchy governs what each agent is permitted to change.

| Tier | Contains | Who Can Modify | Examples |
|------|----------|----------------|----------|
| **Vision** | Core principles, standards, invariants | Human only | "All services use protocol-based DI", "No singletons in production code", "Every public API has integration tests" |
| **Architecture** | Patterns, major components, abstractions | Human or orchestrator with approval | "ServiceRegistry pattern", "AuthService component", "Protocol-based DI pattern" |
| **Quality** | Observations, troubleshooting notes, findings | Any agent | "AuthService lacks error handling", "Login flow refactored on 2024-01-15" |

**Key Principle**: Lower tiers cannot modify higher tiers. A worker (quality-tier agent) can add observations to architecture-tier entities but cannot modify the entity itself. Vision-tier entities are immutable to all agents -- only humans can change them.

**Enforcement Points**:
- The KG server validates `callerRole` against `protection_tier` on every mutation
- The quality reviewer flags vision conflicts as the highest-priority finding (overrides all other findings)
- The governance reviewer blocks any decision that conflicts with vision standards
- Workers are instructed to stop and report if a vision standard conflicts with their task

### 8.5 Safety Net: ExitPlanMode Hook

While the PostToolUse hook on `TaskCreate` (Section 3.3, Section 8.2) is the **primary** governance enforcement mechanism, a `PreToolUse` hook on `ExitPlanMode` provides a **secondary safety net** for plan review. The hook script at `scripts/hooks/verify-governance-review.sh` runs before any agent can present a plan to the human.

**How It Works**:

```
Agent attempts to exit plan mode (present plan)
    |
    v
PreToolUse hook fires -> verify-governance-review.sh
    |
    v
Script checks .avt/governance.db for plan review records
    |
    +-- Plan reviews found (COUNT > 0) -> exit 0 (allow)
    |
    +-- No plan reviews found -> exit 2 (block)
        |
        v
    Agent receives feedback:
    "GOVERNANCE REVIEW REQUIRED: You must call
     submit_plan_for_review() before presenting your plan."
```

**Design Intent**: This hook is the **safety net**, not the primary mechanism. The primary enforcement is the worker protocol itself -- workers are instructed to call `submit_plan_for_review()` before presenting plans. The hook catches cases where an agent skips or forgets the governance checkpoint. If the governance database does not exist (server not running), the hook allows the action to avoid blocking development when governance is intentionally disabled.

### 8.6 Task List + Governance Layering

The system separates concerns into three distinct layers that compose cleanly:

```
+---------------------------------------------------------------+
|                    ENFORCEMENT LAYER                            |
|                                                                |
|  PostToolUse hook on TaskCreate (Section 3.3)                  |
|  Guarantees: every task is governed, no exceptions              |
|  100% interception, subagent inheritance, transparent           |
|                                                                |
|  Script: scripts/hooks/governance-task-intercept.py            |
|  Config: .claude/settings.json (PostToolUse matcher)           |
+---------------------------------------------------------------+
|                      GOVERNANCE LAYER                          |
|                                                                |
|  Policy: Should this task proceed? What reviews are required?  |
|  What standards apply? What is the verdict?                    |
|                                                                |
|  Tools: create_governed_task, add_review_blocker,              |
|         complete_task_review, submit_decision,                 |
|         submit_plan_for_review, submit_completion_review       |
|                                                                |
|  Storage: governance.db (SQLite)                               |
|  Agent: governance-reviewer (via claude --print)               |
|  Server: collab-governance (port 3103)                         |
+---------------------------------------------------------------+
|                    INFRASTRUCTURE LAYER                         |
|                                                                |
|  Mechanics: Persistence, DAG dependencies, file locking,       |
|  cross-session coordination, task state machines               |
|                                                                |
|  Implementation: Claude Code native Task system                |
|  Storage: ~/.claude/tasks/{CLAUDE_CODE_TASK_LIST_ID}/*.json    |
|  Module: task_integration.py (TaskFileManager)                 |
|  Concurrency: fcntl.flock() for atomic file operations         |
+---------------------------------------------------------------+
|                     SHARED NAMESPACE                            |
|                                                                |
|  CLAUDE_CODE_ENABLE_TASKS="true"                               |
|  CLAUDE_CODE_TASK_LIST_ID="agent-vision-team"                  |
|  Both required: first enables TaskCreate, second ensures       |
|  cross-session persistence and shared visibility               |
+---------------------------------------------------------------+
```

**Why Three Layers**:

| Concern | Layer | Rationale |
|---------|-------|-----------|
| Universal interception | Enforcement | The PostToolUse hook guarantees governance coverage regardless of which tool or agent created the task |
| Subagent coverage | Enforcement | Hook inheritance means subagents cannot bypass governance, even without MCP access |
| Task persistence | Infrastructure | Claude Code's native Task system handles JSON file storage, session persistence, and cross-agent visibility |
| DAG dependencies (blockedBy/blocks) | Infrastructure | The native Task system provides dependency graph semantics out of the box |
| File locking | Infrastructure | `task_integration.py` uses `fcntl.flock()` for concurrent-safe reads and writes to task files |
| Review policy | Governance | Whether a task should proceed is a policy question independent of how tasks are stored |
| Standard verification | Governance | Checking decisions against vision and architecture standards is domain logic, not infrastructure |
| Verdict storage | Governance | Review verdicts, findings, and guidance are governance data stored in `governance.db` |
| Institutional memory | Governance | Decisions and verdicts are recorded in the KG for future reference |

**How They Compose**:

1. An agent calls `TaskCreate` (directly or via `create_governed_task()`). The **Infrastructure Layer** writes the task file.

2. The **Enforcement Layer** (PostToolUse hook) fires immediately, discovers the new task, creates a review blocker, and stores governance records. This happens automatically on every `TaskCreate`, whether or not the agent used the governance MCP tool.

3. `complete_task_review()` removes blockers in the **Infrastructure Layer** (via `release_task()` in `task_integration.py`) when reviews pass. Simultaneously, it updates review records in the **Governance Layer** (`governance.db`) with verdicts, findings, and guidance.

4. `get_task_review_status()` reads from **both the Infrastructure and Governance layers**: file-system task state (is the task blocked? how many blockers?) and governance database records (what type of review? what was the verdict?).

**The `task_integration.py` Bridge**:

The `TaskFileManager` class in `mcp-servers/governance/collab_governance/task_integration.py` is the bridge between layers. It reads and writes Claude Code's native task JSON files while the governance server's `GovernanceStore` manages the policy database. Key operations:

| Function | Infrastructure Action | Governance Action |
|----------|-----------------------|-------------------|
| `create_governed_task_pair()` | Write review + impl task JSON files with `blockedBy`/`blocks` relationships | N/A (called by `create_governed_task` which handles governance DB) |
| `add_additional_review()` | Create review task file, add blocker to impl task file | N/A (called by `add_review_blocker` which handles governance DB) |
| `release_task()` | Complete review task file, remove blocker from impl task file | N/A (called by `complete_task_review` which handles governance DB) |
| `get_task_governance_status()` | Read task file, enumerate blockers and their statuses | N/A (called by `get_task_review_status` which merges governance DB data) |

**Strategic Value**: This three-layer separation keeps each concern independent. The Enforcement Layer (PostToolUse hook) guarantees coverage without depending on agent behavior. The Governance Layer can evolve its review policies (new review types, different verdict logic, additional checks) without touching task infrastructure. The Infrastructure Layer can adapt to Claude Code Task system changes (file format, storage location) by modifying only `task_integration.py` and the hook's discovery logic. Each layer can be tested, updated, and reasoned about independently.

## 9. CLAUDE.md Orchestration

The root `CLAUDE.md` is the orchestrator's instruction set. Claude Code reads it at session start and follows it as the primary directive for coordinating subagents, enforcing governance, and managing institutional memory. This section summarizes the key protocols it defines.

### 9.1 Task Decomposition

When given a complex task, the orchestrator:

1. **Breaks it down** into discrete, scopeable units of work
2. **Writes task briefs** as structured markdown in `.avt/task-briefs/`
3. **Creates isolation** via git worktrees (`git worktree add ../project-worker-N -b task/NNN-description`)
4. **Spawns workers** using the Task tool, one per task brief
5. **Reviews work** by spawning the quality-reviewer subagent with the worker's diff
6. **Routes findings** back to workers for resolution
7. **Merges and cleans up** when all findings are resolved and quality gates pass

### 9.2 Task Governance Protocol

The system follows an "Intercept Early, Redirect Early" principle. Every implementation task is **blocked from birth** until governance review approves it.

**Key design**: Agents use `TaskCreate` normally. The PostToolUse hook on `TaskCreate` (Section 3.3) automatically intercepts every task creation and pairs it with a governance review blocker. Governance is enforced by the platform, not by agent compliance.

For richer governance metadata (review type selection, structured context), agents can also use the Governance MCP server's `create_governed_task()` tool:

```
create_governed_task(
    subject: "Implement authentication service",
    description: "Create JWT-based auth with refresh tokens",
    context: "Part of user management epic",
    review_type: "governance"
)
```

Both paths produce the same result: a review task that blocks the implementation task. The PostToolUse hook guarantees that even a plain `TaskCreate("Implement auth service")` call gets governed.

The flow is strictly sequential regardless of which path is used:

```
TaskCreate or create_governed_task()
    --> PostToolUse hook creates governance pair (if TaskCreate used directly)
    --> Review task (pending) blocks Implementation task
    --> Governance review runs (automated or manual)
    --> complete_task_review(verdict: "approved" | "blocked")
    --> If approved and last blocker: Implementation task unblocks
    --> Worker picks up task
```

Additional blockers can be stacked via `add_review_blocker()` (e.g., security review on top of governance review). All blockers must complete before the task becomes available.

### 9.3 Quality Review Protocol

After any significant code change:

1. Spawn the **quality-reviewer** subagent with the diff context
2. Review findings **by tier** (vision first, then architecture, then quality):
   - **Vision conflicts**: Stop all related work and address immediately
   - **Architecture findings**: Route to worker with context, require resolution
   - **Quality findings**: Route to worker; auto-fixable issues can be fixed inline
3. Verify resolution before proceeding

### 9.4 Project Rules Protocol

Project rules are concise behavioral guidelines injected into every agent's context at spawn time. Rules live in `.avt/project-config.json` (not in CLAUDE.md) and are configured via the setup wizard.

Each rule has:
- **Enforcement level**: `enforce` (must follow), `prefer` (explain if deviating), or `guide` (advisory)
- **Scope**: Which agent roles receive the rule (e.g., `worker`, `quality-reviewer`, `all`)
- **Category**: `testing`, `code-quality`, `security`, `performance`, `patterns`, `workflow`, `custom`

At spawn time, the orchestrator compiles enabled rules into a compact preamble (~200-400 tokens) and prepends it to the task prompt. Only rules matching the agent's scope are injected. Rationale is not injected -- agents that need deeper context query the KG via `search_nodes("project rules")`.

### 9.5 Memory Protocol

**Before starting work**, query the Knowledge Graph for context:
- `get_entities_by_tier("vision")` -- load all vision constraints
- `search_nodes("<component name>")` -- find architectural patterns and past solutions
- `search_nodes("<task type> pattern")` -- check for solution patterns matching the task type

**After completing work**, spawn the **kg-librarian** subagent to curate observations. The librarian consolidates redundant observations, promotes recurring solutions to patterns, removes stale entries, and syncs important entries to archival files in `.avt/memory/`.

### 9.6 Research Protocol

The researcher subagent gathers intelligence in two modes:

| Mode | Purpose | Output | Model |
|------|---------|--------|-------|
| **Periodic/Maintenance** | Monitor APIs, frameworks, dependencies for breaking changes, deprecations, or new features | Change reports | Sonnet 4.5 (straightforward monitoring) |
| **Exploratory/Design** | Deep investigation before architectural decisions, technology comparisons, unfamiliar domains | Research briefs | Opus 4.6 (complex, novel analysis) |

Research prompts are defined in `.avt/research-prompts/` and managed via the dashboard or manually. Completed research is stored in `.avt/research-briefs/`. The orchestrator references research briefs in task briefs when spawning workers.

### 9.7 Project Hygiene Protocol

The **project-steward** subagent performs periodic reviews:
- **Weekly**: Cruft detection (unused files, duplicates, dead links)
- **Monthly**: Naming convention audits across files, directories, variables, and types
- **Quarterly**: Deep reviews of folder organization, documentation completeness, and consistency

The steward also runs before releases (ensuring project files are complete) and after major refactoring (verifying organization still makes sense).

### 9.8 Checkpoints and Drift Detection

**Checkpoints** combine session state updates (`session-state.md`) with git tags (`checkpoint-NNN`). After each meaningful unit of work, the orchestrator writes progress and tags the state, enabling resume from the last known-good point after a failure.

**Drift detection** monitors four failure patterns:

| Pattern | Signal | Response |
|---------|--------|----------|
| **Time drift** | Worker on a single task too long without progress | Stop and reassess |
| **Loop drift** | Repeated failures on the same issue | Stop and change approach |
| **Scope drift** | Work outside the task brief's defined scope | Stop and refocus |
| **Quality drift** | Findings accumulating faster than resolution | Stop and prioritize resolution |

### 9.9 No Silent Dismissals

The trust engine enforces a key audit principle: every dismissed finding requires justification. When a finding is deemed not applicable, it must be dismissed via `record_dismissal(finding_id, justification, dismissed_by)`. This creates an audit trail. Future occurrences of the same finding are tracked, not blocked.

---

## 10. VS Code Extension

The Collab Intelligence VS Code extension has evolved significantly beyond the original "observability only" scope. It now provides setup wizards, interactive tutorials, document authoring with AI-assisted formatting, governance management, research prompt management, and a comprehensive React-based dashboard -- all while coexisting cleanly with the Claude Code extension.

### 10.1 Extension Capabilities

The extension provides these major capabilities:

| Capability | Description |
|------------|-------------|
| **Setup Wizard** | 9-step interactive onboarding: welcome, vision docs, architecture docs, quality config, rules, permissions, settings, KG ingestion, completion |
| **Workflow Tutorial** | 10-step interactive guide: welcome, big picture, setup, starting work, behind the scenes, monitoring, knowledge graph, quality gates, tips, ready |
| **VS Code Walkthrough** | Native walkthrough (`avt-getting-started`) with 6 steps covering system overview, three-tier hierarchy, agent team, work cycle, institutional memory, and project setup |
| **Dashboard Webview** | React/Tailwind single-page application showing session status, agent cards, governance panel, governed tasks, activity feed, and setup readiness banner |
| **Governance Panel** | Displays governed tasks, pending reviews, decision history, and governance statistics within the dashboard |
| **Research Prompts Panel** | CRUD management for periodic and exploratory research prompts, with schedule configuration |
| **Document Editor** | Claude CLI-based auto-formatting for vision and architecture documents. Uses temp-file I/O pattern: user drafts content, extension formats via `claude --print`, user reviews and saves |
| **Memory Browser** | TreeView displaying KG entities grouped by protection tier (vision/architecture/quality) with observation and relation details |
| **Findings Panel** | TreeView displaying quality findings grouped by tier, with VS Code diagnostic integration |
| **Tasks Panel** | TreeView displaying task briefs with status indicators |
| **Actions Panel** | TreeView with welcome content providing quick-action buttons: Open Dashboard, Connect to Servers, Setup Wizard, Workflow Tutorial |
| **Status Bar** | Two status bar items showing system health (active/warning/error/inactive) and summary (workers, findings, phase) |
| **MCP Server Manager** | Spawns and manages all 3 MCP server processes (`uv run python -m ...`), with port readiness polling and auto-start on activation |
| **3 MCP Clients** | `KnowledgeGraphClient`, `QualityClient`, `GovernanceClient` -- typed wrappers over SSE connections to the same 3 servers that Claude Code uses |

### 10.2 Extension Backend

The extension backend is organized into five layers:

**Providers** (`extension/src/providers/`):

| File | Class | Purpose |
|------|-------|---------|
| `DashboardWebviewProvider.ts` | `DashboardWebviewProvider` | Manages the React webview panel. Handles message passing between extension host and webview, data aggregation, setup wizard triggers, tutorial triggers, and document formatting via Claude CLI |
| `FindingsTreeProvider.ts` | `FindingsTreeProvider` | TreeDataProvider for quality findings, grouped by tier with diagnostic collection integration |
| `TasksTreeProvider.ts` | `TasksTreeProvider` | TreeDataProvider for task briefs with status-based icons |
| `MemoryTreeProvider.ts` | `MemoryTreeProvider` | TreeDataProvider for KG entities, grouped by protection tier |

**Services** (`extension/src/services/`):

| File | Class | Purpose |
|------|-------|---------|
| `McpClientService.ts` | `McpClientService` | SSE-based MCP protocol client. Manages persistent connections to all 3 servers. Handles JSON-RPC 2.0 over SSE with session ID management, request/response correlation, and structured content parsing |
| `McpServerManager.ts` | `McpServerManager` | Spawns MCP server child processes via `uv run python -m <module>`. Polls port readiness with configurable timeout (15s). Detects already-running servers |
| `FileWatcherService.ts` | `FileWatcherService` | Watches `.avt/task-briefs/**` and `.avt/session-state.md` for filesystem changes, emitting events to refresh tree views and dashboard |
| `StatusBarService.ts` | `StatusBarService` | Manages two status bar items (health indicator + summary). Both click through to the dashboard |
| `ProjectConfigService.ts` | `ProjectConfigService` | Reads/writes `.avt/project-config.json` with atomic writes (write to `.tmp`, then rename). Manages folder structure creation, vision/architecture document CRUD, research prompt CRUD with YAML file generation, permission syncing to `.claude/settings.local.json`, and setup readiness assessment |

**MCP Clients** (`extension/src/mcp/`):

| File | Class | Target Server |
|------|-------|--------------|
| `KnowledgeGraphClient.ts` | `KnowledgeGraphClient` | KG server (:3101) -- `create_entities`, `create_relations`, `add_observations`, `search_nodes`, `get_entity`, `get_entities_by_tier`, `validate_tier_access`, `ingest_documents` |
| `QualityClient.ts` | `QualityClient` | Quality server (:3102) -- `auto_format`, `run_lint`, `run_tests`, `check_coverage`, `check_all_gates`, `validate`, `get_trust_decision`, `record_dismissal` |
| `GovernanceClient.ts` | `GovernanceClient` | Governance server (:3103) -- `get_governance_status`, `get_decision_history`, `get_pending_reviews`, `get_task_review_status` |

**Models** (`extension/src/models/`):

| File | Key Types |
|------|-----------|
| `Activity.ts` | `AgentStatus`, `ActivityEntry`, `GovernedTask`, `GovernanceStats`, `TaskReviewInfo` |
| `Entity.ts` | `Entity`, `Relation`, `ProtectionTier`, `EntityType` |
| `Finding.ts` | `Finding`, `FindingPayload`, `Tier`, `Severity` |
| `Task.ts` | `Task`, `TaskStatus` |
| `ProjectConfig.ts` | `ProjectConfig`, `SetupReadiness`, `RuleEntry`, `RulesConfig`, `PermissionEntry`, `QualityConfig`, plus default rules, default permissions, and optional rules |
| `ResearchPrompt.ts` | `ResearchPrompt`, `ResearchSchedule`, `ResearchResult`, plus `toPromptYaml()` serializer |
| `Message.ts` | Extension/webview message types |

**Commands** (`extension/src/commands/`):

| File | Commands |
|------|----------|
| `systemCommands.ts` | `collab.startSystem`, `collab.stopSystem` |
| `memoryCommands.ts` | `collab.searchMemory` |
| `taskCommands.ts` | `collab.createTaskBrief` |

Additional commands registered directly in `extension.ts`: `collab.connectMcpServers`, `collab.refreshMemory`, `collab.refreshFindings`, `collab.refreshTasks`, `collab.viewDashboard`, `collab.openSetupWizard`, `collab.openWalkthrough`, `collab.openWorkflowTutorial`, `collab.runResearch`, `collab.validateAll`, `collab.ingestDocuments`.

### 10.3 Dashboard Components

The dashboard is a React + Tailwind CSS application built with Vite, rendered inside a VS Code webview panel titled "Agent Operations Center."

**Application Shell** (`extension/webview-dashboard/src/`):

| File | Purpose |
|------|---------|
| `App.tsx` | Root layout: `SessionBar` + `SetupBanner` + `ConnectionBanner` + `AgentCards` + split pane (`GovernancePanel` left 2/5, tabbed `TaskBoard`/`ActivityFeed` right 3/5) + overlay modals (`SetupWizard`, `SettingsPanel`, `ResearchPromptsPanel`, `WorkflowTutorial`) |
| `context/DashboardContext.tsx` | React context providing dashboard state, VS Code API bridge, wizard/settings/tutorial visibility toggles, document format results, research prompt state |
| `hooks/useVsCodeApi.ts` | Hook wrapping the `acquireVsCodeApi()` bridge for message posting |
| `hooks/useDocEditor.ts` | State machine hook for document authoring: `idle` -> `drafting` -> `formatting` -> `reviewing` -> `saving`, with error recovery |
| `types.ts` | Shared type definitions mirroring extension backend models |

**Main Dashboard Components** (`extension/webview-dashboard/src/components/`):

| File | Component | Purpose |
|------|-----------|---------|
| `SessionBar.tsx` | `SessionBar` | Top bar showing session phase, task counts, connection status, and action buttons (Settings, Research, Wizard, Tutorial, Refresh) |
| `SetupBanner.tsx` | `SetupBanner` | Conditional banner shown when setup is incomplete, with readiness checklist and "Run Setup Wizard" button |
| `AgentCards.tsx` | `AgentCards` | Horizontal row of cards showing each agent's status (active/idle/blocked/reviewing/not-configured) with current task info |
| `GovernancePanel.tsx` | `GovernancePanel` | Left panel showing governance stats counters, vision standards list, and architectural elements list |
| `GovernanceItem.tsx` | `GovernanceItem` | Individual governance entity display with observations |
| `TaskBoard.tsx` | `TaskBoard` | Governed task list with review status badges and blocker indicators |
| `ActivityFeed.tsx` | `ActivityFeed` | Chronological activity log with agent/type/governance filtering |
| `ActivityEntry.tsx` | `ActivityEntry` | Individual activity entry with tier-colored badges |
| `SettingsPanel.tsx` | `SettingsPanel` | Modal overlay for editing project settings post-wizard |
| `ResearchPromptsPanel.tsx` | `ResearchPromptsPanel` | Modal overlay for creating, editing, deleting, and running research prompts |

**Setup Wizard** (`extension/webview-dashboard/src/components/wizard/`):

| File | Purpose |
|------|---------|
| `SetupWizard.tsx` | 9-step wizard container with navigation, step validation, and config persistence |
| `WizardStepIndicator.tsx` | Visual step progress indicator with completion state |

Wizard steps (in order):

| Step | Component | What It Configures |
|------|-----------|-------------------|
| 1. Welcome | `WelcomeStep.tsx` | Introduction and language selection |
| 2. Vision Docs | `VisionDocsStep.tsx` | Create/edit vision standard documents with AI-assisted formatting via `DocEditorCard` |
| 3. Architecture Docs | `ArchitectureDocsStep.tsx` | Create/edit architecture documents with AI-assisted formatting via `DocEditorCard` |
| 4. Quality Config | `QualityConfigStep.tsx` | Test, lint, build, and format commands per language |
| 5. Rules | `RulesStep.tsx` | Enable/disable project rules with enforcement levels and agent scopes |
| 6. Permissions | `PermissionsStep.tsx` | Claude Code permission allowlist (recommended + optional) synced to `.claude/settings.local.json` |
| 7. Settings | `SettingsStep.tsx` | Quality gate toggles, coverage threshold, mock test policies, auto-governance, KG auto-curation |
| 8. Ingestion | `IngestionStep.tsx` | Ingest vision and architecture documents into the Knowledge Graph |
| 9. Complete | `CompleteStep.tsx` | Summary and next-steps guidance |

The `DocEditorCard.tsx` component provides the document authoring workflow: the user writes or pastes raw content, clicks "Format," which sends the content to the extension backend for Claude CLI formatting (`claude --print`), then the user reviews and saves.

**Workflow Tutorial** (`extension/webview-dashboard/src/components/tutorial/`):

| File | Purpose |
|------|---------|
| `WorkflowTutorial.tsx` | 10-step tutorial container with navigation |
| `TutorialStepIndicator.tsx` | Visual step progress indicator |

Tutorial steps (in order):

| Step | Component | Topic |
|------|-----------|-------|
| 1. Welcome | `WelcomeStep.tsx` | What the system does and why |
| 2. Big Picture | `BigPictureStep.tsx` | Three-tier hierarchy and agent roles |
| 3. Run Setup | `SetupStep.tsx` | How to run the setup wizard (with launch button) |
| 4. Start Work | `StartingWorkStep.tsx` | Task decomposition and governed task flow |
| 5. Behind the Scenes | `BehindScenesStep.tsx` | What happens when agents execute (governance, quality gates) |
| 6. Monitoring | `MonitoringStep.tsx` | Using the dashboard to monitor agent activity |
| 7. Knowledge Graph | `KnowledgeGraphStep.tsx` | How institutional memory works |
| 8. Quality Gates | `QualityGatesStep.tsx` | Build, lint, test, coverage, and findings gates |
| 9. Tips | `TipsStep.tsx` | Best practices and common patterns |
| 10. Ready | `ReadyStep.tsx` | Summary and getting started |

**Shared UI** (`extension/webview-dashboard/src/components/ui/`):

| File | Component | Purpose |
|------|-----------|---------|
| `WarningDialog.tsx` | `WarningDialog` | Reusable confirmation dialog for destructive actions |

### 10.4 Coexistence with Claude Code Extension

The Collab Intelligence extension and the Claude Code extension serve complementary roles and are designed to run simultaneously without conflict:

| Concern | Collab Intelligence Extension | Claude Code Extension |
|---------|-------------------------------|----------------------|
| AI interaction (prompting, code generation) | No | Yes |
| System monitoring and dashboards | Yes | No |
| Finding display and triage | Yes | No |
| Memory browsing (KG entities) | Yes | No |
| Setup and onboarding | Yes | No |
| Governance management (task review status) | Yes | No |
| Research prompt management | Yes | No |
| MCP server lifecycle (start/stop) | Yes | Uses servers when running |
| Document authoring with AI formatting | Yes (via `claude --print`) | No |
| Code editing and tool execution | No | Yes |

The extension connects to the same 3 MCP servers as Claude Code, using the same SSE transport on the same ports (3101, 3102, 3103). Both can be connected simultaneously. The extension uses read-heavy operations (status queries, entity browsing, decision history) while Claude Code agents perform write-heavy operations (creating entities, submitting decisions, running quality gates).

---

## 11. File System Layout

### Product Repository

The following layout is verified against the actual filesystem:

```
agent-vision-team/
├── .claude/
│   ├── agents/                              # 6 custom subagent definitions
│   │   ├── worker.md
│   │   ├── quality-reviewer.md
│   │   ├── kg-librarian.md
│   │   ├── governance-reviewer.md
│   │   ├── researcher.md
│   │   └── project-steward.md
│   ├── commands/
│   │   └── project-overview.md              # Slash command definition
│   ├── skills/
│   │   └── e2e.md                           # /e2e skill definition
│   ├── settings.json                        # Hooks (PostToolUse on TaskCreate, PreToolUse on ExitPlanMode), MCP servers, model routing
│   └── settings.local.json                  # Permission allowlist (synced by wizard)
│
├── .avt/                                    # Agent Vision Team system config
│   ├── knowledge-graph.jsonl                # KG entity/relation persistence
│   ├── trust-engine.db                      # Quality finding audit trails
│   ├── governance.db                        # Decision store with verdicts
│   ├── task-briefs/
│   │   └── example-001-add-feature.md
│   ├── session-state.md                     # Current session progress
│   ├── memory/                              # Archival memory files (synced by KG Librarian)
│   │   ├── architectural-decisions.md
│   │   ├── research-findings.md
│   │   ├── solution-patterns.md
│   │   └── troubleshooting-log.md
│   ├── research-prompts/
│   │   └── README.md
│   ├── research-briefs/
│   │   └── README.md
│   └── project-config.json                  # Project configuration (managed by wizard)
│
├── extension/                               # VS Code extension
│   ├── src/
│   │   ├── extension.ts                     # Activation entry point
│   │   ├── providers/
│   │   │   ├── DashboardWebviewProvider.ts
│   │   │   ├── FindingsTreeProvider.ts
│   │   │   ├── MemoryTreeProvider.ts
│   │   │   └── TasksTreeProvider.ts
│   │   ├── services/
│   │   │   ├── McpClientService.ts
│   │   │   ├── McpServerManager.ts
│   │   │   ├── FileWatcherService.ts
│   │   │   ├── StatusBarService.ts
│   │   │   └── ProjectConfigService.ts
│   │   ├── mcp/
│   │   │   ├── KnowledgeGraphClient.ts
│   │   │   ├── QualityClient.ts
│   │   │   └── GovernanceClient.ts
│   │   ├── commands/
│   │   │   ├── systemCommands.ts
│   │   │   ├── memoryCommands.ts
│   │   │   └── taskCommands.ts
│   │   ├── models/
│   │   │   ├── Activity.ts
│   │   │   ├── Entity.ts
│   │   │   ├── Finding.ts
│   │   │   ├── Task.ts
│   │   │   ├── ProjectConfig.ts
│   │   │   ├── ResearchPrompt.ts
│   │   │   └── Message.ts
│   │   ├── test/
│   │   │   ├── index.ts
│   │   │   ├── KnowledgeGraphClient.test.ts
│   │   │   ├── McpClientService.test.ts
│   │   │   ├── MemoryTreeProvider.test.ts
│   │   │   └── QualityClient.test.ts
│   │   └── utils/
│   │       ├── config.ts
│   │       └── logger.ts
│   ├── webview-dashboard/
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── main.tsx
│   │   │   ├── index.css
│   │   │   ├── types.ts
│   │   │   ├── context/
│   │   │   │   └── DashboardContext.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useVsCodeApi.ts
│   │   │   │   └── useDocEditor.ts
│   │   │   └── components/
│   │   │       ├── SessionBar.tsx
│   │   │       ├── SetupBanner.tsx
│   │   │       ├── AgentCards.tsx
│   │   │       ├── GovernancePanel.tsx
│   │   │       ├── GovernanceItem.tsx
│   │   │       ├── TaskBoard.tsx
│   │   │       ├── ActivityFeed.tsx
│   │   │       ├── ActivityEntry.tsx
│   │   │       ├── SettingsPanel.tsx
│   │   │       ├── ResearchPromptsPanel.tsx
│   │   │       ├── ui/
│   │   │       │   └── WarningDialog.tsx
│   │   │       ├── wizard/
│   │   │       │   ├── SetupWizard.tsx
│   │   │       │   ├── WizardStepIndicator.tsx
│   │   │       │   └── steps/
│   │   │       │       ├── WelcomeStep.tsx
│   │   │       │       ├── VisionDocsStep.tsx
│   │   │       │       ├── ArchitectureDocsStep.tsx
│   │   │       │       ├── QualityConfigStep.tsx
│   │   │       │       ├── RulesStep.tsx
│   │   │       │       ├── PermissionsStep.tsx
│   │   │       │       ├── SettingsStep.tsx
│   │   │       │       ├── IngestionStep.tsx
│   │   │       │       ├── CompleteStep.tsx
│   │   │       │       └── DocEditorCard.tsx
│   │   │       └── tutorial/
│   │   │           ├── WorkflowTutorial.tsx
│   │   │           ├── TutorialStepIndicator.tsx
│   │   │           └── steps/
│   │   │               ├── WelcomeStep.tsx
│   │   │               ├── BigPictureStep.tsx
│   │   │               ├── SetupStep.tsx
│   │   │               ├── StartingWorkStep.tsx
│   │   │               ├── BehindScenesStep.tsx
│   │   │               ├── MonitoringStep.tsx
│   │   │               ├── KnowledgeGraphStep.tsx
│   │   │               ├── QualityGatesStep.tsx
│   │   │               ├── TipsStep.tsx
│   │   │               └── ReadyStep.tsx
│   │   ├── dist/
│   │   │   └── index.html
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.js
│   │   └── postcss.config.js
│   ├── media/
│   │   ├── icons/
│   │   │   └── collab.svg                   # Activity bar icon
│   │   └── walkthrough/                     # Native walkthrough markdown
│   │       ├── 01-welcome.md
│   │       ├── 02-three-tiers.md
│   │       ├── 03-agents.md
│   │       ├── 04-work-cycle.md
│   │       ├── 05-knowledge-graph.md
│   │       └── 06-setup.md
│   ├── package.json                         # Extension manifest
│   ├── tsconfig.json
│   ├── esbuild.config.js
│   └── README.md
│
├── mcp-servers/
│   ├── knowledge-graph/
│   │   ├── collab_kg/
│   │   │   ├── __init__.py
│   │   │   ├── server.py
│   │   │   ├── graph.py
│   │   │   ├── models.py
│   │   │   ├── tier_protection.py
│   │   │   ├── storage.py
│   │   │   └── ingestion.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── test_server.py
│   │   │   └── test_coverage.py
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── quality/
│   │   ├── collab_quality/
│   │   │   ├── __init__.py
│   │   │   ├── server.py
│   │   │   ├── models.py
│   │   │   ├── config.py
│   │   │   ├── gates.py
│   │   │   ├── storage.py
│   │   │   ├── trust_engine.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── formatting.py
│   │   │       ├── linting.py
│   │   │       ├── testing.py
│   │   │       └── coverage.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── test_server.py
│   │   │   └── test_coverage.py
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── governance/
│       ├── collab_governance/
│       │   ├── __init__.py
│       │   ├── server.py
│       │   ├── models.py
│       │   ├── store.py
│       │   ├── reviewer.py
│       │   ├── kg_client.py
│       │   └── task_integration.py
│       ├── tests/
│       │   └── __init__.py
│       ├── pyproject.toml
│       └── README.md
│
├── e2e/                                     # End-to-end testing harness
│   ├── run-e2e.sh
│   ├── run-e2e.py
│   ├── pyproject.toml
│   ├── README.md
│   ├── generator/
│   │   ├── project_generator.py
│   │   └── domain_templates.py
│   ├── scenarios/                           # 14 test scenarios
│   │   ├── base.py
│   │   ├── s01_kg_tier_protection.py
│   │   ├── s02_governance_decision_flow.py
│   │   ├── s03_governed_task_lifecycle.py
│   │   ├── s04_vision_violation.py
│   │   ├── s05_architecture_deviation.py
│   │   ├── s06_quality_gates.py
│   │   ├── s07_trust_engine.py
│   │   ├── s08_multi_blocker_task.py
│   │   ├── s09_scope_change_detection.py
│   │   ├── s10_completion_guard.py
│   │   ├── s11_hook_based_governance.py
│   │   ├── s12_cross_server_integration.py
│   │   ├── s13_hook_pipeline_at_scale.py
│   │   └── s14_persistence_lifecycle.py
│   ├── parallel/
│   │   └── executor.py
│   └── validation/
│       ├── assertion_engine.py
│       └── report_generator.py
│
├── docs/
│   ├── vision/
│   │   └── vision.md
│   ├── architecture/
│   │   └── architecture.md
│   ├── v1-full-architecture/
│   │   ├── ARCHITECTURE.md
│   │   ├── COLLABORATIVE_INTELLIGENCE_VISION.md
│   │   └── README.md
│   ├── project-overview.md
│   └── gap-analysis-report.md
│
├── scripts/
│   ├── build-extension.sh
│   ├── dogfood-test.sh
│   ├── start-mcp-servers.sh
│   ├── stop-mcp-servers.sh
│   ├── populate-test-data.sh
│   └── hooks/
│       └── verify-governance-review.sh
│
├── templates/                               # Target project scaffolding templates
│   ├── claude-md/
│   │   └── quality-session-CLAUDE.md
│   ├── collab/
│   │   ├── mcp-config.json
│   │   ├── session-state.md
│   │   ├── artifacts/.gitkeep
│   │   ├── task-briefs/.gitkeep
│   │   └── memory/
│   │       ├── architectural-decisions.md
│   │       ├── solution-patterns.md
│   │       └── troubleshooting-log.md
│   └── mcp.json
│
├── prompts/
│   └── claude-code-feature-intelligence-search.md
│
├── work/                                    # Working documents and research
│   ├── QUALITY_CO_AGENT_MASTER.md
│   ├── QUALITY_CO_AGENT_PLAN.md
│   ├── comparative_analysis_of_goose_and_rigour.md
│   └── comprehensive_analysis_of_local_agent_frameworks.md
│
├── .vscode/
│   ├── launch.json
│   └── tasks.json
│
├── ARCHITECTURE.md
├── CLAUDE.md
├── COLLABORATIVE_INTELLIGENCE_VISION.md
├── README.md
├── COMPLETE.md
├── DOGFOOD-CHECKLIST.md
├── RUNBOOK.md
├── package.json
├── start-servers.sh
└── validate.sh
```

### Target Project Layout

After installing the Collaborative Intelligence System on a target project, the following structure is created (by `ProjectConfigService.ensureFolderStructure()` and the setup wizard):

```
target-project/
├── .claude/
│   ├── agents/                              # Copied from product repo
│   │   ├── worker.md
│   │   ├── quality-reviewer.md
│   │   ├── kg-librarian.md
│   │   ├── governance-reviewer.md
│   │   ├── researcher.md
│   │   └── project-steward.md
│   ├── settings.json                        # Hooks configuration
│   └── settings.local.json                  # Permission allowlist (synced by wizard)
│
├── .avt/
│   ├── knowledge-graph.jsonl                # KG data (created by server)
│   ├── trust-engine.db                      # Trust engine SQLite (created by server)
│   ├── governance.db                        # Governance SQLite (created by server)
│   ├── task-briefs/                         # Worker assignments
│   ├── session-state.md                     # Session progress tracking
│   ├── memory/
│   │   ├── architectural-decisions.md
│   │   ├── solution-patterns.md
│   │   ├── troubleshooting-log.md
│   │   └── research-findings.md
│   ├── research-prompts/
│   │   └── README.md
│   ├── research-briefs/
│   │   └── README.md
│   ├── research-prompts.json                # Research prompt registry
│   └── project-config.json                  # Project configuration
│
├── docs/
│   ├── vision/
│   │   └── vision.md                        # Vision standards (starter created by wizard)
│   └── architecture/
│       └── architecture.md                  # Architecture docs (starter created by wizard)
│
├── CLAUDE.md                                # Orchestrator instructions (copied/adapted)
└── [existing project files]
```

**Key differences from the product repository layout**: The target project does not contain the `extension/`, `mcp-servers/`, `e2e/`, `scripts/`, `templates/`, `prompts/`, or `work/` directories. It contains only the runtime artifacts needed for the collaborative intelligence system to operate: agent definitions, persistent data stores, system configuration, and documentation.

## 12. Data Flow Architecture

This section traces end-to-end data paths through the system for key workflows. Each flow is grounded in actual code paths across the three MCP servers, the agent definitions, and the E2E harness.

---

### 12.1 Task Execution Flow

The governed task lifecycle is the core execution primitive. Every implementation task is "blocked from birth" -- it cannot execute until all governance reviews approve it. Two code paths create governance pairs (see Section 8.2):

```
PATH A: PostToolUse Hook (Primary - Automatic)     PATH B: MCP Tool (Explicit)
─────────────────────────────────────────────       ────────────────────────────

Agent calls TaskCreate("Implement X")               Agent calls create_governed_task(
    │                                                    subject, description,
    ▼                                                    context, review_type)
Claude Code writes task file (e.g. 1.json)               │
    │                                                    ▼
    ▼                                               Governance Server (server.py)
PostToolUse hook fires →                                 │
governance-task-intercept.py                             │
    │                                                    │
    ├─ _discover_task_id(): scan task dir               ├─ GovernanceStore.record_governed_task()
    │  for subject match → finds "1"                    │  → INSERT into governed_tasks (SQLite)
    │                                                    │
    ├─ Create review-{uuid}.json                        ├─ TaskFileManager.create_governed_task_pair()
    │  with blocks: ["1"]                               │  → fcntl.LOCK_EX → write review + impl
    │                                                    │  task files → release lock
    ├─ Modify 1.json to add                             │
    │  blockedBy: ["review-{uuid}"]                     ├─ GovernanceStore.record_task_review()
    │                                                    │  → INSERT into task_reviews
    ├─ GovernanceStore: INSERT records                   │
    │                                                    │
    ├─ Queue async review via                            │
    │  _run-governance-review.sh                         │
    │                                                    │
    └─ Return additionalContext                         └─ Return {review_task_id,
       to agent                                              implementation_task_id}
          │                                                    │
          └──────────────────┬─────────────────────────────────┘
                             ▼
          ┌────────────────────────────────────┐
          │  RESULT (same for both paths):      │
          │                                     │
          │  review-{uuid}     blocks    1.json │
          │  status: pending ──────────▶ status: │
          │  type: governance            blocked │
          │                     blockedBy:       │
          │                      [review-{uuid}] │
          │                     CANNOT EXECUTE   │
          └─────────────┬──────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│  Governance Reviewer (manual or automated)            │
│                                                       │
│  complete_task_review(review_task_id, verdict, ...)   │
│                                                       │
│  1. GovernanceStore.complete_task_review(...)          │
│     → UPDATE task_reviews SET status, verdict         │
│                                                       │
│  2. If verdict == "approved" AND no other blockers:   │
│     TaskFileManager.release_task(impl_task_id)        │
│     → Acquires fcntl.LOCK_EX                          │
│     → Removes review from blockedBy array             │
│     → If blockedBy empty: status → "pending"          │
│     → Releases lock                                   │
│                                                       │
│  3. If verdict == "blocked":                          │
│     Task stays blocked; guidance returned to caller   │
└──────────────────────────────────────────────────────┘
                           │
                           ▼ (on approval, all blockers cleared)
┌──────────────────────────────────────────────────────┐
│ Implementation task                                    │
│ status: pending  (now available for worker pickup)    │
│ blockedBy: []                                         │
│ CAN EXECUTE                                          │
└──────────────────────────────────────────────────────┘
```

**Key code paths:**
- `governance-task-intercept.py` (PostToolUse hook): `_discover_task_id()` scans task dir, creates review file, modifies impl file, stores DB records, queues async review
- `server.py`: `create_governed_task` tool handler orchestrates store + file manager (MCP path)
- `task_integration.py`: `TaskFileManager.create_governed_task_pair()` uses `fcntl.LOCK_EX` for atomicity
- `task_integration.py`: `TaskFileManager.release_task()` conditionally unblocks
- `store.py`: `GovernanceStore` persists to SQLite tables `governed_tasks` and `task_reviews`

---

### 12.2 Memory Flow

The Knowledge Graph serves as institutional memory. Data flows through JSONL persistence with in-memory indexing for reads.

```
┌──────────────┐     create_entities()     ┌─────────────────────────────┐
│  Any Agent   │──────────────────────────▶│  KnowledgeGraph (graph.py)  │
│  (via MCP)   │     add_observations()    │                             │
│              │──────────────────────────▶│  1. validate_write_access() │
│              │     search_nodes()        │     (tier_protection.py)    │
│              │──────────────────────────▶│                             │
│              │     get_entity()          │  2. Update in-memory dict   │
│              │──────────────────────────▶│     entities: dict[str, E]  │
│              │     get_entities_by_tier()│                             │
│              │──────────────────────────▶│  3. Append to JSONL         │
└──────────────┘                           │     (storage.py)            │
                                           └──────────────┬──────────────┘
                                                          │
                                                          ▼
                                           ┌─────────────────────────────┐
                                           │  JSONLStorage (storage.py)  │
                                           │                             │
                                           │  append_entity(entity)      │
                                           │  → Append one JSON line     │
                                           │  → Increment write_count    │
                                           │                             │
                                           │  If write_count >= 1000:    │
                                           │    compact()                │
                                           │    → Write all entities to  │
                                           │      temp file              │
                                           │    → Atomic rename over     │
                                           │      original               │
                                           │    → Reset write_count      │
                                           │                             │
                                           │  File: knowledge-graph.jsonl│
                                           │  Path: .avt/                │
                                           └─────────────────────────────┘

Tier Protection Check (on every write):

  ┌─────────────────────────────────────────────────────────────────────┐
  │  validate_write_access(entity, caller_role, change_approved)       │
  │                                                                     │
  │  tier = get_entity_tier(entity)                                    │
  │    → Scans observations for "protection_tier: <tier>"              │
  │    → Falls back to entityType mapping                              │
  │                                                                     │
  │  Vision tier:                                                       │
  │    → REJECT all agent writes (only human can modify)               │
  │    → Raises TierProtectionError                                    │
  │                                                                     │
  │  Architecture tier:                                                 │
  │    → REJECT unless change_approved=True                            │
  │    → Raises TierProtectionError if not approved                    │
  │                                                                     │
  │  Quality tier:                                                      │
  │    → ALLOW all writes                                              │
  └─────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `graph.py`: `KnowledgeGraph` class -- in-memory dict with JSONL backing store
- `storage.py`: `JSONLStorage.compact()` -- temp file + atomic rename after 1000 writes
- `tier_protection.py`: `validate_write_access()` -- enforces tier hierarchy
- `tier_protection.py`: `get_entity_tier()` -- extracts tier from `"protection_tier: "` observations or entityType fallback

---

### 12.3 Vision Conflict Flow

When a worker's action conflicts with a vision-tier standard, the system blocks execution at the earliest possible point.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Worker Agent                                                           │
│  calls: submit_decision(category="pattern_choice", summary="Use X")    │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Governance Server (server.py → submit_decision tool)                   │
│                                                                         │
│  1. Store decision in SQLite                                            │
│     GovernanceStore.record_decision(Decision(...))                      │
│                                                                         │
│  2. Auto-flag check (server.py):                                        │
│     if category in (deviation, scope_change):                           │
│       → Skip AI review                                                  │
│       → Return verdict: needs_human_review                              │
│       → Guidance: "Deviation/scope change requires human approval"      │
│                                                                         │
│  3. Load vision standards from KG                                       │
│     KGClient.get_vision_standards()                                     │
│     → Reads knowledge-graph.jsonl directly                              │
│     → Filters for entityType == "vision_standard"                       │
│                                                                         │
│  4. Load architecture entities from KG                                  │
│     KGClient.get_architecture_entities()                                │
│     → Filters for protection_tier == "architecture"                     │
│                                                                         │
│  5. AI Review via GovernanceReviewer.review_decision()                  │
│     → Builds prompt with standards + architecture + decision details    │
│     → Runs claude --print (temp file I/O pattern)                       │
│     → Parses JSON verdict from response                                 │
│                                                                         │
│  6. Store verdict in SQLite                                             │
│     GovernanceStore.record_review(ReviewVerdict(...))                   │
│                                                                         │
│  7. Record decision in KG for institutional memory                      │
│     KGClient.record_decision(decision, verdict)                        │
│     → Creates entity in knowledge-graph.jsonl                           │
│                                                                         │
│  Returns: ReviewVerdict {verdict, findings, guidance, standards_verified}│
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
         "approved"   "blocked"    "needs_human_review"
              │            │                │
              ▼            ▼                ▼
         Worker        Worker MUST      Worker includes
         proceeds      revise and       context when
         with impl     resubmit         presenting to
                                        human
```

**Key code paths:**
- `server.py`: `submit_decision` tool -- category auto-flag logic at top of handler
- `kg_client.py`: `KGClient.get_vision_standards()` -- reads JSONL, filters by entityType
- `reviewer.py`: `GovernanceReviewer.review_decision()` -> `_build_decision_prompt()` -> `_run_claude()`
- `reviewer.py`: `_run_claude()` -- temp file I/O with `tempfile.mkstemp()`, `GOVERNANCE_MOCK_REVIEW` bypass
- `reviewer.py`: `_parse_verdict()` -> `_extract_json()` -- handles raw JSON, ```json blocks, and brace extraction

---

### 12.4 Governance Decision Flow

This flow details the internal mechanics of a single governance review, from prompt construction through AI evaluation to verdict storage.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  GovernanceReviewer._run_claude(prompt, timeout)                        │
│  (reviewer.py)                                                           │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Check: GOVERNANCE_MOCK_REVIEW env var set?                      │    │
│  │   YES → Return deterministic JSON:                              │    │
│  │         {"verdict":"approved","findings":[],"guidance":"Mock..."}│    │
│  │   NO  → Continue to claude invocation                           │    │
│  └─────────────────────┬───────────────────────────────────────────┘    │
│                        │                                                 │
│                        ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Temp File I/O Pattern:                                          │    │
│  │                                                                  │    │
│  │ input_fd, input_path = tempfile.mkstemp(                        │    │
│  │     prefix="avt-gov-", suffix="-input.md")                      │    │
│  │ output_fd, output_path = tempfile.mkstemp(                      │    │
│  │     prefix="avt-gov-", suffix="-output.md")                     │    │
│  │                                                                  │    │
│  │ Write prompt → input_path                                       │    │
│  │ Close output_fd (so subprocess can write)                       │    │
│  │                                                                  │    │
│  │ subprocess.run(                                                  │    │
│  │     ["claude", "--print"],                                      │    │
│  │     stdin=open(input_path),                                     │    │
│  │     stdout=open(output_path, "w"),                              │    │
│  │     stderr=subprocess.PIPE,                                     │    │
│  │     timeout=timeout                                             │    │
│  │ )                                                                │    │
│  │                                                                  │    │
│  │ Read response ← output_path                                    │    │
│  │ Clean up both temp files in finally block                       │    │
│  └─────────────────────┬───────────────────────────────────────────┘    │
│                        │                                                 │
│                        ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Error Handling:                                                  │    │
│  │   returncode != 0  → verdict: needs_human_review                │    │
│  │   TimeoutExpired   → verdict: needs_human_review                │    │
│  │   FileNotFoundError→ verdict: needs_human_review                │    │
│  │                      ("claude CLI not found")                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  _parse_verdict(raw_response)                                            │
│                                                                          │
│  1. _extract_json(raw):                                                  │
│     a. If starts with "{" → return whole string                          │
│     b. Regex for ```json ... ``` blocks → return match                   │
│     c. Find first "{" to last "}" → return substring                     │
│     d. None → fallback                                                   │
│                                                                          │
│  2. Parse JSON → build ReviewVerdict:                                    │
│     - verdict: Verdict enum (approved | blocked | needs_human_review)    │
│     - findings: list[Finding] (tier, severity, description, suggestion)  │
│     - guidance: str                                                      │
│     - standards_verified: list[str]                                      │
│                                                                          │
│  3. Fallback (unparseable):                                              │
│     → verdict: needs_human_review                                        │
│     → guidance: "Could not parse... Raw response: {first 1000 chars}"   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `reviewer.py`: `_run_claude()` -- lines 64-150, complete temp file lifecycle
- `reviewer.py`: `_extract_json()` -- lines 200-220, three-stage JSON extraction
- `reviewer.py`: `_parse_verdict()` -- lines 152-198, JSON to ReviewVerdict conversion
- `models.py`: `Verdict` enum -- `approved`, `blocked`, `needs_human_review`
- `models.py`: `Finding` -- `tier`, `severity`, `description`, `suggestion`

---

### 12.5 Research Flow

The researcher subagent gathers intelligence to inform development decisions. It operates in two modes: periodic maintenance and exploratory design research.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Orchestrator                                                            │
│  Spawns researcher subagent via Task tool                                │
│  prompt: "Execute research prompt in .avt/research-prompts/rp-xxx.md"   │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Researcher Agent (.claude/agents/researcher.md)                         │
│  Model: opus (novel domains) or sonnet (changelog monitoring)            │
│  Tools: Read, Glob, Grep, WebSearch, WebFetch, collab-kg, collab-gov    │
│                                                                          │
│  Startup:                                                                │
│  1. Read research prompt from .avt/research-prompts/rp-xxx.md           │
│  2. Query KG: search_nodes("<topic>") for existing knowledge            │
│  3. Query KG: get_entities_by_tier("vision") for constraints            │
│                                                                          │
│  Execution (mode-dependent):                                             │
│                                                                          │
│  ┌─────────────────────────┐    ┌─────────────────────────────────┐     │
│  │ Periodic/Maintenance    │    │ Exploratory/Design              │     │
│  │                         │    │                                  │     │
│  │ - Monitor APIs/deps     │    │ - Deep investigation            │     │
│  │ - Detect breaking chgs  │    │ - Compare alternatives          │     │
│  │ - Track deprecations    │    │ - Evaluate technologies         │     │
│  │ - Security advisories   │    │ - Architecture research         │     │
│  │                         │    │                                  │     │
│  │ Output: Change Report   │    │ Output: Research Brief          │     │
│  │ Model: sonnet preferred │    │ Model: opus preferred           │     │
│  └─────────────┬───────────┘    └────────────────┬────────────────┘     │
│                │                                  │                      │
│                └──────────┬───────────────────────┘                      │
│                           ▼                                              │
│  Write output to .avt/research-briefs/rb-xxx.md                         │
│  Record key findings in KG via create_entities / add_observations       │
│                                                                          │
│  Governance integration:                                                 │
│  - Submit architectural recommendations as decisions                     │
│  - Vision-impacting findings flagged for human review                    │
└──────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Consumers                                                               │
│                                                                          │
│  - Orchestrator references briefs in task briefs for workers             │
│  - Workers read .avt/research-briefs/ for implementation context         │
│  - KG retains findings as searchable institutional memory                │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `.claude/agents/researcher.md`: Agent definition with dual-mode operation
- Research prompts stored in `.avt/research-prompts/rp-xxx.md`
- Research briefs output to `.avt/research-briefs/rb-xxx.md`
- KG integration via `collab-kg` MCP tools for persistent memory

---

### 12.6 Project Hygiene Flow

The project-steward subagent maintains project organization, naming conventions, and completeness.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Orchestrator                                                            │
│  Spawns project-steward subagent via Task tool                           │
│  prompt: "Perform a full project hygiene review"                         │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Project Steward (.claude/agents/project-steward.md)                     │
│  Model: sonnet                                                           │
│  Tools: Read, Write, Edit, Bash, Glob, Grep, collab-kg                  │
│                                                                          │
│  Review Areas:                                                           │
│  ┌───────────────────────┬───────────────────────────────────────────┐  │
│  │ Area                  │ What Is Checked                           │  │
│  ├───────────────────────┼───────────────────────────────────────────┤  │
│  │ Project Files         │ LICENSE, README, CONTRIBUTING, CHANGELOG, │  │
│  │                       │ CODE_OF_CONDUCT, SECURITY                 │  │
│  │ Naming Conventions    │ File/dir/variable/type casing consistency │  │
│  │ Folder Organization   │ Logical grouping, depth, orphaned files   │  │
│  │ Documentation         │ README sections, API docs, config docs    │  │
│  │ Cruft Detection       │ Unused files, duplicates, outdated config │  │
│  │ Consistency           │ Indentation, line endings, encoding,      │  │
│  │                       │ import ordering                           │  │
│  └───────────────────────┴───────────────────────────────────────────┘  │
│                                                                          │
│  Schedule:                                                               │
│  - Weekly: cruft detection                                               │
│  - Monthly: naming convention audits                                     │
│  - Quarterly: deep comprehensive reviews                                 │
│                                                                          │
│  Outputs:                                                                │
│  - Review reports (structured findings by priority)                      │
│  - KG entities (naming conventions, structure patterns)                  │
│  - Direct mechanical fixes (renaming, cruft removal)                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `.claude/agents/project-steward.md`: Agent definition with review areas and schedule
- KG integration via `collab-kg` for recording conventions and patterns

---

## 13. E2E Testing Architecture

The project includes an autonomous end-to-end testing harness that exercises all three MCP servers across 14 scenarios with 292+ structural assertions. Every run generates a unique project from a pool of 8 domains, ensuring tests validate structural properties rather than domain-specific content.

---

### 13.1 Design Philosophy

The E2E harness is built on three principles:

1. **Structural assertions, not domain assertions.** "A governed task is blocked from birth" is true regardless of whether the domain is Pet Adoption or Fleet Management. All 292+ assertions check structural properties of the system.

2. **Unique project per run.** Each execution randomly selects a domain, fills templates with randomized components, and generates a fresh workspace. This prevents tests from passing due to hardcoded values.

3. **No live model dependency.** The `GOVERNANCE_MOCK_REVIEW` environment variable causes `GovernanceReviewer._run_claude()` to return a deterministic "approved" verdict without invoking the `claude` binary. Tests exercise the full governance pipeline except the AI reasoning step.

---

### 13.2 Unique Project Generation

The project generator creates a complete workspace from domain-specific templates.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  generate_project(workspace, seed=None)                                  │
│  (e2e/generator/project_generator.py)                                    │
│                                                                          │
│  1. rng = random.Random(seed)     <- Reproducible when seed provided    │
│                                                                          │
│  2. domain = _pick_domain(rng)    <- Random from 8 domain pool          │
│     (e2e/generator/domain_templates.py)                                  │
│                                                                          │
│  3. vision_standards = _materialise_vision_standards(domain, rng)        │
│     -> For each of 5 vision templates:                                   │
│       - Pick random component from domain.components                     │
│       - Fill {domain}, {prefix}, {component} placeholders                │
│       - Assign archetype label (protocol_di, no_singletons, etc.)       │
│                                                                          │
│  4. architecture_patterns = _materialise_architecture_patterns(...)      │
│     -> For each of 2-3 architecture templates:                           │
│       - Pick random component, fill placeholders                         │
│       - Assign pattern label (service_registry, communication, etc.)     │
│                                                                          │
│  5. Write directory structure:                                           │
│     .avt/{task-briefs, memory, research-prompts, research-briefs}       │
│     docs/{vision, architecture}                                          │
│     .claude/{collab, agents}                                             │
│                                                                          │
│  6. Write knowledge-graph.jsonl (seeded with vision + arch entities)     │
│  7. Write .avt/project-config.json                                       │
│  8. Write .avt/session-state.md                                          │
│  9. Write memory stubs (4 archival .md files)                            │
│  10. Create governance.db placeholder                                    │
│                                                                          │
│  Returns: GeneratedProject dataclass                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Domain Pool (8 domains):**

| Domain | Prefix | Components |
|--------|--------|------------|
| Pet Adoption Platform | pet_adoption | AnimalProfileService, AdoptionMatchEngine, ShelterGateway |
| Restaurant Reservation System | restaurant_reservation | BookingService, TableLayoutEngine, WaitlistManager |
| Fitness Tracking App | fitness_tracking | WorkoutEngine, NutritionTracker, ProgressAnalytics |
| Online Learning Platform | online_learning | CourseManager, AssessmentEngine, EnrollmentGateway |
| Smart Home Automation | smart_home | DeviceOrchestrator, RuleEngine, SensorGateway |
| Inventory Management System | inventory_mgmt | StockLedger, ProcurementService, WarehouseRouter |
| Event Ticketing Platform | event_ticketing | TicketIssuanceService, VenueCapacityEngine, PaymentGateway |
| Fleet Management System | fleet_mgmt | VehicleTracker, RouteOptimizer, MaintenanceScheduler |

Each domain provides:
- **3 components**: service/module names used in template filling
- **5 vision templates**: parameterized vision standards with `{domain}`, `{prefix}`, `{component}` placeholders
- **2-3 architecture templates**: parameterized architecture patterns

**Key code paths:**
- `project_generator.py`: `generate_project()` -- main entry point, lines 325-406
- `project_generator.py`: `_materialise_vision_standards()` -- template filling, lines 105-129
- `domain_templates.py`: `get_domain_pool()` -- returns all 8 `DomainTemplate` instances
- `domain_templates.py`: `DomainTemplate` dataclass -- `name`, `prefix`, `components`, `vision_templates`, `architecture_templates`

---

### 13.3 Scenario Inventory

All 14 scenarios inherit from `BaseScenario` (in `e2e/scenarios/base.py`) which provides assertion helpers and timing/error-handling wrappers.

| ID | Scenario | Assertions | What It Validates |
|----|----------|------------|-------------------|
| s01 | KG Tier Protection | 12 | CRUD at all three tiers. Vision entities immutable by worker-role agents. Architecture entities require `change_approved=True`. Quality entities freely writable. |
| s02 | Governance Decision Flow | ~15 | Decision storage in SQLite, AI review verdict flow, status queries, decision history filtering. |
| s03 | Governed Task Lifecycle | 27 | Task pair creation (`create_governed_task_pair`), blocking from birth (`blockedBy` array), release on approval, multi-blocker stacking, blocked verdict behavior. |
| s04 | Vision Violation | ~12 | Attempts to modify vision-tier entities are rejected with `TierProtectionError`. Workers cannot delete, add observations to, or modify vision standards. |
| s05 | Architecture Deviation | ~14 | `deviation` and `scope_change` decision categories are stored and auto-flagged as `needs_human_review` without AI review. |
| s06 | Quality Gates | ~10 | `GovernanceStore.get_status()` returns accurate aggregate counts. Gate configuration read from `.avt/project-config.json`. |
| s07 | Trust Engine | ~12 | Finding record -> dismiss (requires justification) -> audit trail lifecycle. `TrustDecision.BLOCK` for new findings, `TrustDecision.TRACK` for previously dismissed. |
| s08 | Multi-Blocker Task | 19 | 3 stacked review blockers on a single task. Blockers released one at a time. Task stays blocked until ALL are approved. |
| s09 | Scope Change Detection | ~10 | `scope_change` and `deviation` categories -> automatic `needs_human_review` verdict. No AI review invoked. |
| s10 | Completion Guard | ~15 | Unresolved review blocks prevent completion. Missing plan reviews are caught. `submit_completion_review` validates all decisions were reviewed. |
| s12 | Cross-Server Integration | 25 | KG + Governance + Task system interplay. Vision standards loaded from KG for governance review. Decisions recorded back to KG. Task lifecycle spans all three servers. |

**Note:** There is no s11 in the current implementation.

**BaseScenario assertion helpers** (from `e2e/scenarios/base.py`):
- `assert_true(condition, message)` -- basic boolean assertion
- `assert_equal(actual, expected, message)` -- equality check
- `assert_contains(collection, item, message)` -- membership check
- `assert_error(callable, error_type, message)` -- expected exception
- `assert_no_error(callable, message)` -- no exception expected

**Key code paths:**
- `base.py`: `BaseScenario` -- `execute()` wrapper with timing, `ScenarioResult` dataclass
- Each scenario file: `e2e/scenarios/s{NN}_{name}.py` -- class inheriting `BaseScenario`
- `run-e2e.py`: Imports all 11 scenario classes and passes them to the executor

---

### 13.4 Execution Model

Scenarios run in parallel with full isolation. The `ParallelExecutor` provides each scenario with its own KG, governance store, and task directory.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  run-e2e.sh                                                              │
│                                                                          │
│  1. WORKSPACE=$(mktemp -d /tmp/avt-e2e-XXXXXX)                         │
│  2. export GOVERNANCE_MOCK_REVIEW=true                                   │
│  3. trap cleanup EXIT                                                    │
│  4. cd e2e/ && uv run python run-e2e.py --workspace $WORKSPACE          │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  run-e2e.py                                                              │
│                                                                          │
│  1. generate_project(workspace, seed=args.seed)                          │
│     -> Returns GeneratedProject with vision, architecture, paths         │
│                                                                          │
│  2. Instantiate all 11 scenario classes                                   │
│  3. executor = ParallelExecutor(scenarios, project, workspace)           │
│  4. results = executor.run_all()                                         │
│  5. generate_report(results, workspace / "e2e-report.json")             │
│  6. print_summary(results)                                               │
│  7. sys.exit(0 if all passed else 1)                                     │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  ParallelExecutor (e2e/parallel/executor.py)                             │
│                                                                          │
│  Route by isolation_mode:                                                │
│  - "library" scenarios -> ThreadPoolExecutor(max_workers=4)             │
│  - Other modes -> sequential execution                                   │
│                                                                          │
│  Per-scenario isolation setup:                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  scenario_dir = workspace / "scenarios" / scenario.id              │ │
│  │                                                                     │ │
│  │  KnowledgeGraph:                                                    │ │
│  │    kg_path = scenario_dir / "knowledge-graph.jsonl"                │ │
│  │    Pre-seeded with project's 5 vision + 2-3 arch entities          │ │
│  │                                                                     │ │
│  │  GovernanceStore:                                                   │ │
│  │    db_path = scenario_dir / "governance.db"                        │ │
│  │    Fresh SQLite database per scenario                               │ │
│  │                                                                     │ │
│  │  TaskFileManager:                                                   │ │
│  │    task_dir = scenario_dir / "tasks"                                │ │
│  │    Empty directory per scenario                                      │ │
│  │                                                                     │ │
│  │  Injected into scenario as constructor arguments                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  Results collected via futures, exceptions caught per-scenario           │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `run-e2e.sh`: Shell wrapper -- workspace creation, env vars, cleanup trap
- `run-e2e.py`: Python orchestrator -- project generation, scenario instantiation, execution, reporting
- `executor.py`: `ParallelExecutor` -- `ThreadPoolExecutor(max_workers=4)`, per-scenario isolation
- `executor.py`: Isolation setup -- KG JSONL copy, fresh SQLite, fresh task dir, pre-seeded entities

---

### 13.5 Assertion Engine

The assertion engine (`e2e/validation/assertion_engine.py`) provides domain-agnostic assertion helpers that return `(bool, str)` tuples for structured reporting.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  AssertionEngine                                                         │
│  (e2e/validation/assertion_engine.py)                                    │
│                                                                          │
│  Structural Assertions (all return (bool, str)):                         │
│                                                                          │
│  assert_tier_protected(entity, operation, caller_role)                  │
│    -> Verifies tier protection enforcement                               │
│                                                                          │
│  assert_verdict(review_verdict, expected_verdict)                       │
│    -> Checks governance verdict matches expected                         │
│                                                                          │
│  assert_task_blocked(task_status)                                       │
│    -> Confirms task has non-empty blockedBy array                        │
│                                                                          │
│  assert_task_released(task_status)                                      │
│    -> Confirms task has empty blockedBy and status "pending"             │
│                                                                          │
│  assert_has_findings(review_verdict, min_count)                         │
│    -> Checks findings list length >= min_count                           │
│                                                                          │
│  assert_finding_severity(finding, expected_severity)                    │
│    -> Verifies a specific finding has expected severity                  │
│                                                                          │
│  All assertions are domain-agnostic -- they check structure,             │
│  not content. "Task is blocked" is true for Pet Adoption                 │
│  and Fleet Management alike.                                             │
└──────────────────────────────────────────────────────────────────────────┘
```

**Report Generation** (`e2e/validation/report_generator.py`):

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ReportGenerator                                                         │
│                                                                          │
│  generate_report(results, output_path):                                  │
│    -> JSON report with per-scenario results                              │
│    -> Overall pass/fail summary                                          │
│    -> Timing data                                                        │
│                                                                          │
│  print_summary(results):                                                 │
│    -> ANSI-colored console output                                        │
│    -> Pass/fail counts                                                   │
│    -> Failure details with assertion messages                            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `assertion_engine.py`: `AssertionEngine` class -- all assertion methods
- `report_generator.py`: `ReportGenerator` -- JSON + console output
- `report_generator.py`: `generate_report()` and `print_summary()` convenience functions

---

### 13.6 When to Run

| Trigger | Reason |
|---------|--------|
| After modifying any MCP server code | Catches contract drift between servers |
| Before significant releases | Confirms all three servers work together |
| After governance or task system changes | s03, s08, s10 specifically test governed task flow |
| After KG tier protection changes | s01, s04 test tier enforcement |
| After trust engine changes | s07 tests the full finding lifecycle |
| Periodically (CI or manual) | Random domain selection means each run is a uniqueness test |

**Running the harness:**

```bash
./e2e/run-e2e.sh              # Standard run (workspace auto-cleaned)
./e2e/run-e2e.sh --keep       # Preserve workspace for debugging
./e2e/run-e2e.sh --seed 42    # Reproducible project generation
./e2e/run-e2e.sh --verbose    # Enable debug logging
```

**Interpreting failures:** If a scenario fails, the problem is in the server code, not the test. Scenarios call actual Python library APIs directly. The E2E report includes per-assertion pass/fail with descriptive messages to trace the failure to a specific code path.

---

## 14. Research System

The research system provides structured intelligence gathering through the researcher subagent, operating in two distinct modes with governance integration.

---

### 14.1 Dual-Mode Operation

The researcher subagent (`.claude/agents/researcher.md`) operates in two modes, each with different characteristics:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Research System                                   │
│                                                                          │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────┐ │
│  │  Periodic / Maintenance     │    │  Exploratory / Design           │ │
│  │                             │    │                                  │ │
│  │  Purpose:                   │    │  Purpose:                       │ │
│  │  Track external changes     │    │  Inform new development         │ │
│  │                             │    │                                  │ │
│  │  Activities:                │    │  Activities:                    │ │
│  │  - Monitor API changes      │    │  - Evaluate technologies        │ │
│  │  - Detect breaking changes  │    │  - Compare alternatives         │ │
│  │  - Track deprecations       │    │  - Research unfamiliar domains  │ │
│  │  - Security advisories      │    │  - Architecture investigation   │ │
│  │                             │    │                                  │ │
│  │  Model: sonnet (preferred)  │    │  Model: opus (preferred)        │ │
│  │  Output: Change Report      │    │  Output: Research Brief         │ │
│  │                             │    │                                  │ │
│  │  Schedule: configurable     │    │  Trigger: on-demand by          │ │
│  │  (weekly, monthly, etc.)    │    │  orchestrator                   │ │
│  └─────────────────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

**Model selection criteria:**

| Criterion | Use Opus 4.6 | Use Sonnet 4.5 |
|-----------|--------------|----------------|
| Novel or unfamiliar domain | Yes | |
| Architectural decision research | Yes | |
| Security analysis | Yes | |
| Ambiguous requirements | Yes | |
| Changelog monitoring | | Yes |
| Version update tracking | | Yes |
| Straightforward API documentation | | Yes |
| Known domain, factual lookup | | Yes |

---

### 14.2 Research Workflow

```
┌──────────────────────────────────────────────────────────────────────────┐
│  1. Create Research Prompt                                               │
│     Location: .avt/research-prompts/rp-{id}.md                          │
│     Created by: Orchestrator (via dashboard or manually)                 │
│                                                                          │
│     Content:                                                             │
│     - type: periodic | exploratory                                       │
│     - topic: what to research                                            │
│     - context: why this research matters                                 │
│     - scope: boundaries of the investigation                             │
│     - model_hint: opus | sonnet | auto                                   │
│     - output: change_report | research_brief                             │
│     - schedule: (for periodic only) type, frequency, time                │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  2. Spawn Researcher                                                     │
│     Orchestrator uses Task tool with subagent_type: researcher           │
│     prompt: "Execute research prompt in .avt/research-prompts/rp-xxx.md"│
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  3. Researcher Execution                                                 │
│                                                                          │
│  a. Read research prompt                                                 │
│  b. Query KG for existing knowledge on topic                             │
│     -> search_nodes("<topic>")                                           │
│     -> get_entities_by_tier("vision") for constraints                    │
│  c. Gather intelligence using available tools                            │
│     -> WebSearch for current information                                 │
│     -> WebFetch for specific documentation                               │
│     -> Read for local files and configs                                  │
│  d. Analyze and synthesize findings                                      │
│  e. Record key findings in KG                                            │
│     -> create_entities() for new knowledge                               │
│     -> add_observations() for updates to existing entities               │
│  f. Submit architectural recommendations as governance decisions          │
│     -> submit_decision() for vision-impacting findings                   │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  4. Output                                                               │
│     Location: .avt/research-briefs/rb-{id}.md                           │
│                                                                          │
│     Change Report (periodic):                                            │
│     - Structured list of detected changes                                │
│     - Impact assessment per change                                       │
│     - Actionable items for the team                                      │
│                                                                          │
│     Research Brief (exploratory):                                        │
│     - Comprehensive analysis                                             │
│     - Technology comparison matrix                                       │
│     - Recommendations with tradeoffs                                     │
│     - References and sources                                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 14.3 Governance Integration

The researcher integrates with the governance system when findings have architectural or vision implications:

- **Architectural recommendations** are submitted as `pattern_choice` or `component_design` decisions via `submit_decision()`, following the standard governance review flow.
- **Vision-impacting discoveries** (e.g., a dependency deprecation that forces a pattern change) are flagged with category `deviation` or `scope_change`, which auto-triggers `needs_human_review`.
- **KG updates** use the standard tier protection: the researcher can write quality-tier entities freely but cannot modify vision or architecture tiers.

---

### 14.4 Research Prompt Registry

Research prompts are managed in two locations:

1. **Individual prompt files**: `.avt/research-prompts/rp-{id}.md` -- full prompt definition with metadata
2. **Registry index**: `.avt/research-prompts.json` -- index of all prompts for dashboard display and scheduling

The registry tracks:
- Prompt ID and title
- Research type (periodic or exploratory)
- Schedule configuration (for periodic prompts)
- Last execution timestamp
- Associated research brief IDs

---

### 14.5 Consumer Integration

Research outputs feed into the broader system:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Research Brief (.avt/research-briefs/rb-xxx.md)                         │
│                                                                          │
│  Consumed by:                                                            │
│                                                                          │
│  ┌─────────────────┐  References briefs in task briefs                  │
│  │  Orchestrator    │────────────────────────────────────▶ Task Briefs   │
│  └─────────────────┘                                                     │
│                                                                          │
│  ┌─────────────────┐  Reads briefs for implementation context           │
│  │  Workers         │────────────────────────────────────▶ Code          │
│  └─────────────────┘                                                     │
│                                                                          │
│  ┌─────────────────┐  KG entities from research are searchable          │
│  │  Any Agent       │────────────────────────────────────▶ KG Search     │
│  └─────────────────┘                                                     │
│                                                                          │
│  ┌─────────────────┐  Reviews findings for governance impact            │
│  │  Gov Reviewer    │────────────────────────────────────▶ Verdicts      │
│  └─────────────────┘                                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Project Rules System

Project rules are concise behavioral guidelines that complement vision standards and architectural patterns. They cover behavioral guidance that tier-protected entities and quality gates cannot check.

---

### 15.1 Rule Structure

Rules live in `.avt/project-config.json` and are distinct from vision standards (KG tier-protected) and quality gates (deterministic checks).

```
┌─────────────────────────────────────────────────────────────────────────┐
│  .avt/project-config.json                                               │
│                                                                          │
│  {                                                                       │
│    "settings": {                                                         │
│      "autoGovernance": true,                <- governance integration    │
│      "qualityGates": { ... },              <- gate configuration         │
│      "kgAutoCuration": true                <- KG librarian trigger       │
│    },                                                                    │
│    "quality": {                                                          │
│      "testCommands": { ... },              <- per-language commands      │
│      "lintCommands": { ... },                                            │
│      "buildCommands": { ... },                                           │
│      "formatCommands": { ... }                                           │
│    },                                                                    │
│    "permissions": []                        <- rule definitions          │
│  }                                                                       │
│                                                                          │
│  Rule levels:                                                            │
│  - ENFORCE: Non-negotiable. Agent must comply.                           │
│  - PREFER:  Should follow unless specific reason documented.             │
│                                                                          │
│  Rule scopes:                                                            │
│  - Per-agent-type filtering (worker, researcher, steward, etc.)          │
│  - Only relevant rules are injected into each agent's context            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 15.2 Rule Injection Protocol

When the orchestrator spawns a subagent, it compiles applicable rules into a compact preamble prepended to the task prompt:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Orchestrator spawns agent                                               │
│                                                                          │
│  1. Read .avt/project-config.json                                        │
│  2. Filter rules by:                                                     │
│     a. Agent scope (worker, researcher, steward, etc.)                   │
│     b. Enabled status                                                    │
│  3. Compile into preamble (~200-400 tokens):                             │
│                                                                          │
│     ## Project Rules                                                     │
│     These rules govern how work is done in this project. Follow them.    │
│                                                                          │
│     ENFORCE:                                                             │
│     - [enabled enforce-level rules, filtered by agent scope]             │
│                                                                          │
│     PREFER (explain if deviating):                                       │
│     - [enabled prefer-level rules, filtered by agent scope]              │
│                                                                          │
│     ---                                                                  │
│                                                                          │
│  4. Prepend preamble to actual task prompt                               │
│  5. Spawn agent with combined prompt                                     │
│                                                                          │
│  Design constraints:                                                     │
│  - Preamble target: 200-400 tokens                                       │
│  - Rationale is NOT injected (lives in KG for deep context lookup)      │
│  - More rules = reduced agent effectiveness                              │
└──────────────────────────────────────────────────────────────────────────┘
```

**Worker agent compliance** (from `.claude/agents/worker.md`):

The worker startup protocol explicitly includes:
> "Check project rules injected at the top of your task context (under '## Project Rules'). Rules marked ENFORCE are non-negotiable. Rules marked PREFER should be followed unless you document a specific reason to deviate."

---

### 15.3 Relationship to Other Systems

Project rules complement but do not replace the other governance mechanisms:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Governance Layer Stack                                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Vision Standards (KG tier: vision, human-only modification)     │   │
│  │  "All services use protocol-based DI"                            │   │
│  │  -> Enforced by: tier protection + governance review AI          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Architecture Patterns (KG tier: architecture, approved changes) │   │
│  │  "ServiceRegistry pattern for service discovery"                 │   │
│  │  -> Enforced by: tier protection + governance decision review    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Project Rules (.avt/project-config.json, injected into prompts)│   │
│  │  "ENFORCE: Always run tests before committing"                   │   │
│  │  -> Enforced by: agent compliance (prompt-level instruction)    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Quality Gates (deterministic, automated checks)                 │   │
│  │  build: pass, lint: pass, tests: pass, coverage: >= 80%         │   │
│  │  -> Enforced by: Quality MCP server check_all_gates()           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Each layer covers a different enforcement mechanism:                    │
│  - Vision/Architecture: KG tier protection (prevents writes)            │
│  - Project Rules: Prompt injection (guides agent behavior)              │
│  - Quality Gates: Deterministic tooling (blocks on failure)             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 15.4 KG Integration for Rule Rationale

Rule rationale is intentionally not injected into the agent prompt (to keep the preamble compact). Instead, rationale is stored in the KG:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Rule: "ENFORCE: No direct database queries outside repository classes" │
│                                                                          │
│  Prompt Injection (what agents see):                                     │
│  "No direct database queries outside repository classes"                │
│                                                                          │
│  KG Entity (for agents that need deeper context):                        │
│  {                                                                       │
│    "name": "rule_no_direct_db",                                         │
│    "entityType": "project_rule",                                        │
│    "observations": [                                                     │
│      "protection_tier: quality",                                        │
│      "level: enforce",                                                   │
│      "scope: worker",                                                    │
│      "rationale: Direct DB access in services creates tight coupling    │
│       and makes testing difficult. Repository pattern allows mocking    │
│       and query optimization in isolation.",                             │
│      "configured_by: human via setup wizard"                            │
│    ]                                                                     │
│  }                                                                       │
│                                                                          │
│  Agents can query: search_nodes("project rules") for full rationale    │
└──────────────────────────────────────────────────────────────────────────┘
```

This separation ensures:
- **Prompt compactness**: Agents get concise instructions without rationale bloat
- **Deep context available**: Agents that need to understand "why" can query the KG
- **Rationale is curated**: The KG librarian maintains and updates rationale alongside other institutional memory

## 16. Technology Stack

### 16.1 Core Technologies

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Orchestration** | Claude Code CLI + subagents | Latest | Native orchestration platform |
| **AI Models** | Opus 4.6 (worker, quality-reviewer, researcher), Sonnet 4.5 (kg-librarian, governance-reviewer, project-steward), Haiku 4.5 (mechanical tasks) | Feb 2026 | Per-agent model routing based on task complexity |
| **MCP Servers** | Python + FastMCP | Python >=3.12, FastMCP >=2.0.0 | Consistent language across all three servers; FastMCP simplifies server creation |
| **KG Storage** | JSONL | — | Simple, portable, matches Anthropic's KG Memory format |
| **Quality Storage** | SQLite | — | Trust engine history, quality gate state |
| **Governance Storage** | SQLite | — | Decision history, review verdicts, governed task state |
| **VS Code Extension** | TypeScript | >=5.7.0 | VS Code extension platform |
| **Extension Build** | esbuild | >=0.24.0 | Fast bundling for extension backend |
| **Dashboard Webview** | React + TypeScript | React >=19.0.0 | Rich reactive UI for dashboard, wizard, tutorial, governance panel |
| **Webview Build** | Vite | >=6.0.0 | Fast dev server + production build |
| **Webview Styling** | Tailwind CSS | >=3.4.0 | Utility-first CSS with PostCSS + Autoprefixer |
| **E2E Testing** | Python + ThreadPoolExecutor + Pydantic | Python >=3.12, Pydantic >=2.0.0 | Parallel scenario execution with isolation and typed assertions |
| **Build System** | Hatchling | Latest | Python package builds for all MCP servers and E2E harness |
| **Version Control** | Git + worktrees | — | Code state management, worker isolation via branches |
| **Package Management** | npm (extension + webview), uv (Python servers + E2E) | — | Standard per ecosystem |
| **OS** | macOS (Darwin) | — | Primary developer platform |

### 16.2 Version Pinning Notes

All three MCP servers (`collab-kg`, `collab-quality`, `collab-governance`) share the same dependency floor: `fastmcp>=2.0.0`, `pydantic>=2.0.0`, Python `>=3.12`. The E2E harness (`avt-e2e`) depends on `pydantic>=2.0.0` and Python `>=3.12`. All use Hatchling as the build backend.

The extension backend pins `typescript>=5.7.0` and `esbuild>=0.24.0`. The webview dashboard pins `react>=19.0.0`, `vite>=6.0.0`, and `tailwindcss>=3.4.0`. The extension targets VS Code engine `>=1.95.0`.

All packages are at version `0.1.0` (pre-release).

### 16.3 Platform Features

Claude Code provides the execution environment for the entire system. The following table catalogs which platform features the system actively uses, which are available but not yet configured, and which are planned for adoption.

| Feature | Status | How Used |
|---------|--------|----------|
| Custom subagents | **Active** | 6 agents defined in `.claude/agents/`: worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward |
| MCP servers (SSE) | **Active** | 3 servers registered in `.claude/settings.json`: collab-kg (port 3101), collab-quality (port 3102), collab-governance (port 3103) |
| PostToolUse hooks | **Active** | `TaskCreate` hook runs `scripts/hooks/governance-task-intercept.py` to enforce "blocked from birth" invariant on every task creation (core enforcement mechanism) |
| PreToolUse hooks | **Active** | `ExitPlanMode` hook runs `scripts/hooks/verify-governance-review.sh` as safety net for plan review |
| Model routing | **Active** | Per-agent model assignment in `.claude/settings.json` agents block: Opus 4.6 for worker/quality-reviewer, Sonnet 4.5 (default) for kg-librarian/governance-reviewer |
| Skills | **Active** | `/e2e` skill for E2E test harness execution |
| Commands | **Active** | `/project-overview` command for project context |
| Task List (native) | **Active** | `CLAUDE_CODE_ENABLE_TASKS=true` + `CLAUDE_CODE_TASK_LIST_ID` for native task system with cross-session persistence; PostToolUse hook writes governance pairs to native task files |
| Git worktrees | **Active** | Worker isolation via `git worktree add ../project-worker-N -b task/NNN-description` |
| MCP Tool Search | **Planned (immediate)** | 85% context reduction for MCP tool loading. Config-only change: set `ENABLE_TOOL_SEARCH=auto:5`. Requires Sonnet 4+ or Opus 4+ (not Haiku) |
| Effort controls | **Planned (immediate)** | Per-agent effort levels: max for worker/quality-reviewer, medium for kg-librarian, low for project-steward. Config change in agent definitions |
| Context compaction | **Available** | Automatic with Opus 4.6 for long-running orchestrator sessions. No configuration needed |
| 1M context window | **Available** | Automatic with Opus 4.6. Enables extended code reviews and larger session contexts without truncation |
| Setup hooks | **Planned (short-term)** | `--init` for project initialization (KG seeding, config validation), `--maintenance` for periodic tasks (cruft detection, dependency monitoring) |
| Agent Teams | **Monitoring** | Experimental platform feature. Aligns conceptually with our orchestration model (delegate mode, shared task list, plan approval). May replace custom subagent coordination when stable. Potential use: worker swarm teams for parallel implementation. Current blockers: no session resumption for teammates, one team per session, no nested teams |
| Plugins | **Planned (later)** | Natural plugin boundaries exist (3 MCP servers, 6 agents, 1 skill, 1 command, 1 hook). APIs still maturing. Will evaluate after Quality server gate stubs are replaced and governance review protocol stabilizes |

---

## 17. Current Status and Evolution Path

### 17.1 Current Status

This section replaces the v1 "Implementation Phases" checklist, which listed unchecked items that are now substantially complete. The following table reflects the actual state of each component as of February 2026.

| Component | Status | Notes |
|-----------|--------|-------|
| Knowledge Graph Server | **Operational** | 11 tools, JSONL persistence with load-on-startup/append-on-write, three-tier protection (vision/architecture/quality), document ingestion pipeline, full test coverage |
| Quality Server | **Operational (partial gate stubs)** | 8 tools exposed. Trust engine with SQLite persistence is fully functional. `auto_format`, `run_lint`, `run_tests`, and `check_coverage` make real subprocess calls (ruff, prettier, pytest, eslint). The **build gate** and **findings gate** in `check_all_gates()` are stubs returning `passed: true` |
| Governance Server | **Operational** | 10 tools, SQLite persistence, AI-powered review via `claude --print` with governance-reviewer agent, governed task lifecycle with multi-blocker support, KG integration for standard loading |
| Worker Agent | **Operational** | Full governance integration: reads task brief, checks project rules from `.avt/project-config.json`, queries KG for context (`search_nodes`, `get_entities_by_tier`), submits decisions via `submit_decision` (blocks until verdict), implements within task brief scope, runs `check_all_gates()`, calls `submit_completion_review` before reporting done |
| Quality Reviewer Agent | **Operational** | Three-lens review protocol (vision > architecture > quality). Model: Opus 4.6. 6 tools including KG and Quality server access |
| KG Librarian Agent | **Operational** | Memory curation: consolidation, promotion, stale entry removal, archival file sync to `.avt/memory/`. Model: Sonnet 4.5. 5 tools |
| Governance Reviewer Agent | **Operational** | AI review called internally by governance server via `claude --print`. Reviews decisions and plans through vision alignment and architectural conformance lenses. Model: Sonnet 4.5. 4 tools |
| Researcher Agent | **Operational** | Dual-mode research: periodic/maintenance (dependency monitoring, breaking change detection) and exploratory/design (technology evaluation, architectural decisions). Model: Opus 4.6. 7 tools |
| Project Steward Agent | **Operational** | Project hygiene: naming conventions, folder organization, documentation completeness, cruft detection. Periodic cadence: weekly/monthly/quarterly. Model: Sonnet 4.5. 7 tools |
| VS Code Extension | **Operational** | Dashboard webview, 9-step setup wizard, 10-step workflow tutorial, 6-step VS Code walkthrough, governance panel, research prompts panel, 3 MCP clients (KG, Quality, Governance), 4 TreeViews, 15 commands (12 user-facing, 3 internal) |
| E2E Test Harness | **Operational** | 14 scenarios (s01-s14), 292+ structural domain-agnostic assertions, parallel execution with full isolation, random domain generation from 8 templates, mock review mode |
| CLAUDE.md Orchestration | **Operational** | All protocols documented: task decomposition, governance checkpoints, quality review, memory curation, research, project hygiene, drift detection |

### 17.2 Known Gaps

These are known deficiencies in the current implementation. They do not block operation but represent incomplete or inconsistent areas.

**Quality server gates fully connected.** All five gates in `check_all_gates()` now make real checks. The **build gate** reads configured build commands from `.avt/project-config.json` (`quality.buildCommands`) and runs them via `subprocess.run()` with a 300-second timeout. The **findings gate** queries the trust engine for unresolved critical/high-severity findings. The `auto_format`, `run_lint`, `run_tests`, and `check_coverage` tools continue to make real subprocess calls (ruff, prettier, eslint, pytest).

**Extension-system state drift.** The extension dashboard was built incrementally as the system evolved. Some UI components may reference patterns or display states that have since changed. The gap analysis (February 2026) identified that the extension's scope has grown far beyond "observability only" but some internal state representations have not kept pace with governance and research system evolution.

**Agent definitions outside settings.json.** The researcher and project-steward agents are defined in `.claude/agents/` but are not listed in the `agents` block of `.claude/settings.json`. They inherit the `defaultModel: sonnet` setting. The researcher should be explicitly configured for Opus 4.6 to match its documented model assignment.

**v1 scaffolding remnants.** Code from the v1 architecture (Communication Hub server scaffolding, extension session management) is preserved in the codebase and in `docs/v1-full-architecture/`. This is intentional (available for reactivation) but adds cognitive load for new contributors.

### 17.3 Evolution Path

Items are ordered by priority. Effort and dependency information is included to support planning.

| Priority | Item | Effort | Depends On | Notes |
|----------|------|--------|-----------|-------|
| **Immediate** | Enable MCP Tool Search | Config only | — | Set `ENABLE_TOOL_SEARCH=auto:5` in settings. 85% context reduction for tool loading |
| **Immediate** | Set effort controls per agent | Config only | — | Add effort levels to agent definitions in `.claude/settings.json` |
| **Immediate** | Update model references to Opus 4.6 | Trivial | — | Replace Opus 4.5 references in documentation. Code references are model-agnostic |
| **Immediate** | Add researcher/steward to settings.json agents | Config only | — | Explicitly configure model and tools for researcher (Opus 4.6) and project-steward (Sonnet 4.5) |
| **Done** | ~~Replace Quality server gate stubs~~ | Medium | — | Build gate reads `.avt/project-config.json` build commands, findings gate queries trust engine for unresolved critical/high findings. Completed February 2026 |
| **Short-term** | Convert common workflows to model-invocable skills | Low | — | Identify orchestrator patterns that repeat across sessions. Candidates: governance review flow, worker spawn-and-review cycle, KG curation trigger |
| **Short-term** | Add setup hooks (`--init`, `--maintenance`) | Low | — | `--init`: validate project config, seed KG with vision/architecture docs, verify MCP server connectivity. `--maintenance`: run cruft detection, check dependency updates |
| **Short-term** | Align extension UI with current system state | Medium | Architecture doc v2 | Audit dashboard components against current MCP server APIs. Update state representations, add missing governance/research views, remove stale references |
| **Medium-term** | Plugin packaging evaluation | Medium | API stability | Assess whether MCP server APIs, agent definitions, and hook contracts are stable enough to package. Define plugin boundaries. Prototype single-plugin extraction |
| **Medium-term** | Agent Teams evaluation | Evaluate | Platform maturation | Monitor experimental status. When session resumption is supported and nested teams are available, prototype worker swarm team alongside governance policy layer |
| **Future** | Cross-project memory | High | KG design | KG entities that travel between projects. Requires namespace design, conflict resolution, tier portability rules |
| **Future** | Multi-team coordination | High | Agent Teams stabilization | Multiple teams with different specializations (implementation team, review team, research team) coordinating on the same project |
| **Future** | Plugin distribution | Medium | Plugin packaging | Publish to Claude Code plugin marketplace. Requires stable APIs, documentation, versioning strategy |

### 17.4 What Was Completed Since v1

For historical context, the following summarizes what the v1 "Implementation Phases" planned and what actually shipped. All four phases are substantially complete, with the Quality server gate stubs (build and findings gates in `check_all_gates()`) being the primary remaining item from Phase 1.

| v1 Phase | What Was Planned | What Shipped |
|----------|-----------------|-------------|
| **Phase 1: Make MCP Servers Real** | KG: JSONL persistence, delete tools, compaction. Quality: real subprocess calls, SQLite trust engine | KG: fully operational with 11 tools (3 beyond plan), JSONL persistence, tier protection. Quality: 8 tools operational with real subprocess calls, trust engine with SQLite complete. All 5 quality gates now fully connected |
| **Phase 2: Create Subagents + Validate E2E** | 3 agents (worker, quality-reviewer, kg-librarian), CLAUDE.md orchestration, settings.json hooks, end-to-end validation | 6 agents (added governance-reviewer, researcher, project-steward), full CLAUDE.md orchestration with governance/research/hygiene protocols, PostToolUse + PreToolUse hooks, end-to-end workflow validated |
| **Phase 3: Build Extension as Monitoring Layer** | MCP clients, TreeView wiring, file watchers, diagnostics, dashboard, status bar | 3 MCP clients, 4 TreeViews, dashboard webview with React 19, 9-step wizard, 10-step tutorial, VS Code walkthrough, governance panel, research prompts panel, 15 commands (12 user-facing, 3 internal). Scope significantly exceeded plan |
| **Phase 4: Expand and Harden** | Event logging, cross-project memory, multi-worker parallelism, FastMCP 3.0 migration, installation script | E2E test harness (14 scenarios, 292+ assertions), full governance system (not in original plan), research system (not in original plan), project hygiene system (not in original plan). Cross-project memory and FastMCP migration remain future items |

---

## 18. Verification

### 18.1 E2E Test Harness (Primary Verification)

The E2E test harness is the primary verification mechanism for all three MCP servers. It exercises the Python library APIs directly with structural, domain-agnostic assertions.

**Characteristics:**
- 14 scenarios covering KG, Quality, and Governance servers
- 292+ assertions that are structural (not domain-specific)
- Parallel execution via `ThreadPoolExecutor` with full isolation per scenario (separate JSONL, SQLite, task directories)
- Each run generates a unique project from 8 domain templates (Pet Adoption, Restaurant Reservation, Fitness Tracking, etc.)
- `GOVERNANCE_MOCK_REVIEW` environment variable enables deterministic testing without a live `claude` binary

**How to run:**

```bash
./e2e/run-e2e.sh              # Standard run (workspace cleaned up after)
./e2e/run-e2e.sh --keep       # Preserve workspace for debugging
./e2e/run-e2e.sh --seed 42    # Reproducible project generation
./e2e/run-e2e.sh --verbose    # Enable debug logging
```

Or use the `/e2e` skill from within Claude Code.

**When to run:**
- After modifying any MCP server code (catches contract drift)
- Before significant releases (confirms all three servers work together)
- After governance or task system changes (scenarios s03, s08, s10 specifically test the governed task flow)
- Periodically (random domain selection means each run is a genuine uniqueness test)

**Scenario coverage:**

| Scenario | File | What It Validates |
|----------|------|-------------------|
| s01 | `s01_kg_tier_protection.py` | KG CRUD operations + tier-based access control. Vision-tier entities are immutable by workers |
| s02 | `s02_governance_decision_flow.py` | Decision storage, review verdicts (approved/blocked/needs_human_review), status queries |
| s03 | `s03_governed_task_lifecycle.py` | Task pair creation via `create_governed_task`, blocking from birth, release on approval |
| s04 | `s04_vision_violation.py` | Attempts to modify vision-tier entities are rejected regardless of caller |
| s05 | `s05_architecture_deviation.py` | `deviation` and `scope_change` categories are stored and flagged correctly |
| s06 | `s06_quality_gates.py` | `GovernanceStore.get_status()` returns accurate aggregates across decisions |
| s07 | `s07_trust_engine.py` | Finding record, dismiss with justification, audit trail lifecycle |
| s08 | `s08_multi_blocker_task.py` | 3 stacked blockers on a single task, released one at a time, task unblocks only when all clear |
| s09 | `s09_scope_change_detection.py` | `scope_change`/`deviation` categories auto-assign `needs_human_review` verdict |
| s10 | `s10_completion_guard.py` | Unresolved blocks and missing plan reviews are caught by completion review |
| s12 | `s12_cross_server_integration.py` | KG + Governance + Task system interplay across servers |

### 18.2 Component Verification

Each component can be verified independently. The following table provides concrete verification steps for both automated (E2E) and manual approaches.

| Component | How to Verify |
|-----------|--------------|
| **KG server** | **Automated**: E2E scenarios s01 (tier protection), s04 (vision violation). **Manual**: Create entities at each tier via `create_entities`. Attempt to add observation to a vision-tier entity with `callerRole: "worker"` -- verify rejection. Call `search_nodes` -- verify full-text results. Restart server -- verify JSONL persistence survives. Call `ingest_documents` on `docs/vision/` -- verify entities created at vision tier |
| **Quality server** | **Automated**: E2E scenarios s06 (quality gates), s07 (trust engine). **Manual**: Call `check_all_gates()` against the project codebase -- verify structured response with per-gate status. Call `record_dismissal` with a finding ID and justification -- verify audit trail via `get_trust_decision`. Note: `auto_format`/`run_lint`/`run_tests`/`check_coverage` make real subprocess calls; the build and findings gates are stubs |
| **Governance server** | **Automated**: E2E scenarios s02 (decision flow), s03 (governed task lifecycle), s08 (multi-blocker), s09 (scope change), s10 (completion guard). **Manual**: Call `submit_decision` with category `pattern_choice` -- verify it blocks until verdict is returned. Call `create_governed_task` -- verify two tasks created, implementation blocked. Call `get_governance_status` -- verify accurate counts |
| **Worker agent** | Spawn via Task tool with a task brief. Verify full protocol execution: reads brief, checks project rules from `.avt/project-config.json`, queries KG for context (`search_nodes`, `get_entities_by_tier`), submits decisions via `submit_decision` (blocks until verdict), implements within task brief scope, runs `check_all_gates()`, calls `submit_completion_review` before reporting done |
| **Quality reviewer agent** | Spawn with a diff containing a vision violation (e.g., introducing a singleton in production code when vision standard prohibits it). Verify structured finding output with: tier (`vision`), severity, rationale referencing the specific standard, actionable recommendation |
| **KG librarian agent** | Spawn after a work session with accumulated observations. Verify: redundant observations consolidated, recurring solutions promoted to pattern entities, stale entries removed, archival files in `.avt/memory/` synced (architectural-decisions.md, troubleshooting-log.md, solution-patterns.md) |
| **Governance reviewer agent** | Tested indirectly via governance server. Call `submit_decision` or `submit_plan_for_review` with `GOVERNANCE_MOCK_REVIEW` unset -- verify `claude --print` invocation with governance-reviewer agent produces a structured `ReviewVerdict` JSON response |
| **Researcher agent** | Spawn with a research prompt (periodic or exploratory mode). Verify: research brief written to `.avt/research-briefs/` with structured sections (findings, recommendations, action items). For periodic mode, verify change report format. For exploratory mode, verify comparison analysis |
| **Project steward agent** | Spawn with "Perform a full project hygiene review". Verify: report output with categorized findings (naming conventions, folder organization, documentation completeness, cruft detection), priority levels, and specific file references |
| **VS Code extension** | Launch VS Code with extension installed. Verify: Activity Bar shows "Collab Intelligence" container with 4 views (Actions, Memory Browser, Findings, Tasks). Click "Connect to Servers" -- verify 3 MCP clients connect. Open Dashboard -- verify React webview loads with agent cards, activity feed, governance panel. Open Setup Wizard -- verify 9-step flow renders. Open Workflow Tutorial -- verify 10-step flow renders |

### 18.3 Integration Verification

The full integration test validates that all components work together in the governed development workflow, end to end, without extension involvement. This is the successor to the v1 "Phase 2 Validation Test" and reflects the actual system with governance integration.

**Setup:**
1. Start all 3 MCP servers (KG on 3101, Quality on 3102, Governance on 3103)
2. Ensure KG contains vision and architecture entities (via `ingest_documents` or manual `create_entities`)
3. Set `CLAUDE_CODE_ENABLE_TASKS=true` and `CLAUDE_CODE_TASK_LIST_ID=agent-vision-team` (both required for task system and cross-session persistence)
4. Open Claude Code with the project's `.claude/agents/`, `CLAUDE.md`, and `.claude/settings.json`

**Integration flow:**

```
Step 1: Orchestrator receives task
    "Add input validation to the UserService"
        |
Step 2: Orchestrator queries KG for context
    search_nodes("UserService") -> discovers patterns and constraints
    get_entities_by_tier("vision") -> loads all vision standards
        |
Step 3: Orchestrator creates task (either path works)
    TaskCreate("Add input validation to UserService")
    -> PostToolUse hook fires automatically
    -> Review task created (pending, blocks implementation)
    -> Implementation task blocked from birth
        |
Step 4: Governance review executes
    Governance server loads vision standards from KG (JSONL)
    Governance server calls claude --print with governance-reviewer agent
    Governance reviewer checks decision against standards
    complete_task_review(review_task_id, "approved", guidance="...")
    -> Implementation task unblocked
        |
Step 5: Orchestrator creates worktree and spawns worker
    git worktree add ../project-worker-1 -b task/001-add-validation
    Task tool -> worker agent with task brief
        |
Step 6: Worker executes governed protocol
    Worker reads task brief
    Worker checks project rules (.avt/project-config.json)
    Worker queries KG (search_nodes, get_entity)
    Worker submits decisions (submit_decision -> blocks until verdict)
    Worker implements within scope
    Worker runs quality gates (check_all_gates)
    Worker submits completion review (submit_completion_review)
        |
Step 7: Orchestrator spawns quality reviewer
    Task tool -> quality-reviewer with worker's diff
    Quality reviewer applies three-lens protocol:
      Vision lens -> checks against vision entities from KG
      Architecture lens -> checks pattern conformance
      Quality lens -> runs lint/test via Quality server
    Returns structured findings (if any)
        |
Step 8: Finding resolution (if needed)
    Orchestrator routes findings back to worker
    Worker addresses findings
    Quality reviewer re-reviews
    Repeat until clean
        |
Step 9: Merge and checkpoint
    git merge task/001-add-validation
    git tag checkpoint-001
    git worktree remove ../project-worker-1
        |
Step 10: KG curation
    Task tool -> kg-librarian
    Librarian consolidates observations
    Librarian promotes recurring solutions to patterns
    Librarian syncs to .avt/memory/ archival files
```

**Expected outcome:** The entire workflow completes using Claude Code native primitives + 3 MCP servers. The extension is not involved in the flow. Every implementation task is blocked from birth until governance review approves it. Every worker decision is transactionally reviewed. Quality gates run before completion. KG is updated with institutional memory from the session.

**Verification checklist:**

- [ ] Governed task pair created atomically (review blocks implementation)
- [ ] Implementation task cannot be picked up before review completes
- [ ] Worker `submit_decision` calls block until governance verdict
- [ ] `submit_completion_review` catches unresolved blocks or missing plan reviews
- [ ] Quality gates (`check_all_gates`) return structured per-gate results
- [ ] KG librarian successfully consolidates and syncs to archival files
- [ ] Git worktree created, used for isolation, and cleaned up after merge
- [ ] Session state updated in `.avt/session-state.md`
- [ ] Checkpoint tag created for recovery
