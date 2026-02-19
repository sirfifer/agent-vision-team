# Agent Orchestration Flow

## Description

Flow showing how the orchestrator decomposes a complex task, spawns specialized agents, and manages the full lifecycle through review and memory curation.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant H as Human
    participant O as Orchestrator
    participant KG as Knowledge Graph
    participant A as Architect
    participant W as Worker(s)
    participant QR as Quality Reviewer
    participant KGL as KG Librarian
    participant GOV as Governance

    H->>O: Complex task request
    O->>KG: Query context (search_nodes, get_entities_by_tier)
    KG-->>O: Existing patterns, standards

    O->>O: Decompose into sub-tasks
    O->>GOV: TaskCreate (sub-tasks)
    Note over GOV: Hook intercepts, reviews

    alt Architecture needed
        O->>A: Spawn architect teammate
        A->>GOV: submit_decision (pattern choices)
        GOV-->>A: Approved/blocked
        A-->>O: Architecture plan
    end

    O->>W: Spawn worker teammates
    par Worker A
        W->>GOV: submit_decision (key choices)
        GOV-->>W: Approved
        W->>W: Implement
        W->>W: check_all_gates()
    and Worker B
        W->>GOV: submit_decision (key choices)
        GOV-->>W: Approved
        W->>W: Implement
        W->>W: check_all_gates()
    end

    O->>QR: Spawn quality reviewer
    QR->>QR: Review diffs (PIN methodology)
    QR-->>O: Findings (strengths + issues)
    O->>W: Route findings to workers

    W->>W: Address findings
    W-->>O: Complete

    O->>KGL: Spawn KG librarian
    KGL->>KG: Curate observations
    KGL->>KG: Consolidate, promote patterns

    O->>O: git tag checkpoint-NNN
    O-->>H: Task complete
```
