# ARCHITECTURE.md v2 — Agent Vision Team

This document is the authoritative architecture reference for the Agent Vision Team Collaborative Intelligence System. It describes the system as built: a Claude Code-based orchestration platform coordinating 6 custom subagents across 3 MCP servers, with transactional governance review, persistent institutional memory, deterministic quality verification, and a VS Code extension providing setup, monitoring, and management capabilities.

The system runs entirely locally on a developer's machine. There are no cloud services, no API keys to manage (Claude Code Max provides model access), and no network dependencies beyond the Claude Code binary itself. All MCP servers communicate over stdio transport (spawned by Claude Code, not network listeners), and all persistent state lives in the project directory.

---

## 1. System Boundaries and Glossary

### 1.1 In Scope

| Component | Description |
|-----------|-------------|
| **Knowledge Graph MCP Server** | Persistent institutional memory with tier-based access control (port 3101, 11 tools) |
| **Quality MCP Server** | Deterministic quality verification with trust engine (port 3102, 8 tools) |
| **Governance MCP Server** | Transactional review checkpoints and governed task lifecycle (port 3103, 10 tools) |
| **6 Custom Subagents** | Worker, Quality Reviewer, KG Librarian, Governance Reviewer, Researcher, Project Steward |
| **Governance Architecture** | Transactional decision review, governed tasks (blocked-from-birth), multi-blocker support, AI-powered review via `claude --print` |
| **Three-Tier Protection Hierarchy** | Vision > Architecture > Quality — lower tiers cannot modify higher tiers |
| **Project Rules System** | Behavioral guidelines (enforce/prefer) injected into agent prompts from `.avt/project-config.json` |
| **E2E Testing Harness** | 11 scenarios, 172+ structural assertions, parallel execution with full isolation |
| **VS Code Extension** | Setup wizard (10 steps), workflow tutorial (9 steps), governance panel, document editor, research prompts panel, 3 MCP clients |
| **CLAUDE.md Orchestration Protocol** | Orchestrator instructions defining task decomposition, governance checkpoints, quality review, memory curation |
| **Research System** | Research prompts, researcher agent (dual-mode), research briefs |
| **Session Management** | Checkpoints via git tags, session state in `.avt/session-state.md`, worktree isolation |

### 1.2 Out of Scope

| Exclusion | Rationale |
|-----------|-----------|
| External CI/CD pipelines | All quality gates run locally via MCP servers |
| External cloud services | System is fully local; Claude Code Max provides model access |
| API key management | No API keys required (Claude Code Max subscription model) |
| External authentication | No multi-user system; single developer workflow |
| External frameworks or runtimes | MCP servers use Python/uv; extension uses Node/TypeScript — no additional frameworks |
| Production deployment | This is a development-time system, not a deployed service |

### 1.3 Glossary

| Term | Definition |
|------|------------|
| **Orchestrator** | The primary Claude Code session (Opus 4.6) that decomposes tasks, spawns subagents, and coordinates work. Defined by `CLAUDE.md`. |
| **Subagent** | A specialized Claude Code agent spawned via the Task tool, with a scoped system prompt from `.claude/agents/`. |
| **Worker** | Subagent (Opus, 9 tools) that implements scoped tasks within governance constraints. |
| **Quality Reviewer** | Subagent (Opus, 6 tools) that evaluates work through three ordered lenses: vision, architecture, quality. |
| **KG Librarian** | Subagent (Sonnet, 5 tools) that curates institutional memory — consolidates, promotes patterns, syncs archival files. |
| **Governance Reviewer** | Subagent (Sonnet, 4 tools) that evaluates decisions and plans for vision/architecture alignment. **Not spawned by the orchestrator** — called internally by the Governance Server via `claude --print`. |
| **Researcher** | Subagent (Opus, 7 tools) that gathers intelligence in two modes: periodic/maintenance monitoring and exploratory/design research. |
| **Project Steward** | Subagent (Sonnet, 7 tools) that maintains project hygiene: naming conventions, organization, documentation completeness, cruft detection. |
| **MCP Server** | Model Context Protocol server providing tools to Claude Code sessions. Spawned as child processes via stdio transport. |
| **Knowledge Graph (KG)** | Entity-relation graph stored in `.claude/collab/knowledge-graph.jsonl`. Contains vision standards, architectural patterns, components, observations. |
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
│(Opus)  ││Reviewer││Librar- │       │  -er   ││Steward │
│9 tools ││(Opus)  ││ian     │       │(Opus)  ││(Sonnet)│
│        ││6 tools ││(Sonnet)│       │7 tools ││7 tools │
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
│  .claude/collab/                .avt/                                    │
│  ├── knowledge-graph.jsonl      ├── session-state.md                    │
│  ├── trust-engine.db            ├── task-briefs/                        │
│  └── governance.db              ├── memory/                             │
│                                 │   ├── architectural-decisions.md      │
│  ~/.claude/tasks/<list-id>/     │   ├── troubleshooting-log.md          │
│  └── *.json (task files)        │   ├── solution-patterns.md            │
│                                 │   └── research-findings.md            │
│  Git (worktrees, tags,          ├── research-prompts/                   │
│       branches)                 ├── research-briefs/                    │
│                                 └── project-config.json                 │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────┐
                    │  GOVERNANCE REVIEWER (Sonnet)     │
                    │  4 tools | NOT spawned by         │
                    │  orchestrator — called internally │
                    │  by Governance Server via         │
                    │  `claude --print`                 │
                    └──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      VS CODE EXTENSION                                   │
│                                                                         │
│  Setup Wizard (10 steps) │ Workflow Tutorial (9 steps)                  │
│  Governance Panel        │ Research Prompts Panel                       │
│  Document Editor         │ VS Code Walkthrough (6 steps)               │
│  Agent Cards / Activity  │ Settings Panel                              │
│                                                                         │
│  3 MCP Clients: KnowledgeGraphClient, QualityClient, GovernanceClient  │
│  5 Tree Providers: Dashboard, Memory, Findings, Tasks, Actions         │
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
│       ├── Workers (Opus)
│       ├── Quality Reviewer (Opus)
│       ├── KG Librarian (Sonnet)
│       ├── Researcher (Opus)
│       └── Project Steward (Sonnet)
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
- **Fully local**: No network services, no cloud, no API keys.
- **Claude Code Max**: Model access provided by subscription; no API key management.
- **Stdio transport**: MCP servers are spawned as child processes by Claude Code, not network listeners. Port numbers in this document are logical identifiers for documentation, not TCP ports.
- **Single-user**: Designed for one developer per project directory. Multi-user coordination is out of scope.

---

## 3. Claude Code as Orchestration Platform

Claude Code is not a tool the system uses — it IS the orchestration platform. The system leverages Claude Code's native capabilities (subagents, Task tool, MCP integration, hooks, skills) and extends them with governance policy, institutional memory, and quality verification.

### 3.1 Custom Subagents

Six custom subagent definitions live in `.claude/agents/`:

```
.claude/agents/
├── worker.md                # Opus  | 9 tools | KG + Quality + Governance
├── quality-reviewer.md      # Opus  | 6 tools | KG + Quality
├── kg-librarian.md          # Sonnet | 5 tools | KG
├── governance-reviewer.md   # Sonnet | 4 tools | KG (called via claude --print)
├── researcher.md            # Opus  | 7 tools | KG + Governance + WebSearch + WebFetch
└── project-steward.md       # Sonnet | 7 tools | KG + Write + Edit + Bash
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

Used for all implementation work. This is the primary workflow:

```
1. Orchestrator calls create_governed_task() via Governance MCP
   │
   ├─→ Review Task (review-abc123)       Implementation Task (impl-xyz789)
   │   status: pending                    status: pending
   │   blocks: [impl-xyz789]             blockedBy: [review-abc123]
   │                                      CANNOT EXECUTE
   │
2. Governance review runs
   │  (Governance Server invokes governance-reviewer via claude --print)
   │  Loads vision standards from KG, checks alignment, produces verdict
   │
3. On approval: complete_task_review(review-abc123, verdict="approved")
   │  Removes review-abc123 from impl-xyz789.blockedBy
   │  impl-xyz789 now executable
   │
4. Orchestrator spawns Worker with impl-xyz789
   │
   Worker lifecycle:
   │  a. Check get_task_review_status() — confirm unblocked
   │  b. Read task brief, query KG for context
   │  c. For each key decision: submit_decision() → blocks until verdict
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
add_review_blocker(impl-xyz789, "security", "Auth handling requires security review")
   │
   ├─→ New Review Task (review-security-def456)
   │   blocks: [impl-xyz789]
   │
   └─→ impl-xyz789.blockedBy: [review-abc123, review-security-def456]
       BOTH must complete with "approved" before task can execute
```

### 3.3 Lifecycle Hooks

Hooks are configured in `.claude/settings.json` and execute shell scripts at specific points in the Claude Code lifecycle.

#### Current Hooks

| Hook Type | Matcher | Script | Purpose |
|-----------|---------|--------|---------|
| `PreToolUse` | `ExitPlanMode` | `scripts/hooks/verify-governance-review.sh` | Safety net: blocks plan presentation if `submit_plan_for_review` was not called |

#### ExitPlanMode Hook Detail

This hook is the **safety net**, not the primary governance mechanism. The primary mechanism is the transactional `submit_plan_for_review()` tool call that agents make directly.

```bash
# scripts/hooks/verify-governance-review.sh
# Checks governance SQLite DB for plan review records.
# Exit 0 = allow (review found or DB unavailable)
# Exit 2 = block with feedback JSON (no review found)

DB_PATH="${CLAUDE_PROJECT_DIR:-.}/.avt/governance.db"
PLAN_REVIEWS=$(sqlite3 "$DB_PATH" \
  "SELECT COUNT(*) FROM reviews WHERE plan_id IS NOT NULL;" 2>/dev/null || echo "0")

if [ "$PLAN_REVIEWS" -gt 0 ]; then
  exit 0  # Review exists — allow
else
  # Output JSON feedback and block
  echo '{"additionalContext": "GOVERNANCE REVIEW REQUIRED: ..."}'
  exit 2
fi
```

The hook catches the case where an agent forgets to call `submit_plan_for_review()` — it cannot proceed past `ExitPlanMode` without at least one plan review on record.

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
| Knowledge Graph | Entities, relations, observations, tier metadata | `.claude/collab/knowledge-graph.jsonl` |
| Trust Engine | Finding records, dismissals, audit trail | `.claude/collab/trust-engine.db` |
| Governance DB | Decisions, verdicts, review history | `.claude/collab/governance.db` |
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
