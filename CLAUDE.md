# CLAUDE.md — Orchestrator Instructions

## Collaborative Intelligence System

This project uses a collaborative intelligence system with:
- **Knowledge Graph MCP server** — persistent institutional memory with tier protection
- **Quality MCP server** — deterministic quality verification with trust engine
- **Custom subagents** — worker, quality-reviewer, kg-librarian (defined in `.claude/agents/`)

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
2. **Write task briefs**: Create a task brief for each unit in `.claude/collab/task-briefs/`
3. **Create isolation**: Use git worktrees for parallel worker isolation:
   ```bash
   git worktree add ../project-worker-N -b task/NNN-description
   ```
4. **Spawn workers**: Use the Task tool to launch worker subagents, one per task brief
5. **Review work**: After each worker completes, spawn quality-reviewer with the worker's diff
6. **Route findings**: Send findings back to workers for resolution
7. **Merge and cleanup**: When all findings are resolved and gates pass, merge and clean up

## Quality Review Protocol

After any significant code change:

1. **Spawn quality-reviewer** with the diff context
2. **Review findings by tier** (vision first, then architecture, then quality):
   - **Vision conflicts**: Stop all related work, address immediately
   - **Architecture findings**: Route to worker with context, require resolution
   - **Quality findings**: Route to worker, auto-fixable issues can be fixed inline
3. **Verify resolution**: Ensure findings are addressed before proceeding

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
   - Sync important entries to archival files in `.claude/collab/memory/`

## Three-Tier Governance Hierarchy

The system enforces a protection hierarchy via tier metadata:

| Tier | Contains | Who Can Modify | Examples |
|------|----------|----------------|----------|
| **Vision** | Core principles, standards, invariants | Human only | "All services use protocol-based DI", "No singletons in production code" |
| **Architecture** | Patterns, major components, abstractions | Human or orchestrator with approval | "ServiceRegistry pattern", "AuthService component" |
| **Quality** | Observations, troubleshooting notes, findings | Any agent | "AuthService lacks error handling", "Login flow refactored on 2024-01-15" |

**Key principle**: Lower tiers cannot modify higher tiers. Vision conflicts override all other work.

## Checkpoints

After each meaningful unit of work:

1. **Update session state**: Write progress to `.claude/collab/session-state.md`
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
│   └── kg-librarian.md
├── collab/
│   ├── task-briefs/                 # Task briefs for workers
│   ├── session-state.md             # Current session progress
│   ├── memory/                      # Archival memory files
│   │   ├── architectural-decisions.md
│   │   ├── troubleshooting-log.md
│   │   └── solution-patterns.md
│   ├── knowledge-graph.jsonl        # KG persistence (managed by server)
│   └── trust-engine.db              # Trust engine SQLite DB (managed by server)
└── settings.json                    # Claude Code settings and hooks
```

## Starting MCP Servers

Before using the system, ensure both MCP servers are running:

```bash
# Terminal 1: Knowledge Graph server (SSE on port 3101)
cd mcp-servers/knowledge-graph
uv run python -m collab_kg.server

# Terminal 2: Quality server (SSE on port 3102)
cd mcp-servers/quality
uv run python -m collab_quality.server
```

Both servers will be available to all Claude Code sessions and subagents.

## End-to-End Example

**Task**: Add authentication to the API

1. **Query KG for context**:
   ```
   search_nodes("auth")
   get_entities_by_tier("vision")
   ```

2. **Create task brief**: Write `.claude/collab/task-briefs/001-add-auth.md`

3. **Spawn worker**:
   ```
   Task tool → subagent_type: worker
   prompt: "Implement the task in .claude/collab/task-briefs/001-add-auth.md"
   ```

4. **Worker completes and runs gates**: Worker calls `check_all_gates()` before completion

5. **Review work**:
   ```
   Task tool → subagent_type: quality-reviewer
   prompt: "Review the diff for task 001-add-auth"
   ```

6. **Address findings**: If findings exist, route back to worker for resolution

7. **Curate memory**:
   ```
   Task tool → subagent_type: kg-librarian
   prompt: "Curate the knowledge graph after task 001-add-auth"
   ```

8. **Merge and checkpoint**:
   ```bash
   git merge task/001-add-auth
   git tag checkpoint-001
   ```

## Guidelines for Success

- **Trust the hierarchy**: Vision standards are inviolable. Architecture patterns should be followed unless there's a compelling reason to diverge.
- **Quality is deterministic**: Use the Quality server's tools, not subjective judgment.
- **Memory is institutional**: The KG is a shared resource. Keep it clean, accurate, and well-curated.
- **Workers are focused**: Give workers clear, scoped task briefs. Don't let them drift.
- **Review is constructive**: The quality-reviewer is a teammate, not a gatekeeper.
- **Dismissals are justified**: Never silently dismiss a finding. Every dismissal needs a rationale.

## Vision Standards (Examples)

These are placeholders. Populate the KG with your project's actual vision standards:

- "All services use protocol-based dependency injection"
- "No singletons in production code (test mocks are OK)"
- "Every public API has integration tests"
- "Error handling uses Result types, not exceptions"
- "UI components are SwiftUI, not UIKit"

Use `create_entities()` to add vision standards to the KG with `protection_tier: vision`.
