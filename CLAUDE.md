# CLAUDE.md — Orchestrator Instructions

## Collaborative Intelligence System

This project uses a collaborative intelligence system with:
- **Knowledge Graph MCP server** — persistent institutional memory with tier protection
- **Quality MCP server** — deterministic quality verification with trust engine
- **Governance MCP server** — transactional review checkpoints for agent decisions
- **Custom subagents** — architect, worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward, project-bootstrapper (defined in `.claude/agents/`)

## Your Role as Orchestrator

You coordinate multiple specialized subagents to accomplish complex development tasks. You:
- Decompose complex tasks into discrete units of work
- Spawn worker subagents with scoped task briefs
- Ensure quality review via the quality-reviewer subagent
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

The system uses Claude Code's Task System with governance-verified execution. Every implementation task is governed from creation: paired with a rapid automated review that verifies vision alignment before work begins. This reliable verification is what enables safe multi-agent parallelism -- you can confidently scale to more workers knowing that every task passes through the same checks.

### Why This Matters

- **No race conditions**: Tasks are verified before work begins
- **Vision alignment**: Every task is checked against vision standards before execution
- **Memory integration**: Failed approaches from the past are flagged
- **Deterministic flow**: Review → Approve/Redirect → Execute (in that order, always)
- **Safe scaling**: Reliable verification means more parallel agents without risk

### How Task Governance Works (Hook-Based Verification)

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
Task is governed. Work begins once review completes.
```

This fires for EVERY TaskCreate call, EVERY agent, EVERY subagent. No exceptions. No opt-out. The verification is event-driven, not instruction-driven.

### Holistic Governance Review

Individual task governance catches vision violations one task at a time. But some violations only become visible when tasks are considered collectively. A task to "Add a models.py file" passes review individually, but together with "Add a migration runner," "Add a schema definition module," and "Add an ORM query builder," they collectively introduce an unauthorized ORM layer.

The holistic review system detects this by evaluating all tasks from a session as a group before any work begins.

**How it works:**

```
Agent creates Task 1 → PostToolUse fires:
  - Records task with session_id in governance DB
  - Creates flag file: .avt/.holistic-review-pending
  - Spawns background settle checker (waits 3s)

Agent creates Task 2 → PostToolUse fires:
  - Records task, updates flag, spawns new settle checker
  - Previous checker detects newer task and exits

Agent creates Task 3 → PostToolUse fires:
  - Same as above

Background: Settle checker for Task 3 wakes up after 3s:
  - Checks DB: any tasks newer than me? NO → I'm the last task
  - Runs holistic review (GovernanceReviewer.review_task_group())
  - If APPROVED: clears flag file, queues individual reviews
  - If issues found: writes guidance to flag file for revision

Meanwhile: Agent tries to Write/Edit/Bash/Task:
  → PreToolUse checkpoint fires (~1ms)
  → Flag file exists? YES → exit 2 (redirect with feedback)
  → Agent sees "Holistic review in progress, please wait"
```

**Key properties:**
- **Detection is timing-based** (settle/debounce), not reliant on agent behavior
- **Verification is deterministic** (PreToolUse coordinates work sequencing at the platform level)
- **Works for all agent behaviors**: direct work, subagent spawning, or mixed
- **Fast path is ~1ms** when no review is pending (flag file existence check)
- **Single tasks skip holistic review** (MIN_TASKS_FOR_REVIEW = 2)
- **Subagent tasks are handled**: if a subagent creates tasks after the session was already approved, the settle checker cleans up the re-created flag

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
   - **Vision conflicts**: Pause the conflicting work and address the specific conflict. Check the review's `strengths_summary` and `salvage_guidance` to identify what work is sound and can be preserved. The worker should fix only the conflicting aspect, not discard all progress.
   - **Architecture findings**: Route to worker with the full constructive context (strengths, salvage guidance, suggestion). The worker revises the specific deviation while preserving aligned work.
   - **Quality findings**: Route to worker, auto-fixable issues can be fixed inline
3. **Verify resolution**: Ensure findings are addressed before proceeding

## Bootstrap Protocol

The project-bootstrapper subagent onboards an existing, mature codebase into the AVT system by discovering governance artifacts that already exist implicitly in the code and documentation.

### When to Use the Bootstrapper

- **Onboarding an existing project**: The project has code and documentation but no AVT governance artifacts (no KG entities, no vision standards, no architecture docs)
- **Inherited codebase**: Someone is taking over a project and needs to understand its architecture, patterns, and conventions
- **Incremental discovery**: Some governance artifacts exist but there are gaps (e.g., vision standards defined but no architecture docs)

### How to Invoke

```
Task tool -> subagent_type: project-bootstrapper
prompt: "Bootstrap the project at /path/to/codebase"
```

The bootstrapper automatically:
1. Runs a cheap scale assessment (file counts, LOC, package boundaries) in under 5 seconds
2. Classifies the project into a scale tier (Small through Enterprise)
3. Builds a partition map using natural code boundaries
4. Spawns discovery sub-agents in waves (bounded parallelism, up to 15 concurrent)
5. Synthesizes findings into draft artifacts for human review

### What It Produces

| Artifact | Location | Purpose |
|----------|----------|---------|
| **Bootstrap report** | `.avt/bootstrap-report.md` | Primary human review artifact with APPROVE/REJECT/REVISE actions |
| **Vision standard drafts** | `docs/vision/*.md` | One doc per discovered vision standard |
| **Architecture docs** | `docs/architecture/` | Multi-level with Mermaid diagrams: overview, components, patterns, flows |
| **Style guide** | `docs/style/style-guide.md` | Discovered coding conventions |
| **Draft rules** | `.avt/bootstrap-rules-draft.json` | Discovered project rules |

### Human Review Workflow

1. **Read the bootstrap report** (`.avt/bootstrap-report.md`). It contains all discoveries organized by category with confidence levels and source citations.
2. **Review each artifact**: Mark as APPROVE, REJECT, or REVISE. Pay special attention to vision standards since they become immutable once ingested.
3. **After approval**, the bootstrapper (or orchestrator) runs:
   - `ingest_documents("docs/vision/", "vision")` for approved vision standards
   - `ingest_documents("docs/architecture/", "architecture")` for approved architecture docs
   - Merges approved rules from `.avt/bootstrap-rules-draft.json` into `.avt/project-config.json`
4. **Rejected items**: Delete the corresponding draft files
5. **Revised items**: Edit the draft files per feedback, then re-run ingestion

### Scale Handling

The bootstrapper adapts to any codebase size using wave-based bounded parallelism:

| Tier | Source LOC | Estimated Time | Agent Invocations |
|------|-----------|---------------|-------------------|
| Small | < 10K | ~5 min | Inline (no sub-agents) |
| Medium | 10K-100K | ~10 min | ~19 |
| Large | 100K-500K | ~15 min | ~66 |
| Massive | 500K-2M | ~35 min | ~230 |
| Enterprise | 2M+ | ~41 min | ~300 |

### Integration with Other Agents

After bootstrap completes and artifacts are approved:
- **Workers** can now query KG for vision standards and architecture patterns
- **Quality reviewer** can check work against discovered standards
- **Governance reviewer** has vision standards to verify against
- **Architect** has existing patterns to build on
- **KG librarian** can curate the bootstrapped entities

## Architect Protocol

The architect subagent designs architecture with explicit intent and expected outcomes for every decision.

### When to Spawn the Architect

- **Project bootstrap**: When setting up a new project's architecture from vision standards
- **Major feature design**: When a feature requires multiple new architectural decisions
- **Cross-cutting concerns**: When a change affects multiple components or layers
- **Vision alignment questions**: When it's unclear how to serve a vision standard architecturally

### Architect vs Worker

| Concern | Architect | Worker |
|---------|-----------|--------|
| Designs architecture | Yes | No |
| Writes implementation code | No | Yes |
| Submits decisions with intent/outcome | Yes (required) | Yes (required) |
| Produces task briefs for workers | Yes | No |
| Implements task briefs | No | Yes |
| Runs quality gates | No | Yes |

### Intent and Outcome Protocol

Every architectural decision (whether from architect or worker) must include when calling `submit_decision`:

- **intent**: WHY this decision is being made. What problem does it solve?
- **expected_outcome**: WHAT measurable result is expected. Tied to vision where applicable.
- **vision_references**: WHICH vision standard names this outcome serves.

The governance reviewer evaluates intent/outcome quality as part of every decision review. Missing or vague intent/outcome is flagged as a quality finding.

This protocol forces deliberate thinking: articulating an expected outcome before choosing an approach changes how options are evaluated and produces architecture traceable back to vision standards.

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
- **Opus 4.6**: Novel domains, architectural decisions, security analysis, ambiguous requirements
- **Sonnet 4.5**: Changelog monitoring, version updates, straightforward API documentation

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

The system maintains a protection hierarchy via tier metadata:

| Tier | Contains | Who Can Modify | Examples |
|------|----------|----------------|----------|
| **Vision** | Core principles, standards, invariants | Human only | "All services use protocol-based DI", "No singletons in production code" |
| **Architecture** | Patterns, major components, abstractions | Human or orchestrator with approval | "ServiceRegistry pattern", "AuthService component" |
| **Quality** | Observations, troubleshooting notes, findings | Any agent | "AuthService lacks error handling", "Login flow refactored on 2024-01-15" |

**Key principle**: Lower tiers cannot modify higher tiers. Vision conflicts override all other work.

## Transactional Governance Checkpoints

The system provides governance through **transactional MCP tool calls** -- agents call the Governance server, receive a synchronous response, and act on the verdict. This is not fire-and-forget; every checkpoint is a round-trip that returns quickly.

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
- **blocked**: Revise. The response includes `guidance` explaining what to change. The agent revises and resubmits.
- **needs_human_review**: Include the review context when presenting to the human. Automatically assigned for `deviation` and `scope_change` categories.

### Worker Decision Protocol

Workers MUST call `submit_decision` before implementing any key choice:
- Choosing an implementation pattern (`pattern_choice`)
- Designing a component's interface (`component_design`, `api_design`)
- Deviating from established patterns (`deviation`)
- Working outside task brief scope (`scope_change`)

The tool call blocks until the review completes. The worker then acts on the verdict.

### Hook-Based Verification Layer

Three hooks provide deterministic governance verification:

1. **PostToolUse on TaskCreate** (`scripts/hooks/governance-task-intercept.py`): The primary verification mechanism. Fires after every TaskCreate, pairs it with a governance review, tracks session_id, creates the holistic review flag file, and spawns the settle checker for collective review. 100% interception rate, universal and deterministic.

2. **PreToolUse on ExitPlanMode** (`scripts/hooks/verify-governance-review.sh`): Ensures plans are verified before presentation. Redirects agents to submit a plan review if none exists. Checks `.avt/governance.db` for plan review records.

3. **PreToolUse on Write|Edit|Bash|Task** (`scripts/hooks/holistic-review-gate.sh`): Coordinates work sequencing while holistic review completes. Uses a flag file (`.avt/.holistic-review-pending`) as a fast-path checkpoint (~1ms when no review is pending). Stale flags older than 5 minutes are auto-cleared.

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
- `submit_decision(task_id, agent, category, summary, intent, expected_outcome, vision_references, ...)` — submit a decision for transactional review (blocks until verdict)
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
│   ├── project-steward.md
│   └── project-bootstrapper.md
├── collab/
│   ├── knowledge-graph.jsonl        # KG persistence (managed by server)
│   ├── trust-engine.db              # Trust engine SQLite DB (managed by server)
│   └── governance.db                # Governance SQLite DB (managed by server)
└── settings.json                    # Claude Code settings and hooks

.avt/                                # Agent Vision Team system config
├── task-briefs/                     # Task briefs for workers
├── session-state.md                 # Current session progress
├── bootstrap-report.md              # Bootstrap discovery report (generated by bootstrapper)
├── bootstrap-rules-draft.json       # Draft project rules from bootstrap (pending approval)
├── .holistic-review-pending         # Flag file: gates mutation tools during holistic review
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
│   ├── overview.md                      # System-level architecture overview with diagrams
│   ├── components/                      # Per-component architecture docs
│   ├── patterns/                        # Cross-cutting architectural pattern docs
│   └── flows/                           # Key interaction sequence diagrams
├── style/                               # Coding conventions and style guide
│   └── style-guide.md                   # Discovered conventions (generated by bootstrapper)
└── project-overview.md                  # Project overview

e2e/                                     # Autonomous E2E testing harness
├── run-e2e.sh                           # Shell entry point (workspace + cleanup)
├── run-e2e.py                           # Python orchestrator
├── pyproject.toml                       # Dependencies
├── generator/                           # Unique project generation per run
├── scenarios/                           # 14 test scenarios (s01–s14)
├── parallel/                            # ThreadPoolExecutor + isolation
└── validation/                          # Assertion engine + report generator

server/                                  # AVT Gateway (headless web mode)
├── avt_gateway/                         # FastAPI application
│   ├── app.py                           # HTTP/WebSocket API + SPA serving
│   ├── config.py                        # Environment config + API key management
│   ├── services/project_manager.py      # Multi-project lifecycle + port allocation
│   ├── routers/                         # Per-project and global API routes
│   └── ws/manager.py                    # WebSocket real-time event push
├── static/                              # Compiled web dashboard SPA
├── Dockerfile                           # Containerized deployment
├── entrypoint.sh                        # Container startup sequence
└── nginx.conf                           # TLS reverse proxy + WebSocket upgrade
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

### Headless Web Mode (AVT Gateway)

For operating without VS Code, the AVT Gateway serves the dashboard as a standalone web application and manages MCP servers automatically:

```bash
# Local development
cd server
uv run uvicorn avt_gateway.app:app --host 0.0.0.0 --port 8080

# Docker deployment (includes Nginx + TLS)
docker build -t avt-gateway -f server/Dockerfile .
docker run -p 443:443 -v /path/to/project:/project avt-gateway
```

The Gateway supports multi-project management: register multiple project directories, each with isolated MCP server instances on dynamically allocated ports. Access the dashboard at `https://localhost` (Docker) or `http://localhost:8080` (local dev).

## E2E Testing

The project includes an autonomous end-to-end testing harness that exercises all three MCP servers (KG, Governance, Quality) across 14 scenarios with 292+ structural assertions.

### Quick Start

Use the `/e2e` skill or run directly:

```bash
./e2e/run-e2e.sh              # standard run (workspace cleaned up)
./e2e/run-e2e.sh --keep       # preserve workspace for debugging
./e2e/run-e2e.sh --seed 42    # reproducible project generation
./e2e/run-e2e.sh --verbose    # enable debug logging
```

### How It Works

Each run generates a **unique project** from a pool of 8 domains (Pet Adoption, Restaurant Reservation, Fitness Tracking, etc.). The domain is randomly selected, and vision standards, architecture patterns, and components are filled from domain-specific templates. All assertions are **structural and domain-agnostic** -- "a governed task is verified before work begins" is true regardless of whether the domain is Pet Adoption or Fleet Management.

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
| Hook-Based Governance | PostToolUse interception, pair creation, loop prevention |
| Hook Pipeline at Scale | 50 rapid + 20 concurrent tasks, 100% interception |
| Persistence Lifecycle | Full two-phase test: populate all 6 stores via all data flow paths, validate, clean up |

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
├── scenarios/                  # 14 test scenarios (s01–s14)
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

3. **Design architecture** (for tasks requiring architectural decisions):
   ```
   Task tool → subagent_type: architect
   prompt: "Design the authentication architecture for our API. Reference the research brief in .avt/research-briefs/. Produce task briefs for workers."
   ```
   The architect submits each decision with intent, expected_outcome, and vision_references. Governance reviews each decision. The architect produces task briefs in `.avt/task-briefs/`.

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

## Constructive Feedback (PIN Methodology)

All reviews in this system follow PIN methodology: Positive, Innovative, Negative.

- **Why**: When a review only says "blocked," agents discard work unnecessarily. If 95% of work is sound and 5% conflicts with vision, the agent should fix the 5%, not start over.
- **How**: Every review verdict includes `strengths_summary` (what's right overall), and every finding includes `strengths` (what's sound in the related area) and `salvage_guidance` (what to preserve).
- **For orchestrators**: When routing a blocked finding back to a worker, include the strengths and salvage guidance. The worker should know what to keep.
- **For reviewers**: A blocked verdict does not mean "everything is wrong." Always specify what's sound, what needs to change, and the minimal path to resolution.

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
