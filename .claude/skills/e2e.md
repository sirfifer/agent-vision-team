# /e2e — Run the End-to-End Test Suite

Run the autonomous E2E testing harness for the Collaborative Intelligence System. This exercises all three MCP servers (Knowledge Graph, Governance, Quality) across 14 scenarios with 292+ structural assertions.

## What This Does

Each run:
1. **Generates a unique project** from a pool of 8 domains (Pet Adoption, Restaurant Reservation, Fitness Tracking, Online Learning, Smart Home, Inventory Management, Event Ticketing, Fleet Management). The domain is randomly selected, and all vision standards, architecture patterns, and components are filled from domain-specific templates.
2. **Runs 14 test scenarios in parallel**, each with fully isolated storage (separate KG JSONL, SQLite DB, and task directory per scenario).
3. **Validates deterministic outcomes** using structural, domain-agnostic assertions. "Vision entity is immutable" is true regardless of whether the domain is Pet Adoption or Fleet Management.

## Steps

1. Run the E2E harness:

```bash
./e2e/run-e2e.sh
```

2. Read the console output. You will see a summary like:

```
============================================
  AVT E2E Test Suite
============================================
  Workspace: /tmp/avt-e2e-XXXXXX
```

Followed by per-scenario PASS/FAIL lines and a totals section.

3. **If all 14 scenarios pass**: Report the results, including domain name, assertion count, and that all scenarios passed. Note the randomly selected domain to confirm uniqueness.

4. **If any scenario fails**: Diagnose the failure.

   a. Read the failure details in the console output. Each failed assertion shows expected vs actual values.

   b. The failure is in the **server code**, not the test. The E2E scenarios call the actual Python library APIs (`KnowledgeGraph`, `GovernanceStore`, `TaskFileManager`, `TrustEngine`) directly. A test failure means the server behavior has drifted from the expected contract.

   c. Trace the failure to the source:
      - **s01 (KG Tier Protection)**: Check `mcp-servers/knowledge-graph/collab_kg/graph.py` tier enforcement
      - **s02 (Governance Decision Flow)**: Check `mcp-servers/governance/collab_governance/store.py` decision/verdict persistence
      - **s03 (Governed Task Lifecycle)**: Check `mcp-servers/governance/collab_governance/task_integration.py` task creation and blocking
      - **s04 (Vision Violation)**: Check KG tier protection for vision-tier entities
      - **s05 (Architecture Deviation)**: Check governance store `deviation`/`scope_change` categorization
      - **s06 (Quality Gates)**: Check `GovernanceStore.get_status()` aggregate counts
      - **s07 (Trust Engine)**: Check `mcp-servers/quality/collab_quality/trust_engine.py` finding/dismissal lifecycle
      - **s08 (Multi-Blocker Task)**: Check `task_integration.py` multi-blocker release logic
      - **s09 (Scope Change Detection)**: Check governance store `needs_human_review` flagging for scope_change/deviation
      - **s10 (Completion Guard)**: Check `has_unresolved_blocks()` and `has_plan_review()` guards
      - **s11 (Hook-Based Governance)**: Check `scripts/hooks/governance-task-intercept.py` hook mechanics
      - **s12 (Cross-Server Integration)**: Check interplay between KG, Governance, and Task systems
      - **s13 (Hook Pipeline at Scale)**: Check hook interception under concurrent load (50 rapid + 20 concurrent tasks)
      - **s14 (Persistence Lifecycle)**: Full two-phase test of all 6 persistence stores via all data flow paths

   d. Fix the server code, then re-run to confirm the fix.

5. **For reproducible debugging**: Use `--seed` and `--keep`:

```bash
./e2e/run-e2e.sh --seed 42 --keep
```

This uses a fixed RNG seed (same domain every time) and preserves the workspace after the run so you can inspect the generated KG, governance DB, and task files.

6. **For verbose output**: Add `--verbose`:

```bash
./e2e/run-e2e.sh --verbose
```

## Key Design Principles

- **Assertions are structural, not string-matching.** "A governed task is verified before work begins" is checked by confirming the implementation task's `blockedBy` array is non-empty immediately after creation, regardless of what the task subject says.
- **Each run is a genuine system test.** The random domain selection means the harness is continuously testing that the system works with arbitrary data, not just canned fixtures.
- **Failures point to server drift.** If a scenario that passed yesterday fails today, something changed in the MCP server code. The test scenarios themselves are stable.
- **AI reviewer is bypassed.** The `GOVERNANCE_MOCK_REVIEW` env var (set automatically by `run-e2e.sh`) returns a deterministic "approved" verdict so tests don't depend on a live `claude` binary.

## Scenario Reference

| # | Name | What It Tests | Assertions |
|---|------|---------------|------------|
| 01 | KG Tier Protection | CRUD operations + tier-based access control | ~13 |
| 02 | Governance Decision Flow | Decision storage, review verdicts, status queries | ~19 |
| 03 | Governed Task Lifecycle | Task pair creation, blocking, release, multi-blocker | ~26 |
| 04 | Vision Violation | Vision-tier entity immutability | ~10 |
| 05 | Architecture Deviation | DEVIATION and SCOPE_CHANGE decision storage | ~12 |
| 06 | Quality Gates | GovernanceStore.get_status() aggregate counts | ~13 |
| 07 | Trust Engine | Finding lifecycle: record, dismiss, audit trail | ~13 |
| 08 | Multi-Blocker Task | 3 stacked blockers released one at a time | ~18 |
| 09 | Scope Change Detection | scope_change/deviation → needs_human_review | ~14 |
| 10 | Completion Guard | has_unresolved_blocks() and has_plan_review() | ~11 |
| 11 | Hook-Based Governance | PostToolUse interception, pair creation, loop prevention | ~25 |
| 12 | Cross-Server Integration | KG + Governance + Task system interplay | ~23 |
| 13 | Hook Pipeline at Scale | 50 rapid + 20 concurrent tasks, 100% interception | ~24 |
| 14 | Persistence Lifecycle | Two-phase: populate all stores, validate, clean up | ~71 |
