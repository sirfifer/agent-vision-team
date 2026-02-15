---
name: e2e-testing
description: E2E Testing harness details, scenarios, and interpretation guide
user_invocable: true
---

# E2E Testing

The project includes an autonomous end-to-end testing harness that exercises all three MCP servers (KG, Governance, Quality) across 14 scenarios with 292+ structural assertions.

## Quick Start

Use the `/e2e` skill or run directly:

```bash
./e2e/run-e2e.sh              # standard run (workspace cleaned up)
./e2e/run-e2e.sh --keep       # preserve workspace for debugging
./e2e/run-e2e.sh --seed 42    # reproducible project generation
./e2e/run-e2e.sh --verbose    # enable debug logging
```

## How It Works

Each run generates a **unique project** from a pool of 8 domains (Pet Adoption, Restaurant Reservation, Fitness Tracking, etc.). The domain is randomly selected, and vision standards, architecture patterns, and components are filled from domain-specific templates. All assertions are **structural and domain-agnostic**.

Scenarios run in parallel with full isolation: each gets its own KnowledgeGraph (JSONL), GovernanceStore (SQLite), and TaskFileManager (directory). The `GOVERNANCE_MOCK_REVIEW` env var is set automatically so tests don't depend on a live `claude` binary.

## What It Tests

| Scenario | What It Validates |
|----------|-------------------|
| KG Tier Protection | CRUD + tier-based access control (vision entities immutable by workers) |
| Governance Decision Flow | Decision storage, review verdicts, status queries |
| Governed Task Lifecycle | Task pair creation, blocking from birth, release on approval |
| Vision Violation | Attempts to modify vision-tier entities are rejected |
| Architecture Deviation | deviation/scope_change categories stored and flagged correctly |
| Quality Gates | GovernanceStore.get_status() returns accurate aggregates |
| Trust Engine | Finding record, dismiss, audit trail lifecycle |
| Multi-Blocker Task | 3 stacked blockers released one at a time |
| Scope Change Detection | scope_change/deviation -> needs_human_review verdict |
| Completion Guard | Unresolved blocks and missing plan reviews are caught |
| Cross-Server Integration | KG + Governance + Task system interplay |
| Hook-Based Governance | PostToolUse interception, pair creation, loop prevention |
| Hook Pipeline at Scale | 50 rapid + 20 concurrent tasks, 100% interception |
| Persistence Lifecycle | Full two-phase test: populate all 6 stores via all data flow paths, validate, clean up |

## When to Run

- **After modifying any MCP server code** (catches contract drift)
- **Before significant releases** (confirms all three servers work together)
- **After governance or task system changes** (scenarios s03, s08, s10 specifically test the governed task flow)
- **Periodically** (random domain selection means each run is a genuine uniqueness test)

## Interpreting Failures

If a scenario fails, the problem is in the **server code**, not the test. The scenarios call actual Python library APIs directly. Trace failures using the scenario-to-source mapping in the `/e2e` skill documentation.

## File Structure

```
e2e/
├── run-e2e.sh                  # Shell entry point
├── run-e2e.py                  # Python orchestrator
├── pyproject.toml              # Dependencies (pydantic, hatchling)
├── generator/                  # Unique project generation
│   ├── project_generator.py    # Domain selection + template filling
│   └── domain_templates.py     # 8 domain vocabulary pools
├── scenarios/                  # 14 test scenarios (s01-s14)
│   └── base.py                 # BaseScenario + assertion helpers
├── parallel/
│   └── executor.py             # ThreadPoolExecutor + per-scenario isolation
└── validation/
    ├── assertion_engine.py     # Domain-agnostic assertion helpers
    └── report_generator.py     # JSON + console report output
```
