# E2E Testing Harness

Autonomous end-to-end testing for the Collaborative Intelligence System. Exercises all three MCP servers (Knowledge Graph, Governance, Quality) across 14 scenarios with 292+ structural assertions.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
  - [Domain Generation](#domain-generation)
  - [Isolation Model](#isolation-model)
  - [Assertion Philosophy](#assertion-philosophy)
  - [AI Reviewer Bypass](#ai-reviewer-bypass)
- [Command-Line Options](#command-line-options)
- [Scenario Reference](#scenario-reference)
  - [s01 — KG Tier Protection](#s01--kg-tier-protection)
  - [s02 — Governance Decision Flow](#s02--governance-decision-flow)
  - [s03 — Governed Task Lifecycle](#s03--governed-task-lifecycle)
  - [s04 — Vision Violation](#s04--vision-violation)
  - [s05 — Architecture Deviation](#s05--architecture-deviation)
  - [s06 — Quality Gates](#s06--quality-gates)
  - [s07 — Trust Engine](#s07--trust-engine)
  - [s08 — Multi-Blocker Task](#s08--multi-blocker-task)
  - [s09 — Scope Change Detection](#s09--scope-change-detection)
  - [s10 — Completion Guard](#s10--completion-guard)
  - [s11 — Hook-Based Governance](#s11--hook-based-governance)
  - [s12 — Cross-Server Integration](#s12--cross-server-integration)
  - [s13 — Hook Pipeline at Scale](#s13--hook-pipeline-at-scale)
  - [s14 — Persistence Lifecycle](#s14--persistence-lifecycle)
- [Architecture](#architecture)
  - [Directory Structure](#directory-structure)
  - [Execution Flow](#execution-flow)
  - [Component Responsibilities](#component-responsibilities)
- [Writing New Scenarios](#writing-new-scenarios)
  - [Scenario Template](#scenario-template)
  - [Available Assertion Helpers](#available-assertion-helpers)
  - [Registering a New Scenario](#registering-a-new-scenario)
- [Adding New Domains](#adding-new-domains)
- [Report Format](#report-format)
  - [Console Output](#console-output)
  - [JSON Report](#json-report)
- [Debugging Failures](#debugging-failures)
  - [Scenario-to-Source Mapping](#scenario-to-source-mapping)
  - [Common Failure Patterns](#common-failure-patterns)
- [Environment Variables](#environment-variables)
- [FAQ](#faq)

## Overview

The E2E harness validates that the three MCP servers that make up the Collaborative Intelligence System behave correctly when exercised through their Python library APIs. It generates a unique project for every run, ensuring the system is continuously tested against arbitrary data rather than canned fixtures.

**What it tests:**
- Knowledge Graph tier protection (vision/architecture/quality enforcement)
- Governance decision lifecycle (storage, verdicts, history queries)
- Governed task system (atomic creation, blocking, review release)
- Trust engine (finding recording, justified dismissals, audit trail)
- Cross-server integration (KG + Governance + Quality working together)

**What it does NOT test:**
- MCP transport layer (HTTP/SSE) — scenarios use direct Python library imports
- The `claude --print` AI reviewer — bypassed via `GOVERNANCE_MOCK_REVIEW`
- VS Code extension behavior — covered by the extension's own test suite
- External tool execution (ruff, eslint, etc.) — covered by Quality server unit tests

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager (handles dependency installation automatically)

No other dependencies are required. The harness imports MCP server libraries directly from the monorepo; you do not need running servers.

## Quick Start

```bash
# Run the full suite (workspace is created and cleaned up automatically)
./e2e/run-e2e.sh

# Keep the workspace after the run for inspection
./e2e/run-e2e.sh --keep

# Use a fixed seed for reproducible domain selection
./e2e/run-e2e.sh --seed 42

# Enable debug-level logging
./e2e/run-e2e.sh --verbose

# Combine flags
./e2e/run-e2e.sh --seed 42 --keep --verbose
```

If you are using the Claude Code CLI with this project, you can also run `/e2e` to invoke the skill that runs the harness and interprets results.

## How It Works

### Domain Generation

Each run randomly selects one domain from a pool of 8:

| Domain | Prefix | Components |
|--------|--------|------------|
| Pet Adoption Platform | `pet_adoption` | AnimalProfileService, AdoptionMatchEngine, ShelterGateway |
| Restaurant Reservation System | `restaurant_reservation` | BookingService, TableLayoutEngine, WaitlistManager |
| Fitness Tracking App | `fitness_tracking` | WorkoutEngine, NutritionTracker, ProgressAnalytics |
| Online Learning Platform | `online_learning` | CourseEngine, AssessmentService, ProgressTracker |
| Smart Home Hub | `smart_home` | DeviceRegistry, AutomationEngine, EnergyMonitor |
| Inventory Management System | `inventory_mgmt` | StockTracker, OrderFulfillment, SupplierGateway |
| Event Ticketing Platform | `event_ticketing` | EventCatalog, SeatAllocator, PaymentGateway |
| Fleet Management System | `fleet_mgmt` | VehicleTracker, RouteOptimizer, MaintenanceScheduler |

For each domain, the generator:

1. Fills 5 **vision standard** templates with domain-specific language and randomly selected components
2. Fills 2-3 **architecture pattern** templates similarly
3. Writes a complete `.avt/` directory structure (project config, session state, memory stubs)
4. Seeds a `knowledge-graph.jsonl` with the generated vision/architecture entities
5. Creates a governance DB placeholder

The `--seed` flag pins the random number generator so the same domain and component assignments are produced every time, making failures reproducible.

### Isolation Model

Every scenario runs with fully isolated storage:

```
workspace/
├── project/                    # Generated project (shared, read-only by scenarios)
│   ├── .avt/
│   │   ├── project-config.json
│   │   ├── session-state.md
│   │   └── memory/
│   └── .avt/
│       ├── knowledge-graph.jsonl
│       └── governance.db
├── s01-kg-tier-protection/     # Per-scenario isolation
│   ├── knowledge-graph.jsonl   # Scenario's own KG
│   ├── governance.db           # Scenario's own SQLite
│   └── tasks/                  # Scenario's own task files
├── s02-governance-decision-flow/
│   ├── ...
└── e2e-report.json             # Final report
```

Each scenario receives its own:
- **`KnowledgeGraph`** instance backed by a per-scenario JSONL file, pre-seeded with 5 vision standards and 2 architecture patterns
- **`GovernanceStore`** instance backed by a per-scenario SQLite database
- **`TaskFileManager`** instance writing to a per-scenario task directory

This means scenarios never interfere with each other and can run in parallel safely.

**Library-mode scenarios** (all current scenarios) run concurrently via `ThreadPoolExecutor`. **HTTP-mode scenarios** (if any are added later for transport testing) run serially to avoid port conflicts.

### Assertion Philosophy

All assertions are **structural and domain-agnostic**. They verify system behavior contracts, not string content:

| Instead of | We assert |
|------------|-----------|
| `entity.name == "pet_adoption_vision_protocol_di"` | `entity is not None` (a vision entity was created) |
| `error.message == "Cannot delete vision entities"` | `result contains error indicator` (deletion was rejected) |
| `verdict == "approved"` for a specific decision | `decision with category=deviation gets verdict=needs_human_review` (categorical behavior) |

This means the same assertions pass regardless of which domain was randomly selected. A test failure indicates that the **server's behavioral contract has changed**, not that test data is stale.

### AI Reviewer Bypass

The governance server's `GovernanceReviewer` normally calls `claude --print` for AI-powered review. In E2E tests, the `GOVERNANCE_MOCK_REVIEW` environment variable (set automatically by `run-e2e.sh`) causes the reviewer to return a deterministic "approved" verdict:

```python
# In mcp-servers/governance/collab_governance/reviewer.py
if os.environ.get("GOVERNANCE_MOCK_REVIEW"):
    return json.dumps({
        "verdict": "approved",
        "findings": [],
        "guidance": "Mock review: auto-approved for E2E testing.",
        "standards_verified": ["mock"],
    })
```

Code-deterministic paths (like `deviation` and `scope_change` categories automatically getting `needs_human_review`) do not depend on the AI reviewer and work the same way in both modes.

## Command-Line Options

### Shell wrapper (`run-e2e.sh`)

| Flag | Description |
|------|-------------|
| `--keep` | Preserve the temp workspace after the run (default: cleaned up) |
| `--seed N` | Fix the RNG seed for reproducible domain generation |
| `--verbose` | Enable DEBUG-level logging |

### Python orchestrator (`run-e2e.py`)

The Python orchestrator accepts the same flags plus:

| Flag | Description |
|------|-------------|
| `--workspace PATH` | Root directory for the generated project and scenario isolation (required) |
| `--max-workers N` | Maximum parallel threads for library-mode scenarios (default: 4) |

Direct invocation (from the `e2e/` directory):

```bash
uv run python run-e2e.py --workspace /tmp/my-test --seed 42 --verbose
```

## Scenario Reference

### s01 — KG Tier Protection

**File:** `scenarios/s01_kg_tier_protection.py`
**What it tests:** CRUD operations across all three protection tiers.
**Key assertions (~13):**
- Vision-tier entities can be created and read
- Vision-tier entities cannot be deleted by agents
- Vision-tier observations cannot be removed by agents
- Architecture-tier entities can be created and read
- Architecture-tier entities cannot be deleted by agents
- Quality-tier entities can be freely created, read, modified, and deleted
- Entity creation with project-generated vision standards succeeds

### s02 — Governance Decision Flow

**File:** `scenarios/s02_governance_decision_flow.py`
**What it tests:** Decision persistence, review verdicts, and history queries in `GovernanceStore`.
**Key assertions (~19):**
- Decisions across multiple categories are stored correctly
- Decision fields (agent, summary, detail, components, confidence) persist accurately
- Decision history can be queried by task_id, agent, and verdict
- Category-specific metadata is preserved for downstream flagging

### s03 — Governed Task Lifecycle

**File:** `scenarios/s03_governed_task_lifecycle.py`
**What it tests:** The full governed task creation, blocking, and release cycle.
**Key assertions (~26):**
- `create_governed_task_pair` creates both review and implementation tasks atomically
- Implementation task is blocked from birth (non-empty `blockedBy` immediately after creation)
- Completing a review with "approved" releases the implementation task
- Completing a review with "blocked" keeps the implementation task blocked
- Multi-blocker scenarios: task stays blocked until ALL blockers are released

### s04 — Vision Violation

**File:** `scenarios/s04_vision_violation.py`
**What it tests:** That vision-tier KG entities are immutable by agents.
**Key assertions (~10):**
- Agent attempts to delete a vision entity are rejected
- Agent attempts to remove vision-tier observations are rejected
- Human callers can modify vision entities (when applicable)

### s05 — Architecture Deviation

**File:** `scenarios/s05_architecture_deviation.py`
**What it tests:** That `deviation` and `scope_change` decision categories are stored correctly and flagged for human review.
**Key assertions (~12):**
- Decisions with `deviation` category are stored
- Decisions with `scope_change` category are stored
- Both categories produce `needs_human_review` verdicts when processed through the governance flow

### s06 — Quality Gates

**File:** `scenarios/s06_quality_gates.py`
**What it tests:** `GovernanceStore.get_status()` aggregate counts after various operations.
**Key assertions (~13):**
- Status counts reflect the correct number of decisions, reviews, and their verdicts
- Counts update correctly as new decisions and reviews are added

### s07 — Trust Engine

**File:** `scenarios/s07_trust_engine.py`
**What it tests:** The full finding lifecycle in the trust engine.
**Key assertions (~13):**
- Findings can be recorded with all required fields
- Duplicate finding recording is handled gracefully (returns `False`)
- Findings can be dismissed with required justification
- Dismissal without justification is rejected
- Dismissal history is maintained as an audit trail
- Previously dismissed findings return `TRACK` (not `BLOCK`) on subsequent queries

### s08 — Multi-Blocker Task

**File:** `scenarios/s08_multi_blocker_task.py`
**What it tests:** Tasks with 3 stacked review blockers released one at a time.
**Key assertions (~18):**
- An implementation task can have multiple review blockers added
- Completing one blocker does not release the task if others remain
- The task is released only when the final blocker is completed with "approved"
- Each blocker's completion is tracked independently

### s09 — Scope Change Detection

**File:** `scenarios/s09_scope_change_detection.py`
**What it tests:** That `scope_change` and `deviation` categories are correctly identified and flagged.
**Key assertions (~14):**
- Decisions categorized as `scope_change` get `needs_human_review`
- Decisions categorized as `deviation` get `needs_human_review`
- The flagging is deterministic (based on category, not AI review)

### s10 — Completion Guard

**File:** `scenarios/s10_completion_guard.py`
**What it tests:** `has_unresolved_blocks()` and `has_plan_review()` guard methods.
**Key assertions (~11):**
- Tasks with pending review blockers are reported as having unresolved blocks
- Tasks with all blockers completed are reported as clear
- Plan review presence/absence is correctly detected

### s12 — Cross-Server Integration

**File:** `scenarios/s12_cross_server_integration.py`
**What it tests:** End-to-end flow across KG, Governance, and Task systems working together.
**Key assertions (~23):**
- KG entities created in vision/architecture tiers are readable
- Governance decisions can reference KG components
- KG standards are loadable by the governance reviewer's KG client
- Governed tasks can be created referencing governance decisions
- Status queries return accurate cross-system aggregates

### s11 — Hook-Based Governance

**File:** `scenarios/s11_hook_based_governance.py`
**What it tests:** PostToolUse hook interception mechanics for task governance.
**Key assertions (~25):**
- Hook fires on every TaskCreate call
- Governance pair (review task + implementation task) created atomically
- Implementation task is blocked from birth
- Loop prevention skips governance-prefixed tasks
- Async review queued and completed

### s13 — Hook Pipeline at Scale

**File:** `scenarios/s13_hook_pipeline_at_scale.py`
**What it tests:** Hook interception under concurrent load.
**Key assertions (~24):**
- 50 rapid sequential task creations, 100% interception
- 20 concurrent task creations, 100% interception
- No race conditions in governance pair creation
- Governance DB integrity under load

### s14 — Persistence Lifecycle

**File:** `scenarios/s14_persistence_lifecycle.py`
**What it tests:** Full two-phase integration test exercising all 6 persistence stores via all data flow paths.
**Key assertions (~71):**
- **Phase 1 (Populate):** Document ingestion, agent entity creation, governance decisions with KG context, governed task lifecycle, trust engine findings/dismissals, KG Librarian curation (consolidation, pattern promotion, stale removal), archival file sync (KG to .avt/memory/*.md), session state generation, cross-store validation
- **Phase 2 (Cleanup):** Delete quality-tier entities, reset memory files to templates, verify vision/architecture entities preserved, verify all stores queryable

## Architecture

### Directory Structure

```
e2e/
├── __init__.py
├── pyproject.toml              # Package metadata + dependencies (pydantic, hatchling)
├── uv.lock                     # Lockfile for reproducible installs
├── run-e2e.sh                  # Shell entry point: creates workspace, sets env, runs Python
├── run-e2e.py                  # Python orchestrator: generates project, runs scenarios, reports
│
├── generator/                  # Project generation subsystem
│   ├── __init__.py
│   ├── domain_templates.py     # 8 domain definitions with template placeholders
│   └── project_generator.py    # Random domain selection, template filling, filesystem writes
│
├── scenarios/                  # Test scenario modules (one class per file)
│   ├── __init__.py
│   ├── base.py                 # BaseScenario, ScenarioResult, AssertionResult, assertion helpers
│   ├── s01_kg_tier_protection.py
│   ├── s02_governance_decision_flow.py
│   ├── s03_governed_task_lifecycle.py
│   ├── s04_vision_violation.py
│   ├── s05_architecture_deviation.py
│   ├── s06_quality_gates.py
│   ├── s07_trust_engine.py
│   ├── s08_multi_blocker_task.py
│   ├── s09_scope_change_detection.py
│   ├── s10_completion_guard.py
│   └── s12_cross_server_integration.py
│
├── parallel/                   # Execution engine
│   ├── __init__.py
│   └── executor.py             # ThreadPoolExecutor with per-scenario isolation + KG seeding
│
└── validation/                 # Reporting subsystem
    ├── __init__.py
    ├── assertion_engine.py     # Domain-agnostic assertion helper functions
    └── report_generator.py     # JSON file + ANSI console output generation
```

### Execution Flow

```
run-e2e.sh
    │
    ├── Creates temp workspace (/tmp/avt-e2e-XXXXXX)
    ├── Sets GOVERNANCE_MOCK_REVIEW=true
    ├── cd to e2e/ directory (for uv dependency resolution)
    │
    └── run-e2e.py --workspace $WORKSPACE
            │
            ├── 1. generate_project(workspace/project, seed=...)
            │       └── Picks random domain, fills templates, writes .avt/ + KG
            │
            ├── 2. Instantiate all 11 scenario classes
            │       └── Each receives the GeneratedProject + workspace path
            │
            ├── 3. ParallelExecutor.run_scenarios(scenarios)
            │       ├── Library scenarios → ThreadPoolExecutor
            │       │   └── Per scenario: create isolated KG/Store/TaskMgr → execute
            │       └── HTTP scenarios → serial (none currently)
            │
            ├── 4. generate_report() → workspace/e2e-report.json
            │
            ├── 5. print_summary() → console output
            │
            └── 6. Exit code: 0 if all passed, 1 if any failed
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `run-e2e.sh` | Shell entry point. Creates temp workspace, sets environment, invokes Python, cleans up on exit. |
| `run-e2e.py` | Python orchestrator. Parses CLI args, generates project, instantiates scenarios, delegates to executor, generates report. |
| `generator/domain_templates.py` | Defines 8 `DomainTemplate` dataclasses with name, prefix, components, vision templates, and architecture templates. |
| `generator/project_generator.py` | `generate_project()` function: picks domain, fills templates, writes `.avt/` tree and seeded `knowledge-graph.jsonl`. Returns `GeneratedProject` dataclass. |
| `scenarios/base.py` | `BaseScenario` base class with `assert_true`, `assert_equal`, `assert_contains`, `assert_error`, `assert_no_error` helpers. `ScenarioResult` and `AssertionResult` dataclasses. |
| `scenarios/s*.py` | Individual test scenarios. Each inherits `BaseScenario`, overrides `run()`, uses assertion helpers. |
| `parallel/executor.py` | `ParallelExecutor`: routes library scenarios to `ThreadPoolExecutor`, HTTP scenarios to serial loop. Creates isolated `KnowledgeGraph`, `GovernanceStore`, `TaskFileManager` per scenario. Seeds each KG with 5 vision + 2 architecture standards. |
| `validation/assertion_engine.py` | Standalone assertion helper functions returning `(bool, str)` tuples for use in custom validation logic. |
| `validation/report_generator.py` | `ReportGenerator` class: writes JSON report to disk, prints ANSI-colored console summary with per-scenario pass/fail, totals, and failure details. |

## Writing New Scenarios

### Scenario Template

Create a new file in `scenarios/` following this pattern:

```python
"""S13 -- Description of what this scenario tests.

Detailed explanation of the scenario, what server behavior it validates,
and whether it covers positive cases, negative cases, or both.

Scenario type: positive | negative | mixed.
"""

import sys
from pathlib import Path
from typing import Any

# Path setup for MCP server library imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "knowledge-graph"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "governance"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "quality"))

# Import the server libraries you need
from collab_kg.graph import KnowledgeGraph
from collab_governance.store import GovernanceStore
from collab_governance.task_integration import TaskFileManager

from .base import BaseScenario, ScenarioResult


class S13MyNewScenario(BaseScenario):
    """One-line description of the scenario."""

    name = "s13-my-new-scenario"
    isolation_mode = "library"  # or "http" for transport testing

    def run(self, **kwargs: Any) -> ScenarioResult:
        # The executor injects these for library-mode scenarios:
        kg: KnowledgeGraph = kwargs["kg"]
        gov_store: GovernanceStore = kwargs["gov_store"]
        task_mgr: TaskFileManager = kwargs["task_mgr"]
        scenario_dir: Path = kwargs["scenario_dir"]

        # Access the generated project data:
        project = self.project  # GeneratedProject dataclass
        # project.domain_name, project.vision_standards, project.components, etc.

        # --- Positive test: something that should succeed ---
        result = kg.create_entities([{
            "name": "test-entity",
            "entityType": "component",
            "observations": ["test observation"],
        }])
        self.assert_no_error("create entity succeeds", result)

        # --- Negative test: something that should fail ---
        delete_result = kg.delete_entity("some-vision-entity")
        self.assert_error("delete vision entity rejected", delete_result)

        # --- Equality assertion ---
        self.assert_equal("entity count", len(result.get("entities", [])), 1)

        # --- Containment assertion ---
        self.assert_contains("has expected key", result, "entities")

        # Build and return the result
        return self._build_result(scenario_type="mixed")
```

### Available Assertion Helpers

All assertion helpers are defined on `BaseScenario`:

| Method | Parameters | What it checks |
|--------|-----------|---------------|
| `assert_true(name, condition, expected=True, actual=None)` | Boolean condition | `condition` is truthy |
| `assert_equal(name, actual, expected)` | Two values | `actual == expected` |
| `assert_contains(name, haystack, needle)` | Container + element | `needle in haystack` (works with str, list, dict, set) |
| `assert_error(name, result)` | Dict from server call | Result contains `"error"` key, `"success": False`, or `"status": "error"` |
| `assert_no_error(name, result)` | Dict from server call | Result does NOT contain error indicators |

All helpers return an `AssertionResult` and automatically append to the scenario's assertion list.

### Registering a New Scenario

After creating the scenario file, register it in `run-e2e.py`:

1. Add the import:
   ```python
   from e2e.scenarios.s13_my_new_scenario import S13MyNewScenario
   ```

2. Add to the registry list:
   ```python
   ALL_SCENARIO_CLASSES: list[type[BaseScenario]] = [
       # ... existing scenarios ...
       S13MyNewScenario,
   ]
   ```

The `ParallelExecutor` will automatically create isolated storage and execute it alongside the other scenarios.

## Adding New Domains

To add a new domain to the generation pool, edit `generator/domain_templates.py`:

```python
DomainTemplate(
    name="Your Domain Name",
    prefix="your_domain",  # snake_case, used in entity naming
    components=("ServiceA", "ServiceB", "ServiceC"),  # exactly 3
    vision_templates=(
        # Exactly 5 templates, one per archetype:
        # 1. Protocol-based DI
        "All {domain} services MUST use protocol-based dependency injection; ...",
        # 2. No singletons
        "No singletons in production {domain} code; ...",
        # 3. Integration tests
        "Every public API in {domain} MUST have integration tests ...",
        # 4. Authorization/security
        "Data access in {domain} MUST pass through authorization ...",
        # 5. Error handling (Result types)
        "{domain} error handling MUST use Result types; ...",
    ),
    architecture_templates=(
        # 2-3 templates:
        "{component} uses the ServiceRegistry pattern ...",
        "Inter-service communication in {domain} uses ...",
    ),
),
```

**Template placeholders:**
- `{domain}` — replaced with `DomainTemplate.name` (e.g., "Pet Adoption Platform")
- `{prefix}` — replaced with `DomainTemplate.prefix` (e.g., "pet_adoption")
- `{component}` — replaced with a randomly selected component from the 3 defined

The 5 vision template archetypes are fixed to ensure every domain produces structurally equivalent standards:
1. Protocol-based dependency injection requirement
2. No singletons in production
3. Integration test requirement for public APIs
4. Authorization/security requirement
5. Result-type error handling (no thrown exceptions)

## Report Format

### Console Output

The console output uses ANSI colors (automatically disabled when output is not a TTY):

```
======================================================================
  E2E: Pet Adoption Platform
  2026-02-04T12:34:56.789Z
======================================================================

  PASS  s01-kg-tier-protection                  13 passed, 0 failed       12.3ms  [mixed]
  PASS  s02-governance-decision-flow             19 passed, 0 failed       8.7ms  [mixed]
  PASS  s03-governed-task-lifecycle              26 passed, 0 failed      15.1ms  [mixed]
  ...

----------------------------------------------------------------------
  Scenarios:  11 passed, 0 failed, 11 total
  Assertions: 172 passed, 0 failed, 172 total
  Duration:   89.4ms
  Result:     ALL PASSED
======================================================================
```

If any scenario fails, a `FAILURE DETAILS` section follows with per-assertion expected vs actual values.

### JSON Report

Written to `{workspace}/e2e-report.json`:

```json
{
  "suite": "E2E: Pet Adoption Platform",
  "timestamp": "2026-02-04T12:34:56.789000+00:00",
  "summary": {
    "scenarios_total": 11,
    "scenarios_passed": 11,
    "scenarios_failed": 0,
    "assertions_passed": 172,
    "assertions_failed": 0,
    "assertions_total": 172,
    "total_duration_ms": 89.4,
    "success": true
  },
  "scenarios": [
    {
      "name": "s01-kg-tier-protection",
      "passed": 13,
      "failed": 0,
      "total": 13,
      "success": true,
      "duration_ms": 12.3,
      "scenario_type": "mixed",
      "error": null,
      "assertions": [
        {
          "name": "create vision entity succeeds",
          "passed": true,
          "expected": "no error",
          "actual": "status='ok'",
          "error": null
        }
      ]
    }
  ],
  "failures": []
}
```

## Debugging Failures

### Scenario-to-Source Mapping

When a scenario fails, the root cause is in the MCP server code, not the test. Use this mapping to trace failures:

| Scenario | Primary Source File(s) |
|----------|----------------------|
| s01 | `mcp-servers/knowledge-graph/collab_kg/graph.py`, `tier_protection.py` |
| s02 | `mcp-servers/governance/collab_governance/store.py` |
| s03 | `mcp-servers/governance/collab_governance/task_integration.py` |
| s04 | `mcp-servers/knowledge-graph/collab_kg/graph.py`, `tier_protection.py` |
| s05 | `mcp-servers/governance/collab_governance/store.py` |
| s06 | `mcp-servers/governance/collab_governance/store.py` (`.get_status()`) |
| s07 | `mcp-servers/quality/collab_quality/trust_engine.py` |
| s08 | `mcp-servers/governance/collab_governance/task_integration.py` |
| s09 | `mcp-servers/governance/collab_governance/store.py` |
| s10 | `mcp-servers/governance/collab_governance/task_integration.py`, `store.py` |
| s12 | All three server packages |

### Common Failure Patterns

**"Expected no error but got error"** — A server API that previously returned success now returns an error dict. Check whether the API signature or return format changed.

**"Expected error but result appears successful"** — A negative test expected a rejection (e.g., deleting a vision entity) but the operation succeeded. Check whether tier protection was accidentally relaxed.

**"Expected X, got Y" on a count assertion** — Aggregate counts from `get_status()` or similar methods are off. Check whether a new code path is creating/modifying records that affect the count.

**Scenario execution error (traceback)** — The scenario itself crashed, usually due to an import error (API changed) or a missing method. Read the traceback; it will point to the exact line.

### Debugging Workflow

1. Run with `--keep` and `--seed` to get a reproducible, inspectable run:
   ```bash
   ./e2e/run-e2e.sh --seed 42 --keep
   ```

2. Examine the workspace:
   ```bash
   # See the generated project
   ls /tmp/avt-e2e-XXXXXX/project/.avt/

   # Read the generated KG
   cat /tmp/avt-e2e-XXXXXX/project/.avt/knowledge-graph.jsonl

   # Check a specific scenario's isolated data
   ls /tmp/avt-e2e-XXXXXX/s03-governed-task-lifecycle/

   # Read the full JSON report
   cat /tmp/avt-e2e-XXXXXX/e2e-report.json | python3 -m json.tool
   ```

3. Run a specific scenario in isolation by temporarily editing the `ALL_SCENARIO_CLASSES` list in `run-e2e.py` to include only the failing scenario.

## Environment Variables

| Variable | Set By | Purpose |
|----------|--------|---------|
| `GOVERNANCE_MOCK_REVIEW` | `run-e2e.sh` (automatic) | When set to any truthy value, the governance reviewer returns a deterministic "approved" verdict instead of calling `claude --print`. |

## FAQ

**Q: What do the scenario numbers mean?**
A: s01-s10 are the original core scenarios. s11-s13 test hook-based governance (added during governance hook implementation). s14 is the full persistence lifecycle test (added during the persistence audit). All scenarios use library-mode (direct Python imports).

**Q: Can I run a single scenario?**
A: Edit the `ALL_SCENARIO_CLASSES` list in `run-e2e.py` to include only the scenario you want. There is no CLI flag for this yet.

**Q: Do I need running MCP servers?**
A: No. All scenarios import the server libraries directly as Python modules. No HTTP servers need to be running.

**Q: Why does the domain change every run?**
A: Domain randomization is a feature, not a bug. It ensures the system is tested against varied data. All assertions are structural and domain-agnostic, so they pass regardless of which domain is selected. Use `--seed` when you need reproducibility.

**Q: What Python version is required?**
A: Python 3.12 or higher. The `pyproject.toml` specifies `requires-python = ">=3.12"`.

**Q: How do I add a new MCP server to the test harness?**
A: (1) Add its package path to the `sys.path` setup in `run-e2e.py` and `parallel/executor.py`. (2) If scenarios need isolated instances, add instance creation to `ParallelExecutor._run_isolated()`. (3) Write scenarios that exercise the new server's Python API.
