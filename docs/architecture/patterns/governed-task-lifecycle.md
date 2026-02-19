# Governed Task Lifecycle

## Type

pattern

## Description

Every task created via TaskCreate is automatically paired with a governance review through the PostToolUse hook. The review task is linked via `blockedBy`, preventing the implementation task from starting until governance approval. For groups of tasks (2+), a holistic review evaluates them collectively using timing-based settle detection.

## Lifecycle

```mermaid
sequenceDiagram
    participant Agent
    participant CC as Claude Code
    participant Hook as PostToolUse Hook
    participant DB as Governance DB
    participant Rev as AI Reviewer

    Agent->>CC: TaskCreate(subject, description)
    CC->>Hook: PostToolUse event (JSON)
    Hook->>DB: Create review task
    Hook->>DB: Add blockedBy relationship
    Hook->>DB: Record session_id
    Hook-->>CC: Exit 0 (task created)

    Note over Hook: If 2+ tasks in session
    Hook->>Hook: Create holistic review flag
    Hook->>Hook: Spawn settle checker (3s)

    Note over Hook: After 3s quiet
    Hook->>Rev: Holistic review of all tasks
    Rev-->>DB: Approve/block tasks
    Rev->>Hook: Remove holistic flag

    Note over Agent: Individual task reviews
    DB->>Rev: Queue individual reviews
    Rev-->>DB: Approve/block per task
    DB-->>Agent: Task unblocked (blockedBy removed)
```

## Key Properties

- Automatic (no explicit agent cooperation needed)
- Session-scoped (tasks grouped by session_id)
- Settle detection (3s debounce, last checker triggers)
- Stale flag recovery (5-minute auto-clear)
- Single tasks skip holistic review (MIN_TASKS_FOR_REVIEW = 2)
