## The Governed Development Cycle

```
  ┌─────────────────┐
  │  Complex Task    │
  │  (from human)    │
  └────────┬────────┘
           │
  ┌────────▼────────┐
  │   Decompose     │  Orchestrator breaks task
  │   into units    │  into discrete task briefs
  └────────┬────────┘
           │
  ┌────────▼────────┐
  │ Create Governed │  Each task gets a governance
  │ Task            │  review blocker — BLOCKED
  └────────┬────────┘  FROM BIRTH
           │
  ┌────────▼────────┐
  │  Governance     │  Reviews against vision
  │  Review         │  standards and architecture
  └────┬───────┬────┘
       │       │
   Approved  Blocked
       │       │
       │   ┌───▼──────────┐
       │   │ Revise and   │
       │   │ resubmit     │──┐
       │   └──────────────┘  │ (loops until approved)
       │                     │
  ┌────▼────────┐     ┌──────┘
  │  Worker     │     │
  │  Implements │◄────┘
  └────────┬────┘
           │
  ┌────────▼────────┐
  │ Quality Gates   │  Build · Lint · Tests
  │                 │  Coverage · Findings
  └────────┬────────┘
           │
  ┌────────▼────────┐
  │  Merge &        │  Git merge + checkpoint
  │  Checkpoint     │  tag for recovery
  └─────────────────┘
```

**No race conditions.** Tasks cannot be picked up before
review. Every decision is checked before execution.
