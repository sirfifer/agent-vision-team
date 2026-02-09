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
  │ Create Governed │  Each task is paired with a
  │ Task            │  governance review — GOVERNED
  └────────┬────────┘  FROM CREATION
           │
  ┌────────▼────────┐
  │  Governance     │  Reviews against vision
  │  Review         │  standards and architecture
  └────┬───────┬────┘
       │       │
   Approved  Needs Revision
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

**Rapid, reliable verification.** Every task is reviewed
before work begins. Every decision is checked before execution.
