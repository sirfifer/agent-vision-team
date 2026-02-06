## 9. CLAUDE.md Orchestration

The root `CLAUDE.md` is the orchestrator's instruction set. Claude Code reads it at session start and follows it as the primary directive for coordinating subagents, enforcing governance, and managing institutional memory. This section summarizes the key protocols it defines.

### 9.1 Task Decomposition

When given a complex task, the orchestrator:

1. **Breaks it down** into discrete, scopeable units of work
2. **Writes task briefs** as structured markdown in `.avt/task-briefs/`
3. **Creates isolation** via git worktrees (`git worktree add ../project-worker-N -b task/NNN-description`)
4. **Spawns workers** using the Task tool, one per task brief
5. **Reviews work** by spawning the quality-reviewer subagent with the worker's diff
6. **Routes findings** back to workers for resolution
7. **Merges and cleans up** when all findings are resolved and quality gates pass

### 9.2 Task Governance Protocol

The system follows an "Intercept Early, Redirect Early" principle. Every implementation task is **blocked from birth** until governance review approves it.

**Key rule**: Never use `TaskCreate` directly. Instead, use the Governance MCP server:

```
create_governed_task(
    subject: "Implement authentication service",
    description: "Create JWT-based auth with refresh tokens",
    context: "Part of user management epic",
    review_type: "governance"
)
```

This atomically creates two linked tasks:
1. A **review task** (`[GOVERNANCE] Review: ...`) with `status: pending`
2. An **implementation task** (`Implement ...`) with `blockedBy: [review-task-id]`

The flow is strictly sequential:

```
create_governed_task() --> Review task (pending) blocks Implementation task
                       --> Governance review runs
                       --> complete_task_review(verdict: "approved" | "blocked")
                       --> If approved and last blocker: Implementation task unblocks
                       --> Worker picks up task
```

Additional blockers can be stacked via `add_review_blocker()` (e.g., security review on top of governance review). All blockers must complete before the task becomes available.

### 9.3 Quality Review Protocol

After any significant code change:

1. Spawn the **quality-reviewer** subagent with the diff context
2. Review findings **by tier** (vision first, then architecture, then quality):
   - **Vision conflicts**: Stop all related work and address immediately
   - **Architecture findings**: Route to worker with context, require resolution
   - **Quality findings**: Route to worker; auto-fixable issues can be fixed inline
3. Verify resolution before proceeding

### 9.4 Project Rules Protocol

Project rules are concise behavioral guidelines injected into every agent's context at spawn time. Rules live in `.avt/project-config.json` (not in CLAUDE.md) and are configured via the setup wizard.

Each rule has:
- **Enforcement level**: `enforce` (must follow), `prefer` (explain if deviating), or `guide` (advisory)
- **Scope**: Which agent roles receive the rule (e.g., `worker`, `quality-reviewer`, `all`)
- **Category**: `testing`, `code-quality`, `security`, `performance`, `patterns`, `workflow`, `custom`

At spawn time, the orchestrator compiles enabled rules into a compact preamble (~200-400 tokens) and prepends it to the task prompt. Only rules matching the agent's scope are injected. Rationale is not injected -- agents that need deeper context query the KG via `search_nodes("project rules")`.

### 9.5 Memory Protocol

**Before starting work**, query the Knowledge Graph for context:
- `get_entities_by_tier("vision")` -- load all vision constraints
- `search_nodes("<component name>")` -- find architectural patterns and past solutions
- `search_nodes("<task type> pattern")` -- check for solution patterns matching the task type

**After completing work**, spawn the **kg-librarian** subagent to curate observations. The librarian consolidates redundant observations, promotes recurring solutions to patterns, removes stale entries, and syncs important entries to archival files in `.avt/memory/`.

### 9.6 Research Protocol

The researcher subagent gathers intelligence in two modes:

| Mode | Purpose | Output | Model |
|------|---------|--------|-------|
| **Periodic/Maintenance** | Monitor APIs, frameworks, dependencies for breaking changes, deprecations, or new features | Change reports | Sonnet (straightforward monitoring) |
| **Exploratory/Design** | Deep investigation before architectural decisions, technology comparisons, unfamiliar domains | Research briefs | Opus (complex, novel analysis) |

Research prompts are defined in `.avt/research-prompts/` and managed via the dashboard or manually. Completed research is stored in `.avt/research-briefs/`. The orchestrator references research briefs in task briefs when spawning workers.

### 9.7 Project Hygiene Protocol

The **project-steward** subagent performs periodic reviews:
- **Weekly**: Cruft detection (unused files, duplicates, dead links)
- **Monthly**: Naming convention audits across files, directories, variables, and types
- **Quarterly**: Deep reviews of folder organization, documentation completeness, and consistency

The steward also runs before releases (ensuring project files are complete) and after major refactoring (verifying organization still makes sense).

### 9.8 Checkpoints and Drift Detection

**Checkpoints** combine session state updates (`session-state.md`) with git tags (`checkpoint-NNN`). After each meaningful unit of work, the orchestrator writes progress and tags the state, enabling resume from the last known-good point after a failure.

**Drift detection** monitors four failure patterns:

| Pattern | Signal | Response |
|---------|--------|----------|
| **Time drift** | Worker on a single task too long without progress | Stop and reassess |
| **Loop drift** | Repeated failures on the same issue | Stop and change approach |
| **Scope drift** | Work outside the task brief's defined scope | Stop and refocus |
| **Quality drift** | Findings accumulating faster than resolution | Stop and prioritize resolution |

### 9.9 No Silent Dismissals

The trust engine enforces a key audit principle: every dismissed finding requires justification. When a finding is deemed not applicable, it must be dismissed via `record_dismissal(finding_id, justification, dismissed_by)`. This creates an audit trail. Future occurrences of the same finding are tracked, not blocked.

---

## 10. VS Code Extension

The Collab Intelligence VS Code extension has evolved significantly beyond the original "observability only" scope. It now provides setup wizards, interactive tutorials, document authoring with AI-assisted formatting, governance management, research prompt management, and a comprehensive React-based dashboard -- all while coexisting cleanly with the Claude Code extension.

### 10.1 Extension Capabilities

The extension provides these major capabilities:

| Capability | Description |
|------------|-------------|
| **Setup Wizard** | 9-step interactive onboarding: welcome, vision docs, architecture docs, quality config, rules, permissions, settings, KG ingestion, completion |
| **Workflow Tutorial** | 10-step interactive guide: welcome, big picture, setup, starting work, behind the scenes, monitoring, knowledge graph, quality gates, tips, ready |
| **VS Code Walkthrough** | Native walkthrough (`avt-getting-started`) with 6 steps covering system overview, three-tier hierarchy, agent team, work cycle, institutional memory, and project setup |
| **Dashboard Webview** | React/Tailwind single-page application showing session status, agent cards, governance panel, governed tasks, activity feed, and setup readiness banner |
| **Governance Panel** | Displays governed tasks, pending reviews, decision history, and governance statistics within the dashboard |
| **Research Prompts Panel** | CRUD management for periodic and exploratory research prompts, with schedule configuration |
| **Document Editor** | Claude CLI-based auto-formatting for vision and architecture documents. Uses temp-file I/O pattern: user drafts content, extension formats via `claude --print`, user reviews and saves |
| **Memory Browser** | TreeView displaying KG entities grouped by protection tier (vision/architecture/quality) with observation and relation details |
| **Findings Panel** | TreeView displaying quality findings grouped by tier, with VS Code diagnostic integration |
| **Tasks Panel** | TreeView displaying task briefs with status indicators |
| **Actions Panel** | TreeView with welcome content providing quick-action buttons: Open Dashboard, Connect to Servers, Setup Wizard, Workflow Tutorial |
| **Status Bar** | Two status bar items showing system health (active/warning/error/inactive) and summary (workers, findings, phase) |
| **MCP Server Manager** | Spawns and manages all 3 MCP server processes (`uv run python -m ...`), with port readiness polling and auto-start on activation |
| **3 MCP Clients** | `KnowledgeGraphClient`, `QualityClient`, `GovernanceClient` -- typed wrappers over SSE connections to the same 3 servers that Claude Code uses |

### 10.2 Extension Backend

The extension backend is organized into five layers:

**Providers** (`extension/src/providers/`):

| File | Class | Purpose |
|------|-------|---------|
| `DashboardWebviewProvider.ts` | `DashboardWebviewProvider` | Manages the React webview panel. Handles message passing between extension host and webview, data aggregation, setup wizard triggers, tutorial triggers, and document formatting via Claude CLI |
| `FindingsTreeProvider.ts` | `FindingsTreeProvider` | TreeDataProvider for quality findings, grouped by tier with diagnostic collection integration |
| `TasksTreeProvider.ts` | `TasksTreeProvider` | TreeDataProvider for task briefs with status-based icons |
| `MemoryTreeProvider.ts` | `MemoryTreeProvider` | TreeDataProvider for KG entities, grouped by protection tier |

**Services** (`extension/src/services/`):

| File | Class | Purpose |
|------|-------|---------|
| `McpClientService.ts` | `McpClientService` | SSE-based MCP protocol client. Manages persistent connections to all 3 servers. Handles JSON-RPC 2.0 over SSE with session ID management, request/response correlation, and structured content parsing |
| `McpServerManager.ts` | `McpServerManager` | Spawns MCP server child processes via `uv run python -m <module>`. Polls port readiness with configurable timeout (15s). Detects already-running servers |
| `FileWatcherService.ts` | `FileWatcherService` | Watches `.avt/task-briefs/**` and `.avt/session-state.md` for filesystem changes, emitting events to refresh tree views and dashboard |
| `StatusBarService.ts` | `StatusBarService` | Manages two status bar items (health indicator + summary). Both click through to the dashboard |
| `ProjectConfigService.ts` | `ProjectConfigService` | Reads/writes `.avt/project-config.json` with atomic writes (write to `.tmp`, then rename). Manages folder structure creation, vision/architecture document CRUD, research prompt CRUD with YAML file generation, permission syncing to `.claude/settings.local.json`, and setup readiness assessment |

**MCP Clients** (`extension/src/mcp/`):

| File | Class | Target Server |
|------|-------|--------------|
| `KnowledgeGraphClient.ts` | `KnowledgeGraphClient` | KG server (:3101) -- `create_entities`, `create_relations`, `add_observations`, `search_nodes`, `get_entity`, `get_entities_by_tier`, `validate_tier_access`, `ingest_documents` |
| `QualityClient.ts` | `QualityClient` | Quality server (:3102) -- `auto_format`, `run_lint`, `run_tests`, `check_coverage`, `check_all_gates`, `validate`, `get_trust_decision`, `record_dismissal` |
| `GovernanceClient.ts` | `GovernanceClient` | Governance server (:3103) -- `get_governance_status`, `get_decision_history`, `get_pending_reviews`, `get_task_review_status` |

**Models** (`extension/src/models/`):

| File | Key Types |
|------|-----------|
| `Activity.ts` | `AgentStatus`, `ActivityEntry`, `GovernedTask`, `GovernanceStats`, `TaskReviewInfo` |
| `Entity.ts` | `Entity`, `Relation`, `ProtectionTier`, `EntityType` |
| `Finding.ts` | `Finding`, `FindingPayload`, `Tier`, `Severity` |
| `Task.ts` | `Task`, `TaskStatus` |
| `ProjectConfig.ts` | `ProjectConfig`, `SetupReadiness`, `RuleEntry`, `RulesConfig`, `PermissionEntry`, `QualityConfig`, plus default rules, default permissions, and optional rules |
| `ResearchPrompt.ts` | `ResearchPrompt`, `ResearchSchedule`, `ResearchResult`, plus `toPromptYaml()` serializer |
| `Message.ts` | Extension/webview message types |

**Commands** (`extension/src/commands/`):

| File | Commands |
|------|----------|
| `systemCommands.ts` | `collab.startSystem`, `collab.stopSystem` |
| `memoryCommands.ts` | `collab.searchMemory` |
| `taskCommands.ts` | `collab.createTaskBrief` |

Additional commands registered directly in `extension.ts`: `collab.connectMcpServers`, `collab.refreshMemory`, `collab.refreshFindings`, `collab.refreshTasks`, `collab.viewDashboard`, `collab.openSetupWizard`, `collab.openWalkthrough`, `collab.openWorkflowTutorial`, `collab.runResearch`, `collab.validateAll`, `collab.ingestDocuments`.

### 10.3 Dashboard Components

The dashboard is a React + Tailwind CSS application built with Vite, rendered inside a VS Code webview panel titled "Agent Operations Center."

**Application Shell** (`extension/webview-dashboard/src/`):

| File | Purpose |
|------|---------|
| `App.tsx` | Root layout: `SessionBar` + `SetupBanner` + `ConnectionBanner` + `AgentCards` + split pane (`GovernancePanel` left 2/5, tabbed `TaskBoard`/`ActivityFeed` right 3/5) + overlay modals (`SetupWizard`, `SettingsPanel`, `ResearchPromptsPanel`, `WorkflowTutorial`) |
| `context/DashboardContext.tsx` | React context providing dashboard state, VS Code API bridge, wizard/settings/tutorial visibility toggles, document format results, research prompt state |
| `hooks/useVsCodeApi.ts` | Hook wrapping the `acquireVsCodeApi()` bridge for message posting |
| `hooks/useDocEditor.ts` | State machine hook for document authoring: `idle` -> `drafting` -> `formatting` -> `reviewing` -> `saving`, with error recovery |
| `types.ts` | Shared type definitions mirroring extension backend models |

**Main Dashboard Components** (`extension/webview-dashboard/src/components/`):

| File | Component | Purpose |
|------|-----------|---------|
| `SessionBar.tsx` | `SessionBar` | Top bar showing session phase, task counts, connection status, and action buttons (Settings, Research, Wizard, Tutorial, Refresh) |
| `SetupBanner.tsx` | `SetupBanner` | Conditional banner shown when setup is incomplete, with readiness checklist and "Run Setup Wizard" button |
| `AgentCards.tsx` | `AgentCards` | Horizontal row of cards showing each agent's status (active/idle/blocked/reviewing/not-configured) with current task info |
| `GovernancePanel.tsx` | `GovernancePanel` | Left panel showing governance stats counters, vision standards list, and architectural elements list |
| `GovernanceItem.tsx` | `GovernanceItem` | Individual governance entity display with observations |
| `TaskBoard.tsx` | `TaskBoard` | Governed task list with review status badges and blocker indicators |
| `ActivityFeed.tsx` | `ActivityFeed` | Chronological activity log with agent/type/governance filtering |
| `ActivityEntry.tsx` | `ActivityEntry` | Individual activity entry with tier-colored badges |
| `SettingsPanel.tsx` | `SettingsPanel` | Modal overlay for editing project settings post-wizard |
| `ResearchPromptsPanel.tsx` | `ResearchPromptsPanel` | Modal overlay for creating, editing, deleting, and running research prompts |

**Setup Wizard** (`extension/webview-dashboard/src/components/wizard/`):

| File | Purpose |
|------|---------|
| `SetupWizard.tsx` | 9-step wizard container with navigation, step validation, and config persistence |
| `WizardStepIndicator.tsx` | Visual step progress indicator with completion state |

Wizard steps (in order):

| Step | Component | What It Configures |
|------|-----------|-------------------|
| 1. Welcome | `WelcomeStep.tsx` | Introduction and language selection |
| 2. Vision Docs | `VisionDocsStep.tsx` | Create/edit vision standard documents with AI-assisted formatting via `DocEditorCard` |
| 3. Architecture Docs | `ArchitectureDocsStep.tsx` | Create/edit architecture documents with AI-assisted formatting via `DocEditorCard` |
| 4. Quality Config | `QualityConfigStep.tsx` | Test, lint, build, and format commands per language |
| 5. Rules | `RulesStep.tsx` | Enable/disable project rules with enforcement levels and agent scopes |
| 6. Permissions | `PermissionsStep.tsx` | Claude Code permission allowlist (recommended + optional) synced to `.claude/settings.local.json` |
| 7. Settings | `SettingsStep.tsx` | Quality gate toggles, coverage threshold, mock test policies, auto-governance, KG auto-curation |
| 8. Ingestion | `IngestionStep.tsx` | Ingest vision and architecture documents into the Knowledge Graph |
| 9. Complete | `CompleteStep.tsx` | Summary and next-steps guidance |

The `DocEditorCard.tsx` component provides the document authoring workflow: the user writes or pastes raw content, clicks "Format," which sends the content to the extension backend for Claude CLI formatting (`claude --print`), then the user reviews and saves.

**Workflow Tutorial** (`extension/webview-dashboard/src/components/tutorial/`):

| File | Purpose |
|------|---------|
| `WorkflowTutorial.tsx` | 10-step tutorial container with navigation |
| `TutorialStepIndicator.tsx` | Visual step progress indicator |

Tutorial steps (in order):

| Step | Component | Topic |
|------|-----------|-------|
| 1. Welcome | `WelcomeStep.tsx` | What the system does and why |
| 2. Big Picture | `BigPictureStep.tsx` | Three-tier hierarchy and agent roles |
| 3. Run Setup | `SetupStep.tsx` | How to run the setup wizard (with launch button) |
| 4. Start Work | `StartingWorkStep.tsx` | Task decomposition and governed task flow |
| 5. Behind the Scenes | `BehindScenesStep.tsx` | What happens when agents execute (governance, quality gates) |
| 6. Monitoring | `MonitoringStep.tsx` | Using the dashboard to monitor agent activity |
| 7. Knowledge Graph | `KnowledgeGraphStep.tsx` | How institutional memory works |
| 8. Quality Gates | `QualityGatesStep.tsx` | Build, lint, test, coverage, and findings gates |
| 9. Tips | `TipsStep.tsx` | Best practices and common patterns |
| 10. Ready | `ReadyStep.tsx` | Summary and getting started |

**Shared UI** (`extension/webview-dashboard/src/components/ui/`):

| File | Component | Purpose |
|------|-----------|---------|
| `WarningDialog.tsx` | `WarningDialog` | Reusable confirmation dialog for destructive actions |

### 10.4 Coexistence with Claude Code Extension

The Collab Intelligence extension and the Claude Code extension serve complementary roles and are designed to run simultaneously without conflict:

| Concern | Collab Intelligence Extension | Claude Code Extension |
|---------|-------------------------------|----------------------|
| AI interaction (prompting, code generation) | No | Yes |
| System monitoring and dashboards | Yes | No |
| Finding display and triage | Yes | No |
| Memory browsing (KG entities) | Yes | No |
| Setup and onboarding | Yes | No |
| Governance management (task review status) | Yes | No |
| Research prompt management | Yes | No |
| MCP server lifecycle (start/stop) | Yes | Uses servers when running |
| Document authoring with AI formatting | Yes (via `claude --print`) | No |
| Code editing and tool execution | No | Yes |

The extension connects to the same 3 MCP servers as Claude Code, using the same SSE transport on the same ports (3101, 3102, 3103). Both can be connected simultaneously. The extension uses read-heavy operations (status queries, entity browsing, decision history) while Claude Code agents perform write-heavy operations (creating entities, submitting decisions, running quality gates).

---

## 11. File System Layout

### Product Repository

The following layout is verified against the actual filesystem:

```
agent-vision-team/
├── .claude/
│   ├── agents/                              # 6 custom subagent definitions
│   │   ├── worker.md
│   │   ├── quality-reviewer.md
│   │   ├── kg-librarian.md
│   │   ├── governance-reviewer.md
│   │   ├── researcher.md
│   │   └── project-steward.md
│   ├── collab/                              # Persistent data stores (legacy location)
│   │   ├── memory/
│   │   │   ├── architectural-decisions.md
│   │   │   ├── solution-patterns.md
│   │   │   └── troubleshooting-log.md
│   │   ├── session-state.md
│   │   └── task-briefs/
│   │       └── example-001-add-feature.md
│   ├── commands/
│   │   └── project-overview.md              # Slash command definition
│   ├── skills/
│   │   └── e2e.md                           # /e2e skill definition
│   ├── settings.json                        # Claude Code hooks and config
│   └── settings.local.json                  # Permission allowlist (synced by wizard)
│
├── .avt/                                    # Agent Vision Team system config
│   ├── task-briefs/
│   │   └── example-001-add-feature.md
│   ├── session-state.md                     # Current session progress
│   ├── memory/                              # Archival memory files (synced by KG Librarian)
│   │   ├── architectural-decisions.md
│   │   ├── research-findings.md
│   │   ├── solution-patterns.md
│   │   └── troubleshooting-log.md
│   ├── research-prompts/
│   │   └── README.md
│   ├── research-briefs/
│   │   └── README.md
│   └── project-config.json                  # Project configuration (managed by wizard)
│
├── extension/                               # VS Code extension
│   ├── src/
│   │   ├── extension.ts                     # Activation entry point
│   │   ├── providers/
│   │   │   ├── DashboardWebviewProvider.ts
│   │   │   ├── FindingsTreeProvider.ts
│   │   │   ├── MemoryTreeProvider.ts
│   │   │   └── TasksTreeProvider.ts
│   │   ├── services/
│   │   │   ├── McpClientService.ts
│   │   │   ├── McpServerManager.ts
│   │   │   ├── FileWatcherService.ts
│   │   │   ├── StatusBarService.ts
│   │   │   └── ProjectConfigService.ts
│   │   ├── mcp/
│   │   │   ├── KnowledgeGraphClient.ts
│   │   │   ├── QualityClient.ts
│   │   │   └── GovernanceClient.ts
│   │   ├── commands/
│   │   │   ├── systemCommands.ts
│   │   │   ├── memoryCommands.ts
│   │   │   └── taskCommands.ts
│   │   ├── models/
│   │   │   ├── Activity.ts
│   │   │   ├── Entity.ts
│   │   │   ├── Finding.ts
│   │   │   ├── Task.ts
│   │   │   ├── ProjectConfig.ts
│   │   │   ├── ResearchPrompt.ts
│   │   │   └── Message.ts
│   │   ├── test/
│   │   │   ├── index.ts
│   │   │   ├── KnowledgeGraphClient.test.ts
│   │   │   ├── McpClientService.test.ts
│   │   │   ├── MemoryTreeProvider.test.ts
│   │   │   └── QualityClient.test.ts
│   │   └── utils/
│   │       ├── config.ts
│   │       └── logger.ts
│   ├── webview-dashboard/
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── main.tsx
│   │   │   ├── index.css
│   │   │   ├── types.ts
│   │   │   ├── context/
│   │   │   │   └── DashboardContext.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useVsCodeApi.ts
│   │   │   │   └── useDocEditor.ts
│   │   │   └── components/
│   │   │       ├── SessionBar.tsx
│   │   │       ├── SetupBanner.tsx
│   │   │       ├── AgentCards.tsx
│   │   │       ├── GovernancePanel.tsx
│   │   │       ├── GovernanceItem.tsx
│   │   │       ├── TaskBoard.tsx
│   │   │       ├── ActivityFeed.tsx
│   │   │       ├── ActivityEntry.tsx
│   │   │       ├── SettingsPanel.tsx
│   │   │       ├── ResearchPromptsPanel.tsx
│   │   │       ├── ui/
│   │   │       │   └── WarningDialog.tsx
│   │   │       ├── wizard/
│   │   │       │   ├── SetupWizard.tsx
│   │   │       │   ├── WizardStepIndicator.tsx
│   │   │       │   └── steps/
│   │   │       │       ├── WelcomeStep.tsx
│   │   │       │       ├── VisionDocsStep.tsx
│   │   │       │       ├── ArchitectureDocsStep.tsx
│   │   │       │       ├── QualityConfigStep.tsx
│   │   │       │       ├── RulesStep.tsx
│   │   │       │       ├── PermissionsStep.tsx
│   │   │       │       ├── SettingsStep.tsx
│   │   │       │       ├── IngestionStep.tsx
│   │   │       │       ├── CompleteStep.tsx
│   │   │       │       └── DocEditorCard.tsx
│   │   │       └── tutorial/
│   │   │           ├── WorkflowTutorial.tsx
│   │   │           ├── TutorialStepIndicator.tsx
│   │   │           └── steps/
│   │   │               ├── WelcomeStep.tsx
│   │   │               ├── BigPictureStep.tsx
│   │   │               ├── SetupStep.tsx
│   │   │               ├── StartingWorkStep.tsx
│   │   │               ├── BehindScenesStep.tsx
│   │   │               ├── MonitoringStep.tsx
│   │   │               ├── KnowledgeGraphStep.tsx
│   │   │               ├── QualityGatesStep.tsx
│   │   │               ├── TipsStep.tsx
│   │   │               └── ReadyStep.tsx
│   │   ├── dist/
│   │   │   └── index.html
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.js
│   │   └── postcss.config.js
│   ├── media/
│   │   ├── icons/
│   │   │   └── collab.svg                   # Activity bar icon
│   │   └── walkthrough/                     # Native walkthrough markdown
│   │       ├── 01-welcome.md
│   │       ├── 02-three-tiers.md
│   │       ├── 03-agents.md
│   │       ├── 04-work-cycle.md
│   │       ├── 05-knowledge-graph.md
│   │       └── 06-setup.md
│   ├── package.json                         # Extension manifest
│   ├── tsconfig.json
│   ├── esbuild.config.js
│   └── README.md
│
├── mcp-servers/
│   ├── knowledge-graph/
│   │   ├── collab_kg/
│   │   │   ├── __init__.py
│   │   │   ├── server.py
│   │   │   ├── graph.py
│   │   │   ├── models.py
│   │   │   ├── tier_protection.py
│   │   │   ├── storage.py
│   │   │   └── ingestion.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── test_server.py
│   │   │   └── test_coverage.py
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── quality/
│   │   ├── collab_quality/
│   │   │   ├── __init__.py
│   │   │   ├── server.py
│   │   │   ├── models.py
│   │   │   ├── config.py
│   │   │   ├── gates.py
│   │   │   ├── storage.py
│   │   │   ├── trust_engine.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── formatting.py
│   │   │       ├── linting.py
│   │   │       ├── testing.py
│   │   │       └── coverage.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── test_server.py
│   │   │   └── test_coverage.py
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── governance/
│       ├── collab_governance/
│       │   ├── __init__.py
│       │   ├── server.py
│       │   ├── models.py
│       │   ├── store.py
│       │   ├── reviewer.py
│       │   ├── kg_client.py
│       │   └── task_integration.py
│       ├── tests/
│       │   └── __init__.py
│       ├── pyproject.toml
│       └── README.md
│
├── e2e/                                     # End-to-end testing harness
│   ├── run-e2e.sh
│   ├── run-e2e.py
│   ├── pyproject.toml
│   ├── README.md
│   ├── generator/
│   │   ├── project_generator.py
│   │   └── domain_templates.py
│   ├── scenarios/                           # 11 test scenarios
│   │   ├── base.py
│   │   ├── s01_kg_tier_protection.py
│   │   ├── s02_governance_decision_flow.py
│   │   ├── s03_governed_task_lifecycle.py
│   │   ├── s04_vision_violation.py
│   │   ├── s05_architecture_deviation.py
│   │   ├── s06_quality_gates.py
│   │   ├── s07_trust_engine.py
│   │   ├── s08_multi_blocker_task.py
│   │   ├── s09_scope_change_detection.py
│   │   ├── s10_completion_guard.py
│   │   └── s12_cross_server_integration.py
│   ├── parallel/
│   │   └── executor.py
│   └── validation/
│       ├── assertion_engine.py
│       └── report_generator.py
│
├── docs/
│   ├── vision/
│   │   └── vision.md
│   ├── architecture/
│   │   └── architecture.md
│   ├── v1-full-architecture/
│   │   ├── ARCHITECTURE.md
│   │   ├── COLLABORATIVE_INTELLIGENCE_VISION.md
│   │   └── README.md
│   ├── project-overview.md
│   └── gap-analysis-report.md
│
├── scripts/
│   ├── build-extension.sh
│   ├── dogfood-test.sh
│   ├── start-mcp-servers.sh
│   ├── stop-mcp-servers.sh
│   ├── populate-test-data.sh
│   └── hooks/
│       └── verify-governance-review.sh
│
├── templates/                               # Target project scaffolding templates
│   ├── claude-md/
│   │   └── quality-session-CLAUDE.md
│   ├── collab/
│   │   ├── mcp-config.json
│   │   ├── session-state.md
│   │   ├── artifacts/.gitkeep
│   │   ├── task-briefs/.gitkeep
│   │   └── memory/
│   │       ├── architectural-decisions.md
│   │       ├── solution-patterns.md
│   │       └── troubleshooting-log.md
│   └── mcp.json
│
├── prompts/
│   └── claude-code-feature-intelligence-search.md
│
├── work/                                    # Working documents and research
│   ├── QUALITY_CO_AGENT_MASTER.md
│   ├── QUALITY_CO_AGENT_PLAN.md
│   ├── comparative_analysis_of_goose_and_rigour.md
│   └── comprehensive_analysis_of_local_agent_frameworks.md
│
├── .vscode/
│   ├── launch.json
│   └── tasks.json
│
├── ARCHITECTURE.md
├── CLAUDE.md
├── COLLABORATIVE_INTELLIGENCE_VISION.md
├── README.md
├── COMPLETE.md
├── DOGFOOD-CHECKLIST.md
├── RUNBOOK.md
├── package.json
├── start-servers.sh
└── validate.sh
```

### Target Project Layout

After installing the Collaborative Intelligence System on a target project, the following structure is created (by `ProjectConfigService.ensureFolderStructure()` and the setup wizard):

```
target-project/
├── .claude/
│   ├── agents/                              # Copied from product repo
│   │   ├── worker.md
│   │   ├── quality-reviewer.md
│   │   ├── kg-librarian.md
│   │   ├── governance-reviewer.md
│   │   ├── researcher.md
│   │   └── project-steward.md
│   ├── collab/
│   │   ├── knowledge-graph.jsonl            # KG data (created by server)
│   │   ├── trust-engine.db                  # Trust engine SQLite (created by server)
│   │   └── governance.db                    # Governance SQLite (created by server)
│   ├── settings.json                        # Hooks configuration
│   └── settings.local.json                  # Permission allowlist (synced by wizard)
│
├── .avt/
│   ├── task-briefs/                         # Worker assignments
│   ├── session-state.md                     # Session progress tracking
│   ├── memory/
│   │   ├── architectural-decisions.md
│   │   ├── solution-patterns.md
│   │   ├── troubleshooting-log.md
│   │   └── research-findings.md
│   ├── research-prompts/
│   │   └── README.md
│   ├── research-briefs/
│   │   └── README.md
│   ├── research-prompts.json                # Research prompt registry
│   └── project-config.json                  # Project configuration
│
├── docs/
│   ├── vision/
│   │   └── vision.md                        # Vision standards (starter created by wizard)
│   └── architecture/
│       └── architecture.md                  # Architecture docs (starter created by wizard)
│
├── CLAUDE.md                                # Orchestrator instructions (copied/adapted)
└── [existing project files]
```

**Key differences from the product repository layout**: The target project does not contain the `extension/`, `mcp-servers/`, `e2e/`, `scripts/`, `templates/`, `prompts/`, or `work/` directories. It contains only the runtime artifacts needed for the collaborative intelligence system to operate: agent definitions, persistent data stores, system configuration, and documentation.
