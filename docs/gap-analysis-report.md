# Gap Analysis Report: Agent Vision Team

**Date**: 2026-02-05
**Prepared For**: Architecture refresh planning
**Sources**: Claude Code capabilities (Feb 2026, first-party Anthropic docs), ARCHITECTURE.md (root, 1154 lines), actual codebase

---

## Executive Summary

The root ARCHITECTURE.md describes a system with 2 MCP servers (Knowledge Graph + Quality) and 3 custom agents (worker, quality-reviewer, kg-librarian). The actual codebase has evolved to **3 MCP servers** and **6 custom agents**, with an entire governance subsystem that is fully built and operational but completely absent from the architecture document.

The governance system — the single largest undocumented subsystem — provides transactional decision review, blocked-from-birth task governance, multi-blocker support, and AI-powered review via `claude --print`. It is deeply integrated into the worker agent's protocol, the extension's dashboard, and the E2E test harness. None of this appears in ARCHITECTURE.md.

Simultaneously, Claude Code has shipped major new platform capabilities in the last two weeks: **Opus 4.6** (1M context window, effort controls, context compaction), **Agent Teams** (experimental multi-agent coordination with shared task lists and peer messaging), **Plugins & Marketplaces** (distributable feature bundles), and the **native Task List system** (persistent DAG with cross-session coordination). These create new architectural opportunities that should inform the next version of the architecture document.

This report provides the evidence base for an ARCHITECTURE.md v2. It catalogs every gap, inventories new platform capabilities, and surfaces strategic choices that require direction before the architecture can be updated.

---

## 1. Claude Code Capability Inventory (February 2026)

This section covers capabilities available as of the Opus 4.6 release (February 5, 2026), validated against first-party Anthropic documentation.

### 1.1 Opus 4.6 Model Improvements

| Capability | Detail | Source |
|-----------|--------|--------|
| Context window | **1M tokens (beta)** — first for Opus-class models | [anthropic.com/news/claude-opus-4-6](https://www.anthropic.com/news/claude-opus-4-6) |
| Max output | **128K tokens** | Same |
| Effort controls | Four levels: low, medium, high, max — adjustable via `/model` with arrow keys | Same |
| Context compaction | **Beta** — auto-summarizes older context for long-running tasks | Same |
| Long-context accuracy | 76% on MRCR v2 (8-needle 1M variant) vs. 18.5% for Sonnet 4.5 | Same |
| Agentic coding | Highest score on Terminal-Bench 2.0 | Same |
| Pricing | Same as Opus 4.5: $5/$25 per million tokens; premium after 200K: $10/$37.50 | Same |
| Model ID | `claude-opus-4-6` | Same |

### 1.2 Task List System (January 2026)

The native Task List replaced the simpler TodoWrite-based tracking. Key properties from [code.claude.com/docs/en/interactive-mode](https://code.claude.com/docs/en/interactive-mode):

- **Automatic creation**: Claude creates task lists automatically during complex, multi-step work
- **Terminal display**: Toggle with `Ctrl+T`, shows up to 10 tasks with status indicators (pending/in-progress/completed)
- **Persistence**: Tasks persist across context compactions (stored on disk, not in conversation)
- **Cross-session sharing**: `CLAUDE_CODE_TASK_LIST_ID=<name> claude` shares a task list across sessions via `~/.claude/tasks/<name>/`
- **DAG dependencies**: Tasks can block other tasks; blocked tasks auto-unblock when dependencies complete
- **File locking**: Prevents race conditions when multiple agents claim the same task
- **Fallback**: Set `CLAUDE_CODE_ENABLE_TASKS=false` to revert to previous TODO list

### 1.3 Agent Teams (Experimental)

From [code.claude.com/docs/en/agent-teams](https://code.claude.com/docs/en/agent-teams):

- **Enable**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json or environment
- **Architecture**: Team lead (main session) + teammates (separate Claude Code instances) + shared task list + mailbox
- **Communication**: Teammates message each other directly (not just through lead); `message` (one-to-one) and `broadcast` (all)
- **Display modes**: In-process (default, Shift+Up/Down to navigate) or split panes (tmux/iTerm2)
- **Delegate mode**: Restricts lead to coordination-only tools (Shift+Tab to toggle)
- **Plan approval**: Teammates can be required to plan before implementing; lead approves/rejects
- **Limitations**: No session resumption with in-process teammates, one team per session, no nested teams, lead is fixed, split panes require tmux/iTerm2

### 1.4 Plugins & Marketplaces

From [code.claude.com/docs/en/features-overview](https://code.claude.com/docs/en/features-overview):

- **What**: Bundle skills, hooks, subagents, and MCP servers into a single installable plugin
- **Namespacing**: Plugin skills use `/<plugin-name>:<skill>` format to avoid conflicts
- **Distribution**: Via plugin marketplaces for cross-repository adoption
- **Status**: Available now, not experimental

### 1.5 Skills (Unified with Commands)

- `.claude/commands/` and `.claude/skills/` unified — both create `/<name>` commands
- If both exist for same name, skill takes precedence
- **Model-invocable**: Claude auto-loads based on task relevance (default)
- **User-only**: Set `disable-model-invocation: true` for zero context cost until manually invoked
- **Isolated execution**: `context: fork` runs skill in subagent context
- Skills in subagents are fully preloaded at launch (not on-demand)

### 1.6 MCP Tool Search

- Auto lazy-loads MCP tools when they exceed 10% of context window
- **85% reduction** in MCP tool context overhead
- Loads only 3-5 most relevant tools per task
- Requires Sonnet 4+ or Opus 4+ (not Haiku)
- Enable/disable: `ENABLE_TOOL_SEARCH=auto:5` or `false`

### 1.7 Other Notable Features

| Feature | Detail |
|---------|--------|
| Setup hooks | Triggered via `--init`, `--init-only`, `--maintenance` for project initialization |
| `--from-pr` | Resume sessions by PR number or URL |
| Browser integration | `--chrome` flag for Chrome control (beta) |
| Keybindings | Customizable via `~/.claude/keybindings.json` |
| PR status display | Clickable PR link in footer with color-coded review state |
| Prompt suggestions | Context-aware suggestions based on git history and conversation |

---

## 2. Architecture Document vs. Actual Codebase

### 2.1 Components Built but Not Documented

These are significant features that exist in the codebase with no corresponding section in ARCHITECTURE.md.

#### Governance MCP Server (Port 3103)

**Status**: Fully implemented. 698-line `server.py`, 10 tools, SQLite persistence, AI-powered review.

This is the single largest gap. The governance server provides:

- **Transactional decision review**: `submit_decision` blocks until verdict (approved/blocked/needs_human_review)
- **Plan review**: `submit_plan_for_review` reviews entire plans against standards
- **Completion review**: `submit_completion_review` verifies all decisions reviewed before task completion
- **Governed task pairs**: `create_governed_task` atomically creates implementation task blocked by review task
- **Multi-blocker support**: `add_review_blocker` stacks additional reviews (security, architecture, etc.)
- **AI review engine**: `reviewer.py` calls `claude --print` with governance-reviewer agent via temp file I/O pattern
- **KG integration**: `kg_client.py` reads JSONL directly for synchronous standard loading
- **Task file integration**: `task_integration.py` manipulates Claude Code's native task files for blocking/releasing

**Decision categories**: pattern_choice, component_design, api_design, deviation, scope_change
**Verdicts**: approved, blocked, needs_human_review (auto-assigned for deviation/scope_change)

#### Governance Reviewer Agent

**File**: `.claude/agents/governance-reviewer.md`
**Model**: Sonnet | **Tools**: Read, Glob, Grep, mcp:collab-kg (4 tools)

Called internally by the governance server via `claude --print` — not spawned by the orchestrator directly. Reviews decisions/plans through vision alignment and architectural conformance lenses.

#### Researcher Agent

**File**: `.claude/agents/researcher.md`
**Model**: Opus | **Tools**: Read, Glob, Grep, WebSearch, WebFetch, mcp:collab-kg, mcp:collab-governance (7 tools)

Two modes: periodic/maintenance (monitoring dependencies, detecting breaking changes) and exploratory/design (informing architectural decisions). Outputs change reports or research briefs to `.avt/research-briefs/`.

#### Project Steward Agent

**File**: `.claude/agents/project-steward.md`
**Model**: Sonnet | **Tools**: Read, Write, Edit, Glob, Grep, Bash, mcp:collab-kg (7 tools)

Maintains project hygiene: naming conventions, folder organization, documentation completeness, cruft detection. Periodic cadence: weekly (cruft), monthly (naming audit), quarterly (deep review).

#### E2E Testing Harness

**Location**: `e2e/` | **Scenarios**: 12 | **Assertions**: 172+ | **Execution**: Parallel with full isolation

Tests all 3 MCP servers across 11 scenarios (s01-s10, s12 — numbering skips s11): KG tier protection, governance decision flow, governed task lifecycle, vision violations, architecture deviations, quality gates, trust engine, multi-blocker tasks, scope change detection, completion guards, cross-server integration. Uses `GOVERNANCE_MOCK_REVIEW` to avoid live `claude` binary dependency. Generates unique projects from 8 domain templates.

#### Project Rules System

Configured in `.avt/project-config.json` with enforcement levels (enforce/prefer). Rules are injected into agent prompts at spawn time. Workers check project rules during startup; quality reviewer verifies compliance.

#### Extension: Setup Wizard, Tutorial, Governance Panel

The extension has evolved far beyond "observability only":

- **Setup wizard**: 10-step onboarding (Welcome, Vision docs, Architecture docs, Quality config, Rules, Permissions, Settings, Ingestion, Complete)
- **Workflow tutorial**: 9-step interactive guide
- **VS Code walkthrough**: 6-step native onboarding
- **Governance panel**: Governed tasks display, pending reviews, decision history
- **Research prompts panel**: Research prompt management UI
- **Document editor**: Claude CLI-based editor with auto-formatting
- **Agent enrichment**: Infers runtime state from governance data, pending reviews
- **3 MCP clients**: KnowledgeGraphClient, QualityClient, GovernanceClient

### 2.2 Components Described in ARCHITECTURE.md but Superseded or Not Built

| Component | In ARCHITECTURE.md | Actual Status |
|-----------|-------------------|---------------|
| Communication Hub Server (port 3100) | Described in "not building yet" section | Never built. Functionality distributed across governance server and native Task tool |
| Agent registry via Hub | Described | Replaced by filesystem detection in extension (scans `.claude/agents/*.md`) |
| SSE event stream | Described at `/events` | Not implemented — extension uses polling (10-second interval) |
| Inter-session messaging | Via `send_message`/`get_messages` | Replaced by governance transactional review model |
| SessionManagerService | Described in extension | Not implemented |
| WorktreeService | Described in extension | Not implemented as separate service |
| HubClient.ts | Described in extension `mcp/` | Does not exist |

### 2.3 Stale or Incorrect Information

| Item | ARCHITECTURE.md Says | Reality |
|------|---------------------|---------|
| Model | "Opus 4.5" throughout | Opus 4.6 (released Feb 5, 2026) |
| MCP server count | "only two MCP servers remain (KG + Quality)" | 3 servers: KG, Quality, Governance |
| Agent count | 3 (worker, quality-reviewer, kg-librarian) | 6 (+governance-reviewer, researcher, project-steward) |
| Extension role | "observability only" | Extensive: wizard, tutorial, document editor, governance panel, research prompts |
| KG tool count | 8 tools | 11 tools (added `delete_relations`, `ingest_documents`, `validate_tier_access`) |
| Worker agent tools | 8 tools (no governance) | 9 tools (includes `mcp:collab-governance`) |
| Worker protocol | Basic: read brief, query KG, implement, run gates | Extended: check project rules, create governed tasks, submit decisions, submit plans, submit completion review |
| Implementation phases | Phase 1-4 checklist (mostly unchecked) | All phases substantially completed; checklist is stale |
| File system layout | Shows files that don't exist | Actual layout has diverged significantly |
| Extension project structure | Lists non-existent files (`HubClient.ts`, `McpTransport.ts`, `Agent.ts`, etc.) | Different actual files and structure |

### 2.4 Summary Gap Table

| Category | ARCHITECTURE.md | Reality | Gap Severity |
|----------|----------------|---------|-------------|
| MCP servers | 2 (KG + Quality) | 3 (+Governance) | **Critical** — entire subsystem missing |
| Agents | 3 | 6 (+governance-reviewer, researcher, project-steward) | **Critical** — half the agents undocumented |
| Worker protocol | Basic KG + quality | +governance decisions, project rules, governed tasks | **High** — core workflow changed |
| Extension scope | "Observability only" | Wizard, tutorial, governance panel, 40+ components | **High** — understates by order of magnitude |
| Governance | Not mentioned | Full transactional system with 10 tools | **Critical** — not mentioned at all |
| E2E testing | Not mentioned | 11 scenarios, 172+ assertions | **High** — not mentioned at all |
| Task governance | Not mentioned | Blocked-from-birth pattern, multi-blocker | **Critical** — core system behavior |
| Model references | Opus 4.5 | Opus 4.6 | **Medium** — dated but not structurally wrong |
| Project rules | Not mentioned | Implemented with enforcement levels | **Medium** — operational feature missing |
| Research system | Not mentioned | Agent + prompts + briefs | **Medium** — operational feature missing |
| Implementation phases | Unchecked items | Substantially completed | **Low** — stale but informational |

---

## 3. Complete Tool Inventory (29 Tools Across 3 Servers)

### Knowledge Graph Server — Port 3101 (11 tools)

| # | Tool | Parameters | Purpose |
|---|------|-----------|---------|
| 1 | `create_entities` | entities: list[dict] | Create entities with tier protection |
| 2 | `create_relations` | relations: list[dict] | Create relations between entities |
| 3 | `add_observations` | entity_name, observations, callerRole, changeApproved | Add observations (tier-protected) |
| 4 | `search_nodes` | query: str | Full-text search across entities |
| 5 | `get_entity` | name: str | Retrieve entity with relations |
| 6 | `get_entities_by_tier` | tier: str | Get all entities at a protection tier |
| 7 | `delete_observations` | entity_name, observations, callerRole, changeApproved | Remove observations (tier-protected) |
| 8 | `delete_entity` | entity_name, callerRole | Delete entity (tier-protected) |
| 9 | `delete_relations` | relations: list[dict] | Delete specific relations |
| 10 | `ingest_documents` | folder: str, tier: str | Ingest markdown files into KG entities |
| 11 | `validate_tier_access` | entity_name, operation, callerRole | Check if operation is allowed |

**ARCHITECTURE.md listed 8 tools** — missing `delete_relations`, `ingest_documents`, `validate_tier_access`.

### Quality Server — Port 3102 (8 tools)

| # | Tool | Parameters | Purpose |
|---|------|-----------|---------|
| 1 | `auto_format` | files?, language? | Format code via ruff/prettier/etc. |
| 2 | `run_lint` | files?, language? | Lint code via ruff/eslint/etc. |
| 3 | `run_tests` | scope?, language? | Run test suites |
| 4 | `check_coverage` | language? | Check test coverage |
| 5 | `check_all_gates` | — | Aggregate all quality gates |
| 6 | `validate` | — | Comprehensive validation with summary |
| 7 | `get_trust_decision` | finding_id | Get trust engine classification |
| 8 | `record_dismissal` | finding_id, justification, dismissed_by | Record finding dismissal with audit trail |

**ARCHITECTURE.md listed 8 tools** — matches. Note: tool implementations still partially delegate to stubs rather than real subprocess calls.

### Governance Server — Port 3103 (10 tools) — NOT IN ARCHITECTURE.MD

| # | Tool | Parameters | Purpose |
|---|------|-----------|---------|
| 1 | `submit_decision` | task_id, agent, category, summary, detail, components_affected, alternatives_considered, confidence | Transactional decision review (blocks until verdict) |
| 2 | `submit_plan_for_review` | task_id, agent, plan_summary, plan_content, components_affected | Full plan review against standards |
| 3 | `submit_completion_review` | task_id, agent, summary_of_work, files_changed | Final governance check before completion |
| 4 | `get_decision_history` | task_id?, agent?, verdict? | Query past decisions and verdicts |
| 5 | `get_governance_status` | — | Dashboard overview (counts, recent activity) |
| 6 | `create_governed_task` | subject, description, context, review_type | Atomically create task pair (review blocks implementation) |
| 7 | `add_review_blocker` | implementation_task_id, review_type, context | Add additional review blocker to task |
| 8 | `complete_task_review` | review_task_id, verdict, guidance, findings, standards_verified | Complete review, potentially releasing task |
| 9 | `get_task_review_status` | implementation_task_id | Get review status and blockers |
| 10 | `get_pending_reviews` | — | List all pending reviews |

---

## 4. Agent Comparison Table

| Agent | Model | Tool Count | MCP Access | Role | In ARCHITECTURE.md? |
|-------|-------|-----------|------------|------|---------------------|
| **worker** | Opus | 9 | KG + Quality + Governance | Implement scoped tasks, submit decisions, create governed tasks | Partially (missing governance integration) |
| **quality-reviewer** | Opus | 6 | KG + Quality | Three-lens review (vision > architecture > quality) | Yes (mostly accurate) |
| **kg-librarian** | Sonnet | 5 | KG | Curate KG, consolidate, promote patterns, sync archival files | Yes (accurate) |
| **governance-reviewer** | Sonnet | 4 | KG | AI-powered decision/plan review (called via claude --print) | No |
| **researcher** | Opus | 7 | KG + Governance | Periodic monitoring + exploratory research | No |
| **project-steward** | Sonnet | 7 | KG | Project hygiene, naming, documentation, cruft detection | No |

---

## 5. Features Leveraged vs. Not Yet Leveraged

### Already Using

| Claude Code Feature | How We Use It |
|--------------------|---------------|
| Subagents via Task tool | 6 custom agents in `.claude/agents/` |
| MCP servers (SSE transport) | 3 servers registered in `.claude/settings.json` |
| PreToolUse hooks | ExitPlanMode → `verify-governance-review.sh` |
| Model routing per agent | Opus for worker/quality-reviewer/researcher, Sonnet for others |
| Skills | `/e2e` skill for E2E testing |
| Commands | `/project-overview` command |
| `CLAUDE_CODE_TASK_LIST_ID` | Referenced in CLAUDE.md for cross-session persistence |
| Git worktrees | Referenced in CLAUDE.md for worker isolation |

### Not Yet Leveraged

| Claude Code Feature | Opportunity | Effort | Priority |
|--------------------|-------------|--------|----------|
| **MCP Tool Search** | 85% context reduction for tool loading — pure config change | Trivial | **Immediate** |
| **Effort controls** | Optimize per-agent: `max` for worker, `medium` for librarian, `low` for steward | Trivial | **Immediate** |
| **Agent Teams** | Native multi-agent coordination could complement governance model | Evaluate | **Monitor** |
| **Plugins** | Package system for cross-project distribution | Medium | **Plan for later** |
| **Context compaction** | Longer-running orchestrator sessions | None (automatic) | **Immediate** |
| **1M context window** | Extended code reviews, larger session contexts | None (automatic) | **Immediate** |
| **Setup hooks** | `--init` / `--maintenance` for project initialization automation | Low | **Short-term** |
| **Skills (model-invocable)** | Convert common workflows to auto-loaded skills | Low | **Short-term** |
| **`--from-pr` flag** | PR-based session resumption | None | **Short-term** |
| **Delegate mode** | Restrict orchestrator to coordination-only (Agent Teams feature) | Evaluate | **Monitor** |
| **Plan approval** | Require teammate plan approval before implementation (Agent Teams feature) | Evaluate | **Monitor** |

---

## 6. Strategic Choices

These choices shape the forward-looking sections of ARCHITECTURE.md v2.

### Choice A: Agent Teams vs. Current Subagent + Governance Model

**Context**: Agent Teams (experimental) provides native multi-agent coordination with shared task lists, peer-to-peer messaging, delegate mode, and plan approval. Our system already has multi-agent coordination via subagents + governance transactional review.

**Comparison**:

| Aspect | Our Current Model | Agent Teams |
|--------|------------------|-------------|
| Task blocking | Governed tasks blocked from birth until review passes | DAG dependencies auto-block, but no governance review |
| Communication | Orchestrator routes all findings | Teammates message each other directly |
| Review model | Transactional: submit_decision blocks until verdict | Plan approval: lead approves/rejects teammate plans |
| Coordination | Orchestrator manages all work | Shared task list with self-coordination |
| Token cost | Lower (subagent results summarized) | Higher (each teammate = separate instance) |
| Governance guarantees | Strong (blocked-from-birth, multi-blocker) | None (no governance layer) |
| Session resumption | Yes (subagents are within session) | No (teammates lost on resume) |

**Recommendation: Monitor, don't adopt yet.**

Agent Teams is experimental with significant limitations. Our governance model provides guarantees (blocked-from-birth, multi-blocker, transactional review) that Agent Teams does not. However, several Agent Teams concepts align with our architecture:
- **Delegate mode** maps to our orchestrator pattern (coordination, not implementation)
- **Shared task list** maps to our governed task system
- **Plan approval** maps to our governance review

When Agent Teams stabilizes, it could serve as the coordination layer while governance remains the policy layer — similar to our recommended Task List framing (see Choice B).

**Document in ARCHITECTURE.md v2 as**: "Platform feature under evaluation. Aligns conceptually with our orchestration model. When stable, may replace custom subagent coordination while governance remains the policy layer."

### Choice B: Native Task List as Transport + Governance as Policy

**Context**: The native Task List provides DAG dependencies, file locking, cross-session persistence, and automatic unblocking. Our `task_integration.py` already manipulates the Claude Code task file system directly. These are complementary layers.

**Recommendation: Adopt this framing.**

- **Task List = infrastructure layer**: persistence, DAG, file locking, cross-session coordination
- **Governance = policy layer**: whether a task should proceed, what reviews are required, what standards apply
- `create_governed_task` creates tasks in the native system with governance review blockers
- `complete_task_review` removes blockers in the native system when reviews pass
- `CLAUDE_CODE_TASK_LIST_ID` enables the shared namespace

This is already how the system works — `task_integration.py` reads and writes Claude Code's native task files. The architecture document should formalize this two-layer framing.

### Choice C: Plugin Packaging

**Context**: Claude Code now supports packaging skills, hooks, subagents, and MCP servers as distributable plugins.

**Assessment**: Our system has natural plugin boundaries:
- 3 MCP servers (Python packages)
- 6 agent definitions (markdown files)
- 1 skill (`/e2e`), 1 command (`/project-overview`)
- 1 hook (governance review verification)
- VS Code extension (separate distribution)

**Recommendation: Plan for it, don't build yet.** The system's APIs are still maturing (Quality server has stubs, governance review protocol may evolve). Document as a milestone in the architecture's evolution path.

### Choice D: MCP Tool Search

**Context**: Auto lazy-loads MCP tools when they exceed 10% of context, providing 85% context reduction.

**Recommendation: Adopt immediately.** Pure configuration change, no code needed. Our agents access 4-9 tools each; lazy loading will reduce startup context significantly.

---

## 7. Recommendations by Priority

### Immediate (No Code Changes)

1. **Enable MCP Tool Search** — configuration change in `.claude/settings.json`
2. **Update model references** — Opus 4.5 → Opus 4.6 throughout CLAUDE.md and documentation
3. **Leverage effort controls** — set effort levels per agent role in agent definitions
4. **Context compaction and 1M context** — available automatically with Opus 4.6

### Short-term (Part of Architecture Update)

5. **Write ARCHITECTURE.md v2** — comprehensive document reflecting actual system state (3 servers, 6 agents, governance, E2E testing, extension evolution)
6. **Formalize Task List + Governance layering** — document the two-layer model (infrastructure + policy)
7. **Convert common workflows to skills** — identify orchestrator patterns that could be model-invocable skills
8. **Add setup hooks** — `--init` for project initialization, `--maintenance` for periodic tasks

### Medium-term (Post Architecture Update)

9. **Replace Quality server stubs** — connect `auto_format`, `run_lint`, `run_tests`, `check_coverage` to real subprocess calls
10. **Plugin packaging evaluation** — assess API stability, define plugin boundaries
11. **Agent Teams evaluation** — monitor experimental status; prototype when session resumption is fixed

### Future (Requires Platform Maturation)

12. **Cross-project memory** — KG entities that travel between projects
13. **Multi-team coordination** — when Agent Teams supports nested teams
14. **Plugin distribution** — publish to a marketplace when system is stable
15. **Browser integration** — explore for automated testing or UI review workflows

---

## 8. ARCHITECTURE.md v2 — Proposed Section Outline

The new document should retain the strong organizational structure of v1 but update every section to match reality.

| # | Section | Key Changes from v1 |
|---|---------|-------------------|
| 1 | System Boundaries and Glossary | Remove Hub; add Governance, governed tasks, project rules, researcher, steward |
| 2 | System Overview | 3 servers, 6 agents; new diagram; governance reviewer called by server |
| 3 | Claude Code as Orchestration Platform | Update for Task List, Agent Teams (monitoring), Plugins, Skills, effort controls |
| 4 | Knowledge Graph MCP Server | 11 tools (add 3 new); document ingestion pipeline |
| 5 | Quality MCP Server | 8 tools; note partial stub status; specialist routing |
| 6 | **Governance MCP Server** (NEW) | Full 10-tool interface, SQLite schema, AI review pipeline, task integration |
| 7 | Custom Subagent Definitions | All 6 agents with YAML frontmatter, model, tools, protocols |
| 8 | **Governance Architecture** (NEW) | Transactional review, governed tasks, multi-blocker, "Intercept Early Redirect Early" |
| 9 | CLAUDE.md Orchestration | Updated protocols: governance decisions, project rules, research |
| 10 | VS Code Extension | Actual scope: wizard, tutorial, governance panel, 3 MCP clients, 40+ components |
| 11 | File System Layout | Actual layout including `.avt/`, `e2e/`, `docs/`, `scripts/` |
| 12 | Data Flow Architecture | Governance flow, research flow, project hygiene flow (new); updated task flow |
| 13 | **E2E Testing Architecture** (NEW) | 11 scenarios, domain generation, parallel execution, mock review |
| 14 | **Research System** (NEW) | Researcher agent, dual-mode, research prompts/briefs |
| 15 | **Project Rules System** (NEW) | project-config.json, enforcement levels, agent scope filtering |
| 16 | Technology Stack | Opus 4.6, Task List, Agent Teams (monitoring), Plugins (planned) |
| 17 | Current Status and Evolution Path | Replace stale "Implementation Phases" with actual status + roadmap |
| 18 | Verification | E2E harness, component verification, integration verification |

---

## Appendix A: Extension Component Inventory

### Dashboard React Components (webview-dashboard/src/)

**Core Layout**: App.tsx, DashboardContext.tsx, SetupBanner.tsx, SessionBar.tsx
**Agent & Activity**: AgentCards.tsx, ActivityFeed.tsx, ActivityEntry.tsx, TaskBoard.tsx
**Governance**: GovernancePanel.tsx, GovernanceItem.tsx
**Settings & Config**: SettingsPanel.tsx, ResearchPromptsPanel.tsx

**Setup Wizard** (10 steps): WelcomeStep, VisionDocsStep, ArchitectureDocsStep, QualityConfigStep, RulesStep, PermissionsStep, SettingsStep, IngestionStep, CompleteStep, DocEditorCard

**Workflow Tutorial** (9 steps): WelcomeStep, BigPictureStep, SetupStep, StartingWorkStep, BehindScenesStep, MonitoringStep, KnowledgeGraphStep, QualityGatesStep, TipsStep, ReadyStep

**Shared**: WizardStepIndicator.tsx, TutorialStepIndicator.tsx, WorkflowTutorial.tsx, SetupWizard.tsx

### Extension Backend (extension/src/)

**Providers**: DashboardWebviewProvider, MemoryTreeProvider, FindingsTreeProvider, TasksTreeProvider, ActionsTreeProvider
**MCP Clients**: KnowledgeGraphClient, QualityClient, GovernanceClient
**Services**: McpClientService, McpServerManager, FileWatcherService, StatusBarService, ProjectConfigService
**Commands**: systemCommands, taskCommands, memoryCommands
**Models**: Entity, Finding, Task, Activity, ProjectConfig, Message, ResearchPrompt

## Appendix B: Governance Server Internal Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Agent calls submit_decision() / submit_plan_for_review()       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ server.py                                                        │
│  1. Store decision in SQLite (store.py)                          │
│  2. Auto-flag deviation/scope_change for human review            │
│  3. Load vision standards from KG (kg_client.py reads JSONL)     │
│  4. Load architecture entities from KG                           │
│  5. Call reviewer.review_decision() / review_plan()              │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ reviewer.py (GovernanceReviewer)                                 │
│  1. Build prompt: decision + standards → JSON response expected  │
│  2. Write prompt to temp file (mkstemp)                          │
│  3. Run: claude --print --agent governance-reviewer < tempfile   │
│  4. Read response from output temp file                          │
│  5. Parse JSON into ReviewVerdict                                │
│  6. Cleanup temp files in finally block                          │
│  (Mock mode: GOVERNANCE_MOCK_REVIEW returns deterministic OK)    │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ Back in server.py                                                │
│  6. Store review verdict in SQLite                               │
│  7. Record decision in KG (kg_client.record_decision)            │
│  8. Return verdict to calling agent                              │
└──────────────────────────────────────────────────────────────────┘
```

## Appendix C: Governed Task Lifecycle

```
create_governed_task("Implement auth", review_type="governance")
    │
    ├─→ Review Task (review-abc)          Implementation Task (impl-xyz)
    │   status: pending                    status: pending
    │   blocks: [impl-xyz]                 blockedBy: [review-abc]
    │                                      ❌ CANNOT EXECUTE
    │
    ▼ (Governance review runs)
    │
    ├─ If add_review_blocker(impl-xyz, "security"):
    │   New Review Task (review-def)
    │   impl-xyz blockedBy: [review-abc, review-def]
    │   ❌ STILL CANNOT EXECUTE
    │
    ▼ complete_task_review(review-abc, verdict="approved")
    │   Remove review-abc from impl-xyz.blockedBy
    │   impl-xyz blockedBy: [review-def]
    │   ❌ STILL CANNOT EXECUTE (one blocker remains)
    │
    ▼ complete_task_review(review-def, verdict="approved")
    │   Remove review-def from impl-xyz.blockedBy
    │   impl-xyz blockedBy: []
    │   ✅ CAN NOW EXECUTE
    │
    ▼ Worker picks up impl-xyz
        │
        ├─ submit_decision() for key choices (blocks until verdict)
        ├─ Implement within scope
        ├─ submit_plan_for_review() before presenting plan
        ├─ check_all_gates() via Quality server
        └─ submit_completion_review() before reporting done
```
