# Governance MCP Server

Transactional review checkpoints for agent decisions. Agents call governance tools, **receive a synchronous response**, and act on the verdict. Every checkpoint is a rapid round-trip, not fire-and-forget. This reliable verification is what enables safe multi-agent parallelism.

## Architecture

```
Agent calls submit_decision()
        │
        ▼
┌──────────────────────────┐
│  Governance MCP Server   │
│  (FastMCP, port 3103)    │
│                          │
│  1. Store in SQLite      │
│  2. Load KG standards    │
│  3. claude --print       │◄── governance-reviewer agent
│  4. Store verdict        │
│  5. Record in KG         │
│  6. Return verdict       │
└──────────────────────────┘
        │
        ▼
Agent receives {verdict, findings, guidance}
```

## Quick Start

```bash
# Install dependencies
cd mcp-servers/governance
uv sync

# Run the server
uv run python -m collab_governance.server
# → SSE on http://localhost:3103
```

The server is also configured in `.claude/settings.json` and starts automatically in Claude Code sessions.

## MCP Tools

### `submit_decision` — Primary checkpoint

Called by agents **before implementing any key decision**. The tool returns once the rapid review completes.

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | `str` | Task this decision belongs to |
| `agent` | `str` | Calling agent name (e.g. `"worker-1"`) |
| `category` | `str` | `pattern_choice`, `component_design`, `api_design`, `deviation`, `scope_change` |
| `summary` | `str` | Brief summary of the decision |
| `detail` | `str` | Detailed explanation |
| `components_affected` | `list[str]` | Component names affected |
| `alternatives_considered` | `list[dict]` | `[{option, reason_rejected}]` |
| `confidence` | `str` | `high`, `medium`, `low` |

**Returns:** `{verdict, decision_id, findings, guidance, standards_verified}`

**Verdict values:**
- `approved` — Proceed with implementation
- `blocked` — Revise approach per `guidance`, resubmit
- `needs_human_review` — Auto-assigned for `deviation` and `scope_change` categories

### `submit_plan_for_review` — Plan checkpoint

Called **before presenting a plan** to the human.

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | `str` | Task this plan belongs to |
| `agent` | `str` | Calling agent name |
| `plan_summary` | `str` | Brief summary |
| `plan_content` | `str` | Full plan (markdown) |
| `components_affected` | `list[str]` | Components the plan touches |

**Returns:** `{verdict, review_id, findings, guidance, decisions_reviewed, standards_verified}`

### `submit_completion_review` — Worker completion checkpoint

Called **when a worker finishes its task**.

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | `str` | Task being completed |
| `agent` | `str` | Completing agent name |
| `summary_of_work` | `str` | What was done |
| `files_changed` | `list[str]` | Modified files |

**Returns:** `{verdict, review_id, unreviewed_decisions, findings, guidance}`

Automatically flags if:
- Any decisions were never reviewed
- Any previously redirected decisions remain unresolved

### `get_decision_history` — Query

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | `str?` | Filter by task |
| `agent` | `str?` | Filter by agent |
| `verdict` | `str?` | Filter by verdict |

**Returns:** `{decisions: [{id, task_id, sequence, agent, category, summary, confidence, verdict, guidance, created_at}]}`

### `get_governance_status` — Dashboard

No parameters.

**Returns:** `{total_decisions, approved, blocked, needs_human_review, pending, recent_activity}`

## Internal Flow

When an agent calls `submit_decision`:

1. **Store** — Decision saved to SQLite (`.avt/governance.db`) with auto-incremented sequence
2. **Load standards** — Vision standards and architecture entities read from KG JSONL file
3. **Auto-flag** — `deviation` and `scope_change` categories automatically get `needs_human_review`
4. **AI review** — For other categories, runs `claude --print` with the governance-reviewer agent, passing decision details and all applicable standards
5. **Parse verdict** — Extracts structured JSON from the AI response (handles clean JSON, markdown blocks, and embedded JSON)
6. **Store review** — Verdict saved to SQLite linked to the decision
7. **Record in KG** — Decision+verdict appended to KG JSONL for institutional memory
8. **Return** — Verdict returned to the calling agent

## Modules

| Module | Purpose |
|--------|---------|
| `server.py` | FastMCP tool definitions and main entry point |
| `models.py` | Pydantic models: Decision, ReviewVerdict, Finding, Alternative, GovernedTaskRecord, HolisticReviewRecord |
| `store.py` | SQLite persistence: decisions, reviews, governed_tasks, holistic_reviews tables |
| `kg_client.py` | Direct JSONL reader for KG vision/architecture data |
| `reviewer.py` | `claude --print` orchestration with prompt templates, JSON parsing, and `review_task_group()` for holistic review |
| `session_state.py` | Generates `.avt/session-state.md` from governance DB (task stats, decision history) |
| `task_integration.py` | Direct manipulation of Claude Code task files for governed task execution |

## SQLite Schema

```sql
decisions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,     -- auto-incremented per task
    agent TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    detail TEXT,
    components_affected TEXT,       -- JSON array
    alternatives TEXT,              -- JSON array of {option, reason_rejected}
    confidence TEXT,
    created_at TEXT NOT NULL
)

reviews (
    id TEXT PRIMARY KEY,
    decision_id TEXT REFERENCES decisions(id),
    plan_id TEXT,                   -- NULL for decision reviews, set for plan/completion reviews
    verdict TEXT NOT NULL,          -- approved, blocked, needs_human_review
    findings TEXT,                  -- JSON array of {tier, severity, description, suggestion}
    guidance TEXT,
    standards_verified TEXT,        -- JSON array
    reviewer TEXT NOT NULL,
    created_at TEXT NOT NULL
)

governed_tasks (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    description TEXT,
    context TEXT,
    review_type TEXT DEFAULT 'governance',
    implementation_task_id TEXT,
    review_task_id TEXT,
    session_id TEXT,                -- links tasks from the same agent session
    status TEXT DEFAULT 'pending',
    verdict TEXT,
    guidance TEXT,
    findings TEXT,                  -- JSON array
    standards_verified TEXT,        -- JSON array
    created_at TEXT NOT NULL
)

holistic_reviews (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,       -- links to governed_tasks.session_id
    task_ids TEXT NOT NULL,         -- JSON array of implementation_task_ids
    task_subjects TEXT NOT NULL,    -- JSON array of task subjects
    collective_intent TEXT,
    verdict TEXT,                   -- approved, blocked, needs_human_review
    findings TEXT,                  -- JSON array
    guidance TEXT,
    standards_verified TEXT,        -- JSON array
    reviewer TEXT DEFAULT 'governance-reviewer',
    created_at TEXT NOT NULL
)
```

## Holistic Governance Review

Individual task review is necessary but not sufficient. Tasks that each pass review individually may collectively introduce unauthorized architectural shifts. Holistic review evaluates all tasks from a session as a group before work begins, typically completing in seconds.

### How It Works

```
Agent creates Task 1, 2, 3 ...
        |
        v
PostToolUse hook fires for each:
  - Records task with session_id + timestamp
  - Creates flag file: .avt/.holistic-review-pending
  - Spawns background settle checker (3s debounce)
        |
        v
Settle checker (last one) detects no newer tasks:
  - Calls reviewer.review_task_group()
  - Evaluates collective intent against vision standards
  - If approved: clears flag, queues individual reviews
  - If issues found: updates flag with constructive guidance
        |
        v
PreToolUse checkpoint on Write|Edit|Bash|Task:
  - Fast path (~1ms): no flag file -> allow
  - Flag exists: read status -> coordinate work sequencing
```

### Key Properties

- **MIN_TASKS_FOR_REVIEW = 2**: Single tasks skip holistic review (proceed directly to individual review)
- **Settle/debounce**: Each PostToolUse spawns a background checker that waits 3s. Only the last checker triggers the holistic review
- **session_id tracking**: All tasks from the same agent session are linked via `session_id` from the hook input
- **Stale flag recovery**: The PreToolUse checkpoint auto-clears flags older than 5 minutes
- **Subagent handling**: Subagents inherit hooks; if a subagent creates tasks after a session is approved, the settle checker detects the existing review and cleans up
- **Reviewer method**: `GovernanceReviewer.review_task_group()` runs `claude --print` with collective intent analysis

### Related Files

| File | Purpose |
|------|---------|
| `scripts/hooks/governance-task-intercept.py` | PostToolUse hook: creates flag, spawns settle checker |
| `scripts/hooks/_holistic-settle-check.py` | Background settle checker: debounce, holistic review trigger |
| `scripts/hooks/holistic-review-gate.sh` | PreToolUse checkpoint: coordinates work while review completes |
| `collab_governance/reviewer.py` | `review_task_group()` method for collective intent review |
| `collab_governance/models.py` | `HolisticReviewRecord` Pydantic model |
| `collab_governance/store.py` | `holistic_reviews` table, session-based queries |

## Verification Checkpoints

Two `PreToolUse` hooks provide deterministic verification:

1. **ExitPlanMode checkpoint** (`scripts/hooks/verify-governance-review.sh`): Checks the SQLite DB for plan review records. If none exist, redirects the agent to submit a plan review first. This is a backup mechanism for the Decision Protocol.

2. **Holistic review checkpoint** (`scripts/hooks/holistic-review-gate.sh`): Checks for `.avt/.holistic-review-pending` flag file. If present, coordinates work sequencing until holistic review completes, ensuring all mutation tools (Write, Edit, Bash) and delegation tools (Task) wait for the rapid collective intent verification. This is the primary assurance mechanism for collective intent review.

## Integration with VS Code Extension

The extension's `GovernanceClient` (`extension/src/mcp/GovernanceClient.ts`) wraps `get_governance_status` and `get_decision_history` for dashboard display. On connect and refresh, governance data populates the Activity Feed with decision/review entries.
