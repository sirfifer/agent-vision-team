## 16. Technology Stack

### 16.1 Core Technologies

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Orchestration** | Claude Code CLI + subagents | Latest | Native orchestration platform |
| **AI Models** | Opus 4.6 (worker, quality-reviewer, researcher), Sonnet 4.5 (kg-librarian, governance-reviewer, project-steward), Haiku 4.5 (mechanical tasks) | Feb 2026 | Per-agent model routing based on task complexity |
| **MCP Servers** | Python + FastMCP | Python >=3.12, FastMCP >=2.0.0 | Consistent language across all three servers; FastMCP simplifies server creation |
| **AVT Gateway** | Python + FastAPI + uvicorn + httpx + websockets | Python >=3.12, FastAPI >=0.115 | Standalone web backend for remote operation: REST API, WebSocket push, job runner |
| **Web Server** | Nginx | Latest | Reverse proxy, TLS termination, SPA static file serving |
| **Container** | Docker + docker-compose | Latest | Standalone deployment packaging, GitHub Codespaces support |
| **KG Storage** | JSONL | — | Simple, portable, matches Anthropic's KG Memory format |
| **Quality Storage** | SQLite | — | Trust engine history, quality gate state |
| **Governance Storage** | SQLite | — | Decision history, review verdicts, governed task state |
| **VS Code Extension** | TypeScript | >=5.7.0 | VS Code extension platform |
| **Extension Build** | esbuild | >=0.24.0 | Fast bundling for extension backend |
| **Dashboard Webview** | React + TypeScript | React >=19.0.0 | Rich reactive UI for dashboard, wizard, tutorial, governance panel |
| **Webview Build** | Vite | >=6.0.0 | Fast dev server + production build |
| **Webview Styling** | Tailwind CSS | >=3.4.0 | Utility-first CSS with PostCSS + Autoprefixer |
| **E2E Testing** | Python + ThreadPoolExecutor + Pydantic | Python >=3.12, Pydantic >=2.0.0 | Parallel scenario execution with isolation and typed assertions |
| **Build System** | Hatchling | Latest | Python package builds for all MCP servers and E2E harness |
| **Version Control** | Git + worktrees | — | Code state management, worker isolation via branches |
| **Package Management** | npm (extension + webview), uv (Python servers + E2E) | — | Standard per ecosystem |
| **OS** | macOS (Darwin) | — | Primary developer platform |

### 16.2 Version Pinning Notes

All three MCP servers (`collab-kg`, `collab-quality`, `collab-governance`) share the same dependency floor: `fastmcp>=2.0.0`, `pydantic>=2.0.0`, Python `>=3.12`. The AVT Gateway (`avt-gateway`) adds `fastapi>=0.115`, `uvicorn`, `httpx`, and `websockets`. The E2E harness (`avt-e2e`) depends on `pydantic>=2.0.0` and Python `>=3.12`. All use Hatchling as the build backend.

The extension backend pins `typescript>=5.7.0` and `esbuild>=0.24.0`. The webview dashboard pins `react>=19.0.0`, `vite>=6.0.0`, and `tailwindcss>=3.4.0`. The dashboard supports dual build modes: VS Code mode (output to `dist/`) and web mode (output to `server/static/` with hashed filenames). The extension targets VS Code engine `>=1.95.0`.

All packages are at version `0.1.0` (pre-release).

### 16.3 Platform Features

Claude Code provides the execution environment for the entire system. The following table catalogs which platform features the system actively uses, which are available but not yet configured, and which are planned for adoption.

| Feature | Status | How Used |
|---------|--------|----------|
| Custom subagents | **Active** | 6 agents defined in `.claude/agents/`: worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward |
| MCP servers (SSE) | **Active** | 3 servers registered in `.claude/settings.json`: collab-kg (port 3101), collab-quality (port 3102), collab-governance (port 3103) |
| PreToolUse hooks | **Active** | `ExitPlanMode` → `verify-governance-review.sh`; `Write\|Edit\|Bash\|Task` → `holistic-review-gate.sh` (governance gate) + `context-reinforcement.py` (three-layer context injection: session context, static router, background distillation) |
| PostToolUse hooks | **Active** | `TaskCreate` → `governance-task-intercept.py` (task governance pairing, session tracking, context pipeline integration) |
| SessionStart hooks | **Active** | `compact` → `post-compaction-reinject.sh` (restores session context + vision standards after context compaction) |
| TeammateIdle hooks | **Active** | `teammate-idle-gate.sh` (prevents idle with pending governance obligations) |
| TaskCompleted hooks | **Active** | `task-completed-gate.sh` (enforces governance gates before task completion) |
| Model routing | **Active** | Per-agent model assignment in `.claude/settings.json` agents block: Opus 4.6 for worker/quality-reviewer, Sonnet 4.5 (default) for kg-librarian/governance-reviewer |
| Skills | **Active** | `/e2e` skill for E2E test harness execution |
| Commands | **Active** | `/project-overview` command for project context |
| Task List (native) | **Active** | `CLAUDE_CODE_TASK_LIST_ID` for cross-session task persistence; governed task system writes to native task files |
| Git worktrees | **Active** | Worker isolation via `git worktree add ../project-worker-N -b task/NNN-description` |
| MCP Tool Search | **Planned (immediate)** | 85% context reduction for MCP tool loading. Config-only change: set `ENABLE_TOOL_SEARCH=auto:5`. Requires Sonnet 4.5+ or Opus 4.6+ (not Haiku 4.5) |
| Effort controls | **Planned (immediate)** | Per-agent effort levels: max for worker/quality-reviewer, medium for kg-librarian, low for project-steward. Config change in agent definitions |
| Context compaction | **Available** | Automatic with Opus 4.6 for long-running orchestrator sessions. No configuration needed |
| 1M context window | **Available** | Automatic with Opus 4.6. Enables extended code reviews and larger session contexts without truncation |
| Setup hooks | **Planned (short-term)** | `--init` for project initialization (KG seeding, config validation), `--maintenance` for periodic tasks (cruft detection, dependency monitoring) |
| Agent Teams | **Monitoring** | Experimental platform feature. Aligns conceptually with our orchestration model (delegate mode, shared task list, plan approval). May replace custom subagent coordination when stable. Potential use: worker swarm teams for parallel implementation. Current blockers: no session resumption for teammates, one team per session, no nested teams |
| Plugins | **Planned (later)** | Natural plugin boundaries exist (3 MCP servers, 6 agents, 1 skill, 1 command, 1 hook). APIs still maturing. Will evaluate after Quality server stubs are replaced and governance review protocol stabilizes |

---

## 17. Current Status and Evolution Path

### 17.1 Current Status

This section replaces the v1 "Implementation Phases" checklist, which listed unchecked items that are now substantially complete. The following table reflects the actual state of each component as of February 2026.

| Component | Status | Notes |
|-----------|--------|-------|
| Knowledge Graph Server | **Operational** | 11 tools, JSONL persistence with load-on-startup/append-on-write, three-tier protection (vision/architecture/quality), document ingestion pipeline, full test coverage |
| Quality Server | **Operational (partial stubs)** | 8 tools exposed. Trust engine with SQLite persistence is fully functional. `auto_format`, `run_lint`, `run_tests`, and `check_coverage` delegate to stubs rather than real subprocess calls (ruff, prettier, pytest, eslint) |
| Governance Server | **Operational** | 10 tools, SQLite persistence, AI-powered review via `claude --print` with governance-reviewer agent, governed task lifecycle with multi-blocker support, KG integration for standard loading |
| Worker Agent | **Operational** | Full governance integration: reads task brief, checks project rules from `.avt/project-config.json`, queries KG for context (`search_nodes`, `get_entities_by_tier`), submits decisions via `submit_decision` (blocks until verdict), implements within task brief scope, runs `check_all_gates()`, calls `submit_completion_review` before reporting done |
| Quality Reviewer Agent | **Operational** | Three-lens review protocol (vision > architecture > quality). Model: Opus 4.6. 6 tools including KG and Quality server access |
| KG Librarian Agent | **Operational** | Memory curation: consolidation, promotion, stale entry removal, archival file sync to `.avt/memory/`. Model: Sonnet 4.5. 5 tools |
| Governance Reviewer Agent | **Operational** | AI review called internally by governance server via `claude --print`. Reviews decisions and plans through vision alignment and architectural conformance lenses. Model: Sonnet 4.5. 4 tools |
| Researcher Agent | **Operational** | Dual-mode research: periodic/maintenance (dependency monitoring, breaking change detection) and exploratory/design (technology evaluation, architectural decisions). Model: Opus 4.6. 7 tools |
| Project Steward Agent | **Operational** | Project hygiene: naming conventions, folder organization, documentation completeness, cruft detection. Periodic cadence: weekly/monthly/quarterly. Model: Sonnet 4.5. 7 tools |
| VS Code Extension | **Operational** | Dashboard webview, 9-step setup wizard, 10-step workflow tutorial, 6-step VS Code walkthrough, governance panel, decision explorer, quality gates panel, findings panel, research prompts panel, job submission, 3 MCP clients (KG, Quality, Governance), 4 TreeViews, 12 commands |
| AVT Gateway | **Operational** | FastAPI backend with 35 REST endpoints, WebSocket push, job runner with Claude CLI integration, API-key auth, 8 router modules. Ports of ProjectConfigService and McpClientService from TypeScript to Python |
| Container Packaging | **Operational** | Dockerfile (python:3.12-slim + Node.js 22 + Claude CLI + Nginx), docker-compose.yml, entrypoint.sh, nginx.conf, .devcontainer/devcontainer.json for GitHub Codespaces |
| Dual-Mode Dashboard | **Operational** | React dashboard runs in VS Code (postMessage) or standalone browser (HTTP + WebSocket) via transport abstraction. Web build outputs to `server/static/` with hashed filenames. Mobile-responsive layout |
| E2E Test Harness | **Operational** | 14 scenarios (s01-s14), 292+ structural domain-agnostic assertions, parallel execution with full isolation, random domain generation from 8 templates, mock review mode |
| Context Drift Prevention | **Operational** | Three-layer injection (session context, static router, post-compaction), session context distillation via background haiku calls, goal tracking through governance review pipeline, 13 tunable settings with dashboard UI controls, 120 hook-level unit tests across 10 test groups |
| CLAUDE.md Orchestration | **Operational** | All protocols documented: task decomposition, governance checkpoints, quality review, memory curation, research, project hygiene, drift detection |

### 17.2 Known Gaps

These are known deficiencies in the current implementation. They do not block operation but represent incomplete or inconsistent areas.

**Quality server tool stubs.** The `auto_format`, `run_lint`, `run_tests`, and `check_coverage` tools accept parameters and return structured responses, but they do not call real subprocesses (ruff, prettier, eslint, pytest). The trust engine and quality gate aggregation (`check_all_gates`, `validate`) are fully functional. The stubs return plausible but synthetic results. This means quality gates pass based on stub output, not actual code analysis.

**Extension-system state drift.** The extension dashboard was built incrementally as the system evolved. Some UI components may reference patterns or display states that have since changed. The gap analysis (February 2026) identified that the extension's scope has grown far beyond "observability only" but some internal state representations have not kept pace with governance and research system evolution.

**Agent definitions outside settings.json.** The researcher and project-steward agents are defined in `.claude/agents/` but are not listed in the `agents` block of `.claude/settings.json`. They inherit the `defaultModel: sonnet` setting. The researcher should be explicitly configured for Opus 4.6 to match its documented model assignment.

**v1 scaffolding remnants.** Code from the v1 architecture (Communication Hub server scaffolding, extension session management) is preserved in the codebase and in `docs/v1-full-architecture/`. This is intentional (available for reactivation) but adds cognitive load for new contributors.

### 17.3 Evolution Path

Items are ordered by priority. Effort and dependency information is included to support planning.

| Priority | Item | Effort | Depends On | Notes |
|----------|------|--------|-----------|-------|
| **Immediate** | Enable MCP Tool Search | Config only | — | Set `ENABLE_TOOL_SEARCH=auto:5` in settings. 85% context reduction for tool loading |
| **Immediate** | Set effort controls per agent | Config only | — | Add effort levels to agent definitions in `.claude/settings.json` |
| ~~**Immediate**~~ | ~~Update model references to Opus 4.6~~ | ~~Trivial~~ | — | **Done.** All model references updated to Opus 4.6, Sonnet 4.5, Haiku 4.5 |
| **Immediate** | Add researcher/steward to settings.json agents | Config only | — | Explicitly configure model and tools for researcher (Opus 4.6) and project-steward (Sonnet 4.5) |
| **Short-term** | Replace Quality server stubs with real subprocess calls | Medium | — | Connect `auto_format`/`run_lint`/`run_tests`/`check_coverage` to ruff, prettier, eslint, pytest via `subprocess.run`. Requires specialist routing config per language |
| **Short-term** | Convert common workflows to model-invocable skills | Low | — | Identify orchestrator patterns that repeat across sessions. Candidates: governance review flow, worker spawn-and-review cycle, KG curation trigger |
| **Short-term** | Add setup hooks (`--init`, `--maintenance`) | Low | — | `--init`: validate project config, seed KG with vision/architecture docs, verify MCP server connectivity. `--maintenance`: run cruft detection, check dependency updates |
| ~~**Short-term**~~ | ~~Align extension UI with current system state~~ | ~~Medium~~ | — | **Done.** Dashboard now includes DecisionExplorer, FindingsPanel, QualityGatesPanel, JobSubmission, JobList. Dual-mode transport supports VS Code and standalone web |
| **Medium-term** | Plugin packaging evaluation | Medium | API stability | Assess whether MCP server APIs, agent definitions, and hook contracts are stable enough to package. Define plugin boundaries. Prototype single-plugin extraction |
| **Medium-term** | Agent Teams evaluation | Evaluate | Platform maturation | Monitor experimental status. When session resumption is supported and nested teams are available, prototype worker swarm team alongside governance policy layer |
| **Future** | Cross-project memory | High | KG design | KG entities that travel between projects. Requires namespace design, conflict resolution, tier portability rules |
| **Future** | Multi-team coordination | High | Agent Teams stabilization | Multiple teams with different specializations (implementation team, review team, research team) coordinating on the same project |
| **Future** | Plugin distribution | Medium | Plugin packaging | Publish to Claude Code plugin marketplace. Requires stable APIs, documentation, versioning strategy |

### 17.4 What Was Completed Since v1

For historical context, the following summarizes what the v1 "Implementation Phases" planned and what actually shipped. All five phases are substantially complete, with the Quality server stubs being the primary remaining item from Phase 1.

| v1 Phase | What Was Planned | What Shipped |
|----------|-----------------|-------------|
| **Phase 1: Make MCP Servers Real** | KG: JSONL persistence, delete tools, compaction. Quality: real subprocess calls, SQLite trust engine | KG: fully operational with 11 tools (3 beyond plan), JSONL persistence, tier protection. Quality: 8 tools operational, trust engine with SQLite complete. **Gap**: formatting/linting/testing still delegate to stubs |
| **Phase 2: Create Subagents + Validate E2E** | 3 agents (worker, quality-reviewer, kg-librarian), CLAUDE.md orchestration, settings.json hooks, end-to-end validation | 6 agents (added governance-reviewer, researcher, project-steward), full CLAUDE.md orchestration with governance/research/hygiene protocols, PreToolUse hooks, end-to-end workflow validated |
| **Phase 3: Build Extension as Monitoring Layer** | MCP clients, TreeView wiring, file watchers, diagnostics, dashboard, status bar | 3 MCP clients, 4 TreeViews, dashboard webview with React 19, 10-step wizard, 9-step tutorial, VS Code walkthrough, governance panel, research prompts panel, 12 commands. Scope significantly exceeded plan |
| **Phase 4: Expand and Harden** | Event logging, cross-project memory, multi-worker parallelism, FastMCP 3.0 migration, installation script | E2E test harness (13 scenarios, 221 assertions), full governance system (not in original plan), research system (not in original plan), project hygiene system (not in original plan). Cross-project memory and FastMCP migration remain future items |
| **Phase 5: Remote Operation** | (Not in original plan) | AVT Gateway (FastAPI, 35 REST endpoints, WebSocket push, job runner), dual-mode React dashboard (VS Code + standalone web), container packaging (Dockerfile, docker-compose, Codespaces), mobile-responsive layout, API-key auth. Zero changes to MCP servers, hooks, or agents |

---

## 18. Verification

### 18.1 E2E Test Harness (Primary Verification)

The E2E test harness is the primary verification mechanism for all three MCP servers. It exercises the Python library APIs directly with structural, domain-agnostic assertions.

**Characteristics:**
- 14 scenarios covering KG, Quality, and Governance servers
- 292+ assertions that are structural (not domain-specific)
- Parallel execution via `ThreadPoolExecutor` with full isolation per scenario (separate JSONL, SQLite, task directories)
- Each run generates a unique project from 8 domain templates (Pet Adoption, Restaurant Reservation, Fitness Tracking, etc.)
- `GOVERNANCE_MOCK_REVIEW` environment variable enables deterministic testing without a live `claude` binary

**Additional test suites:**
- **Hook unit tests**: 120 assertions across 10 groups in `scripts/hooks/test-hook-unit.sh`, covering governance hooks (Groups 1-5) and context reinforcement (Groups 6-10: session context injection, distillation, update, post-compaction, governance pipeline integration)
- **MCP access tests**: 15 assertions verifying MCP tool availability
- **Capability matrix tests**: 13 assertions verifying tool access at direct/subagent levels
- **Hook live tests**: Level 1-4 integration tests covering mock interception, real AI review, subagent inheritance, and session-scoped flags

**How to run:**

```bash
./e2e/run-e2e.sh              # Standard run (workspace cleaned up after)
./e2e/run-e2e.sh --keep       # Preserve workspace for debugging
./e2e/run-e2e.sh --seed 42    # Reproducible project generation
./e2e/run-e2e.sh --verbose    # Enable debug logging
```

Or use the `/e2e` skill from within Claude Code.

**When to run:**
- After modifying any MCP server code (catches contract drift)
- Before significant releases (confirms all three servers work together)
- After governance or task system changes (scenarios s03, s08, s10 specifically test the governed task flow)
- Periodically (random domain selection means each run is a genuine uniqueness test)

**Scenario coverage:**

| Scenario | File | What It Validates |
|----------|------|-------------------|
| s01 | `s01_kg_tier_protection.py` | KG CRUD operations + tier-based access control. Vision-tier entities are immutable by workers |
| s02 | `s02_governance_decision_flow.py` | Decision storage, review verdicts (approved/blocked/needs_human_review), status queries |
| s03 | `s03_governed_task_lifecycle.py` | Task pair creation via `create_governed_task`, blocking from birth, release on approval |
| s04 | `s04_vision_violation.py` | Attempts to modify vision-tier entities are rejected regardless of caller |
| s05 | `s05_architecture_deviation.py` | `deviation` and `scope_change` categories are stored and flagged correctly |
| s06 | `s06_quality_gates.py` | `GovernanceStore.get_status()` returns accurate aggregates across decisions |
| s07 | `s07_trust_engine.py` | Finding record, dismiss with justification, audit trail lifecycle |
| s08 | `s08_multi_blocker_task.py` | 3 stacked blockers on a single task, released one at a time, task unblocks only when all clear |
| s09 | `s09_scope_change_detection.py` | `scope_change`/`deviation` categories auto-assign `needs_human_review` verdict |
| s10 | `s10_completion_guard.py` | Unresolved blocks and missing plan reviews are caught by completion review |
| s12 | `s12_cross_server_integration.py` | KG + Governance + Task system interplay across servers |

### 18.2 Component Verification

Each component can be verified independently. The following table provides concrete verification steps for both automated (E2E) and manual approaches.

| Component | How to Verify |
|-----------|--------------|
| **KG server** | **Automated**: E2E scenarios s01 (tier protection), s04 (vision violation). **Manual**: Create entities at each tier via `create_entities`. Attempt to add observation to a vision-tier entity with `callerRole: "worker"` -- verify rejection. Call `search_nodes` -- verify full-text results. Restart server -- verify JSONL persistence survives. Call `ingest_documents` on `docs/vision/` -- verify entities created at vision tier |
| **Quality server** | **Automated**: E2E scenarios s06 (quality gates), s07 (trust engine). **Manual**: Call `check_all_gates()` against the project codebase -- verify structured response with per-gate status. Call `record_dismissal` with a finding ID and justification -- verify audit trail via `get_trust_decision`. Note: `auto_format`/`run_lint`/`run_tests`/`check_coverage` currently return stub results |
| **Governance server** | **Automated**: E2E scenarios s02 (decision flow), s03 (governed task lifecycle), s08 (multi-blocker), s09 (scope change), s10 (completion guard). **Manual**: Call `submit_decision` with category `pattern_choice` -- verify it blocks until verdict is returned. Call `create_governed_task` -- verify two tasks created, implementation blocked. Call `get_governance_status` -- verify accurate counts |
| **Worker agent** | Spawn via Task tool with a task brief. Verify full protocol execution: reads brief, checks project rules from `.avt/project-config.json`, queries KG for context (`search_nodes`, `get_entities_by_tier`), submits decisions via `submit_decision` (blocks until verdict), implements within task brief scope, runs `check_all_gates()`, calls `submit_completion_review` before reporting done |
| **Quality reviewer agent** | Spawn with a diff containing a vision violation (e.g., introducing a singleton in production code when vision standard prohibits it). Verify structured finding output with: tier (`vision`), severity, rationale referencing the specific standard, actionable recommendation |
| **KG librarian agent** | Spawn after a work session with accumulated observations. Verify: redundant observations consolidated, recurring solutions promoted to pattern entities, stale entries removed, archival files in `.avt/memory/` synced (architectural-decisions.md, troubleshooting-log.md, solution-patterns.md) |
| **Governance reviewer agent** | Tested indirectly via governance server. Call `submit_decision` or `submit_plan_for_review` with `GOVERNANCE_MOCK_REVIEW` unset -- verify `claude --print` invocation with governance-reviewer agent produces a structured `ReviewVerdict` JSON response |
| **Researcher agent** | Spawn with a research prompt (periodic or exploratory mode). Verify: research brief written to `.avt/research-briefs/` with structured sections (findings, recommendations, action items). For periodic mode, verify change report format. For exploratory mode, verify comparison analysis |
| **Project steward agent** | Spawn with "Perform a full project hygiene review". Verify: report output with categorized findings (naming conventions, folder organization, documentation completeness, cruft detection), priority levels, and specific file references |
| **VS Code extension** | Launch VS Code with extension installed. Verify: Activity Bar shows "Collab Intelligence" container with 4 views (Actions, Memory Browser, Findings, Tasks). Click "Connect to Servers" -- verify 3 MCP clients connect. Open Dashboard -- verify React webview loads with agent cards, activity feed, governance panel, decision explorer, quality gates, job submission. Open Setup Wizard -- verify 9-step flow renders. Open Workflow Tutorial -- verify 10-step flow renders |
| **AVT Gateway** | Start all 3 MCP servers, then start Gateway: `cd server && uv run uvicorn avt_gateway.app:app --port 8080`. Verify: `GET /api/health` returns 200. `GET /api/dashboard` returns full dashboard state. `POST /api/mcp/connect` connects to all 3 MCP servers. `POST /api/jobs` with a prompt creates a queued job. WebSocket at `/api/ws?token=<key>` receives push events. Web dashboard at `http://localhost:8080` loads and displays live data |
| **Container deployment** | Build: `docker compose build`. Run: `docker compose up -d`. Verify: `https://localhost` serves the React dashboard. API key is displayed in container logs. Dashboard shows connected MCP server status. Job submission form is functional. Mobile layout (resize browser) shows stacked panels |

### 18.3 Integration Verification

The full integration test validates that all components work together in the governed development workflow, end to end, without extension involvement. This is the successor to the v1 "Phase 2 Validation Test" and reflects the actual system with governance integration.

**Setup:**
1. Start all 3 MCP servers (KG on 3101, Quality on 3102, Governance on 3103)
2. Ensure KG contains vision and architecture entities (via `ingest_documents` or manual `create_entities`)
3. Set `CLAUDE_CODE_TASK_LIST_ID=agent-vision-team` for cross-session task persistence
4. Open Claude Code with the project's `.claude/agents/`, `CLAUDE.md`, and `.claude/settings.json`

**Integration flow:**

```
Step 1: Orchestrator receives task
    "Add input validation to the UserService"
        |
Step 2: Orchestrator queries KG for context
    search_nodes("UserService") -> discovers patterns and constraints
    get_entities_by_tier("vision") -> loads all vision standards
        |
Step 3: Orchestrator creates governed task
    create_governed_task("Add input validation to UserService",
        review_type="governance")
    -> Review task created (pending)
    -> Implementation task created (blocked by review)
        |
Step 4: Governance review executes
    Governance server loads vision standards from KG (JSONL)
    Governance server calls claude --print with governance-reviewer agent
    Governance reviewer checks decision against standards
    complete_task_review(review_task_id, "approved", guidance="...")
    -> Implementation task unblocked
        |
Step 5: Orchestrator creates worktree and spawns worker
    git worktree add ../project-worker-1 -b task/001-add-validation
    Task tool -> worker agent with task brief
        |
Step 6: Worker executes governed protocol
    Worker reads task brief
    Worker checks project rules (.avt/project-config.json)
    Worker queries KG (search_nodes, get_entity)
    Worker submits decisions (submit_decision -> blocks until verdict)
    Worker implements within scope
    Worker runs quality gates (check_all_gates)
    Worker submits completion review (submit_completion_review)
        |
Step 7: Orchestrator spawns quality reviewer
    Task tool -> quality-reviewer with worker's diff
    Quality reviewer applies three-lens protocol:
      Vision lens -> checks against vision entities from KG
      Architecture lens -> checks pattern conformance
      Quality lens -> runs lint/test via Quality server
    Returns structured findings (if any)
        |
Step 8: Finding resolution (if needed)
    Orchestrator routes findings back to worker
    Worker addresses findings
    Quality reviewer re-reviews
    Repeat until clean
        |
Step 9: Merge and checkpoint
    git merge task/001-add-validation
    git tag checkpoint-001
    git worktree remove ../project-worker-1
        |
Step 10: KG curation
    Task tool -> kg-librarian
    Librarian consolidates observations
    Librarian promotes recurring solutions to patterns
    Librarian syncs to .avt/memory/ archival files
```

**Expected outcome:** The entire workflow completes using Claude Code native primitives + 3 MCP servers. The extension is not involved in the flow. Every implementation task is blocked from birth until governance review approves it. Every worker decision is transactionally reviewed. Quality gates run before completion. KG is updated with institutional memory from the session.

**Verification checklist:**

- [ ] Governed task pair created atomically (review blocks implementation)
- [ ] Implementation task cannot be picked up before review completes
- [ ] Worker `submit_decision` calls block until governance verdict
- [ ] `submit_completion_review` catches unresolved blocks or missing plan reviews
- [ ] Quality gates (`check_all_gates`) return structured per-gate results
- [ ] KG librarian successfully consolidates and syncs to archival files
- [ ] Git worktree created, used for isolation, and cleaned up after merge
- [ ] Session state updated in `.avt/session-state.md`
- [ ] Checkpoint tag created for recovery
