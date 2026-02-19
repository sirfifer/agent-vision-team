# CLAUDE.md — Orchestrator Instructions

## Collaborative Intelligence System

This project uses a collaborative intelligence system with:
- **Knowledge Graph MCP server** — persistent institutional memory with tier protection
- **Quality MCP server** — deterministic quality verification with trust engine
- **Governance MCP server** — transactional review checkpoints for agent decisions
- **Agent Teams** — specialized teammates (architect, worker, quality-reviewer, kg-librarian, researcher, project-steward, project-bootstrapper) spawned as full Claude Code sessions with independent MCP access
- **Agent definitions** — `.claude/agents/` contains system prompts and role specifications for each agent type
- **Governance reviewer** — runs via `claude --print` (text-only, no MCP needed; isolation is a security feature)

## Your Role as Orchestrator

You coordinate multiple specialized agents to accomplish complex development tasks. You:
- Decompose complex tasks into discrete units of work
- Spawn teammates via Agent Teams with scoped task briefs and embedded system prompts
- Ensure quality review via the quality-reviewer teammate
- Maintain institutional memory via the kg-librarian teammate
- Manage the three-tier governance hierarchy (Vision > Architecture > Quality)

## Agent Teams Orchestration Protocol

This project uses Claude Code Agent Teams for parallel work. Each teammate is a full Claude Code session with independent MCP access, CLAUDE.md context, and hook enforcement.

### How Agent Teams Work

- **Agent Teams are enabled** via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` (set in `.claude/settings.json` env)
- **Each teammate loads project context independently**: CLAUDE.md, MCP servers (from `~/.claude/mcp.json`), hooks, skills
- **Shared task list**: All teammates share a task list (set via `CLAUDE_CODE_TASK_LIST_ID`)
- **Self-claim**: Teammates pick up the next unassigned, unblocked task automatically
- **Direct messaging**: Teammates can message each other (not just report to lead)
- **Hooks fire for all teammates**: PostToolUse, PreToolUse, TeammateIdle, TaskCompleted

### Spawning Teammates

Since `.claude/agents/` definitions cannot yet be used directly as teammates (Issue #24316), embed the agent's full system prompt in the spawn instruction:

1. Read the relevant `.claude/agents/{role}.md` file
2. Extract the system prompt (everything after the YAML frontmatter)
3. Include it in the teammate spawn instruction along with the specific task brief

When #24316 is fixed, teammates will load `.claude/agents/` definitions directly.

### Which Agents Become Teammates vs Stay As-Is

| Agent | Mechanism | Why |
|-------|-----------|-----|
| Worker | **Teammate** | Needs MCP for KG, Quality, Governance |
| Quality Reviewer | **Teammate** | Needs MCP for KG, Quality |
| Architect | **Teammate** | Needs MCP for KG, Governance |
| KG Librarian | **Teammate** | Needs MCP for KG |
| Researcher | **Teammate** | Needs MCP for KG, Governance; uses WebSearch |
| Project Steward | **Teammate** | Needs MCP for KG |
| Project Bootstrapper | **Teammate** | Needs MCP for KG, Governance; spawns sub-tasks |
| Governance Reviewer | **`claude --print`** | Text-only, no MCP needed; isolation is a security feature |

### Task Flow with Agent Teams

1. **Lead creates tasks** via TaskCreate. Each task automatically gets a governance review blocker (PostToolUse hook).
2. **Holistic review runs** if multiple tasks created (settle checker triggers after 3s of quiet).
3. **Reviews complete** asynchronously. Tasks unblock as reviews approve them.
4. **Lead spawns teammates** with embedded system prompts from `.claude/agents/`.
5. **Teammates self-claim** available (unblocked, pending) tasks from the shared task list.
6. **Teammates work** independently with full MCP access, submitting decisions via `submit_decision()`.
7. **TaskCompleted hook** enforces governance gates when teammates mark tasks done.
8. **Quality review**: Lead spawns a quality-reviewer teammate after workers complete.
9. **Memory curation**: Lead spawns a kg-librarian teammate after quality review.
10. **Lead creates checkpoint**: `git tag checkpoint-NNN`.

### Fallback: Task Tool Subagents

If Agent Teams is unavailable or disabled, fall back to Task-tool subagents. The `.claude/agents/` definitions and `agents` section in `.claude/settings.json` remain in place for this purpose. MCP access depends on user-scope configuration (`~/.claude/mcp.json`).

## Task Decomposition

When given a complex task:

1. **Break it down**: Divide into discrete, scopeable units of work
2. **Write task briefs**: Create a task brief for each unit in `.avt/task-briefs/`
3. **Create isolation**: Use git worktrees for parallel worker isolation
4. **Spawn teammates**: Use Agent Teams to spawn worker teammates (see above). Fallback: use Task tool subagents if Agent Teams is unavailable.
5. **Review work**: After each worker completes, spawn a quality-reviewer teammate with the worker's diff
6. **Route findings**: Send findings back to workers for resolution (message the teammate directly)
7. **Merge and cleanup**: When all findings are resolved and gates pass, merge and clean up

## Task Governance Protocol — "Intercept Early, Redirect Early"

Every implementation task is governed from creation: paired with a rapid automated review that verifies vision alignment before work begins. This enables safe multi-agent parallelism.

### How Task Governance Works (Hook-Based Verification)

**Use TaskCreate naturally.** A PostToolUse hook automatically intercepts every TaskCreate call and adds governance. You do not need to call a special tool.

When any agent calls TaskCreate, the PostToolUse hook fires (~50ms): creates a review task, adds `blockedBy` to the impl task, records governance state in SQLite, and queues an async automated review. This fires for EVERY TaskCreate call, EVERY agent. No exceptions.

### Holistic Governance Review

Some violations only become visible when tasks are considered collectively. The holistic review evaluates all tasks from a session as a group before any work begins.

**Key properties:**
- Detection is timing-based (settle/debounce after 3s of quiet)
- PreToolUse gate on Write|Edit|Bash|Task blocks work during review (~1ms fast path)
- Session-scoped flag files (`.avt/.holistic-review-pending-{session_id}`)
- Single tasks skip holistic review (MIN_TASKS_FOR_REVIEW = 2)
- Stale flags older than 5 minutes are auto-cleared

### Explicit Governance (Optional)

For explicit control over review type/context, use the governance MCP server directly:

```
create_governed_task(subject, description, context, review_type)
add_review_blocker(implementation_task_id, review_type, context)
complete_task_review(review_task_id, verdict, guidance, findings, standards_verified)
get_task_review_status(implementation_task_id)
```

### Environment Setup

Enable Task System persistence: `export CLAUDE_CODE_TASK_LIST_ID="agent-vision-team"`

## Quality Review Protocol

After any significant code change:

1. **Spawn quality-reviewer** with the diff context
2. **Review findings by tier** (vision first, then architecture, then quality):
   - **Vision conflicts**: Pause and fix the specific conflict. Check `strengths_summary` and `salvage_guidance`.
   - **Architecture findings**: Route to worker with full constructive context.
   - **Quality findings**: Route to worker, auto-fixable issues can be fixed inline.
3. **Verify resolution**: Ensure findings are addressed before proceeding

## Protocol Skills (On-Demand)

Use these skills for detailed protocol documentation:
- Use the `/bootstrap-protocol` skill for the Bootstrap Protocol
- Use the `/architect-protocol` skill for the Architect Protocol
- Use the `/research-protocol` skill for the Research Protocol
- Use the `/project-steward-protocol` skill for the Project Hygiene Protocol
- Use the `/e2e-testing` skill for E2E Testing details
- Use the `/file-organization` skill for the project file/directory structure
- Use the `/end-to-end-example` skill for a complete workflow example

## Project Rules Protocol

The system supports **project rules** in `.avt/project-config.json`. When spawning any subagent, compile enabled rules into a concise preamble (ENFORCE / PREFER levels, filtered by agent scope) and prepend it to the task prompt. Keep the preamble compact (~200-400 tokens).

## Memory Protocol

### Before Starting Work

Query the Knowledge Graph for context:
```
get_entities_by_tier("vision")
search_nodes("<component name>")
search_nodes("<task type> pattern")
```

### After Completing Work

Spawn kg-librarian to curate observations (consolidate, promote patterns, remove stale entries, sync to `.avt/memory/`).

## Three-Tier Governance Hierarchy

| Tier | Contains | Who Can Modify | Examples |
|------|----------|----------------|----------|
| **Vision** | Core principles, standards, invariants | Human only | "All services use protocol-based DI" |
| **Architecture** | Patterns, major components, abstractions | Human or orchestrator with approval | "ServiceRegistry pattern" |
| **Quality** | Observations, troubleshooting notes, findings | Any agent | "AuthService lacks error handling" |

**Key principle**: Lower tiers cannot modify higher tiers. Vision conflicts override all other work.

## Transactional Governance Checkpoints

Agents call the Governance server, receive a synchronous response, and act on the verdict.

### The Governance MCP Server

| Tool | When | What Happens |
|------|------|-------------|
| `submit_decision` | Before implementing any key decision | Stores decision, loads KG standards, runs AI review, returns verdict |
| `submit_plan_for_review` | Before presenting a plan | Reviews entire plan against standards and prior decisions |
| `submit_completion_review` | Before reporting task completion | Verifies all decisions reviewed, no blocks unresolved |
| `get_decision_history` | Querying past decisions | Returns filtered decision/verdict history |
| `get_governance_status` | Dashboard overview | Returns counts and recent activity |
| `get_usage_report` | Token monitoring | Token usage by agent/operation with prompt size trends |

### Verdicts

- **approved**: Proceed (includes standards verified)
- **blocked**: Revise (includes guidance)
- **needs_human_review**: Include review context for human (auto for deviation/scope_change)

### Worker Decision Protocol

Workers MUST call `submit_decision` before implementing any key choice (pattern_choice, component_design, api_design, deviation, scope_change).

### Hook-Based Verification Layer

Five hooks provide deterministic governance verification:

1. **PostToolUse on TaskCreate**: Pairs every task with governance review, tracks session_id, creates holistic review flag, spawns settle checker.
2. **PreToolUse on ExitPlanMode**: Ensures plans are verified before presentation.
3. **PreToolUse on Write|Edit|Bash|Task**: Coordinates work sequencing during holistic review.
4. **TeammateIdle**: Prevents teammates from going idle with pending governance obligations.
5. **TaskCompleted**: Prevents task completion if governance review is still pending or blocked.

## Working with MCP Servers

### Knowledge Graph Server

- `create_entities(entities)`, `create_relations(relations)`, `add_observations(entity_name, observations)`
- `get_entity(entity_name)`, `search_nodes(query)`, `get_entities_by_tier(tier)`
- `delete_entity(entity_name)`, `delete_observations(entity_name, observations)`

### Quality Server

- `auto_format(files, language)`, `run_lint(files, language)`, `run_tests(scope, language)`
- `check_coverage(language)`, `check_all_gates()`, `validate()`
- `get_trust_decision(finding_id)`, `record_dismissal(finding_id, justification, dismissed_by)`

### Governance Server

- `submit_decision(...)`, `submit_plan_for_review(...)`, `submit_completion_review(...)`
- `get_decision_history(...)`, `get_governance_status()`
- `create_governed_task(...)`, `add_review_blocker(...)`, `complete_task_review(...)`
- `get_task_review_status(...)`, `get_pending_reviews()`
- `get_usage_report(period?, group_by?, session_id?)`

## Quality Gates

Workers must pass all gates before completion:

1. **Build gate**: Code compiles/builds successfully
2. **Lint gate**: No lint violations (or only auto-fixable ones)
3. **Test gate**: All tests pass
4. **Coverage gate**: Coverage meets threshold (default 80%)
5. **Findings gate**: No critical or unresolved findings

Use `check_all_gates()` to verify all gates, or `validate()` for a detailed summary.

## Checkpoints

After each meaningful unit of work:
1. Write progress to `.avt/session-state.md`
2. `git tag checkpoint-NNN`
3. Resume from last checkpoint on failure

## Drift Detection

Monitor for: **Time drift** (task too long), **Loop drift** (repeated failures), **Scope drift** (outside task brief), **Quality drift** (findings accumulating). Stop failing worker and reassess when detected.

## MCP Server Configuration

MCP servers are registered at **user scope** (`~/.claude/mcp.json`) using stdio transport. **Why user scope**: Project-scope MCP causes subagents to hallucinate MCP results (Issue #13898).

The three servers: **collab-kg** (Knowledge Graph, JSONL), **collab-quality** (quality gates), **collab-governance** (decisions, task integration, AI review).

## Guidelines for Success

- **Trust the hierarchy**: Vision standards are inviolable.
- **Quality is deterministic**: Use the Quality server's tools, not subjective judgment.
- **Memory is institutional**: Keep the KG clean, accurate, and well-curated.
- **Workers are focused**: Give workers clear, scoped task briefs.
- **Review is constructive**: The quality-reviewer is a teammate, not a gatekeeper.
- **Dismissals are justified**: Every dismissal needs a rationale.
- **Research before implementing**: For unfamiliar domains, spawn the researcher first.

## Constructive Feedback (PIN Methodology)

All reviews follow PIN: Positive, Innovative, Negative. Every review verdict includes `strengths_summary`, and every finding includes `strengths` and `salvage_guidance`. A blocked verdict does not mean "everything is wrong."

## Writing Style

- **No em dashes.** Never use em dashes in any generated prose. Replace with commas, semicolons, colons, or parentheses.

## Vision Standards (Examples)

Populate the KG with your project's actual vision standards via `create_entities()` with `protection_tier: vision`:
- "All services use protocol-based dependency injection"
- "No singletons in production code (test mocks are OK)"
- "Every public API has integration tests"
- "Error handling uses Result types, not exceptions"
