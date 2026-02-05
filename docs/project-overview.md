# Agent Vision Team — Project Overview

> A platform-native multi-agent system for software development built on Claude Code, providing tier-protected institutional memory, transactional governance, and deterministic quality verification through three MCP servers and six specialized subagents.

**Last Updated**: 2026-02-04

---

## What This Project Is

Agent Vision Team is a collaborative intelligence system that coordinates multiple specialized AI agents to accomplish complex development tasks. It runs entirely on Claude Code Max — no API keys, no external orchestration frameworks — and extends Claude Code's native capabilities with three MCP servers that provide what the platform cannot do on its own: persistent institutional memory, transactional governance checkpoints, and deterministic quality verification.

The system is organized around a three-tier governance hierarchy: **Vision** (immutable project principles), **Architecture** (human-gated structural patterns), and **Quality** (automated code standards). Every piece of work an agent produces is measured against this hierarchy. A perfectly linted function that violates the project's design philosophy is a failure, not a success.

A human developer, working through a primary Claude Code session (the orchestrator), decomposes complex tasks and delegates them to six specialized subagents. Workers implement scoped tasks. The quality reviewer evaluates work through a three-lens model. The KG librarian curates institutional memory so knowledge survives across sessions. The governance reviewer provides AI-powered decision review inside the governance server. The researcher gathers intelligence — monitoring external dependencies and investigating unfamiliar domains — so workers implement from informed positions rather than guessing. The project steward maintains organizational hygiene: naming conventions, folder structure, documentation completeness, and cruft detection. Each agent has a distinct role, and together they sustain coherent, high-quality development over extended autonomous sessions.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│              HUMAN + PRIMARY SESSION (Orchestrator)               │
│    Interactive Claude Code session (Opus 4.5)                     │
│    Reads: CLAUDE.md, session-state.md                            │
│    Uses: Task tool to spawn all subagents                        │
└──┬──────────┬──────────┬──────────┬──────────┬───────────────────┘
   │          │          │          │          │
┌──▼───────┐ ┌▼────────┐ ┌▼────────┐ ┌▼────────┐ ┌▼────────────┐
│ WORKER   │ │QUALITY  │ │  KG     │ │RESEARCH-│ │  PROJECT    │
│          │ │REVIEWER │ │LIBRARIAN│ │  ER     │ │  STEWARD    │
│ (Opus)   │ │ (Opus)  │ │(Sonnet) │ │(Opus/  │ │  (Sonnet)   │
│          │ │         │ │         │ │ Sonnet) │ │             │
└──┬───────┘ └──┬──────┘ └──┬──────┘ └──┬──────┘ └──┬──────────┘
   │            │            │           │           │
┌──▼────────────▼────────────▼───────────▼───────────▼───────────┐
│                     THREE MCP SERVERS                           │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │Knowledge Graph│   │   Quality    │   │    Governance      │  │
│  │    :3101      │   │    :3102     │   │      :3103         │  │
│  └──────────────┘   └──────────────┘   └─────────┬──────────┘  │
│                                                   │             │
│                                          ┌────────▼──────────┐  │
│                                          │   GOVERNANCE      │  │
│                                          │    REVIEWER       │  │
│                                          │    (Sonnet)       │  │
│                                          │ Called internally  │  │
│                                          │ via claude --print │  │
│                                          └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
   │
┌──▼──────────────────────────────────────────┐
│          VS CODE EXTENSION                   │
│    (Observability Dashboard — Read Only)     │
└──────────────────────────────────────────────┘
```

### Platform-Native Philosophy

The architecture follows a strict principle: build only what Claude Code cannot do. Claude Code provides agent spawning, coordination, parallel execution, lifecycle hooks, session persistence, model routing, and permission control natively. The three MCP servers exist because the platform genuinely lacks persistent institutional memory, transactional governance, and deterministic quality tool wrapping.

| Provided by Claude Code (native) | Provided by MCP Servers (custom) |
|---|---|
| Subagent spawning via Task tool | Persistent tier-protected memory (KG) |
| Parent-child communication | Deterministic quality verification |
| Lifecycle hooks | Transactional governance review |
| Git worktree management | Governed task execution |
| Session persistence/resume | Trust engine with audit trails |
| Model routing per subagent | AI-powered decision review |
| Tool restrictions and permissions | — |

---

## Three-Tier Governance Hierarchy

The organizing principle for the entire system:

| Tier | Contains | Who Can Modify | Examples |
|------|----------|----------------|----------|
| **Vision** | Core principles, design philosophy, fundamental purpose | Human only | "All services use protocol-based DI", "No singletons in production code" |
| **Architecture** | Patterns, major components, established abstractions | Human or orchestrator with approval | "ServiceRegistry pattern", "AuthService component" |
| **Quality** | Observations, findings, troubleshooting notes | Any agent | "AuthService lacks error handling", "Login flow refactored" |

Lower tiers cannot modify higher tiers. Vision conflicts override all other work. This hierarchy is enforced at the server level — a misbehaving subagent cannot accidentally corrupt vision-tier data.

---

## Three MCP Servers

### Knowledge Graph Server (Port 3101)

Persistent institutional memory with tier-based access control. Stores entities (components, patterns, decisions, vision standards), relations between them, and timestamped observations. All Claude Code sessions share the same graph.

**Implementation**: Python + FastMCP, JSONL persistence at `.claude/collab/knowledge-graph.jsonl`

**Tools**: `create_entities`, `create_relations`, `add_observations`, `search_nodes`, `get_entity`, `get_entities_by_tier`, `delete_observations`, `delete_entity`

**Tier Protection**: Enforced at the tool level. Vision-tier entities are immutable by agents. Architecture-tier writes require explicit approval. Quality-tier is open to all callers.

**Key files**: `mcp-servers/knowledge-graph/collab_kg/` — `server.py` (FastMCP entry), `graph.py` (entity/relation CRUD), `storage.py` (JSONL persistence), `tier_protection.py` (access control), `ingestion.py` (document ingestion pipeline)

### Quality Server (Port 3102)

Deterministic quality verification wrapping real tools behind a unified MCP interface, plus a trust engine for finding management.

**Implementation**: Python + FastMCP, SQLite persistence for trust engine

**Tools**: `auto_format`, `run_lint`, `run_tests`, `check_coverage`, `check_all_gates`, `validate`, `get_trust_decision`, `record_dismissal`

**Supported languages**: Python (ruff, pytest), TypeScript/JavaScript (eslint, prettier, npm test), Swift (swiftlint, swiftformat, xcodebuild), Rust (clippy, rustfmt, cargo test)

**Five quality gates**: Build, lint, tests, coverage (default 80% threshold), findings (no critical unresolved)

**Trust engine principle**: No silent dismissals. Every dismissed finding requires a justification string and the identity of who dismissed it, creating an auditable trail.

**Key files**: `mcp-servers/quality/collab_quality/` — `server.py`, `tools/` (formatting, linting, testing, coverage), `trust_engine.py`, `gates.py`

### Governance Server (Port 3103)

Transactional review checkpoints for agent decisions, implementing the "intercept early, redirect early" pattern. Workers submit decisions and block until the governance server returns a verdict.

**Implementation**: Python + FastMCP, SQLite persistence for decision store

**Decision tools**: `submit_decision`, `submit_plan_for_review`, `submit_completion_review`, `get_decision_history`, `get_governance_status`

**Governed task tools**: `create_governed_task`, `add_review_blocker`, `complete_task_review`, `get_task_review_status`, `get_pending_reviews`

**Decision categories**: `pattern_choice`, `component_design`, `api_design`, `deviation`, `scope_change`

**Verdicts**: `approved` (proceed), `blocked` (stop, guidance provided), `needs_human_review` (escalate)

**Review process**: When a decision is submitted, the governance server loads vision standards from the KG, runs the governance-reviewer subagent via `claude --print` for AI-powered review, stores the verdict in SQLite, records the decision in the KG for institutional memory, and returns the verdict to the calling agent.

**Governed task lifecycle**: `create_governed_task` atomically creates a review task and an implementation task. The implementation task is blocked from birth — its `blockedBy` array references the review. Multiple review blockers can be stacked (governance, security, architecture). The task is released only when all blockers are approved.

**Key files**: `mcp-servers/governance/collab_governance/` — `server.py`, `store.py` (SQLite decision store), `reviewer.py` (AI review logic), `task_integration.py` (Claude Code Task System integration), `kg_client.py` (KG integration)

---

## Six Custom Subagents

All defined in `.claude/agents/` as markdown files with YAML frontmatter specifying model, tools, and system prompt.

| Agent | Model | Role | MCP Access |
|-------|-------|------|------------|
| **Worker** | Opus | Implements scoped tasks from task briefs. Queries KG for constraints, submits decisions for governance review, runs quality gates before completion. | KG, Quality, Governance |
| **Quality Reviewer** | Opus | Three-lens evaluation: Vision (highest) → Architecture → Quality. Returns structured findings with project-specific rationale. | KG, Quality |
| **KG Librarian** | Sonnet | Curates institutional memory after work sessions. Consolidates observations, promotes recurring solutions to patterns, removes stale entries, syncs to archival files. | KG |
| **Governance Reviewer** | Sonnet | Evaluates decisions and plans against vision and architecture standards. Called internally by the governance server via `claude --print`. Returns structured verdicts. | KG |
| **Researcher** | Opus/Sonnet | Gathers intelligence in two modes: periodic/maintenance (tracking external dependencies) and exploratory/design (informing architectural decisions). Produces research briefs. | KG, Governance |
| **Project Steward** | Sonnet | Maintains project hygiene: naming conventions, folder organization, documentation completeness, cruft detection, consistency checks. | KG |

### The Quality Reviewer — Three-Lens Evaluation

The Quality Reviewer evaluates work in strict order:

1. **Vision Lens** — Does this work align with project identity? Vision conflicts stop all related work immediately.
2. **Architecture Lens** — Does this work follow established patterns? Detects "ad-hoc pattern drift" where new code reinvents existing solutions.
3. **Quality Lens** — Does the code pass automated checks? Auto-fixes formatting; reports issues needing judgment.

Every finding includes project-specific rationale (not generic advice), a concrete suggestion for how to fix it, and a reference to the KG entity or standard being violated. The reviewer is read-focused — it evaluates code but does not write production code.

### The Researcher — Intelligence Before Implementation

The researcher operates in two distinct modes:

**Periodic/Maintenance Research** monitors APIs, frameworks, and tools the project depends on. It detects breaking changes, deprecation notices, new features, and security advisories. The orchestrator can schedule these as recurring prompts. Output is structured change reports with actionable items prioritized by urgency.

**Exploratory/Design Research** is spawned before architectural decisions or when entering unfamiliar domains. It surveys the landscape, evaluates competing approaches, documents tradeoffs, and synthesizes recommendations. Output is research briefs stored in `.avt/research-briefs/` that feed directly into task briefs for workers.

The model is selected based on complexity: **Opus** for novel domains, architectural decisions, security analysis, and ambiguous requirements. **Sonnet** for routine changelog monitoring, version updates, and straightforward documentation lookups.

The researcher creates `research_finding` entities in the KG, establishing baselines so future research produces net-new insights rather than rediscovering what's already known. Key discoveries are synced to `.avt/memory/research-findings.md` by the KG librarian.

The core principle: **workers should never need to do substantial research** — that's the researcher's job. Workers implement based on research findings, not on their own investigation.

### The Project Steward — Organizational Hygiene

The project steward maintains everything that makes a project professional and maintainable — not code logic, but the organizational fabric surrounding it.

**What it monitors**:
- **Essential project files**: README, LICENSE, CONTRIBUTING, CHANGELOG, CODE_OF_CONDUCT, SECURITY — verifying they exist, aren't stubs, and are up to date
- **Naming conventions**: Consistent casing across files, directories, variables, and types per language norms (kebab-case, snake_case, PascalCase)
- **Folder organization**: Logical grouping, appropriate depth, no orphaned files, clear separation of concerns
- **Documentation completeness**: README sections, API docs, configuration documentation, script headers
- **Cruft detection**: Unused files, duplicates, outdated configs, dead links, resolved TODO/FIXME comments
- **Consistency**: Indentation style, line endings, encoding, import ordering

**Periodic review cadence**: Weekly for cruft detection and dead link checking. Monthly for full naming consistency audits. Quarterly for deep documentation review and structural analysis.

The steward can make mechanical fixes directly (renaming files, removing cruft) when the change is non-controversial. For structural changes or deletions that might affect other developers, it flags them for the orchestrator. It records naming conventions and project structure patterns as KG entities so future reviews have an established baseline.

### The Governance Reviewer — The Brain Inside Governance

The governance reviewer is unique among the six agents: it is not spawned directly by the orchestrator. Instead, it runs inside the governance server, called via `claude --print` whenever a decision, plan, or completion review is submitted.

When the governance server receives a `submit_decision` call, it loads vision standards from the KG, passes them along with the decision details to the governance reviewer, and the reviewer applies three checks in strict order:

1. **Vision alignment** — Does the decision conflict with any vision standard? If so, verdict is `blocked`.
2. **Architectural conformance** — Does it follow established patterns? Unjustified deviation means `blocked`.
3. **Consistency check** — For plan reviews, were blocked decisions reimplemented? For completion reviews, were all decisions actually reviewed?

The reviewer returns structured verdicts with findings, guidance, and a list of standards verified. This makes governance transactional — agents submit decisions and block until the reviewer responds through the server.

---

## Task Execution Flow

```
1. Human gives orchestrator a complex task
2. Orchestrator decomposes into subtasks, writes task briefs to .avt/task-briefs/
3. Orchestrator creates git worktrees for parallel worker isolation
4. Worker queries KG for vision/architecture constraints
5. Worker submits key decisions to Governance server (blocks until verdict)
6. Worker implements, runs quality gates via Quality server
7. Quality Reviewer applies three-lens review to the diff
8. Findings route back to Worker for resolution
9. On completion: merge worktree, checkpoint (git tag), curate memory via KG Librarian
```

### Governed Task Flow

```
create_governed_task()
    ├── Creates review task (pending)
    └── Creates implementation task (blocked by review)
         └── Task CANNOT run until review completes

complete_task_review(verdict: "approved")
    └── Releases implementation task → worker picks it up

add_review_blocker(review_type: "security")
    └── Stacks additional review → both must complete before execution
```

### Research Flow

Before complex or unfamiliar tasks, the orchestrator spawns the researcher to gather intelligence first:

```
1. Orchestrator identifies a task requiring research (unfamiliar domain,
   architectural decision, technology evaluation)
2. Orchestrator spawns researcher with a research prompt
3. Researcher queries KG for existing knowledge on the topic
4. Researcher uses WebSearch/WebFetch to gather external intelligence
5. Researcher creates research_finding entities in the KG
6. Researcher produces a research brief in .avt/research-briefs/
7. Orchestrator references the research brief in task briefs for workers
8. Workers implement with research context — no guesswork required
```

For periodic monitoring, the researcher tracks external dependencies on a schedule — detecting breaking changes, deprecations, and security advisories before they cause problems.

### Project Hygiene Flow

The project steward runs periodically or before significant events (releases, major refactors, new project setup):

```
1. Orchestrator spawns project steward
2. Steward scans project structure, naming, documentation, cruft
3. Steward makes mechanical fixes directly (renaming, cruft removal)
4. Steward records naming conventions as KG entities for future reference
5. Steward returns structured review report with prioritized findings
6. Orchestrator addresses findings or delegates to workers
```

---

## Project Rules — Context Injection for Agent Quality

The three-tier governance hierarchy protects vision standards and architectural patterns. But below those tiers lies a gap: practical working rules that govern how code is written day-to-day. Rules like "no mock tests," "run the build before reporting completion," and "follow existing patterns" aren't vision or architecture — they're the behavioral expectations for how agents produce work.

**The key insight**: Every subagent starts as a fresh session. By injecting concise rules at spawn time, agents see fresh instructions at peak attention. Rules live in `.avt/project-config.json` and are compiled into a compact preamble prepended to each agent's task prompt.

### How Rules Are Structured

Each rule has a **statement** (concise imperative), a **rationale** (one sentence, not injected into context), an **enforcement level** (enforce, prefer, or guide), and a **scope** (which agent types it applies to). The default set covers the most common AI coding quality failures:

- **Enforce**: Write real tests (no mocks), require test coverage, run build before completion, follow existing patterns, read code before modifying it, don't suppress warnings
- **Prefer** (explain if deviating): Keep changes focused, reassess after repeated failures

### How Rules Get Injected

When the orchestrator spawns a subagent, enabled rules for that agent's scope are compiled into a preamble:

```
## Project Rules
ENFORCE:
- Write real tests, never mocks (unless external service boundaries)
- All new code must have test coverage
- Run build + tests before reporting completion
...

PREFER (explain if deviating):
- Keep changes focused — don't refactor surrounding code
...

---
[actual task prompt]
```

The preamble is grouped by enforcement level (not category) and kept compact — targeting 200-400 tokens for 8-12 rules. Rationale is omitted from the injection; it lives in the Knowledge Graph for agents that need deeper context via `search_nodes("project rules")`.

### Rules vs. Other Enforcement Mechanisms

| Mechanism | What It Enforces | How |
|-----------|------------------|-----|
| **Vision Standards** | Core principles (immutable) | Tier-protected KG entities |
| **Architecture Patterns** | Structural decisions (human-gated) | KG entities + governance review |
| **Quality Gates** | Deterministic checks (build, lint, tests) | Tool execution via Quality MCP server |
| **Project Rules** | Behavioral guidance tools can't check | Context injection at agent spawn |

Rules fill the gap that tools can't check: "search for existing patterns before creating new ones" can't be verified by a linter, but it matters for code quality. If a linter or test can check it, use quality gates instead.

### Configuration

Rules are configured in the setup wizard (the "Rules" step after "Quality Config") or edited directly in `.avt/project-config.json`. The wizard shows a token budget meter indicating how much context enabled rules consume, and a warning about the balance between agent quality and agent agency.

---

## VS Code Extension

**Role**: Observability layer — monitors and displays system state. Does NOT orchestrate, spawn agents, or manage sessions. The system works fully from CLI without the extension.

**Implementation**: TypeScript + React (dashboard webview), esbuild + Vite

**Capabilities**:
- **Memory Browser**: KG entities grouped by protection tier
- **Findings Panel**: Quality findings mapped to VS Code diagnostics
- **Tasks Panel**: Task briefs from filesystem
- **Dashboard Webview**: Real-time overview with session state, agent status cards, activity feed, governance decisions panel, research prompts manager
- **Setup Wizard**: 8-step onboarding flow (welcome, vision docs, architecture docs, quality config, rules, permissions, settings, ingestion)
- **Status Bar**: Aggregated system health indicator

**MCP Connectivity**: Connects to the same three MCP servers via HTTP clients (`McpClientService`). Reads only — no writes.

**Key files**: `extension/src/extension.ts` (entry point), `extension/src/providers/DashboardWebviewProvider.ts` (React dashboard host), `extension/src/services/McpClientService.ts` (MCP connections), `extension/webview-dashboard/` (React app)

---

## E2E Testing Harness

An autonomous end-to-end testing system that exercises all three MCP servers across 11 scenarios with 172+ structural assertions.

**How it works**: Each run generates a unique project from a pool of 8 domains (Pet Adoption, Restaurant Reservation, Fitness Tracking, E-commerce, Social Media, Healthcare, Project Management, Fleet Management). Vision standards, architecture patterns, and components are filled from domain-specific templates. All assertions are structural and domain-agnostic — behavioral contracts hold regardless of domain.

**Isolation**: Each scenario gets its own KnowledgeGraph (JSONL), GovernanceStore (SQLite), and TaskFileManager (directory). Scenarios run in parallel via `ThreadPoolExecutor`.

| Scenario | What It Validates |
|----------|-------------------|
| s01 | KG CRUD + tier-based access control (vision entities immutable by workers) |
| s02 | Decision storage, review verdicts, status queries |
| s03 | Governed task pair creation, blocking from birth, release on approval |
| s04 | Attempts to modify vision-tier entities are rejected |
| s05 | deviation/scope_change categories stored and flagged correctly |
| s06 | GovernanceStore.get_status() returns accurate aggregates |
| s07 | Finding → dismiss → audit trail lifecycle |
| s08 | 3 stacked blockers released one at a time |
| s09 | scope_change/deviation → needs_human_review verdict |
| s10 | Unresolved blocks and missing plan reviews caught |
| s12 | KG + Governance + Task system cross-server interplay |

**Usage**:
```bash
./e2e/run-e2e.sh              # standard run
./e2e/run-e2e.sh --keep       # preserve workspace for debugging
./e2e/run-e2e.sh --seed 42    # reproducible domain selection
./e2e/run-e2e.sh --verbose    # debug logging
```

**Key files**: `e2e/run-e2e.sh` (entry point), `e2e/run-e2e.py` (Python orchestrator), `e2e/generator/` (project generation + 8 domain templates), `e2e/scenarios/` (11 test scenarios), `e2e/parallel/executor.py` (ThreadPoolExecutor with isolation)

---

## Persistent State and File Organization

### Runtime Data

| Path | What | Managed By |
|------|------|------------|
| `.claude/collab/knowledge-graph.jsonl` | KG entity/relation persistence | KG Server |
| `.claude/collab/trust-engine.db` | Quality finding audit trails | Quality Server |
| `.claude/collab/governance.db` | Decision store with verdicts | Governance Server |

### Project Configuration

| Path | What |
|------|------|
| `.avt/project-config.json` | Project setup, language settings, quality gate configuration, permissions, project rules |
| `.avt/session-state.md` | Current session goals, progress, blockers, checkpoints |
| `.avt/task-briefs/` | Scoped assignments for worker subagents |

### Archival Memory

The KG Librarian syncs important graph entries to human-readable files:

| Path | What |
|------|------|
| `.avt/memory/architectural-decisions.md` | Significant decisions and rationale |
| `.avt/memory/troubleshooting-log.md` | Problems, what was tried, what worked |
| `.avt/memory/solution-patterns.md` | Promoted patterns with implementations |
| `.avt/memory/research-findings.md` | Key discoveries from researcher output |

### Research

| Path | What |
|------|------|
| `.avt/research-prompts/` | Research prompt definitions |
| `.avt/research-briefs/` | Completed research output from researcher subagent |

### Agent and System Configuration

| Path | What |
|------|------|
| `.claude/agents/*.md` | Six custom subagent definitions (worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward) |
| `.claude/settings.json` | MCP server registration, lifecycle hooks, agent tool permissions |
| `CLAUDE.md` | Orchestrator instructions — task decomposition, governance protocol, quality review, memory protocol, drift detection |

### Documentation

| Path | What |
|------|------|
| `docs/vision/vision.md` | Vision standard definitions (templates for project customization) |
| `docs/architecture/architecture.md` | Architecture standard definitions (templates for project customization) |
| `docs/project-overview.md` | This document |

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | Claude Code CLI + native subagents | Agent spawning, coordination, session management |
| MCP Servers | Python 3.12+ / FastMCP 2.x | Three servers: KG, Quality, Governance |
| KG Persistence | JSONL | Lightweight, version-controllable, matches Anthropic's KG Memory format |
| Decision/Trust Store | SQLite | Zero-config transactional storage for governance and trust engine |
| VS Code Extension | TypeScript + esbuild | Extension host runtime |
| Dashboard | React 19 + Vite | Rich observability webview |
| E2E Testing | Python + Pydantic + ThreadPoolExecutor | Autonomous scenario-based testing |
| Quality Tools | ruff, eslint, prettier, swiftlint, clippy, pytest | Deterministic verification |
| AI Models | Opus 4.5 (judgment), Sonnet 4.5 (routine) | Capability-first model routing |
| Package Management | npm (extension), uv (Python servers) | Standard per ecosystem |
| Version Control | Git + worktrees | Code state, worker isolation, checkpoints |

---

## Getting Started

### Prerequisites

- Claude Code with Max subscription
- Python 3.12+ with `uv` package manager
- Node.js 18+ (for VS Code extension, optional)

### Install Dependencies

```bash
cd mcp-servers/knowledge-graph && uv sync
cd mcp-servers/quality && uv sync
cd mcp-servers/governance && uv sync

# Optional: extension
cd extension && npm install
```

### Start MCP Servers

```bash
# Terminal 1: Knowledge Graph (port 3101)
cd mcp-servers/knowledge-graph && uv run python -m collab_kg.server

# Terminal 2: Quality (port 3102)
cd mcp-servers/quality && uv run python -m collab_quality.server

# Terminal 3: Governance (port 3103)
cd mcp-servers/governance && uv run python -m collab_governance.server
```

### Run Tests

```bash
# Unit tests
cd mcp-servers/knowledge-graph && uv run pytest   # 18 tests, 74% coverage
cd mcp-servers/quality && uv run pytest            # 26 tests, 48% coverage
cd extension && npm test                           # 9 unit tests

# E2E (exercises all 3 servers, 11 scenarios, 172+ assertions)
./e2e/run-e2e.sh
```

### Start a Session

```bash
claude   # CLAUDE.md provides orchestrator instructions automatically
```

---

## Guiding Principles

These principles, drawn from the system's development, govern how it's built and used:

- **Vision First**: Vision standards are immutable by agents. Only humans define the vision. Agents enforce it but never propose changes to it.
- **Build Only What the Platform Cannot Do**: Claude Code handles orchestration natively. Custom infrastructure is limited to three MCP servers providing capabilities the platform genuinely lacks.
- **Intercept Early, Redirect Early**: Implementation tasks are blocked from birth until governance review approves them. No race conditions where work starts before review.
- **Deterministic Verification Over AI Judgment**: The most reliable trust signal is a compiler, linter, or test suite — not another LLM's opinion. Quality gates are deterministic.
- **No Silent Dismissals**: Every dismissed finding requires justification and identity. Audit trails are non-negotiable.
- **Support, Not Policing**: The quality system's primary purpose is making workers produce better work than they would alone — through pattern memory, architectural guidance, and constructive coaching.
- **Research Before Implementing**: For unfamiliar domains or architectural decisions, spawn the researcher first. Workers implement based on research findings, not on their own investigation. This separation keeps workers focused on implementation and prevents them from going down rabbit holes.

---

## Current Status

All four implementation phases are complete:

- **Phase 1** (MCP Servers): KG with JSONL persistence and tier protection, Quality with trust engine and multi-language tool wrapping, Governance with transactional review and governed tasks
- **Phase 2** (Subagents + Validation): Six custom subagent definitions, orchestrator CLAUDE.md, settings and hooks
- **Phase 3** (Extension): VS Code extension with Memory Browser, Findings Panel, Tasks Panel, Dashboard webview, setup wizard
- **Phase 4** (Governance + E2E): Governance server, governed task system, AI-powered review, E2E harness with 11 scenarios

**Planned**: Cross-project memory, multi-worker parallelism patterns, installation script for target projects.

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) — Orchestrator instructions and protocols
- [COLLABORATIVE_INTELLIGENCE_VISION.md](../COLLABORATIVE_INTELLIGENCE_VISION.md) — Original vision document (conceptual foundation)
- [ARCHITECTURE.md](../ARCHITECTURE.md) — Engineering-level architecture specification
- [E2E Testing Harness](../e2e/README.md) — Autonomous test suite documentation
- [Knowledge Graph Server](../mcp-servers/knowledge-graph/README.md) — KG API and tier protection
- [Quality Server](../mcp-servers/quality/README.md) — Quality tools and trust engine
- [Governance Server](../mcp-servers/governance/README.md) — Governance tools and governed tasks
