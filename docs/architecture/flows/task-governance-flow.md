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
    participant SC as Settle Checker
    participant HR as Holistic Reviewer
    participant CU as Context Updater
    participant IR as Individual Reviewer
    participant W as Worker

    O->>CC: TaskCreate("Implement feature A")
    CC->>PTU: PostToolUse event
    PTU->>DB: Create review task R1
    PTU->>DB: blockedBy(A, R1)
    PTU->>DB: Record session S1
    PTU-->>CC: Exit 0

    O->>CC: TaskCreate("Implement feature B")
    CC->>PTU: PostToolUse event
    PTU->>DB: Create review task R2
    PTU->>DB: blockedBy(B, R2)
    PTU->>DB: Record session S1
    PTU->>PTU: Create holistic flag
    PTU->>SC: Spawn settle checker (3s)
    PTU-->>CC: Exit 0

    Note over SC: Wait 3s for quiet
    SC->>HR: Trigger holistic review
    HR->>DB: Load all session S1 tasks
    HR->>HR: Evaluate collectively
    HR->>DB: Approve holistic review
    HR->>DB: Remove holistic flag
    HR->>CU: Spawn _update-session-context.py (background)
    HR->>IR: Queue individual reviews

    Note over CU: Update session context with milestones/discoveries

    IR->>DB: Review task A individually
    IR->>DB: Approve R1
    IR->>DB: Remove blockedBy(A, R1)
    IR->>CU: Spawn _update-session-context.py (background)
    IR->>DB: Review task B individually
    IR->>DB: Approve R2
    IR->>DB: Remove blockedBy(B, R2)
    IR->>CU: Spawn _update-session-context.py (background)

    Note over CU: Throttled: only runs if >60s since last update

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
