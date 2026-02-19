# Task Governance Flow

## Description

End-to-end flow from task creation through governance review to task execution. Shows how the PostToolUse hook, holistic review, and individual review interact.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant CC as Claude Code
    participant PTU as PostToolUse Hook
    participant DB as Governance DB
    participant SC as Settle Checker
    participant HR as Holistic Reviewer
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
    HR->>IR: Queue individual reviews

    IR->>DB: Review task A individually
    IR->>DB: Approve R1
    IR->>DB: Remove blockedBy(A, R1)
    IR->>DB: Review task B individually
    IR->>DB: Approve R2
    IR->>DB: Remove blockedBy(B, R2)

    O->>W: Spawn worker for task A
    W->>W: Check gates, implement
    W->>CC: TaskCompleted(A)
```
