# Task Governance Flow

## Description

End-to-end flow from task creation through governance review to task execution, including context update integration. Shows how the PostToolUse hook, holistic review, individual review, and session context evolution interact.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant CC as Claude Code
    participant PTU as PostToolUse Hook
    participant DB as Governance DB
    participant AE as Audit Emitter
    participant SC as Settle Checker
    participant HR as Holistic Reviewer
    participant CU as Context Updater
    participant IR as Individual Reviewer
    participant ASC as Audit Settle Checker
    participant W as Worker

    O->>CC: TaskCreate("Implement feature A")
    CC->>PTU: PostToolUse event
    PTU->>DB: Create review task R1
    PTU->>DB: blockedBy(A, R1)
    PTU->>DB: Record session S1
    PTU->>AE: emit_audit_event("governance.task_pair_created")
    PTU->>ASC: Spawn audit settle checker (5s)
    PTU-->>CC: Exit 0

    O->>CC: TaskCreate("Implement feature B")
    CC->>PTU: PostToolUse event
    PTU->>DB: Create review task R2
    PTU->>DB: blockedBy(B, R2)
    PTU->>DB: Record session S1
    PTU->>PTU: Create holistic flag
    PTU->>SC: Spawn settle checker (3s)
    PTU->>AE: emit_audit_event("governance.task_pair_created")
    PTU->>ASC: Spawn audit settle checker (5s)
    PTU-->>CC: Exit 0

    Note over SC: Wait 3s for quiet
    SC->>HR: Trigger holistic review
    HR->>DB: Load all session S1 tasks
    HR->>HR: Evaluate collectively
    HR->>DB: Approve holistic review
    HR->>DB: Remove holistic flag
    HR->>AE: emit_audit_event("governance.holistic_review_completed")
    HR->>CU: Spawn _update-session-context.py (background)
    HR->>IR: Queue individual reviews

    Note over CU: Update session context with milestones/discoveries

    IR->>DB: Review task A individually
    IR->>DB: Approve R1
    IR->>DB: Remove blockedBy(A, R1)
    IR->>AE: emit_audit_event("governance.individual_review_completed")
    IR->>CU: Spawn _update-session-context.py (background)
    IR->>DB: Review task B individually
    IR->>DB: Approve R2
    IR->>DB: Remove blockedBy(B, R2)
    IR->>AE: emit_audit_event("governance.individual_review_completed")
    IR->>CU: Spawn _update-session-context.py (background)

    Note over CU: Throttled: only runs if >60s since last update
    Note over ASC: Audit settles after 5s quiet; runs processor for stats + anomaly detection

    O->>W: Spawn worker for task A
    W->>W: Check gates, implement
    W->>CC: TaskCompleted(A)
```

## Context Update Integration Points

After governance reviews complete, the session context file (`.avt/.session-context-{session_id}.json`) is updated via `_update-session-context.py`:

1. **After holistic review**: `_holistic-settle-check.py` spawns the context updater to capture collective review findings
2. **After individual review**: `_run-governance-review.sh` spawns the context updater to mark goal progress and add discoveries
3. **Throttling**: Updates run at most once per 60 seconds (configurable via `sessionContextDebounceSeconds`)
4. **Non-blocking**: All context updates run as detached background processes (`start_new_session=True`)

## Audit Event Integration Points

When audit is enabled (`settings.audit.enabled: true`), hooks emit audit events alongside their normal behavior. All emissions are wrapped in `try/except: pass` (TAP guarantee) so they never affect governance operations.

1. **PostToolUse hook** (`governance-task-intercept.py`): Emits `governance.task_pair_created` after creating the review task pair; spawns `_audit-settle-check.py` (5s debounce, longer than governance's 3s)
2. **Holistic review** (`_holistic-settle-check.py`): Emits `governance.holistic_review_completed` or `governance.holistic_review_skipped`
3. **Individual review** (`_run-governance-review.sh`): Emits `governance.individual_review_completed` with verdict and review duration
4. **Plan exit gate** (`verify-governance-review.sh`): Emits `governance.plan_exit_attempted` with allowed/blocked status
5. **Task completion gate** (`task-completed-gate.sh`): Emits `task.completion_attempted` with allowed/blocked status
6. **Teammate idle gate** (`teammate-idle-gate.sh`): Emits `agent.idle_blocked` when a teammate is blocked from going idle

After events settle (5s of quiet), the audit processor reads new events, updates rolling statistics in SQLite, and checks anomaly thresholds. See [Audit Agent](../components/audit-agent.md) for the full processing pipeline.
