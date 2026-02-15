# Agent Vision Team -- Project Overview

> A platform-native multi-agent system for software development built on Claude Code, providing tier-protected institutional memory, transactional governance, and deterministic quality verification through three MCP servers, eight specialized agents, Agent Teams orchestration, a five-hook verification layer, and a standalone web gateway for remote operation.

**Last Updated**: 2026-02-14

---

## What This Project Is

Agent Vision Team is a collaborative intelligence system that coordinates multiple specialized AI agents to accomplish complex development tasks. It runs entirely on Claude Code Max and extends Claude Code's native capabilities with three MCP servers that provide what the platform cannot do on its own: persistent institutional memory, transactional governance checkpoints, and deterministic quality verification.

The system is organized around a three-tier governance hierarchy: **Vision** (immutable project principles), **Architecture** (human-gated structural patterns), and **Quality** (automated code standards). Every piece of work an agent produces is measured against this hierarchy. A perfectly linted function that violates the project's design philosophy is a failure, not a success.

A human developer, working through a primary Claude Code session (the orchestrator), decomposes complex tasks and delegates them to eight specialized agents. Agents are spawned as **Agent Teams teammates**: full Claude Code sessions with independent MCP access, shared task lists, and hook enforcement. The architect designs system architecture with explicit intent and expected outcomes, producing task briefs that workers implement. Workers implement scoped tasks. The quality reviewer evaluates work through a three-lens model. The KG librarian curates institutional memory so knowledge survives across sessions. The governance reviewer provides AI-powered decision review inside the governance server. The researcher gathers intelligence, monitoring external dependencies and investigating unfamiliar domains, so workers implement from informed positions rather than guessing. The project steward maintains organizational hygiene: naming conventions, folder structure, documentation completeness, and cruft detection. The project bootstrapper onboards existing codebases by discovering governance artifacts that already exist implicitly in code and documentation. Each agent has a distinct role, and together they sustain coherent, high-quality development over extended autonomous sessions.

The system operates in two modes: **locally** via the VS Code extension for developers at their workstation, or **remotely** via a standalone web gateway that serves the same React dashboard over HTTPS. The remote mode enables job submission from any device (including phones), persistent container-based deployment, and full management without VS Code.

---

## System Architecture

```
+-----------------------------------------------------------------+
|           HUMAN + PRIMARY SESSION (Orchestrator / Lead)          |
|    Interactive Claude Code session (Opus 4.6)                   |
|    Reads: CLAUDE.md + on-demand skills (.claude/skills/)        |
|    Uses: Agent Teams to spawn teammates                         |
|    Env: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1                  |
+--+------+----------+----------+----------+----------+-----------+
   |      |          |          |          |          |
+--v---+ +v--------+ +v--------+ +v--------+ +v--------+ +------------+
|ARCHI-| | WORKER  | |QUALITY  | |  KG     | |RESEARCH-| |  PROJECT   |
| TECT | |         | |REVIEWER | |LIBRARIAN| |  ER     | |  STEWARD   |
|(Opus | |(Opus 4.6| |(Opus 4.6| |(Sonnet  | |(Opus 4.6| | (Sonnet    |
| 4.6) | |)        | |)        | | 4.5)    | |/Sonnet  | |  4.5)      |
|      | |         | |         | |         | | 4.5)    | |            |
|      | |         | |         | |         | |         | |  PROJECT   |
|      | |         | |         | |         | |         | |  BOOTSTRAP |
|      | |         | |         | |         | |         | |  PER       |
|      | |         | |         | |         | |         | | (Opus 4.6) |
+--+---+ +--+------+ +--+------+ +--+------+ +--+------+ +--+---------+
   |        |            |           |           |           |
   |     All teammates: full Claude Code sessions             |
   |     with independent MCP, hooks, CLAUDE.md               |
   |     Shared task list, self-claim, direct messaging       |
+--v--------v------------v-----------v-----------v-----------v---+
|                   FIVE-HOOK VERIFICATION LAYER                  |
|                                                                 |
| 1. PostToolUse(TaskCreate)     governance-task-intercept.py     |
| 2. PreToolUse(ExitPlanMode)    verify-governance-review.sh      |
| 3. PreToolUse(Write|Edit|...)  holistic-review-gate.sh          |
| 4. TeammateIdle                teammate-idle-gate.sh            |
| 5. TaskCompleted               task-completed-gate.sh           |
+-----------------------------------------------------------------+
                          |
+-------------------------v---------------------------------------+
|                     THREE MCP SERVERS                            |
|                                                                  |
|  +---------------+   +--------------+   +--------------------+   |
|  |Knowledge Graph|   |   Quality    |   |    Governance      |   |
|  |    :3101      |   |    :3102     |   |      :3103         |   |
|  +---------------+   +--------------+   +---------+----------+   |
|                                                    |              |
|                                           +--------v----------+  |
|                                           |   GOVERNANCE      |  |
|                                           |    REVIEWER       |  |
|                                           |  (Sonnet 4.5)     |  |
|                                           | Called internally  |  |
|                                           | via claude --print |  |
|                                           +-------------------+  |
+--------------+-----------------------------------------------+---+
               |                                               |
    +----------+----------+          +-------------------------v------+
    |  VS CODE EXTENSION  |          |     AVT GATEWAY (FastAPI)      |
    |  (Local mode)       |          |     (Remote mode)              |
    |                     |          |                                |
    |  Setup Wizard       |          |  +----------+ +-----------+   |
    |  Governance Panel   |          |  | REST API | | WebSocket |   |
    |  Token Usage Panel  |          |  | 35 routes| | (push)    |   |
    |  Research Prompts   |          |  +----------+ +-----------+   |
    |  3 MCP Clients      |          |  +----------+ +-----------+   |
    |  4 TreeViews        |          |  | Job Run  | | Claude CLI|   |
    |  12 Commands        |          |  +----------+ +-----------+   |
    +---------------------+          +----------+--------------------+
                                                |
                                       +--------v--------+
                                       |  Nginx + SPA    |
                                       |  Browser / Phone|
                                       +-----------------+
```

### Platform-Native Philosophy

The architecture follows a strict principle: build only what Claude Code cannot do. Claude Code provides Agent Teams orchestration, teammate spawning, coordination, parallel execution, lifecycle hooks, session persistence, model routing, and permission control natively. The three MCP servers exist because the platform genuinely lacks persistent institutional memory, transactional governance, and deterministic quality tool wrapping.

| Provided by Claude Code (native) | Provided by MCP Servers (custom) |
|---|---|
| Agent Teams: teammate spawning, shared tasks, self-claim | Persistent tier-protected memory (KG) |
| Parent-child and peer-to-peer communication | Deterministic quality verification |
| Five lifecycle hooks (PostToolUse, PreToolUse, TeammateIdle, TaskCompleted) | Transactional governance review |
| Git worktree management | Governed task execution |
| Session persistence/resume | Trust engine with audit trails |
| Model routing per teammate | AI-powered decision review |
| Tool restrictions and permissions | Token usage tracking |

### Agent Teams as Primary Orchestration

The system uses Claude Code's **Agent Teams** feature (enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) as its primary orchestration mechanism. Each teammate is a full Claude Code session with:

- **Independent MCP access**: All three MCP servers available (KG, Quality, Governance)
- **CLAUDE.md and hooks**: Every teammate loads project context and hook enforcement independently
- **Shared task list**: All teammates share a task list (via `CLAUDE_CODE_TASK_LIST_ID`)
- **Self-claim**: Teammates pick up the next unassigned, unblocked task automatically
- **Direct messaging**: Teammates can message each other, not just report to the lead
- **On-demand skills**: Detailed protocol documentation available via `.claude/skills/` (invokable as `/skill-name`)

Since `.claude/agents/` definitions cannot yet be used directly as teammates (Issue #24316), the lead reads the relevant `.claude/agents/{role}.md` file and embeds the full system prompt in the teammate spawn instruction. When this issue is resolved, teammates will load agent definitions directly.

**Fallback**: If Agent Teams is unavailable or disabled, the system falls back to Task-tool subagents. The `.claude/agents/` definitions and `agents` section in `.claude/settings.json` remain in place for this purpose.

---

## Three-Tier Governance Hierarchy

The organizing principle for the entire system:

| Tier | Contains | Who Can Modify | Examples |
|------|----------|----------------|----------|
| **Vision** | Core principles, design philosophy, fundamental purpose | Human only | "All services use protocol-based DI", "No singletons in production code" |
| **Architecture** | Patterns, major components, established abstractions | Human or orchestrator with approval | "ServiceRegistry pattern", "AuthService component" |
| **Quality** | Observations, findings, troubleshooting notes | Any agent | "AuthService lacks error handling", "Login flow refactored" |

Lower tiers cannot modify higher tiers. Vision conflicts override all other work. This hierarchy is enforced at the server level; a misbehaving agent cannot accidentally corrupt vision-tier data.

---

## Three MCP Servers

### Knowledge Graph Server (Port 3101)

Persistent institutional memory with tier-based access control. Stores entities (components, patterns, decisions, vision standards), relations between them, and timestamped observations. All Claude Code sessions share the same graph.

**Implementation**: Python + FastMCP, JSONL persistence at `.avt/knowledge-graph.jsonl`

**Tools**: `create_entities`, `create_relations`, `add_observations`, `get_entity`, `search_nodes`, `get_entities_by_tier`, `delete_entity`, `delete_relations`, `delete_observations`, `ingest_documents`, `validate_tier_access`

**Tier Protection**: Enforced at the tool level. Vision-tier entities are immutable by agents. Architecture-tier writes require explicit approval. Quality-tier is open to all callers.

**Key files**: `mcp-servers/knowledge-graph/collab_kg/` -- `server.py` (FastMCP entry), `graph.py` (entity/relation CRUD), `storage.py` (JSONL persistence), `tier_protection.py` (access control), `ingestion.py` (document ingestion pipeline)

### Quality Server (Port 3102)

Deterministic quality verification wrapping real tools behind a unified MCP interface, plus a trust engine for finding management.

**Implementation**: Python + FastMCP, SQLite persistence for trust engine

**Tools**: `auto_format`, `run_lint`, `run_tests`, `check_coverage`, `check_all_gates`, `validate`, `get_trust_decision`, `record_dismissal`

**Supported languages**: Python (ruff, pytest), TypeScript/JavaScript (eslint, prettier, npm test), Swift (swiftlint, swiftformat, xcodebuild), Rust (clippy, rustfmt, cargo test)

**Five quality gates**: Build, lint, tests, coverage (default 80% threshold), findings (no critical unresolved)

**Trust engine principle**: No silent dismissals. Every dismissed finding requires a justification string and the identity of who dismissed it, creating an auditable trail.

**Key files**: `mcp-servers/quality/collab_quality/` -- `server.py`, `tools/` (formatting, linting, testing, coverage), `trust_engine.py`, `gates.py`

### Governance Server (Port 3103)

Transactional review checkpoints for agent decisions, implementing the "intercept early, redirect early" pattern. Workers submit decisions and block until the governance server returns a verdict.

**Implementation**: Python + FastMCP, SQLite persistence for decision store

**Decision tools**: `submit_decision`, `submit_plan_for_review`, `submit_completion_review`, `get_decision_history`, `get_governance_status`

**Governed task tools**: `create_governed_task`, `add_review_blocker`, `complete_task_review`, `get_task_review_status`, `get_pending_reviews`

**Usage tracking tools**: `get_usage_report` -- token usage reports for governance AI calls with breakdown by agent/operation, prompt size trends, and session filtering

**Decision categories**: `pattern_choice`, `component_design`, `api_design`, `deviation`, `scope_change`

**Review types**: `governance`, `security`, `architecture`, `memory`, `vision`, `custom`

**Verdicts**: `approved` (proceed), `blocked` (stop, guidance provided), `needs_human_review` (escalate)

**Review process**: When a decision is submitted, the governance server loads vision standards from the KG (with 5-minute TTL cache for performance), runs the governance-reviewer agent via `claude --print` for AI-powered review, stores the verdict in SQLite, records the decision in the KG for institutional memory, and returns the verdict to the calling agent.

**Token usage tracking**: Every AI review invocation (decision review, plan review, completion review, task group review, hook review) is tracked as a `UsageRecord` with input/output tokens, cache reads/creation, duration, prompt size, and model used. The `get_usage_report` tool provides aggregated reports by period (day/week) and grouping (agent/operation), including prompt size trends for detecting context bloat.

**Governed task lifecycle**: `create_governed_task` atomically creates a review task and an implementation task. The implementation task is governed from creation; its `blockedBy` array references the review, and rapid automated review is queued immediately. Multiple review checkpoints can be stacked (governance, security, architecture). The task proceeds once all reviews are complete.

**Holistic governance review**: Before work begins, all tasks from a session are evaluated as a group. A settle/debounce pattern detects when the agent has finished creating tasks, then runs a collective intent review against vision standards, typically completing in seconds. If the collective intent is problematic, tasks receive constructive guidance for revision. Session-scoped flag files (`.avt/.holistic-review-pending-{session_id}`) ensure concurrent Agent Teams teammates have independent holistic reviews without interfering with each other.

**KG client caching**: The governance server's `KGClient` caches vision standards and architecture entity queries with a 5-minute TTL using `time.monotonic()`. This avoids repeated JSONL file reads during review bursts. The cache can be explicitly invalidated via `invalidate_cache()`.

**Data models**: `Decision`, `ReviewVerdict`, `GovernedTaskRecord`, `TaskReviewRecord`, `UsageRecord`, `HolisticReviewRecord` (all Pydantic, defined in `models.py`)

**Key files**: `mcp-servers/governance/collab_governance/` -- `server.py`, `store.py` (SQLite: decisions, reviews, governed_tasks, task_reviews, usage, holistic_reviews), `reviewer.py` (AI review logic + `review_task_group()`), `task_integration.py` (Claude Code Task System integration), `kg_client.py` (KG integration with TTL cache), `models.py` (Pydantic models including `UsageRecord` and `HolisticReviewRecord`)

---

## Five-Hook Verification Layer

Five Claude Code lifecycle hooks provide deterministic governance verification. These hooks fire for ALL agents (lead, teammates, subagents) with no exceptions and no opt-out.

| # | Hook Type | Matcher | Script | Purpose |
|---|-----------|---------|--------|---------|
| 1 | PostToolUse | `TaskCreate` | `governance-task-intercept.py` | Pairs every task with a governance review; tracks `session_id`; creates session-scoped holistic review flag; spawns settle checker |
| 2 | PreToolUse | `ExitPlanMode` | `verify-governance-review.sh` | Ensures plans are verified before presentation; redirects agents to submit plan review if none exists |
| 3 | PreToolUse | `Write\|Edit\|Bash\|Task` | `holistic-review-gate.sh` | Coordinates work sequencing during holistic review; uses session-scoped flag files with ~1ms fast-path when no review is pending |
| 4 | TeammateIdle | (all) | `teammate-idle-gate.sh` | Prevents Agent Teams teammates from going idle while they have pending governance obligations |
| 5 | TaskCompleted | (all) | `task-completed-gate.sh` | Prevents task completion if governance review is still pending or blocked; skips review tasks |

### Session-Scoped Holistic Review

The holistic review system evaluates all tasks from a session as a group before any work begins. This catches collective violations that individual review cannot detect (e.g., four tasks that individually look fine but collectively introduce an unauthorized ORM layer).

**How it works**:

```
Agent creates Task 1 -> PostToolUse fires:
  - Records task with session_id in governance DB
  - Creates session-scoped flag: .avt/.holistic-review-pending-{session_id}
  - Spawns background settle checker (waits 3s)

Agent creates Task 2 -> PostToolUse fires:
  - Records task, updates flag, spawns new settle checker
  - Previous checker detects newer task and exits

Agent creates Task 3 -> PostToolUse fires:
  - Same as above

Background: Settle checker for Task 3 wakes up after 3s:
  - Checks DB: any tasks newer than me? NO -> I'm the last task
  - Runs holistic review (GovernanceReviewer.review_task_group())
  - If APPROVED: clears flag file, queues individual reviews
  - If issues found: writes guidance to flag file for revision

Meanwhile: Agent tries to Write/Edit/Bash/Task:
  -> PreToolUse checkpoint fires (~1ms)
  -> Any session-scoped flag file exists? YES -> exit 2 (redirect with feedback)
  -> Agent sees "Holistic review in progress, please wait"
```

**Key properties**:
- Detection is timing-based (settle/debounce), not reliant on agent behavior
- Verification is deterministic (PreToolUse coordinates work sequencing at the platform level)
- Session-scoped flag files: each teammate session gets its own flag, preventing cross-session interference
- Fast path is ~1ms when no review is pending (flag file glob check)
- Single tasks skip holistic review (`MIN_TASKS_FOR_REVIEW = 2`)
- Stale flags older than 5 minutes are auto-cleared

---

## Eight Specialized Agents

All defined in `.claude/agents/` as markdown files with YAML frontmatter specifying model, tools, and system prompt. When spawned as Agent Teams teammates, the lead embeds the full system prompt in the spawn instruction (pending Issue #24316 for native agent definition loading).

| Agent | Model | Mechanism | Role | MCP Access |
|-------|-------|-----------|------|------------|
| **Architect** | Opus 4.6 | Teammate | Designs architecture with explicit intent and expected outcomes. Produces task briefs for workers. Does not write implementation code. | KG, Governance |
| **Worker** | Opus 4.6 | Teammate | Implements scoped tasks from task briefs. Queries KG for constraints, submits decisions for governance review, runs quality gates before completion. | KG, Quality, Governance |
| **Quality Reviewer** | Opus 4.6 | Teammate | Three-lens evaluation: Vision (highest) -> Architecture -> Quality. Returns structured findings with project-specific rationale. | KG, Quality |
| **KG Librarian** | Sonnet 4.5 | Teammate | Curates institutional memory after work sessions. Consolidates observations, promotes recurring solutions to patterns, removes stale entries, syncs to archival files. | KG |
| **Governance Reviewer** | Sonnet 4.5 | `claude --print` | Evaluates decisions and plans against vision and architecture standards. Called internally by the governance server. Returns structured verdicts. Isolation is a security feature. | KG (via KGClient) |
| **Researcher** | Opus 4.6/Sonnet 4.5 | Teammate | Gathers intelligence in two modes: periodic/maintenance (tracking external dependencies) and exploratory/design (informing architectural decisions). Produces research briefs. | KG, Governance |
| **Project Steward** | Sonnet 4.5 | Teammate | Maintains project hygiene: naming conventions, folder organization, documentation completeness, cruft detection, consistency checks. | KG |
| **Project Bootstrapper** | Opus 4.6 | Teammate | Onboards existing codebases by discovering governance artifacts (vision standards, architecture patterns, conventions) implicitly present in code and documentation. | KG, Governance |

### The Quality Reviewer -- Three-Lens Evaluation

The Quality Reviewer evaluates work in strict order:

1. **Vision Lens** -- Does this work align with project identity? Vision conflicts stop all related work immediately.
2. **Architecture Lens** -- Does this work follow established patterns? Detects "ad-hoc pattern drift" where new code reinvents existing solutions.
3. **Quality Lens** -- Does the code pass automated checks? Auto-fixes formatting; reports issues needing judgment.

Every finding includes project-specific rationale (not generic advice), a concrete suggestion for how to fix it, and a reference to the KG entity or standard being violated. The reviewer is read-focused; it evaluates code but does not write production code.

### The Researcher -- Intelligence Before Implementation

The researcher operates in two distinct modes:

**Periodic/Maintenance Research** monitors APIs, frameworks, and tools the project depends on. It detects breaking changes, deprecation notices, new features, and security advisories. The orchestrator can schedule these as recurring prompts. Output is structured change reports with actionable items prioritized by urgency.

**Exploratory/Design Research** is spawned before architectural decisions or when entering unfamiliar domains. It surveys the landscape, evaluates competing approaches, documents tradeoffs, and synthesizes recommendations. Output is research briefs stored in `.avt/research-briefs/` that feed directly into task briefs for workers.

The model is selected based on complexity: **Opus 4.6** for novel domains, architectural decisions, security analysis, and ambiguous requirements. **Sonnet 4.5** for routine changelog monitoring, version updates, and straightforward documentation lookups.

The researcher creates `research_finding` entities in the KG, establishing baselines so future research produces net-new insights rather than rediscovering what's already known. Key discoveries are synced to `.avt/memory/research-findings.md` by the KG librarian.

The core principle: **workers should never need to do substantial research**; that's the researcher's job. Workers implement based on research findings, not on their own investigation.

### The Architect -- Intent-Driven Design

The architect designs system architecture with a strict protocol: every decision must articulate its intent (why), expected outcome (what measurable result), and vision references (which standards it serves) before proposing a solution. This forces deliberate thinking and produces architecture traceable back to vision standards.

**Two operating modes**:

**Upfront Design** (project bootstrap or major features): The architect loads all vision standards and existing architecture from the KG, identifies key architectural decisions, explores at least two alternatives per decision, submits each via `submit_decision` with full intent/outcome chain, and produces design documents and task briefs for workers.

**Ongoing Decisions** (feature evolution): The architect checks existing patterns, identifies the gap the new feature creates, traces it to vision standards, submits the decision for governance review, and produces a task brief for the worker who will implement it.

The architect does not write implementation code. It designs and the worker implements. This separation ensures architectural decisions are deliberate and documented, not buried in implementation details.

### The Project Bootstrapper -- Codebase Onboarding

The project bootstrapper onboards an existing, mature codebase into the AVT system by discovering governance artifacts that already exist implicitly in code and documentation. It is a discoverer, not a creator: it surfaces what exists and presents it for human review.

**How it works**:

1. **Scale assessment**: Runs a cheap CLI-based analysis (file counts, LOC, package boundaries) in under 5 seconds, classifying the project into a scale tier (Small through Enterprise)
2. **Partition map**: Builds a map of natural code boundaries for bounded parallelism
3. **Discovery waves**: Spawns sub-agents in waves (up to 15 concurrent) to discover vision standards, architecture patterns, coding conventions, and project rules
4. **Synthesis**: Produces draft artifacts for human review

| Artifact | Location | Purpose |
|----------|----------|---------|
| Bootstrap report | `.avt/bootstrap-report.md` | Primary review artifact with APPROVE/REJECT/REVISE actions |
| Vision standard drafts | `docs/vision/*.md` | One doc per discovered vision standard |
| Architecture docs | `docs/architecture/` | Multi-level with Mermaid diagrams |
| Style guide | `docs/style/style-guide.md` | Discovered coding conventions |
| Draft rules | `.avt/bootstrap-rules-draft.json` | Discovered project rules |

### The Governance Reviewer -- The Brain Inside Governance

The governance reviewer is unique among the eight agents: it is not spawned as a teammate. Instead, it runs inside the governance server, called via `claude --print` whenever a decision, plan, or completion review is submitted. This isolation is a security feature; the reviewer has no write access to the codebase.

When the governance server receives a `submit_decision` call, it loads vision standards from the KG (using the cached KGClient), passes them along with the decision details to the governance reviewer, and the reviewer applies three checks in strict order:

1. **Vision alignment** -- Does the decision conflict with any vision standard? If so, verdict is `blocked`.
2. **Architectural conformance** -- Does it follow established patterns? Unjustified deviation means `blocked`.
3. **Consistency check** -- For plan reviews, were blocked decisions reimplemented? For completion reviews, were all decisions actually reviewed?

The reviewer returns structured verdicts with findings, guidance, and a list of standards verified. This makes governance transactional; agents submit decisions and block until the reviewer responds through the server.

---

## Task Execution Flow with Agent Teams

```
1. Human gives orchestrator a complex task
2. Orchestrator decomposes into subtasks, writes task briefs to .avt/task-briefs/
3. Orchestrator creates tasks via TaskCreate
   -> PostToolUse hook automatically creates governance pairs
   -> Holistic review flag file created (.avt/.holistic-review-pending-{session_id})
   -> Settle checker spawns (3s debounce)
4. After all tasks created, settle checker triggers holistic review
   -> If approved: flag cleared, individual reviews queued
   -> If issues: flag updated with guidance
5. Orchestrator spawns Agent Teams teammates with embedded system prompts
6. Teammates self-claim available (unblocked, pending) tasks
7. Each teammate:
   a. Queries KG for vision/architecture constraints
   b. Submits key decisions to Governance server (blocks until verdict)
   c. Implements the task
   d. Runs quality gates via Quality server (check_all_gates)
   e. TaskCompleted hook verifies governance status before allowing completion
8. Lead spawns quality-reviewer teammate to review the diff
9. Findings route back to worker (direct teammate messaging)
10. On completion: merge, checkpoint (git tag), curate memory via KG librarian teammate
```

### Governed Task Flow

```
create_governed_task() / TaskCreate hook
    +-- Creates review task (pending)
    +-- Pairs implementation task with review (governed from creation)
    +-- Creates session-scoped flag (.avt/.holistic-review-pending-{session_id})
    +-- Spawns settle checker (3s debounce)

Settle checker (after all tasks created):
    +-- Runs holistic review (collective intent vs vision)
    +-- If approved: clears flag, queues individual reviews
    +-- If issues found: updates flag with guidance for revision

complete_task_review(verdict: "approved")
    +-- Task unblocks -> teammate picks it up via self-claim

add_review_blocker(review_type: "security")
    +-- Stacks additional review -> both must complete before execution
```

### Drift Detection in Agent Teams

The hook layer provides automatic drift detection:

- **Time drift**: TeammateIdle hook checks if the teammate still has pending governance obligations
- **Loop drift**: TaskCompleted hook verifies governance status, preventing premature completion
- **Scope drift**: TeammateIdle hook keeps teammates working on their assigned tasks
- **Quality drift**: TaskCompleted hook blocks completion until governance approves

### Research Flow

Before complex or unfamiliar tasks, the orchestrator spawns the researcher to gather intelligence first:

```
1. Orchestrator identifies a task requiring research (unfamiliar domain,
   architectural decision, technology evaluation)
2. Orchestrator spawns researcher teammate with a research prompt
3. Researcher queries KG for existing knowledge on the topic
4. Researcher uses WebSearch/WebFetch to gather external intelligence
5. Researcher creates research_finding entities in the KG
6. Researcher produces a research brief in .avt/research-briefs/
7. Orchestrator references the research brief in task briefs for workers
8. Worker teammates implement with research context
```

### Architecture Design Flow

```
1. Orchestrator identifies a task requiring architectural decisions
2. Orchestrator spawns architect teammate with a design brief
3. Architect loads vision standards and existing architecture from KG
4. For each decision: articulates intent, expected outcome, vision references
5. Architect submits each decision via submit_decision (blocks until verdict)
6. Architect produces design documents and task briefs in .avt/task-briefs/
7. Architect submits the full plan via submit_plan_for_review
8. Worker teammates implement from task briefs with architectural context
```

---

## CLAUDE.md and On-Demand Skills

The orchestrator's instructions are split between a concise `CLAUDE.md` (under 300 lines) and seven on-demand skill files in `.claude/skills/`. CLAUDE.md contains core orchestrator instructions that every session needs. Detailed protocol documentation is loaded on demand via skill invocation (`/skill-name`), saving approximately 3,400+ tokens per teammate session (with 5 teammates, that is 17,000+ tokens saved).

| Skill | File | What It Contains |
|-------|------|------------------|
| `/bootstrap-protocol` | `.claude/skills/bootstrap-protocol.md` | Full bootstrap protocol with scale tiers, human review workflow |
| `/architect-protocol` | `.claude/skills/architect-protocol.md` | Architect vs Worker roles, intent/outcome protocol |
| `/research-protocol` | `.claude/skills/research-protocol.md` | Research modes, workflow, model selection |
| `/project-steward-protocol` | `.claude/skills/project-steward-protocol.md` | Steward monitors, review cadence |
| `/e2e-testing` | `.claude/skills/e2e-testing.md` | 14 scenarios table, quick start, interpretation guide |
| `/file-organization` | `.claude/skills/file-organization.md` | Full project directory tree |
| `/end-to-end-example` | `.claude/skills/end-to-end-example.md` | 9-step auth implementation walkthrough |

---

## Project Rules -- Context Injection for Agent Quality

The three-tier governance hierarchy protects vision standards and architectural patterns. But below those tiers lies a gap: practical working rules that govern how code is written day-to-day. Rules like "no mock tests," "run the build before reporting completion," and "follow existing patterns" aren't vision or architecture; they're the behavioral expectations for how agents produce work.

**The key insight**: Every teammate starts as a fresh session. By injecting concise rules at spawn time, agents see fresh instructions at peak attention. Rules live in `.avt/project-config.json` and are compiled into a compact preamble prepended to each agent's task prompt.

### How Rules Are Structured

Each rule has a **statement** (concise imperative), a **rationale** (one sentence, not injected into context), an **enforcement level** (enforce, prefer, or guide), and a **scope** (which agent types it applies to).

### Rules vs. Other Enforcement Mechanisms

| Mechanism | What It Enforces | How |
|-----------|------------------|-----|
| **Vision Standards** | Core principles (immutable) | Tier-protected KG entities |
| **Architecture Patterns** | Structural decisions (human-gated) | KG entities + governance review |
| **Quality Gates** | Deterministic checks (build, lint, tests) | Tool execution via Quality MCP server |
| **Project Rules** | Behavioral guidance tools can't check | Context injection at agent spawn |
| **Lifecycle Hooks** | Governance process compliance | Platform-level event interception |

---

## Observability and Management Layer

The system provides two interfaces for observability, management, and job submission. Both share the same React dashboard (29+ components, zero VS Code imports) and connect to the same three MCP servers.

### VS Code Extension (Local Mode)

**Role**: Setup, monitoring, and management for developers at their workstation. Provides interactive onboarding, system observability, governance management, research prompt management, and document authoring. Does NOT orchestrate or spawn agents. The system works fully from CLI without the extension.

**Implementation**: TypeScript + React (dashboard webview), esbuild + Vite

**Capabilities**:
- **Setup Wizard**: 9-step interactive onboarding (welcome, vision docs, architecture docs, quality config, rules, permissions, settings, KG ingestion, completion) with AI-assisted document formatting
- **Workflow Tutorial**: 10-step interactive guide covering the full system lifecycle
- **Dashboard Webview**: React/Tailwind application showing session status, agent cards, governance panel, governed tasks, decision explorer, quality gates, activity feed, token usage panel, job submission, and setup readiness banner
- **Token Usage Panel**: Collapsible panel showing governance AI call consumption with Day/Week period selection, Agent/Operation grouping, summary stats (calls, tokens, duration), breakdown table, and prompt size trend visualization for detecting context bloat
- **Governance Panel**: Governed tasks, pending reviews, decision history, and governance statistics
- **Research Prompts Panel**: CRUD management for periodic and exploratory research prompts with schedule configuration
- **Document Editor**: Claude CLI-based auto-formatting for vision and architecture documents using temp-file I/O pattern
- **Memory Browser**: TreeView displaying KG entities grouped by protection tier
- **Findings Panel**: TreeView displaying quality findings with VS Code diagnostic integration
- **Tasks Panel**: TreeView displaying task briefs with status indicators
- **12 Commands**: System start/stop, MCP connection, refresh operations, dashboard, wizard, walkthrough, tutorial, research, validation, ingestion

**MCP Connectivity**: 3 MCP Clients (`KnowledgeGraphClient`, `QualityClient`, `GovernanceClient`) connecting to the same three MCP servers via SSE transport.

**Key files**: `extension/src/extension.ts` (entry point), `extension/src/providers/DashboardWebviewProvider.ts` (React dashboard host + `handleRequestUsageReport`), `extension/src/services/McpClientService.ts` (MCP connections), `extension/webview-dashboard/` (React app)

### AVT Gateway (Remote Mode)

**Role**: Standalone HTTP/WebSocket backend that replaces the VS Code extension's message-routing role, enabling full remote operation from any browser. Serves the same React dashboard as a standalone web application with API-key authentication.

**Implementation**: Python + FastAPI + uvicorn + httpx, served behind Nginx

**Architecture**:
```
Browser / Phone
     |
HTTPS (443)
     |
  Nginx         -- reverse proxy, TLS, serves SPA static files
   /    \
 /api    /static
  |        \
Gateway    React Dashboard (Vite SPA build)
(FastAPI)
port 8080
  |
  +-- MCP SSE connections (:3101, :3102, :3103)
  +-- File I/O (.avt/, docs/, .claude/)
  +-- Claude CLI (job submission, formatting)
```

**Capabilities**:
- **35 REST API endpoints** mapping every VS Code `postMessage` type to HTTP: dashboard state, config CRUD, document CRUD, governance tasks/status/decisions, quality validation/findings, research prompts/briefs, job submission
- **WebSocket server-push** at `/api/ws`: real-time dashboard updates, governance status changes, job progress events. Background poller broadcasts diffs every 5 seconds
- **Job runner**: Submit work from any device (prompt, agent type, model selection). Jobs queue and execute via Claude CLI with temp-file I/O pattern. Max 1 concurrent job (configurable). Job state persists to `.avt/jobs/` as JSON
- **API-key authentication**: Auto-generated bearer token stored in `.avt/api-key.txt`. All `/api/*` endpoints require `Authorization: Bearer <key>`. WebSocket uses `?token=<key>` query param
- **Dual-mode transport**: The React dashboard detects its environment at runtime. In VS Code it uses `postMessage`; in a browser it uses HTTP + WebSocket. Same components, same state management, zero duplication

### Transport Abstraction

The React dashboard uses a transport abstraction (`useTransport.ts`) that provides a unified interface for both modes:

- **VS Code mode**: Wraps `acquireVsCodeApi().postMessage` and `window.addEventListener('message')`
- **Web mode**: Maps all message types to HTTP endpoints via a route lookup table, manages WebSocket connection with auto-reconnect for server-push events

This means `DashboardContext.tsx` (the central state manager) required exactly one line change: swapping `useVsCodeApi()` for `useTransport()`. All 29+ React components are unchanged.

---

## E2E Testing Harness

An autonomous end-to-end testing system that exercises all three MCP servers across 14 scenarios with 292+ structural assertions.

**How it works**: Each run generates a unique project from a pool of 8 domains (Pet Adoption Platform, Restaurant Reservation System, Fitness Tracking App, Online Learning Platform, Smart Home Automation, Inventory Management System, Event Ticketing Platform, Fleet Management System). Vision standards, architecture patterns, and components are filled from domain-specific templates. All assertions are structural and domain-agnostic; behavioral contracts hold regardless of domain.

**Isolation**: Each scenario gets its own KnowledgeGraph (JSONL), GovernanceStore (SQLite), and TaskFileManager (directory). Scenarios run in parallel via `ThreadPoolExecutor`.

| Scenario | What It Validates |
|----------|-------------------|
| s01 | KG CRUD + tier-based access control (vision entities immutable by workers) |
| s02 | Decision storage, review verdicts, status queries |
| s03 | Governed task pair creation, blocking from birth, release on approval |
| s04 | Attempts to modify vision-tier entities are rejected |
| s05 | deviation/scope_change categories stored and flagged correctly |
| s06 | GovernanceStore.get_status() returns accurate aggregates |
| s07 | Finding -> dismiss -> audit trail lifecycle |
| s08 | 3 stacked blockers released one at a time |
| s09 | scope_change/deviation -> needs_human_review verdict |
| s10 | Unresolved blocks and missing plan reviews caught |
| s11 | PostToolUse hook interception mechanics for task governance |
| s12 | KG + Governance + Task system cross-server interplay |
| s13 | Hook interception under concurrent load (50 rapid + 20 concurrent) |
| s14 | Full two-phase persistence lifecycle across all 6 stores |

**Additional test suites**:
- **Unit tests**: 37 assertions across KG (18) and Quality (19) servers
- **MCP access tests**: 15 assertions verifying MCP tool availability across session types
- **Capability matrix tests**: 13 assertions verifying file write, edit, bash, and MCP access at direct/subagent levels
- **Hook live tests**: Level 1-4 tests covering mock interception, real AI review, subagent inheritance, and session-scoped flags

**Usage**:
```bash
./e2e/run-e2e.sh              # standard run
./e2e/run-e2e.sh --keep       # preserve workspace for debugging
./e2e/run-e2e.sh --seed 42    # reproducible domain selection
./e2e/run-e2e.sh --verbose    # debug logging
```

**Key files**: `e2e/run-e2e.sh` (entry point), `e2e/run-e2e.py` (Python orchestrator), `e2e/generator/` (project generation + 8 domain templates), `e2e/scenarios/` (14 test scenarios, s01-s14), `e2e/parallel/executor.py` (ThreadPoolExecutor with isolation)

---

## Persistent State and File Organization

### Runtime Data

| Path | What | Managed By |
|------|------|------------|
| `.avt/knowledge-graph.jsonl` | KG entity/relation persistence | KG Server |
| `.avt/trust-engine.db` | Quality finding audit trails | Quality Server |
| `.avt/governance.db` | Decision store with verdicts, holistic reviews, and usage records | Governance Server |
| `.avt/.holistic-review-pending-{session_id}` | Session-scoped flag files coordinating work during holistic review | PostToolUse hook |
| `.avt/api-key.txt` | Gateway API authentication key (auto-generated) | AVT Gateway |
| `.avt/jobs/` | Job submission state and output (JSON files) | AVT Gateway |

### Project Configuration

| Path | What |
|------|------|
| `.avt/project-config.json` | Project setup, language settings, quality gate configuration, permissions, project rules |
| `.avt/session-state.md` | Current session goals, progress, blockers, checkpoints |
| `.avt/task-briefs/` | Scoped assignments for worker teammates |

### Archival Memory

The KG Librarian syncs important graph entries to human-readable files:

| Path | What |
|------|------|
| `.avt/memory/architectural-decisions.md` | Significant decisions and rationale |
| `.avt/memory/troubleshooting-log.md` | Problems, what was tried, what worked |
| `.avt/memory/solution-patterns.md` | Promoted patterns with implementations |
| `.avt/memory/research-findings.md` | Key discoveries from researcher output |

### Agent and System Configuration

| Path | What |
|------|------|
| `.claude/agents/*.md` | Eight agent definitions (architect, worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward, project-bootstrapper) |
| `.claude/skills/*.md` | Seven on-demand skill files (bootstrap-protocol, architect-protocol, research-protocol, project-steward-protocol, e2e-testing, file-organization, end-to-end-example) |
| `.claude/settings.json` | Agent Teams config, five lifecycle hooks, agent tool permissions, env vars |
| `CLAUDE.md` | Orchestrator instructions (under 300 lines; detailed protocols in skills) |

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | Claude Code CLI + Agent Teams | Teammate spawning, shared tasks, self-claim, hooks |
| MCP Servers | Python 3.12+ / FastMCP 2.x | Three servers: KG, Quality, Governance |
| AVT Gateway | Python 3.12+ / FastAPI + uvicorn + httpx | Standalone web backend, REST API, WebSocket, job runner |
| Web Server | Nginx | Reverse proxy, TLS termination, SPA static serving |
| KG Persistence | JSONL | Lightweight, version-controllable, matches Anthropic's KG Memory format |
| Decision/Trust/Usage Store | SQLite | Zero-config transactional storage for governance, trust engine, and usage tracking |
| VS Code Extension | TypeScript + esbuild | Extension host runtime (local mode) |
| Dashboard | React 19 + Vite | Rich observability webview (dual-mode: VS Code + standalone web) |
| E2E Testing | Python + Pydantic + ThreadPoolExecutor | Autonomous scenario-based testing |
| Quality Tools | ruff, eslint, prettier, swiftlint, clippy, pytest | Deterministic verification |
| AI Models | Opus 4.6 (judgment), Sonnet 4.5 (routine) | Capability-first model routing |
| Container | Docker + docker-compose | Standalone deployment, GitHub Codespaces support |
| Package Management | npm (extension), uv (Python servers + gateway) | Standard per ecosystem |
| Version Control | Git + worktrees | Code state, worker isolation, checkpoints |

---

## Getting Started

### Option A: Local Development (VS Code)

#### Prerequisites

- Claude Code with Max subscription
- Python 3.12+ with `uv` package manager
- Node.js 18+ (for VS Code extension, optional)

#### Install Dependencies

```bash
cd mcp-servers/knowledge-graph && uv sync
cd mcp-servers/quality && uv sync
cd mcp-servers/governance && uv sync

# Optional: extension
cd extension && npm install
```

#### Start MCP Servers

```bash
# Terminal 1: Knowledge Graph (port 3101)
cd mcp-servers/knowledge-graph && uv run python -m collab_kg.server

# Terminal 2: Quality (port 3102)
cd mcp-servers/quality && uv run python -m collab_quality.server

# Terminal 3: Governance (port 3103)
cd mcp-servers/governance && uv run python -m collab_governance.server
```

#### Start a Session

```bash
claude   # CLAUDE.md provides orchestrator instructions automatically
```

### Option B: Remote / Container Deployment

#### Docker Compose (Self-Hosted)

```bash
# Set your API key
export ANTHROPIC_API_KEY=your-key-here

# Build and start all services (MCP servers + Gateway + Nginx + dashboard)
docker compose up -d

# Access the dashboard
open https://localhost
```

The container runs all 3 MCP servers, the AVT Gateway, and Nginx in a single image. Mount your project repo as a volume:

```yaml
# docker-compose.yml
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

The repository includes a `.devcontainer/devcontainer.json` that configures a full Codespaces environment. Open the repo in Codespaces and all services start automatically. Codespaces provides automatic HTTPS via port forwarding, shareable URLs with GitHub auth, and access from any device including phones.

#### Cloud VPS

Deploy on any machine with Docker (DigitalOcean, Hetzner, AWS Lightsail). Use `docker compose up -d` and configure Let's Encrypt for public TLS. Cost: $5-20/month.

### Run Tests

```bash
# Unit tests
cd mcp-servers/knowledge-graph && uv run pytest   # 18 tests
cd mcp-servers/quality && uv run pytest            # 19 tests
cd extension && npm test                           # 9 unit tests

# E2E (exercises all 3 servers, 14 scenarios, 292+ assertions)
./e2e/run-e2e.sh

# Hook live tests
./scripts/hooks/test-hook-live.sh --level 1       # mock interception
./scripts/hooks/test-hook-live.sh --level 4       # session-scoped flags

# Capability matrix
./scripts/hooks/test-capability-matrix.sh         # 13 checks
```

---

## Guiding Principles

These principles, drawn from the system's development, govern how it's built and used:

- **Vision First**: Vision standards are immutable by agents. Only humans define the vision. Agents enforce it but never propose changes to it.
- **Build Only What the Platform Cannot Do**: Claude Code handles orchestration natively via Agent Teams. Custom infrastructure is limited to three MCP servers providing capabilities the platform genuinely lacks.
- **Intercept Early, Redirect Early**: Implementation tasks are governed from creation and verified before work begins, with minimal introduced latency. Holistic review evaluates tasks as a group to catch collective violations that individual review cannot detect. This reliable verification is what enables safe multi-agent parallelism.
- **Deterministic Verification Over AI Judgment**: The most reliable trust signal is a compiler, linter, or test suite, not another LLM's opinion. Quality gates are deterministic.
- **No Silent Dismissals**: Every dismissed finding requires justification and identity. Audit trails are non-negotiable.
- **Support, Not Policing**: The quality system's primary purpose is making workers produce better work than they would alone, through pattern memory, architectural guidance, and constructive coaching.
- **Research Before Implementing**: For unfamiliar domains or architectural decisions, spawn the researcher first. Workers implement based on research findings, not on their own investigation.
- **Token Efficiency**: Keep CLAUDE.md concise (under 300 lines) with detailed protocols in on-demand skills. Cache frequently-read KG data. Track token usage to detect prompt bloat early.

---

## Current Status

All five implementation phases are complete, plus an Agent Teams adaptation:

- **Phase 1** (MCP Servers): KG with JSONL persistence and tier protection, Quality with trust engine and multi-language tool wrapping, Governance with transactional review and governed tasks
- **Phase 2** (Subagents + Validation): Eight agent definitions, orchestrator CLAUDE.md, settings and hooks
- **Phase 3** (Extension): VS Code extension with Memory Browser, Findings Panel, Tasks Panel, Dashboard webview, setup wizard
- **Phase 4** (Governance + E2E): Governance server, governed task system, AI-powered review, holistic collective-intent review with two-layer assurance, E2E harness with 14 scenarios and 292+ assertions
- **Phase 5** (Remote Operation): AVT Gateway (FastAPI, 35 REST endpoints, WebSocket push, job runner), dual-mode React dashboard, container packaging (Docker, Codespaces), mobile-responsive layout
- **Agent Teams Adaptation**: Five-hook verification layer (PostToolUse, PreToolUse, TeammateIdle, TaskCompleted), session-scoped holistic review flag files, token usage tracking with dashboard panel, CLAUDE.md skills refactor (963 -> 284 lines), KG client TTL caching

**Total test assertions**: 37 unit + 15 MCP + 13 capability + 292 E2E = 357 assertions

**Planned**: Cross-project memory, multi-worker parallelism patterns, installation script for target projects, native `.claude/agents/` teammate loading (blocked on Issue #24316).

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) -- Orchestrator instructions and protocols
- [Architecture](./architecture/) -- System architecture documentation
- [COLLABORATIVE_INTELLIGENCE_VISION.md](../COLLABORATIVE_INTELLIGENCE_VISION.md) -- Original vision document (conceptual foundation)
- [ARCHITECTURE.md](../ARCHITECTURE.md) -- Engineering-level architecture specification
- [E2E Testing Harness](../e2e/README.md) -- Autonomous test suite documentation
- [Knowledge Graph Server](../mcp-servers/knowledge-graph/README.md) -- KG API and tier protection
- [Quality Server](../mcp-servers/quality/README.md) -- Quality tools and trust engine
- [Governance Server](../mcp-servers/governance/README.md) -- Governance tools and governed tasks
- [AVT Gateway](../server/pyproject.toml) -- Standalone web gateway for remote operation
- On-demand skills: `.claude/skills/*.md` -- Detailed protocol documentation
