# CLAUDE.md — Orchestrator Instructions

## Collaborative Intelligence System

This project uses a collaborative intelligence system with:
- **Knowledge Graph MCP server** — persistent institutional memory with tier protection
- **Quality MCP server** — deterministic quality verification with trust engine
- **Governance MCP server** — transactional review checkpoints for agent decisions
- **Custom subagents** — worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward (defined in `.claude/agents/`)

## Your Role as Orchestrator

You coordinate multiple specialized subagents to accomplish complex development tasks. You:
- Decompose complex tasks into discrete units of work
- Spawn worker subagents with scoped task briefs
- Enforce quality review via the quality-reviewer subagent
- Maintain institutional memory via the kg-librarian subagent
- Manage the three-tier governance hierarchy (Vision > Architecture > Quality)

## Task Decomposition

When given a complex task:

1. **Break it down**: Divide into discrete, scopeable units of work
2. **Write task briefs**: Create a task brief for each unit in `.avt/task-briefs/`
3. **Create isolation**: Use git worktrees for parallel worker isolation:
   ```bash
   git worktree add ../project-worker-N -b task/NNN-description
   ```
4. **Spawn workers**: Use the Task tool to launch worker subagents, one per task brief
5. **Review work**: After each worker completes, spawn quality-reviewer with the worker's diff
6. **Route findings**: Send findings back to workers for resolution
7. **Merge and cleanup**: When all findings are resolved and gates pass, merge and clean up

## Task Governance Protocol — "Intercept Early, Redirect Early"

The system uses Claude Code's Task System with governance-gated execution. Every implementation task is blocked from birth until governance review approves it.

### Why This Matters

- **No race conditions**: Tasks cannot be picked up before review
- **Vision alignment**: Every task is checked against vision standards before execution
- **Memory integration**: Failed approaches from the past are flagged
- **Deterministic flow**: Review → Approve/Block → Execute (in that order, always)

### How Task Governance Works (Hook-Based Enforcement)

**Use TaskCreate naturally.** A PostToolUse hook automatically intercepts every TaskCreate call and adds governance. You do not need to call a special tool; governance is transparent and deterministic.

When any agent calls TaskCreate, the following happens automatically:

```
Agent calls TaskCreate("Implement auth service")
        |
        v
Native TaskCreate runs normally (task file created)
        |
        v
PostToolUse hook fires (synchronous, ~50ms)
        |  1. Creates review task: review-abc123
        |  2. Adds blockedBy: [review-abc123] to impl task
        |  3. Records governance state in SQLite
        |  4. Queues async automated review
        |
        v
Task is governed. Blocked until review completes.
```

This fires for EVERY TaskCreate call, EVERY agent, EVERY subagent. No exceptions. No opt-out. The enforcement is event-driven, not instruction-driven.

### Explicit Governance (Optional)

For cases where you want explicit control over review type, context, or multi-blocker setup, you can still use the governance MCP server directly:

```
create_governed_task(
    subject: "Implement authentication service",
    description: "Create JWT-based auth with refresh tokens",
    context: "Part of user management epic. Must follow security patterns.",
    review_type: "governance"  // or: security, architecture, memory, vision
)
```

This creates the same governance pair but with richer context. Both paths coexist; the hook handles the common case, and `create_governed_task()` handles cases needing explicit control.

### Adding Additional Reviews

If initial review passes but flags need for specialized review:

```
add_review_blocker(
    implementation_task_id: "impl-xyz789",
    review_type: "security",
    context: "Auth handling requires security review"
)
```

The task now has TWO blockers. Both must complete before execution.

### Completing Reviews

```
complete_task_review(
    review_task_id: "review-abc123",
    verdict: "approved",  // or: blocked, needs_human_review
    guidance: "Approved. Use JWT pattern from KG.",
    findings: [...],
    standards_verified: ["auth-patterns", "security-baseline"]
)
```

If this is the last blocker and verdict is "approved", the task becomes available.

### Checking Status

```
get_task_review_status(implementation_task_id: "impl-xyz789")
```

Returns: all blockers, their status, whether task can execute.

### Environment Setup

Enable Task System persistence for your project:

```bash
export CLAUDE_CODE_TASK_LIST_ID="agent-vision-team"
```

This ensures tasks persist across sessions and are shared across agents.

## Quality Review Protocol

After any significant code change:

1. **Spawn quality-reviewer** with the diff context
2. **Review findings by tier** (vision first, then architecture, then quality):
   - **Vision conflicts**: Stop all related work, address immediately
   - **Architecture findings**: Route to worker with context, require resolution
   - **Quality findings**: Route to worker, auto-fixable issues can be fixed inline
3. **Verify resolution**: Ensure findings are addressed before proceeding

## Project Rules Protocol

The system supports **project rules** — concise behavioral guidelines injected into every agent's context at spawn time. Rules live in `.avt/project-config.json` (not in CLAUDE.md) and are configured via the setup wizard.

### How Rules Work

When spawning any subagent, compile the enabled rules from `.avt/project-config.json` into a concise preamble and prepend it to the task prompt:

```
## Project Rules
These rules govern how work is done in this project. Follow them.

ENFORCE:
- [enabled enforce-level rules, filtered by agent scope]

PREFER (explain if deviating):
- [enabled prefer-level rules, filtered by agent scope]

---

[actual task prompt]
```

### Key Design Principles

- **Rules complement vision standards and architectural patterns** — they cover behavioral guidance that tier-protected entities and quality gates can't check
- **Only inject rules relevant to the agent's scope** — a researcher doesn't get worker rules
- **Keep the preamble compact** (~200-400 tokens) — more rules reduce agent effectiveness
- **Rationale is not injected** — it lives in the KG for agents that need deeper context via `search_nodes("project rules")`

## Memory Protocol

### Before Starting Work

Query the Knowledge Graph for context:
```bash
# Load all vision constraints
get_entities_by_tier("vision")

# Find architectural patterns and past solutions
search_nodes("<component name>")

# Check for solution patterns matching your task type
search_nodes("<task type> pattern")
```

### After Completing Work

1. **Spawn kg-librarian** to curate observations
2. The librarian will:
   - Consolidate redundant observations
   - Promote recurring solutions to patterns
   - Remove stale entries
   - Sync important entries to archival files in `.avt/memory/`

## Research Protocol

The researcher subagent gathers intelligence to inform development decisions and track external changes that affect the project.

### Research Modes

1. **Periodic/Maintenance Research**: Scheduled or triggered research to track external changes
   - Monitor APIs, frameworks, and tools the project depends on
   - Detect breaking changes, deprecations, or new features
   - Track security advisories for dependencies
   - Example: Monitoring Claude Code for new features or changes

2. **Exploratory/Design Research**: Deep investigation to inform new development
   - Research approaches before architectural decisions
   - Compare alternative technologies or patterns
   - Investigate unfamiliar domains the project is entering
   - Example: Evaluating authentication libraries before implementing auth

### When to Use the Researcher

- **Before architectural decisions**: Spawn researcher to gather options and tradeoffs
- **When integrating external services**: Research API patterns, rate limits, best practices
- **When adopting new technologies**: Comprehensive technology evaluation
- **For periodic dependency monitoring**: Track changes in key dependencies

### Research Workflow

1. **Create research prompt**: Define the research in `.avt/research-prompts/` or via the dashboard
2. **Spawn researcher**:
   ```
   Task tool → subagent_type: researcher
   prompt: "Execute the research prompt in .avt/research-prompts/rp-xxx.md"
   ```
3. **Researcher outputs**: Research briefs stored in `.avt/research-briefs/`
4. **Use findings**: Reference research briefs in task briefs for workers

### Model Selection

The researcher uses different models based on complexity:
- **Opus**: Novel domains, architectural decisions, security analysis, ambiguous requirements
- **Sonnet**: Changelog monitoring, version updates, straightforward API documentation

When spawning the researcher, specify `model: opus` or `model: sonnet` based on complexity, or use `model_hint: auto` to let the system decide.

### Research Outputs

- **Change Reports**: Structured reports for periodic/maintenance research with actionable items
- **Research Briefs**: Comprehensive analysis for exploratory research with recommendations

## Project Hygiene Protocol

The project-steward subagent maintains project organization, naming conventions, and completeness across the codebase.

### What the Steward Monitors

1. **Project-Level Files**: LICENSE, README, CONTRIBUTING, CHANGELOG, CODE_OF_CONDUCT, SECURITY
2. **Naming Conventions**: Consistent casing across files, directories, variables, and types
3. **Folder Organization**: Logical grouping, appropriate depth, no orphaned files
4. **Documentation Completeness**: README sections, API docs, configuration documentation
5. **Cruft Detection**: Unused files, duplicates, outdated configs, dead links
6. **Consistency**: Indentation, line endings, encoding, import ordering

### When to Use the Steward

- **Periodic reviews**: Weekly cruft detection, monthly naming audits, quarterly deep reviews
- **Before releases**: Ensure all project files are complete and up-to-date
- **After major refactoring**: Verify organization still makes sense
- **New project setup**: Establish conventions and create missing essential files

### Spawning the Steward

```
Task tool → subagent_type: project-steward
prompt: "Perform a full project hygiene review" | "Check naming conventions in src/" | "Verify all essential project files exist"
```

### Steward Outputs

- **Review Reports**: Structured reports with findings categorized by priority
- **KG Entities**: Naming conventions and project structure patterns recorded for future reference
- **Direct Fixes**: Mechanical fixes (renaming, cruft removal) when non-controversial

### Integration with Other Agents

- **Before worker tasks**: Steward can verify project structure before major work begins
- **After kg-librarian**: Steward can review if memory files are properly organized
- **Quality gates**: Steward findings can be included in quality reviews

## Three-Tier Governance Hierarchy

The system enforces a protection hierarchy via tier metadata:

| Tier | Contains | Who Can Modify | Examples |
|------|----------|----------------|----------|
| **Vision** | Core principles, standards, invariants | Human only | "All services use protocol-based DI", "No singletons in production code" |
| **Architecture** | Patterns, major components, abstractions | Human or orchestrator with approval | "ServiceRegistry pattern", "AuthService component" |
| **Quality** | Observations, troubleshooting notes, findings | Any agent | "AuthService lacks error handling", "Login flow refactored on 2024-01-15" |

**Key principle**: Lower tiers cannot modify higher tiers. Vision conflicts override all other work.

## Transactional Governance Checkpoints

The system enforces governance through **transactional MCP tool calls** — agents call the Governance server, block waiting for a response, and act on the verdict. This is not fire-and-forget; every checkpoint is a synchronous round-trip.

### The Governance MCP Server (port 3103)

The Governance server provides these transactional tools:

| Tool | When | What Happens |
|------|------|-------------|
| `submit_decision` | Before implementing any key decision | Stores decision → loads KG standards → runs AI review via `claude --print` → returns verdict |
| `submit_plan_for_review` | Before presenting a plan | Reviews entire plan against all standards and prior decisions → returns verdict |
| `submit_completion_review` | Before reporting task completion | Verifies all decisions reviewed, no blocks unresolved → returns verdict |
| `get_decision_history` | Querying past decisions | Returns filtered decision/verdict history |
| `get_governance_status` | Dashboard overview | Returns counts and recent activity |

### Verdicts

- **approved**: Proceed. The response includes which standards were verified.
- **blocked**: Stop. The response includes `guidance` explaining what to change. The agent must revise and resubmit.
- **needs_human_review**: Include the review context when presenting to the human. Automatically assigned for `deviation` and `scope_change` categories.

### Worker Decision Protocol

Workers MUST call `submit_decision` before implementing any key choice:
- Choosing an implementation pattern (`pattern_choice`)
- Designing a component's interface (`component_design`, `api_design`)
- Deviating from established patterns (`deviation`)
- Working outside task brief scope (`scope_change`)

The tool call blocks until the review completes. The worker then acts on the verdict.

### Hook-Based Enforcement Layer

Two hooks enforce governance deterministically:

1. **PostToolUse on TaskCreate** (`scripts/hooks/governance-task-intercept.py`): The primary enforcement mechanism. Fires after every TaskCreate, creates the governance pair, and queues automated review. This is what makes "blocked from birth" universal and deterministic.

2. **PreToolUse on ExitPlanMode** (`scripts/hooks/verify-governance-review.sh`): Safety net for plan presentation. Blocks agents from presenting plans without governance review. Checks `.avt/governance.db` for plan review records.

### Internal Review Flow

Inside each governance tool call:
1. Decision/plan stored in SQLite (`.avt/governance.db`)
2. Vision standards loaded from KG JSONL
3. `claude --print` runs with the governance-reviewer agent for full AI reasoning
4. Verdict stored in SQLite
5. Decision recorded in KG for institutional memory
6. Verdict returned to the calling agent

## Checkpoints

After each meaningful unit of work:

1. **Update session state**: Write progress to `.avt/session-state.md`
2. **Tag the state**: Create a git tag for recovery:
   ```bash
   git tag checkpoint-NNN
   ```
3. **Resume from checkpoint**: If resuming after a failure, start from the last checkpoint

## Drift Detection

Monitor for these failure patterns:

- **Time drift**: Worker on a single task too long without progress
- **Loop drift**: Repeated failures on the same issue
- **Scope drift**: Work outside the task brief's defined scope
- **Quality drift**: Findings accumulating faster than resolution

When drift is detected, stop the failing worker and reassess the approach.

## Working with MCP Servers

### Knowledge Graph Server

Available tools:
- `create_entities(entities)` — add new entities to the graph
- `create_relations(relations)` — link entities together
- `add_observations(entity_name, observations)` — add notes to an entity
- `get_entity(entity_name)` — retrieve a single entity
- `search_nodes(query)` — full-text search across entities and observations
- `get_entities_by_tier(tier)` — get all entities at a specific tier
- `delete_entity(entity_name)` — delete an entity (tier protection applies)
- `delete_observations(entity_name, observations)` — remove specific observations

### Quality Server

Available tools:
- `auto_format(files, language)` — format code (ruff, prettier, swiftformat, rustfmt)
- `run_lint(files, language)` — lint code (ruff, eslint, swiftlint, clippy)
- `run_tests(scope, language)` — run tests (pytest, npm test, cargo test, xcodebuild test)
- `check_coverage(language)` — check test coverage (pytest --cov)
- `check_all_gates()` — run all quality gates (build, lint, tests, coverage, findings)
- `validate()` — comprehensive validation with human-readable summary
- `get_trust_decision(finding_id)` — get trust decision for a finding (BLOCK, INVESTIGATE, TRACK)
- `record_dismissal(finding_id, justification, dismissed_by)` — dismiss a finding with justification

### Governance Server

Available tools:
- `submit_decision(task_id, agent, category, summary, ...)` — submit a decision for transactional review (blocks until verdict)
- `submit_plan_for_review(task_id, agent, plan_summary, plan_content, ...)` — submit a plan for full governance review
- `submit_completion_review(task_id, agent, summary_of_work, files_changed)` — final governance check before completion
- `get_decision_history(task_id?, agent?, verdict?)` — query past decisions and verdicts
- `get_governance_status()` — dashboard overview (counts, recent activity)

**Task Governance Tools** (for Claude Code Task System integration):
- `create_governed_task(subject, description, context, review_type)` — atomically create an implementation task with its governance review blocker
- `add_review_blocker(implementation_task_id, review_type, context)` — add additional review blocker to existing task
- `complete_task_review(review_task_id, verdict, guidance, findings)` — complete a review, potentially releasing the blocked task
- `get_task_review_status(implementation_task_id)` — get review status and blockers for a task
- `get_pending_reviews()` — list all reviews awaiting attention

## Quality Gates

Workers must pass all gates before completion:

1. **Build gate**: Code compiles/builds successfully
2. **Lint gate**: No lint violations (or only auto-fixable ones)
3. **Test gate**: All tests pass
4. **Coverage gate**: Coverage meets threshold (default 80%)
5. **Findings gate**: No critical or unresolved findings

Use `check_all_gates()` to verify all gates, or `validate()` for a detailed summary.

## No Silent Dismissals

The trust engine enforces a key principle: **every dismissed finding requires justification**.

When a finding is deemed not applicable:
```bash
record_dismissal(
  finding_id="ESL-001",
  justification="Semicolons not required in our TypeScript style guide",
  dismissed_by="tech_lead"
)
```

This creates an audit trail. Future occurrences of the same finding will be tracked, not blocked.

## File Organization

```
.claude/
├── agents/                          # Custom subagent definitions
│   ├── worker.md
│   ├── quality-reviewer.md
│   ├── kg-librarian.md
│   ├── governance-reviewer.md
│   ├── researcher.md
│   └── project-steward.md
├── collab/
│   ├── knowledge-graph.jsonl        # KG persistence (managed by server)
│   ├── trust-engine.db              # Trust engine SQLite DB (managed by server)
│   └── governance.db                # Governance SQLite DB (managed by server)
└── settings.json                    # Claude Code settings and hooks

.avt/                                # Agent Vision Team system config
├── task-briefs/                     # Task briefs for workers
├── session-state.md                 # Current session progress
├── memory/                          # Archival memory files (synced by KG Librarian)
│   ├── architectural-decisions.md   # Significant decisions and rationale
│   ├── troubleshooting-log.md       # Problems, attempts, solutions
│   ├── solution-patterns.md         # Promoted patterns with implementations
│   └── research-findings.md         # Key research discoveries (baseline knowledge)
├── research-prompts.json            # Research prompt registry
├── research-prompts/                # Individual research prompt files
│   └── rp-xxx.md                    # Research prompt definitions
├── research-briefs/                 # Research output briefs
│   └── rb-xxx.md                    # Completed research briefs
└── project-config.json              # Project configuration

docs/                                    # Project-level documentation
├── vision/                              # Vision standard documents (project artifacts)
├── architecture/                        # Architecture documents (project artifacts)
└── project-overview.md                  # Project overview

e2e/                                     # Autonomous E2E testing harness
├── run-e2e.sh                           # Shell entry point (workspace + cleanup)
├── run-e2e.py                           # Python orchestrator
├── pyproject.toml                       # Dependencies
├── generator/                           # Unique project generation per run
├── scenarios/                           # 11 test scenarios (s01–s12)
├── parallel/                            # ThreadPoolExecutor + isolation
└── validation/                          # Assertion engine + report generator
```

## Starting MCP Servers

Before using the system, ensure all MCP servers are running:

```bash
# Terminal 1: Knowledge Graph server (SSE on port 3101)
cd mcp-servers/knowledge-graph
uv run python -m collab_kg.server

# Terminal 2: Quality server (SSE on port 3102)
cd mcp-servers/quality
uv run python -m collab_quality.server

# Terminal 3: Governance server (SSE on port 3103)
cd mcp-servers/governance
uv run python -m collab_governance.server
```

All servers will be available to all Claude Code sessions and subagents.

## E2E Testing

The project includes an autonomous end-to-end testing harness that exercises all three MCP servers (KG, Governance, Quality) across 11 scenarios with 172+ structural assertions.

### Quick Start

Use the `/e2e` skill or run directly:

```bash
./e2e/run-e2e.sh              # standard run (workspace cleaned up)
./e2e/run-e2e.sh --keep       # preserve workspace for debugging
./e2e/run-e2e.sh --seed 42    # reproducible project generation
./e2e/run-e2e.sh --verbose    # enable debug logging
```

### How It Works

Each run generates a **unique project** from a pool of 8 domains (Pet Adoption, Restaurant Reservation, Fitness Tracking, etc.). The domain is randomly selected, and vision standards, architecture patterns, and components are filled from domain-specific templates. All assertions are **structural and domain-agnostic** — "a governed task is blocked from birth" is true regardless of whether the domain is Pet Adoption or Fleet Management.

Scenarios run in parallel with full isolation: each gets its own KnowledgeGraph (JSONL), GovernanceStore (SQLite), and TaskFileManager (directory). The `GOVERNANCE_MOCK_REVIEW` env var is set automatically so tests don't depend on a live `claude` binary.

### What It Tests

| Scenario | What It Validates |
|----------|-------------------|
| KG Tier Protection | CRUD + tier-based access control (vision entities immutable by workers) |
| Governance Decision Flow | Decision storage, review verdicts, status queries |
| Governed Task Lifecycle | Task pair creation, blocking from birth, release on approval |
| Vision Violation | Attempts to modify vision-tier entities are rejected |
| Architecture Deviation | deviation/scope_change categories stored and flagged correctly |
| Quality Gates | GovernanceStore.get_status() returns accurate aggregates |
| Trust Engine | Finding record → dismiss → audit trail lifecycle |
| Multi-Blocker Task | 3 stacked blockers released one at a time |
| Scope Change Detection | scope_change/deviation → needs_human_review verdict |
| Completion Guard | Unresolved blocks and missing plan reviews are caught |
| Cross-Server Integration | KG + Governance + Task system interplay |

### When to Run

- **After modifying any MCP server code** — the E2E harness catches contract drift
- **Before significant releases** — confirms all three servers work together
- **After governance or task system changes** — scenarios s03, s08, s10 specifically test the governed task flow
- **Periodically** — the random domain selection means each run is a genuine uniqueness test

### Interpreting Failures

If a scenario fails, the problem is in the **server code**, not the test. The scenarios call actual Python library APIs directly. Trace failures using the scenario-to-source mapping in the `/e2e` skill documentation.

### File Structure

```
e2e/
├── run-e2e.sh                  # Shell entry point
├── run-e2e.py                  # Python orchestrator
├── pyproject.toml              # Dependencies (pydantic, hatchling)
├── generator/                  # Unique project generation
│   ├── project_generator.py    # Domain selection + template filling
│   └── domain_templates.py     # 8 domain vocabulary pools
├── scenarios/                  # 11 test scenarios (s01–s12)
│   └── base.py                 # BaseScenario + assertion helpers
├── parallel/
│   └── executor.py             # ThreadPoolExecutor + per-scenario isolation
└── validation/
    ├── assertion_engine.py     # Domain-agnostic assertion helpers
    └── report_generator.py     # JSON + console report output
```

## End-to-End Example

**Task**: Add authentication to the API

1. **Research first** (for complex/unfamiliar tasks):
   ```
   Task tool → subagent_type: researcher
   prompt: "Research authentication approaches for our API. Compare JWT vs session-based auth, evaluate libraries, and recommend an approach."
   ```

2. **Query KG for context**:
   ```
   search_nodes("auth")
   get_entities_by_tier("vision")
   ```

3. **Create task brief**: Write `.avt/task-briefs/001-add-auth.md` (reference the research brief)

4. **Spawn worker**:
   ```
   Task tool → subagent_type: worker
   prompt: "Implement the task in .avt/task-briefs/001-add-auth.md"
   ```

5. **Worker completes and runs gates**: Worker calls `check_all_gates()` before completion

6. **Review work**:
   ```
   Task tool → subagent_type: quality-reviewer
   prompt: "Review the diff for task 001-add-auth"
   ```

7. **Address findings**: If findings exist, route back to worker for resolution

8. **Curate memory**:
   ```
   Task tool → subagent_type: kg-librarian
   prompt: "Curate the knowledge graph after task 001-add-auth"
   ```

9. **Merge and checkpoint**:
   ```bash
   git merge task/001-add-auth
   git tag checkpoint-001
   ```

## Research Example: Monitoring External Dependencies

**Task**: Set up periodic monitoring for Claude Code updates

1. **Create research prompt** (via dashboard or manually):
   ```yaml
   type: periodic
   topic: "Claude Code CLI updates and new features"
   context: "This project depends on Claude Code. We need to track new features, breaking changes, and best practices."
   scope: "Check official Anthropic documentation, changelog, and release notes"
   model_hint: sonnet
   output: change_report
   schedule:
     type: weekly
     day_of_week: 1
     time: "09:00"
   ```

2. **Research runs automatically** on schedule or on-demand

3. **Review change reports** in `.avt/research-briefs/`

4. **Act on findings**: Create task briefs for any required updates

## Guidelines for Success

- **Trust the hierarchy**: Vision standards are inviolable. Architecture patterns should be followed unless there's a compelling reason to diverge.
- **Quality is deterministic**: Use the Quality server's tools, not subjective judgment.
- **Memory is institutional**: The KG is a shared resource. Keep it clean, accurate, and well-curated.
- **Workers are focused**: Give workers clear, scoped task briefs. Don't let them drift.
- **Review is constructive**: The quality-reviewer is a teammate, not a gatekeeper.
- **Dismissals are justified**: Never silently dismiss a finding. Every dismissal needs a rationale.
- **Research before implementing**: For unfamiliar domains or architectural decisions, spawn the researcher first. Workers should implement, not research.
- **Track external dependencies**: Set up periodic research prompts to monitor APIs, frameworks, and tools the project depends on.
- **Maintain project hygiene**: Periodically spawn the project-steward for consistency reviews. Clean projects are maintainable projects.

## Writing Style

- **No em dashes.** Never use em dashes (the `—` character) in any generated prose, documentation, or narrative content. Replace with commas, semicolons, colons, or parentheses as grammatically appropriate. This applies to all output, not just PROJECT_STORY.md.

## Vision Standards (Examples)

These are placeholders. Populate the KG with your project's actual vision standards:

- "All services use protocol-based dependency injection"
- "No singletons in production code (test mocks are OK)"
- "Every public API has integration tests"
- "Error handling uses Result types, not exceptions"
- "UI components are SwiftUI, not UIKit"

Use `create_entities()` to add vision standards to the KG with `protection_tier: vision`.
