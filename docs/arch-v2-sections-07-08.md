## 7. Custom Subagent Definitions

The system defines six specialized subagents in `.claude/agents/`. Each is a Markdown file with YAML frontmatter declaring the model, tool access, and MCP server bindings. The orchestrator spawns subagents via the Claude Code Task tool, injecting task-specific context and project rules into each invocation.

### Agent Comparison Table

| Agent | Model | Tool Count | MCP Access | Role | Spawned By |
|-------|-------|------------|------------|------|------------|
| **Worker** | Opus 4.6 | 9 | KG + Quality + Governance | Implement scoped tasks with full governance integration | Orchestrator |
| **Quality Reviewer** | Opus 4.6 | 6 | KG + Quality | Three-lens review (vision, architecture, quality) | Orchestrator |
| **KG Librarian** | Sonnet 4.5 | 5 | KG | Curate institutional memory, consolidate observations | Orchestrator |
| **Governance Reviewer** | Sonnet 4.5 | 4 | KG | AI-powered decision review against vision/architecture standards | Governance Server (via `claude --print`) |
| **Researcher** | Opus 4.6 | 8 | KG + Governance | Periodic monitoring + exploratory design research | Orchestrator |
| **Project Steward** | Sonnet 4.5 | 7 | KG | Project hygiene, naming conventions, cruft detection | Orchestrator |

> **Note on Governance Reviewer**: Unlike the other five agents, the governance-reviewer is NOT spawned by the orchestrator. It is invoked internally by the Governance MCP server via `claude --print` when `submit_decision()`, `submit_plan_for_review()`, or `submit_completion_review()` are called. It runs as a headless subprocess, not a Task tool subagent.

---

### 7.1 Worker

**File**: `.claude/agents/worker.md`

```yaml
---
model: opus
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - mcp:collab-kg
  - mcp:collab-quality
  - mcp:collab-governance
---
```

**MCP Server Access**: Knowledge Graph (port 3101), Quality (port 3102), Governance (port 3103)

**Role**: Implements specific tasks assigned by the orchestrator. Workers are the only agents that write production code. They operate within strictly scoped task briefs and must pass all governance checkpoints before, during, and after implementation.

**Protocol**:

| Phase | Step | Detail |
|-------|------|--------|
| **Startup** | 1. Read task brief | From task prompt or `.avt/task-briefs/` |
| | 2. Check project rules | Injected in context under `## Project Rules`. `ENFORCE` rules are non-negotiable; `PREFER` rules require documented justification to deviate. |
| | 3. Query KG for vision standards | `get_entities_by_tier("vision")` to load all vision constraints |
| | 4. Query KG for patterns | `search_nodes("<component>")` to find architectural patterns and past solutions |
| | 5. Note governed relations | Check `governed_by` relations linking components to vision standards |
| **Task Creation** | 6. Create governed tasks | Call `create_governed_task()` on Governance server. NEVER use `TaskCreate` directly. |
| | 7. Verify task unblocked | Call `get_task_review_status()` to confirm approval before starting work |
| **During Work** | 8. Submit decisions | Call `submit_decision()` for every key choice (pattern_choice, component_design, api_design, deviation, scope_change). **This call blocks until verdict returns.** |
| | 9. Act on verdicts | `approved`: proceed. `blocked`: revise and resubmit. `needs_human_review`: include context and wait. |
| | 10. Submit plans | Call `submit_plan_for_review()` before presenting any plan |
| | 11. Stay in scope | Follow patterns from KG, do not modify files outside task brief |
| **Completion** | 12. Submit completion review | Call `submit_completion_review()` with work summary and changed files |
| | 13. Run quality gates | Call `check_all_gates()` via Quality server |
| | 14. Return summary | Structured output: what was done, files changed, gate results, governance verdicts, concerns |

**Constraints**:
- Do not modify files outside the task brief's scope
- Do not modify vision-tier or architecture-tier KG entities
- If a vision standard conflicts with the task, stop and report the conflict
- Do not skip governance checkpoints -- every key decision must be submitted
- Pass `callerRole: "worker"` in all KG operations

---

### 7.2 Quality Reviewer

**File**: `.claude/agents/quality-reviewer.md`

```yaml
---
model: opus
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - mcp:collab-kg
  - mcp:collab-quality
---
```

**MCP Server Access**: Knowledge Graph (port 3101), Quality (port 3102)

**Role**: Evaluates work through three ordered lenses: vision alignment, architectural conformance, and quality compliance. The quality reviewer is a read-focused agent -- it reviews code but does not write production code.

**Protocol -- Three-Lens Review (Strict Order)**:

| Lens | Priority | KG Query | What It Checks | Severity |
|------|----------|----------|----------------|----------|
| **1. Vision** | Highest | `get_entities_by_tier("vision")` | Alignment with every applicable vision standard. A vision conflict is the ONLY finding reported -- it overrides everything else. | `vision_conflict` |
| **2. Architecture** | Medium | `search_nodes("<affected components>")` | Adherence to established patterns (`follows_pattern` relations). Detection of ad-hoc pattern drift: new code that reinvents something an existing pattern handles. | `architectural` |
| **3. Quality** | Standard | `check_all_gates()`, `run_lint()`, `check_coverage()` | Quality gate results, lint violations, test coverage. Compliance with project rules injected in context. | `logic`, `style`, `formatting` |

**Finding Format**: Every finding must include:
- Project-specific rationale (not generic advice)
- Concrete suggestion for remediation
- Reference to the KG entity or standard being violated

**Constraints**:
- Read-focused: review code, do not write production code
- Pass `callerRole: "quality"` in all KG operations
- Do not modify vision-tier or architecture-tier KG entities
- Constructive tone: teammate, not gatekeeper

---

### 7.3 KG Librarian

**File**: `.claude/agents/kg-librarian.md`

```yaml
---
model: sonnet
tools:
  - Read
  - Write
  - Glob
  - Grep
  - mcp:collab-kg
---
```

**MCP Server Access**: Knowledge Graph (port 3101)

**Role**: Curates institutional memory after work sessions. The librarian consolidates raw observations into well-organized knowledge, promotes recurring solutions to patterns, and syncs important entries to archival files.

**Protocol**:

| Phase | Step | Detail |
|-------|------|--------|
| **Review** | 1. Query recent activity | Find recently added entities and observations in the KG |
| **Consolidate** | 2. Merge redundant observations | Combine overlapping observations on the same entity into coherent entries |
| **Promote** | 3. Create solution patterns | When the same fix or approach appears 3+ times, create a `solution_pattern` entity |
| **Clean** | 4. Remove stale entries | Delete observations that are no longer accurate (outdated descriptions, resolved problems) |
| **Validate** | 5. Check tier consistency | Ensure no vision-tier entities have been modified by agents; report violations |
| **Sync** | 6. Update archival files | Write important KG entries to `.avt/memory/` files |

**Archival File Mapping**:

| File | Contents |
|------|----------|
| `.avt/memory/architectural-decisions.md` | Significant decisions and their rationale |
| `.avt/memory/troubleshooting-log.md` | Problems, what was tried, what worked |
| `.avt/memory/solution-patterns.md` | Promoted patterns with steps and reference implementations |
| `.avt/memory/research-findings.md` | Key discoveries from research that establish new baselines |

**Constraints**:
- Do not create or modify vision-tier entities
- Do not create or modify architecture-tier entities without `changeApproved: true`
- Do not delete entities that have `governed_by` relations pointing to them
- Pass `callerRole: "quality"` in all KG operations (librarian operates at the quality tier)

---

### 7.4 Governance Reviewer

**File**: `.claude/agents/governance-reviewer.md`

```yaml
---
model: sonnet
tools:
  - Read
  - Glob
  - Grep
  - mcp:collab-kg
---
```

**MCP Server Access**: Knowledge Graph (port 3101)

**Role**: AI-powered decision evaluator invoked internally by the Governance MCP server. Evaluates agent decisions and plans through the lens of vision alignment and architectural conformance. Returns structured JSON verdicts.

**Invocation**: The governance-reviewer is NOT spawned by the orchestrator via the Task tool. Instead, the Governance server's `GovernanceReviewer` class invokes it via `claude --print` (headless subprocess) when processing `submit_decision()`, `submit_plan_for_review()`, or `submit_completion_review()` calls. This makes governance review a synchronous round-trip within the MCP tool call.

**Review Protocol (Strict Order)**:

| Check | Priority | Action on Failure |
|-------|----------|-------------------|
| **1. Vision Alignment** | Highest | Load standards via `get_entities_by_tier("vision")`. Any vision conflict produces a `blocked` verdict immediately -- overrides everything else. |
| **2. Architectural Conformance** | Medium | Search KG for patterns and components. Detect ad-hoc pattern drift. Unjustified deviation produces a `blocked` verdict. |
| **3. Consistency Check** | Standard | For plan reviews: verify blocked decisions were not reimplemented. For completion reviews: verify all decisions were reviewed. Inconsistencies produce a `blocked` verdict. |

**Response Format**:

```json
{
  "verdict": "approved | blocked | needs_human_review",
  "findings": [
    {
      "tier": "vision | architecture | quality",
      "severity": "vision_conflict | architectural | logic",
      "description": "specific finding with project context",
      "suggestion": "concrete fix"
    }
  ],
  "guidance": "brief guidance for the agent",
  "standards_verified": ["list of standards checked and passed"]
}
```

**Verdict Rules**:
- **approved**: Decision aligns with all applicable standards. Includes which standards were verified.
- **blocked**: Decision conflicts with vision or architecture. Includes specific findings with suggestions.
- **needs_human_review**: Decision involves deviation, scope change, or ambiguous interpretation. Includes context for the human.

**Constraints**:
- Read-only: evaluate, do not implement
- Do not modify any KG entities
- Pass `callerRole: "quality"` in all KG operations
- Every finding must reference the actual standard or pattern being violated
- Always include a suggestion for remediation

---

### 7.5 Researcher

**File**: `.claude/agents/researcher.md`

```yaml
---
model: opus
tools:
  - Read
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - mcp:collab-kg
  - mcp:collab-governance
---
```

**MCP Server Access**: Knowledge Graph (port 3101), Governance (port 3103)

**Role**: Gathers intelligence to inform development decisions and tracks external changes. The researcher is the only agent with web access (`WebSearch`, `WebFetch`). Workers should never do substantial research -- that is the researcher's job.

**Research Modes**:

| Mode | Trigger | Output | Stored In |
|------|---------|--------|-----------|
| **Periodic/Maintenance** | Scheduled or on-demand | Change reports (breaking changes, deprecations, security advisories) | KG + `.avt/memory/research-findings.md` |
| **Exploratory/Design** | Before architectural decisions | Research briefs with options, tradeoffs, recommendations | `.avt/research-briefs/` |

**Protocol**:

| Phase | Step | Detail |
|-------|------|--------|
| **Startup** | 1. Read research prompt | From task prompt or `.avt/research-prompts/` |
| | 2. Determine research mode | Periodic or exploratory |
| | 3. Query KG for existing knowledge | `search_nodes("<topic>")` to avoid rediscovering known information |
| | 4. Note dependency relations | Check `depends_on` and `integrates_with` relations |
| **Periodic Research** | 5. Identify scope | Which technologies, APIs, or dependencies to check |
| | 6. Gather intelligence | Use `WebSearch` and `WebFetch` for changelogs, release notes, advisories |
| | 7. Analyze relevance | Filter findings to what affects this project |
| | 8. Record findings | Add observations to relevant KG entities |
| | 9. Flag actionable items | Categorize: breaking changes, deprecations, new features, security advisories |
| **Exploratory Research** | 5. Survey the landscape | Search for patterns, best practices, case studies, documentation |
| | 6. Evaluate options | For each viable approach: how it works, pros/cons, integration cost, risks |
| | 7. Synthesize recommendations | Present options with analysis, not information dumps |
| | 8. Submit research conclusion | Call `submit_decision(category="research_complete")` on Governance server |

**Model Selection**: The orchestrator selects the model based on research complexity:

| Complexity | Model | Use When |
|------------|-------|----------|
| High | Opus 4.6 | Novel domains, architectural decisions, security analysis, ambiguous requirements |
| Routine | Sonnet 4.5 | Changelog monitoring, version updates, straightforward API documentation |

**Constraints**:
- Do not modify vision-tier or architecture-tier KG entities (observations only)
- Do not make implementation decisions -- provide options and analysis
- Do not skip governance checkpoints for research that informs architecture
- Cite sources for all significant claims
- Distinguish fact from interpretation; flag uncertainty

---

### 7.6 Project Steward

**File**: `.claude/agents/project-steward.md`

```yaml
---
model: sonnet
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - mcp:collab-kg
---
```

**MCP Server Access**: Knowledge Graph (port 3101)

**Role**: Maintains project hygiene, organization, naming conventions, and completeness across the codebase. The steward is the guardian of project-level quality -- not code logic, but everything that makes a project professional and maintainable.

**Review Areas**:

| Area | What It Checks |
|------|----------------|
| **Project-Level Files** | Presence and completeness of LICENSE, README, CONTRIBUTING, CHANGELOG, CODE_OF_CONDUCT, SECURITY, .gitignore |
| **Naming Conventions** | Consistent casing across files, directories, variables, types, constants, test files per language/framework norms |
| **Folder Organization** | Logical grouping, consistent depth, no orphaned files, separation of concerns |
| **Documentation Completeness** | README sections, API docs, configuration documentation, script header comments |
| **Cruft Detection** | Unused files, duplicates, empty directories, temp files, outdated configs, dead links, resolved TODOs |
| **Consistency** | Indentation style, line endings, file encoding, import ordering, export patterns |

**Protocol**:

| Phase | Step | Detail |
|-------|------|--------|
| **Startup** | 1. Query KG for standards | `search_nodes("naming convention")`, `search_nodes("project structure")`, `get_entities_by_tier("architecture")` |
| | 2. Scan project root | Check for essential project files |
| | 3. Map folder structure | Build a mental map of organization |
| **Review** | 4. Check essential files | Verify existence and completeness (not stubs or placeholders) |
| | 5. Analyze naming | Sample files across directories for casing consistency |
| | 6. Detect cruft | Look for orphaned, duplicate, or outdated files |
| | 7. Review documentation | Check README and key docs for accuracy |
| **Output** | 8. Produce structured report | Findings categorized by priority (immediate, short-term, long-term) |
| | 9. Record KG entities | Create `naming_convention` and `project_structure` entities |

**Direct Fix Policy**: The steward CAN fix issues directly when the fix is mechanical (renaming, cruft removal) and non-controversial. It must ask the orchestrator before deleting files that might still be in use, making structural changes, modifying legal files, or changing multi-developer workflows.

**Periodic Review Schedule**:
- **Weekly**: Cruft detection, dead link checking
- **Monthly**: Full naming consistency audit
- **Quarterly**: Deep documentation review, structure analysis

**Constraints**:
- Do not modify code logic -- only project organization and documentation
- Do not modify vision-tier or architecture-tier KG entities
- Pass `callerRole: "quality"` in all KG operations
- When uncertain if something is cruft, flag it rather than delete it
- Respect existing conventions even if different ones would be preferred
- Always explain rationale behind naming/organization recommendations

---

## 8. Governance Architecture

### 8.1 Philosophy: "Intercept Early, Redirect Early"

Every implementation task is blocked from birth until governance review approves it. This is the central invariant of the governance system. There are no race conditions where work could start before review, no optimistic execution paths, and no fire-and-forget review requests.

The design principle is deterministic ordering: **Review -> Approve/Block -> Execute**. This order is enforced structurally through task dependency graphs, not through convention or documentation.

Why this matters:
- **Vision conflicts are caught before code is written**, not during code review
- **Failed approaches from institutional memory are flagged** before workers repeat them
- **Scope creep is detected at the decision level**, not the pull request level
- **Architectural drift is prevented**, not corrected after the fact

### 8.2 Governed Task Lifecycle

The `create_governed_task()` tool atomically creates two tasks in the Claude Code native Task system:

1. **Review Task** (status: pending) -- blocks the implementation task
2. **Implementation Task** (status: pending, blockedBy: [review task]) -- CANNOT execute until review passes

```
create_governed_task("Implement auth service", review_type="governance")
    |
    +-------------------------------------+------------------------------------------+
    v                                     v                                          |
+------------------------------+  +--------------------------------------+           |
| Review Task (review-abc123)  |  | Implementation Task (impl-xyz789)    |           |
|                              |  |                                      |           |
| subject: [GOVERNANCE]        |  | subject: Implement auth service      |           |
|   Review: Implement auth     |  | status: pending                      |           |
|   service                    |  | blockedBy: [review-abc123]           |           |
| status: pending              |  |                                      |           |
| blocks: [impl-xyz789]        |  | XX CANNOT EXECUTE                    |           |
+------------------------------+  +--------------------------------------+           |
              |                                                                      |
              v                                                                      |
+---------------------------------------------------------------------+              |
| Governance Review Executes:                                         |              |
|   - Load vision standards from KG                                   |              |
|   - Load architecture patterns from KG                              |              |
|   - Check memory for failed approaches                              |              |
|   - AI review via governance-reviewer (claude --print)              |              |
+---------------------------------------------------------------------+              |
              |                                                                      |
   +----------+-------------------+                                                  |
   v          v                   v                                                  |
APPROVED    BLOCKED          NEEDS_HUMAN_REVIEW                                      |
   |          |                   |                                                  |
   |          |                   v                                                  |
   |          |          Human must resolve.                                          |
   |          |          Task stays blocked.                                          |
   |          |                                                                      |
   |          v                                                                      |
   |   Task stays blocked                                                            |
   |   with guidance. Agent                                                          |
   |   must revise approach.                                                         |
   |                                                                                 |
   v                                                                                 |
complete_task_review(review-abc123, "approved", ...)                                  |
   |                                                                                 |
   v                                                                                 |
review-abc123 blockedBy removed from impl-xyz789                                     |
   |                                                                                 |
   v                                                                                 |
If no remaining blockers -> impl-xyz789 is AVAILABLE for execution ------------------+
```

**Stacking Additional Reviews**:

If initial governance review passes but flags a need for specialized review, additional blockers can be added:

```
add_review_blocker(
    implementation_task_id: "impl-xyz789",
    review_type: "security",
    context: "Auth handling requires security review"
)
```

The implementation task now has TWO blockers. Both must be individually completed via `complete_task_review()` before the task unblocks:

```
impl-xyz789
  blockedBy: [review-abc123, review-security-def456]
                    |                    |
                    v                    v
         complete_task_review()  complete_task_review()
         verdict: approved       verdict: approved
                    |                    |
                    v                    v
            blocker removed       blocker removed
                    |                    |
                    +--------+-----------+
                             v
                  blockedBy: [] -> TASK AVAILABLE
```

**Implementation**: The `create_governed_task_pair()` function in `mcp-servers/governance/collab_governance/task_integration.py` handles atomic creation. Review tasks are always written to disk before implementation tasks, ensuring the blocker reference is valid at creation time. File-level locking via `fcntl.flock()` prevents concurrent modification.

### 8.3 Transactional Decision Review

Worker agents call `submit_decision()` on the Governance MCP server before implementing any key choice. This is a **synchronous round-trip** -- the tool call blocks until the review completes and a verdict is returned. It is not fire-and-forget.

**Internal Flow of `submit_decision()`**:

```
Worker calls submit_decision(task_id, agent, category, summary, ...)
    |
    v
1. Decision stored in SQLite (.claude/collab/governance.db)
    |
    v
2. Vision standards loaded from KG JSONL
    |
    v
3. Architecture entities loaded from KG
    |
    v
4. Category check:
    +-- deviation or scope_change -> auto-verdict: needs_human_review
    |
    +-- all other categories:
        |
        v
    5. claude --print invoked with governance-reviewer agent
       (full AI reasoning against standards)
        |
        v
    6. ReviewVerdict parsed from reviewer output
    |
    v
7. Review stored in SQLite
    |
    v
8. Decision recorded in KG for institutional memory
    |
    v
9. Verdict returned to the calling worker
```

**Decision Categories**:

| Category | When Used | Behavior |
|----------|-----------|----------|
| `pattern_choice` | Choosing an implementation pattern | AI review against standards |
| `component_design` | Designing a component's interface | AI review against standards |
| `api_design` | Designing an API surface | AI review against standards |
| `deviation` | Intentionally deviating from an established pattern | Auto-verdict: `needs_human_review` |
| `scope_change` | Working outside the task brief's defined scope | Auto-verdict: `needs_human_review` |

**Verdicts**:

| Verdict | Meaning | Agent Action |
|---------|---------|--------------|
| `approved` | Decision aligns with all applicable standards | Proceed with implementation. Response includes which standards were verified. |
| `blocked` | Decision conflicts with vision or architecture | Stop. Response includes `guidance` explaining what to change. Revise and resubmit. |
| `needs_human_review` | Ambiguous, deviation, or scope change | Include the review context when presenting to the human. Do not proceed with the blocked aspect until resolved. |

**Plan Review**: Workers must also call `submit_plan_for_review()` before presenting any plan. This reviews the complete plan against all standards and checks that blocked decisions were not reimplemented.

**Completion Review**: Workers must call `submit_completion_review()` before reporting task completion. This verifies:
- All decisions were reviewed (no unreviewed decisions)
- No blocked decisions remain unresolved
- Work aligns with standards

If unreviewed decisions or unresolved blocks are found, the completion review returns a `blocked` verdict.

### 8.4 Three-Tier Governance Hierarchy

The Knowledge Graph enforces a protection hierarchy via `protection_tier` metadata on entities. Lower tiers cannot modify higher tiers. This hierarchy governs what each agent is permitted to change.

| Tier | Contains | Who Can Modify | Examples |
|------|----------|----------------|----------|
| **Vision** | Core principles, standards, invariants | Human only | "All services use protocol-based DI", "No singletons in production code", "Every public API has integration tests" |
| **Architecture** | Patterns, major components, abstractions | Human or orchestrator with approval | "ServiceRegistry pattern", "AuthService component", "Protocol-based DI pattern" |
| **Quality** | Observations, troubleshooting notes, findings | Any agent | "AuthService lacks error handling", "Login flow refactored on 2024-01-15" |

**Key Principle**: Lower tiers cannot modify higher tiers. A worker (quality-tier agent) can add observations to architecture-tier entities but cannot modify the entity itself. Vision-tier entities are immutable to all agents -- only humans can change them.

**Enforcement Points**:
- The KG server validates `callerRole` against `protection_tier` on every mutation
- The quality reviewer flags vision conflicts as the highest-priority finding (overrides all other findings)
- The governance reviewer blocks any decision that conflicts with vision standards
- Workers are instructed to stop and report if a vision standard conflicts with their task

### 8.5 Safety Net: ExitPlanMode Hook

A `PreToolUse` hook on `ExitPlanMode` provides a backup enforcement mechanism. The hook script at `scripts/hooks/verify-governance-review.sh` runs before any agent can present a plan to the human.

**How It Works**:

```
Agent attempts to exit plan mode (present plan)
    |
    v
PreToolUse hook fires -> verify-governance-review.sh
    |
    v
Script checks .avt/governance.db for plan review records
    |
    +-- Plan reviews found (COUNT > 0) -> exit 0 (allow)
    |
    +-- No plan reviews found -> exit 2 (block)
        |
        v
    Agent receives feedback:
    "GOVERNANCE REVIEW REQUIRED: You must call
     submit_plan_for_review() before presenting your plan."
```

**Design Intent**: This hook is the **safety net**, not the primary mechanism. The primary enforcement is the worker protocol itself -- workers are instructed to call `submit_plan_for_review()` before presenting plans. The hook catches cases where an agent skips or forgets the governance checkpoint. If the governance database does not exist (server not running), the hook allows the action to avoid blocking development when governance is intentionally disabled.

### 8.6 Task List + Governance Layering

The system separates concerns into two distinct layers that compose cleanly:

```
+---------------------------------------------------------------+
|                      GOVERNANCE LAYER                          |
|                                                                |
|  Policy: Should this task proceed? What reviews are required?  |
|  What standards apply? What is the verdict?                    |
|                                                                |
|  Tools: create_governed_task, add_review_blocker,              |
|         complete_task_review, submit_decision,                 |
|         submit_plan_for_review, submit_completion_review       |
|                                                                |
|  Storage: governance.db (SQLite)                               |
|  Agent: governance-reviewer (via claude --print)               |
|  Server: collab-governance (port 3103)                         |
+---------------------------------------------------------------+
|                    INFRASTRUCTURE LAYER                         |
|                                                                |
|  Mechanics: Persistence, DAG dependencies, file locking,       |
|  cross-session coordination, task state machines               |
|                                                                |
|  Implementation: Claude Code native Task system                |
|  Storage: ~/.claude/tasks/{CLAUDE_CODE_TASK_LIST_ID}/*.json    |
|  Module: task_integration.py (TaskFileManager)                 |
|  Concurrency: fcntl.flock() for atomic file operations         |
+---------------------------------------------------------------+
|                     SHARED NAMESPACE                            |
|                                                                |
|  CLAUDE_CODE_TASK_LIST_ID="agent-vision-team"                  |
|  Ensures tasks persist across sessions and are shared          |
|  across all agents in the project                              |
+---------------------------------------------------------------+
```

**Why Two Layers**:

| Concern | Layer | Rationale |
|---------|-------|-----------|
| Task persistence | Infrastructure | Claude Code's native Task system already handles JSON file storage, session persistence, and cross-agent visibility |
| DAG dependencies (blockedBy/blocks) | Infrastructure | The native Task system provides dependency graph semantics out of the box |
| File locking | Infrastructure | `task_integration.py` uses `fcntl.flock()` for concurrent-safe reads and writes to task files |
| Review policy | Governance | Whether a task should proceed is a policy question independent of how tasks are stored |
| Standard verification | Governance | Checking decisions against vision and architecture standards is domain logic, not infrastructure |
| Verdict storage | Governance | Review verdicts, findings, and guidance are governance data stored in `governance.db` |
| Institutional memory | Governance | Decisions and verdicts are recorded in the KG for future reference |

**How They Compose**:

1. `create_governed_task()` creates tasks in the **native Task List** (infrastructure) with `blockedBy` relationships pointing to review tasks. Simultaneously, it creates governance records in `governance.db` (policy).

2. `complete_task_review()` removes blockers in the **native Task system** (via `release_task()` in `task_integration.py`) when reviews pass. Simultaneously, it updates review records in `governance.db` with verdicts, findings, and guidance.

3. `get_task_review_status()` reads from **both layers**: file-system task state (is the task blocked? how many blockers?) and governance database records (what type of review? what was the verdict?).

**The `task_integration.py` Bridge**:

The `TaskFileManager` class in `mcp-servers/governance/collab_governance/task_integration.py` is the bridge between layers. It reads and writes Claude Code's native task JSON files while the governance server's `GovernanceStore` manages the policy database. Key operations:

| Function | Infrastructure Action | Governance Action |
|----------|-----------------------|-------------------|
| `create_governed_task_pair()` | Write review + impl task JSON files with `blockedBy`/`blocks` relationships | N/A (called by `create_governed_task` which handles governance DB) |
| `add_additional_review()` | Create review task file, add blocker to impl task file | N/A (called by `add_review_blocker` which handles governance DB) |
| `release_task()` | Complete review task file, remove blocker from impl task file | N/A (called by `complete_task_review` which handles governance DB) |
| `get_task_governance_status()` | Read task file, enumerate blockers and their statuses | N/A (called by `get_task_review_status` which merges governance DB data) |

**Strategic Value**: This two-layer separation keeps governance independent of the transport mechanism. If Claude Code's Task system changes its file format, only `task_integration.py` needs to adapt. The governance policy logic, standards verification, and review workflows remain unchanged. Conversely, governance rules can evolve (new review types, different verdict logic, additional checks) without touching the task infrastructure.
