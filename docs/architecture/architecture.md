# AVT System Architecture

This document describes the technical architecture of the Agent Vision Team system: the data flows, component interactions, concurrency patterns, and data models that make multi-agent governed development work.

**Last Updated**: 2026-02-14

---

## Architecture Overview

The AVT system has four architectural layers, each with distinct responsibilities:

```
+---------------------------------------------------------------+
|  LAYER 1: ORCHESTRATION (Claude Code Native)                  |
|  Agent Teams lead + teammates, shared task list, hooks        |
+---------------------------------------------------------------+
          |                    |                    |
+---------------------------------------------------------------+
|  LAYER 2: VERIFICATION (Five Lifecycle Hooks)                 |
|  PostToolUse, PreToolUse, TeammateIdle, TaskCompleted         |
+---------------------------------------------------------------+
          |                    |                    |
+---------v-----+  +---------v-----+  +-----------v-----------+
|  LAYER 3a:    |  |  LAYER 3b:    |  |  LAYER 3c:            |
|  Knowledge    |  |  Quality      |  |  Governance            |
|  Graph        |  |  Server       |  |  Server                |
|  (JSONL)      |  |  (SQLite)     |  |  (SQLite + AI Review)  |
+---------------+  +---------------+  +------------------------+
                                             |
+---------------------------------------------------------------------------+
|  LAYER 4: OBSERVABILITY (VS Code Extension / AVT Gateway)                 |
|  React dashboard, REST API, WebSocket, transport abstraction              |
+---------------------------------------------------------------------------+
```

**Layer 1 (Orchestration)** is entirely Claude Code native. The lead session decomposes tasks and spawns teammates. Teammates are full Claude Code sessions with independent MCP access, shared task lists, and self-claim. No custom orchestration code exists.

**Layer 2 (Verification)** is the bridge between Claude Code's native capabilities and the governance system. Five hooks intercept platform events (task creation, tool use, plan mode exit, teammate idle, task completion) and enforce governance invariants.

**Layer 3 (MCP Servers)** provides the three capabilities Claude Code lacks: persistent memory (KG), deterministic quality checks (Quality), and transactional governance review (Governance). Each server runs as a separate process communicating via MCP protocol (stdio in production, SSE in development).

**Layer 4 (Observability)** provides human visibility. The VS Code extension and AVT Gateway both present the same React dashboard, connecting to Layer 3 servers. This layer is read-heavy and does not affect agent behavior.

---

## Component Interaction Diagram

```
Human
  |
  v
Lead Session (Opus 4.6)
  |
  +-- TaskCreate("Implement auth")
  |     |
  |     v [PostToolUse hook fires]
  |     governance-task-intercept.py
  |       +-- Creates review-abc in governed_tasks table
  |       +-- Sets blockedBy on impl task
  |       +-- Creates .avt/.holistic-review-pending-{session_id}
  |       +-- Spawns _holistic-settle-check.py (background, 3s delay)
  |
  +-- TaskCreate("Add tests") ... (same hook cycle)
  |
  +-- Tries to Write/Edit/Bash/Task
  |     |
  |     v [PreToolUse hook fires]
  |     holistic-review-gate.sh
  |       +-- Checks: .avt/.holistic-review-pending-* exists?
  |       +-- YES -> exit 2 (redirect: "Holistic review in progress")
  |       +-- NO  -> exit 0 (proceed, ~1ms fast path)
  |
  +-- [Background] _holistic-settle-check.py wakes up
  |     +-- Queries governed_tasks: any newer than me?
  |     +-- NO -> Runs review_task_group() via claude --print
  |     +-- Verdict approved -> Removes flag, queues individual reviews
  |
  +-- Spawns Teammate "worker-1" (Agent Teams)
        |
        +-- Teammate self-claims unblocked task
        +-- Teammate calls submit_decision() -> Governance Server
        |     +-- KGClient loads vision standards (cached, 5min TTL)
        |     +-- Governance reviewer runs via claude --print
        |     +-- Verdict returned synchronously
        +-- Teammate implements
        +-- Teammate calls check_all_gates() -> Quality Server
        +-- Teammate marks task complete
              |
              v [TaskCompleted hook fires]
              task-completed-gate.sh
                +-- Checks governed_tasks status
                +-- If pending_review -> exit 2 (block completion)
                +-- If approved -> exit 0 (allow)
```

---

## Data Flow: Governance Decision Lifecycle

A single governance decision flows through multiple components:

```
1. Agent calls submit_decision(task_id, category, summary, intent, ...)
   |
   v
2. Governance Server (server.py)
   +-- Stores Decision in SQLite (decisions table)
   +-- Loads vision standards via KGClient (cached)
   +-- Loads architecture entities via KGClient (cached)
   |
   v
3. Reviewer (reviewer.py)
   +-- Builds prompt: vision standards + architecture + decision details
   +-- Writes prompt to temp file (avoids CLI arg length limits)
   +-- Runs: claude --print < temp_input > temp_output
   +-- Parses structured verdict from output
   +-- Records UsageRecord (tokens, duration, prompt size)
   |
   v
4. Governance Server
   +-- Stores ReviewVerdict in SQLite (reviews table)
   +-- Records decision in KG via KGClient.record_decision()
   +-- Returns verdict to calling agent
   |
   v
5. Agent acts on verdict
   +-- approved: proceed with implementation
   +-- blocked: revise based on guidance, resubmit
   +-- needs_human_review: escalate to orchestrator
```

---

## Data Flow: Hook-Based Task Governance

When any agent calls `TaskCreate`, the PostToolUse hook creates the governance chain:

```
1. TaskCreate("Implement auth service")
   +-- Claude Code creates task file (e.g., 1.json)
   |
   v
2. PostToolUse hook fires (governance-task-intercept.py)
   +-- _discover_task_id(): finds newest task file (prefers unblocked)
   +-- Governance Server: create_governed_task()
   |   +-- Creates GovernedTaskRecord (session_id from hook input)
   |   +-- Creates TaskReviewRecord (status: pending)
   |   +-- Returns review_task_id
   +-- Claude Code Task API: adds blockedBy[review_task_id] to impl task
   +-- Creates flag file: .avt/.holistic-review-pending-{session_id}
   +-- Spawns settle checker (background process)
   |
   v
3. Settle Checker (_holistic-settle-check.py, wakes after 3s)
   +-- Queries governed_tasks: tasks with same session_id newer than me?
   +-- If YES: exit (a newer checker will handle it)
   +-- If NO: I'm the last task
   |   +-- If task_count < MIN_TASKS_FOR_REVIEW (2): skip holistic review
   |   +-- Else: run review_task_group()
   |       +-- Collects all task subjects from session
   |       +-- Builds collective intent prompt
   |       +-- Runs claude --print for AI review
   |       +-- Stores HolisticReviewRecord
   |       +-- If approved: removes flag, queues individual reviews
   |       +-- If issues: writes guidance to flag file
   |
   v
4. Individual Reviews (queued after holistic approval)
   +-- Each review task processed via complete_task_review()
   +-- On approval: updates GovernedTaskRecord status
   +-- Removes blockedBy from implementation task
   +-- Task becomes available for teammate self-claim
```

---

## Concurrency Model

### Agent Teams Concurrency

```
Lead Session
  |
  +-- Teammate "architect-1" (full Claude Code session)
  |     +-- Own MCP connections (KG, Quality, Governance)
  |     +-- Own hook enforcement (all 5 hooks)
  |     +-- Own session_id for holistic review
  |
  +-- Teammate "worker-1" (full Claude Code session)
  |     +-- Shared task list (self-claim)
  |     +-- Direct messaging to/from other teammates
  |
  +-- Teammate "worker-2" (full Claude Code session)
  |     +-- Can work in parallel with worker-1
  |     +-- Separate git worktree for isolation
  |
  +-- Teammate "quality-reviewer-1" (full Claude Code session)
        +-- Reviews worker diffs after completion
```

**Task list concurrency**: All teammates share a task list. Self-claim uses Claude Code's native task locking; two teammates cannot claim the same task. Tasks transition through states: `pending` -> `in_progress` -> `completed`.

**Session-scoped holistic review**: Each session (lead, each teammate) gets its own holistic review flag file. Teammate "worker-1" creating tasks triggers a holistic review scoped to worker-1's session, without blocking worker-2's session.

**SQLite concurrency**: The governance store uses SQLite's WAL mode for concurrent reads. Write serialization is handled by SQLite's file locking. Hook scripts that write to the DB use short transactions to minimize lock contention.

### Settle/Debounce Pattern

The holistic review uses a settle pattern to detect when task creation has finished:

```
Time:  0ms    50ms    100ms   3100ms   3150ms   6150ms
       |       |       |       |        |        |
Task 1 +------>|       |       |        |        |
       |  Task 2 +---->|       |        |        |
       |       |  Task 3 +---->|        |        |
       |       |       |       |        |        |
Check 1 ........[wait 3s]......X (newer exists, exit)
       Check 2 .........[wait 3s].......X (newer exists, exit)
              Check 3 ..........[wait 3s]........+ (I'm last -> review)
```

Each `TaskCreate` spawns a background checker that waits 3 seconds. When it wakes, it queries the DB for any tasks with the same session_id created after it. If newer tasks exist, it exits silently. Only the checker for the last task proceeds to run the holistic review.

---

## Data Models

### Governance Server Models (Pydantic)

```
Decision
  +-- id: str (uuid hex, 12 chars)
  +-- task_id: str
  +-- sequence: int
  +-- agent: str
  +-- category: DecisionCategory (pattern_choice | component_design |
  |                                api_design | deviation | scope_change)
  +-- summary: str
  +-- detail: str
  +-- intent: str              # WHY this decision
  +-- expected_outcome: str     # WHAT measurable result
  +-- vision_references: [str]  # Which vision standards served
  +-- components_affected: [str]
  +-- alternatives_considered: [Alternative]
  +-- confidence: Confidence (high | medium | low)
  +-- created_at: str (ISO 8601)

ReviewVerdict
  +-- id: str
  +-- decision_id: str?
  +-- plan_id: str?
  +-- verdict: Verdict (approved | blocked | needs_human_review)
  +-- findings: [Finding]
  +-- guidance: str
  +-- strengths_summary: str
  +-- standards_verified: [str]
  +-- reviewer: str
  +-- created_at: str

Finding
  +-- tier: str (vision | architecture | quality)
  +-- severity: str
  +-- description: str
  +-- suggestion: str
  +-- strengths: [str]          # What's sound (PIN methodology)
  +-- salvage_guidance: str     # What to preserve

GovernedTaskRecord
  +-- id: str
  +-- implementation_task_id: str
  +-- subject: str
  +-- description: str
  +-- context: str
  +-- reviews: [str]            # TaskReviewRecord IDs
  +-- current_status: str       # pending_review | approved | blocked
  +-- session_id: str           # Links tasks from same session
  +-- created_at: str
  +-- released_at: str?

TaskReviewRecord
  +-- id: str
  +-- review_task_id: str
  +-- implementation_task_id: str
  +-- review_type: ReviewType (governance | security | architecture |
  |                            memory | vision | custom)
  +-- status: TaskReviewStatus (pending | in_progress | approved |
  |                             blocked | needs_human_review)
  +-- context: str
  +-- verdict: Verdict?
  +-- guidance: str
  +-- findings: [Finding]
  +-- standards_verified: [str]
  +-- created_at: str
  +-- completed_at: str?

UsageRecord
  +-- id: str
  +-- timestamp: str
  +-- session_id: str
  +-- agent: str                # e.g., "governance-reviewer"
  +-- operation: str            # review_decision | review_plan |
  |                             # review_completion | review_task_group |
  |                             # hook_review
  +-- model: str                # sonnet | opus | haiku
  +-- input_tokens: int
  +-- output_tokens: int
  +-- cache_read_tokens: int
  +-- cache_creation_tokens: int
  +-- duration_ms: int
  +-- related_id: str           # Links to decision/review/task
  +-- prompt_bytes: int

HolisticReviewRecord
  +-- id: str
  +-- session_id: str
  +-- task_ids: [str]
  +-- task_subjects: [str]
  +-- collective_intent: str
  +-- verdict: Verdict?
  +-- findings: [Finding]
  +-- guidance: str
  +-- strengths_summary: str
  +-- standards_verified: [str]
  +-- reviewer: str
  +-- created_at: str
```

### Knowledge Graph Models

```
Entity (JSONL record)
  +-- type: "entity"
  +-- name: str                 # Unique identifier
  +-- entityType: str           # vision_standard | architectural_standard |
  |                             # pattern | component | governance_decision |
  |                             # research_finding | ...
  +-- observations: [str]       # Timestamped notes
  +-- protection_tier: str?     # vision | architecture | quality

Relation (JSONL record)
  +-- type: "relation"
  +-- from: str                 # Source entity name
  +-- to: str                   # Target entity name
  +-- relationType: str         # implements | depends_on | violates | ...
```

---

## Storage Architecture

### SQLite Schema (Governance Server)

```
governance.db
  +-- decisions          # Agent decisions with intent/outcome
  +-- reviews            # Review verdicts with findings
  +-- governed_tasks     # Task governance state + session_id
  +-- task_reviews       # Individual review records
  +-- usage              # Token usage tracking per AI invocation
  +-- holistic_reviews   # Collective task group review records
```

All tables use TEXT primary keys (UUID hex). The `governed_tasks` table includes `session_id` for session-scoped queries. The `usage` table enables aggregation by period, agent, operation, and session.

### JSONL (Knowledge Graph)

```
.avt/knowledge-graph.jsonl
  Line 1: {"type": "entity", "name": "...", "entityType": "...", ...}
  Line 2: {"type": "relation", "from": "...", "to": "...", ...}
  ...
```

Append-only during normal operation. `compact()` rewrites from in-memory state (caution: see KGClient race condition in Known Issues below).

### Flag Files (Session-Scoped Holistic Review)

```
.avt/.holistic-review-pending-{session_id}
```

Created by PostToolUse hook. Checked by PreToolUse gate via glob (`~1ms`). Removed by settle checker on holistic review approval. Auto-cleared after 5 minutes (stale recovery). Each concurrent session gets its own flag.

---

## Caching Architecture

### KGClient TTL Cache

The governance server's `KGClient` caches frequently-read KG queries to avoid repeated JSONL file parsing during review bursts:

```
KGClient
  +-- _cache: dict[str, tuple[float, list[dict]]]
  |     Key: "vision_standards" | "architecture_entities"
  |     Value: (monotonic_timestamp, cached_data)
  +-- _CACHE_TTL: 300 seconds (5 minutes)
  +-- invalidate_cache(): clears all cached entries
```

**Design decisions**:
- Instance-level cache (not global) for test isolation
- `time.monotonic()` for accurate TTL (immune to wall-clock changes)
- No automatic invalidation on writes (vision standards are immutable; 5-minute staleness for architecture entities is acceptable)
- Explicit `invalidate_cache()` for programmatic control

---

## CLI Invocation Pattern

All AI review invocations use temp-file I/O to avoid CLI argument length limits (~256KB on macOS) and pipe buffering issues:

```
Python (reviewer.py):
  1. Write prompt to temp file (tempfile.mkstemp())
  2. subprocess.run(["claude", "--print", ...], stdin=input_fd, stdout=output_fd)
  3. Read output from temp file
  4. Clean up in finally block
  5. Reject prompts over 100KB before sending

TypeScript (DashboardWebviewProvider.ts):
  1. Write prompt to temp file (fs.mkdtemp + writeFile)
  2. spawn with file descriptors: stdio: [inputFd, outputFd, 'pipe']
  3. Read output from temp file
  4. Clean up in finally block
  5. Size gate: reject raw content over 100KB
```

---

## Transport Abstraction (Dual-Mode Dashboard)

The React dashboard operates in two modes through a transport abstraction:

```
                   DashboardContext.tsx
                         |
                   useTransport()
                    /          \
          VS Code mode      Web mode
          |                 |
  postMessage()       HTTP fetch() + WebSocket
  addEventListener    Route lookup table
```

**VS Code mode**: Messages flow through `acquireVsCodeApi().postMessage()` to `DashboardWebviewProvider.ts`, which routes to MCP clients or file system operations.

**Web mode**: Messages are mapped to HTTP endpoints via a route lookup table in `useTransport.ts`. Server-push events arrive over WebSocket with auto-reconnect. The same React components work unchanged in both modes.

**Key design**: `DashboardContext.tsx` required exactly one line change (swapping `useVsCodeApi()` for `useTransport()`). All 29+ components work identically in both modes.

---

## Known Issues

### KGClient Compact Race Condition

`KGClient.record_decision()` appends directly to JSONL, bypassing the `KnowledgeGraph` in-memory cache. If `compact()` runs before a reload, it rewrites JSONL from memory, silently dropping KGClient-appended records.

**Workaround**: Call `kg._load_from_storage()` after KGClient writes, before compaction.

**Permanent fix needed**: Route KGClient writes through the KG API, or have `compact()` reload from storage first.

### Agent Definition Loading (Issue #24316)

`.claude/agents/` definitions cannot yet be used directly when spawning Agent Teams teammates. The lead must read the agent file and embed the full system prompt in the spawn instruction. This is a Claude Code platform limitation expected to be resolved.

### Nested Session Detection (Claude Code 2.1.42+)

Running `claude -p` inside a Claude Code session fails unless `unset CLAUDECODE` is called first. This affects the governance reviewer's `claude --print` invocations, which must unset the variable before spawning.
