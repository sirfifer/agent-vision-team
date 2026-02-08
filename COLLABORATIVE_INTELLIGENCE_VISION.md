# Collaborative Intelligence System: Architectural Vision

A system of collaborative agents whose primary purpose is preserving and serving the project's vision and architectural integrity. Every capability this system provides — institutional memory, quality enforcement, research, session management — exists to ensure that all development work, whether by a single agent or a coordinated team, faithfully serves the project's vision and follows established architecture. Originally conceived as a "Quality Co-Agent," the scope expanded when we recognized that code quality is downstream of architecture, and architecture is downstream of vision. Protecting the higher-order concerns is what makes the lower-order ones achievable.

**Execution Platform: Claude Code Max.** This entire system operates through Claude Code sessions on a Claude Max subscription. Claude Code provides the orchestration primitives natively — custom subagents, background task execution, lifecycle hooks, parallel sessions, worktree isolation, session resume — and MCP servers extend those primitives with persistent institutional memory, deterministic quality verification, and transactional governance review. No API keys are needed. No external orchestration frameworks. The platform handles coordination; we build only what it cannot do.

**Platform-Native Philosophy.** This architecture is deliberately built on top of Claude Code's native capabilities rather than around them. Where the v1 design called for a custom Communication Hub server and extension-driven session management, we now use Claude Code's built-in subagent system, Task tool, and lifecycle hooks. The result is less custom code, faster validation, and tighter integration with the platform's evolution. This is also an experiment: by pushing the boundaries of what native primitives can handle, we'll learn precisely where custom infrastructure becomes necessary — and build it with that hard-won knowledge rather than speculation.

---

## Core Principles

**P1: Vision First, Architecture Second, Quality Third**
The system's hierarchy of concerns mirrors the hierarchy of what matters in a project. Vision (what the project IS and who it serves) governs architecture (how we build it). Architecture governs quality (the standards we enforce). Every agent's work is measured against this hierarchy: a perfectly linted function that violates the project's voice-first design is a failure, not a success. Vision standards are immutable by agents (only the human defines the vision). Architectural standards are high-friction (agents propose changes, human approves). Quality standards are automated and low-friction. This ordering ensures the system protects what matters most.

**P2: Mutual Confidence, Not Gatekeeping**
The quality system and dev agents should "have each other's back." Confidence in tool calls comes from genuine understanding of the VALUE of each action. The quality agent doesn't just check boxes; it understands why a check matters. The dev agent trusts that quality feedback is genuinely helpful. Neither side "owns" quality; it's shared.

**P3: Bidirectional Agency**
The quality system is not an admonishing schoolmarm. It pushes back constructively, questions architectural decisions, but ultimately enables the coding agent to do its best work. The dev agent should feel supported, not policed.

**P4: True Multi-Agentic Composition**
Not "multiple copies of the same thing." True specialization where:
- Task specialists handle specific domains (CodeRabbit for code review, specialized linters per language)
- External specialist agents are delegated to and their output consumed agentically (not just human-readable PR comments)
- If something is 3x better at TypeScript linting, it gets the TypeScript work

**P5: Specialist Delegation with Agentic Information Exchange**
External tools designed for human consumption (CodeRabbit PR reviews, etc.) should be consumed programmatically. The information exchange between all agents should be agentic and full of agency, not limited to human-readable formats.

**P6: Justified Complexity / Simplicity as a Vector**
Every architectural decision must justify its existence. "Simple" is not a state but an intention, a constant reflective pressure. When pushing hard on features, the answer will often be "yes, this earns its place." But not always. Architectural flexibility and pluggability where needed, but not where it doesn't earn its keep.

**P7: Extended Autonomous Sessions (The Ultimate Goal)**
A system of 1-to-many coding agents + the quality system works for hours (many hours) without:
- Derailing or losing focus
- Quality degradation
- Going into the weeds
- Being unchecked

End result is not just what was hoped for but potentially BETTER. That success is attributable specifically to the collaboration, not achievable by multiple Claude Code instances alone.

**P8: Claude Code Max as the Execution Platform**
All agentic work runs through Claude Code sessions on a Max subscription. This means:
- The orchestrator is the human's primary Claude Code session
- Workers are Claude Code subagents spawned via the Task tool, running in worktrees or background
- The quality reviewer is a Claude Code subagent with access to Quality MCP tools; the governance reviewer validates decisions via the Governance MCP server
- MCP servers provide unique capabilities the platform lacks: persistent institutional memory, deterministic quality verification, and transactional governance review
- Git coordinates code state; the filesystem stores artifacts and human-readable archives
- The human developer is always the ultimate orchestrator with Claude Code as the instrument
- Model selection follows "capability first": Opus 4.6 is the default for anything requiring judgment; Sonnet 4.5 for genuinely routine tasks where speed is an advantage; Haiku 4.5 only for purely mechanical operations

**P9: Build Only What the Platform Cannot Do**
Before building any custom infrastructure, verify that Claude Code's native capabilities don't already solve the problem. Custom MCP servers are justified only for capabilities the platform genuinely lacks. Custom orchestration code is justified only when declarative configuration (CLAUDE.md, subagent definitions, hooks) cannot express the needed behavior. This principle kept us from building a Communication Hub server and extension-driven session management — Claude Code's subagent system, Task tool, and lifecycle hooks already handle those concerns.

---

## The Core Metaphor: A Team with a Shared Mission

A pipeline is: hooks fire, tools run, state files update, agents read state. That's plumbing. This system is a **team united by a shared mission**: realizing the project's vision through disciplined architecture and quality execution. Every member's work, from code generation to quality review to research, is measured against that mission.

- Members have distinct expertise and genuinely different perspectives
- They communicate bidirectionally with rich context, not just pass structured findings
- They develop working confidence in each other through track record, not just permission scoping
- The quality of the collective output exceeds what any individual member could produce
- They can sustain focus and coherence over long working sessions
- **Every member understands the project's vision and protects it.** The quality subagent is the explicit guardian, but all sessions operate within the vision's boundaries.

The architecture supports this at every level: the knowledge graph encodes vision and architectural standards that all sessions consult, MCP servers provide the persistent memory, quality verification, and governance review, Claude Code's native primitives provide the orchestration, and git provides the transaction log.

---

## The Platform: Claude Code Max + MCP Servers

Claude Code provides the orchestration primitives natively. MCP servers extend those primitives with capabilities the platform does not provide. The division is clear and deliberate.

### What Claude Code Provides (Native — We Don't Rebuild These)

| Capability | Claude Code Primitive | How We Use It |
|---|---|---|
| **Agent spawning** | Custom subagents (`.claude/agents/*.md`) | Define worker, quality-reviewer, kg-librarian, governance-reviewer, researcher, project-steward as subagent files |
| **Parallel execution** | Task tool with `run_in_background` | Orchestrator spawns multiple workers simultaneously |
| **Agent coordination** | Parent-child communication via Task results | Orchestrator delegates work, receives results, chains subagents |
| **Lifecycle hooks** | `SubagentStart`, `SubagentStop`, `PreToolUse`, `PostToolUse` | Track when subagents begin/end, validate operations, coordinate holistic governance review |
| **Worker isolation** | Git worktrees + parallel sessions | Each worker subagent operates in its own worktree |
| **Session configuration** | CLAUDE.md + skills injection | Project CLAUDE.md instructs the orchestrator; skills preload domain knowledge |
| **Model routing** | Per-subagent model selection | Opus 4.6 for judgment, Sonnet 4.5 for routine, Haiku 4.5 for mechanical |
| **Session persistence** | `--resume`, session IDs, transcript storage | Multi-day continuity for long-running work |
| **Permission control** | `permissionMode`, tool restrictions per subagent | Quality subagent is read-focused, workers have edit access |

### What MCP Servers Provide (Custom — Unique Value)

| Capability | MCP Server | Why the Platform Can't Do This |
|---|---|---|
| **Persistent institutional memory** | Knowledge Graph server | Claude Code sessions are ephemeral. Memory doesn't survive across sessions natively. The KG provides persistent, structured, tier-protected memory that all sessions can query. |
| **Deterministic quality verification** | Quality server | Claude Code can invoke tools, but doesn't bundle linter/formatter/test runner wrappers. The Quality server provides a unified MCP interface to ruff, eslint, swiftlint, pytest, etc., plus a trust engine for finding management. |
| **Transactional governance review** | Governance server | Claude Code provides task management but not synchronous governance checkpoints. The Governance server provides transactional decision review, governed task lifecycle management, holistic collective-intent review, and plan/completion verification, ensuring every key decision is reviewed against vision standards before implementation proceeds. |

### What We Deliberately Don't Build

| Capability | Why Not |
|---|---|
| **Communication Hub / message router** | Claude Code's Task tool + subagent system handles agent spawning, coordination, and result delivery. The Governance MCP server provides transactional review checkpoints (synchronous tool-call-based review, not a message router), and its SQLite database serves as the audit trail for decisions and verdicts. |
| **Agent registry** | The orchestrator knows who it spawned. SubagentStart/SubagentStop hooks can track lifecycle events. |
| **Extension-driven orchestration** | Claude Code IS the orchestrator. The extension monitors; it doesn't drive. |
| **Custom session management** | Subagent definitions + CLAUDE.md provide declarative session configuration. No imperative process management needed. |
| **LangGraph / AutoGen / CrewAI** | Requires API keys. Incompatible with Claude Code Max. Claude Code's native primitives cover the same use cases. |

### Genuine Boundaries

| Boundary | Why | Implication |
|---|---|---|
| Subagent nesting | Subagents cannot spawn subagents. | Workflows are one level deep. The orchestrator spawns all workers directly. |
| Background subagent MCP access | Background subagents cannot use MCP tools. | Workers that need KG/Quality MCP access must run in foreground, or the orchestrator pre-fetches context for them. |
| Dynamic model switching | Model is set at session/subagent creation. | Strategic model selection happens at spawn time. |
| ~~Session-scoped tasks~~ | Claude Code's native Task List now provides persistence across sessions. | Cross-session continuity uses the Task List alongside the KG and filesystem. This was a previous limitation that has since been resolved by the platform. |

---

## 1. Agent Topology

The three-tier oversight model maps onto Claude Code's native subagent system. Six specialized subagents serve distinct roles, with five spawned by the orchestrator and one (the governance-reviewer) invoked internally by the Governance server:

```
┌──────────────────────────────────────────────────────────────────┐
│               HUMAN + PRIMARY SESSION (Orchestrator)              │
│   The human developer in an interactive Claude Code session.      │
│   Maintains goals, delegates work, reviews results,               │
│   manages checkpoints via git.                                    │
└────────────┬─────────────────────────────────────────────────────┘
             │ spawns via Task tool
             │
    ┌────────┴─────────────────────────────────────────────────┐
    │                                                          │
    │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │
    │  │    WORKER     │  │   QUALITY     │  │  RESEARCHER  │  │
    │  │    SUBAGENT   │  │   REVIEWER    │  │  SUBAGENT    │  │
    │  │  (.claude/    │  │   SUBAGENT    │  │ (.claude/    │  │
    │  │   agents/     │  │  (.claude/    │  │  agents/     │  │
    │  │   worker.md)  │  │   agents/     │  │  researcher  │  │
    │  │              │  │   quality-    │  │  .md)        │  │
    │  │              │  │   reviewer    │  │              │  │
    │  │              │  │   .md)        │  │              │  │
    │  └──────┬───────┘  └──────┬────────┘  └──────────────┘  │
    │         │                 │                               │
    │         │   MCP Tools     │                               │
    │         ├─────────────────┤                               │
    │         │                 │                               │
    │    ┌────▼──────┐   ┌─────▼───────┐   ┌──────────────┐   │
    │    │Knowledge  │   │  Quality    │   │ Governance   │   │
    │    │  Graph    │   │  Server     │   │ Server       │   │
    │    │  Server   │   │             │   │              │   │
    │    └───────────┘   └─────────────┘   └──────┬───────┘   │
    │                                             │            │
    │                              invokes via claude --print  │
    │                                             │            │
    │                                    ┌────────▼─────────┐  │
    │                                    │   GOVERNANCE     │  │
    │                                    │   REVIEWER       │  │
    │                                    │  (.claude/agents/ │  │
    │                                    │   governance-    │  │
    │                                    │   reviewer.md)   │  │
    │                                    │  (NOT spawned by │  │
    │                                    │   orchestrator)  │  │
    │                                    └──────────────────┘  │
    │                                                          │
    │  ┌────────────────────────────────────────────────────┐  │
    │  │   KG LIBRARIAN SUBAGENT                            │  │
    │  │  (.claude/agents/kg-librarian.md)                   │  │
    │  │   Curates memory after work sessions                │  │
    │  └────────────────────────────────────────────────────┘  │
    │                                                          │
    │  ┌────────────────────────────────────────────────────┐  │
    │  │   PROJECT STEWARD SUBAGENT                         │  │
    │  │  (.claude/agents/project-steward.md)                │  │
    │  │   Maintains project hygiene and organization        │  │
    │  └────────────────────────────────────────────────────┘  │
    │                                                          │
    └──────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────┐
    │    VS Code Extension (observability only)                 │
    │    Reads from MCP servers + filesystem                    │
    │    Displays agents, findings, memory, tasks               │
    └──────────────────────────────────────────────────────────┘
```

**The Orchestrator: Human + Primary Session**
- The human developer is the strategic decision-maker who directs the team.
- The primary Claude Code session acts as the "project lead" brain, using the Task tool to spawn specialized subagents.
- Research on Human-Agent Interaction validates this: the "Co-pilot" model where humans navigate and agents drive consistently outperforms full automation.
- The orchestrator session uses its own built-in subagents (Explore, Plan) for investigation, and spawns custom subagents for sustained specialized work.

**Worker Subagents: Spawned via Task Tool**
- Each worker is a custom subagent defined in `.claude/agents/worker.md` with a specialized system prompt.
- Workers receive their brief through the task prompt or by reading structured task files.
- Workers can run in foreground (with MCP access to KG and Quality) or background (for parallelism, but without MCP).
- Workers operate in isolated git worktrees to prevent file conflicts.
- Results flow back to the orchestrator naturally through the Task tool's return mechanism.

**Quality Reviewer Subagent: The Three-Lens Evaluator**
- A custom subagent defined in `.claude/agents/quality-reviewer.md` with access to Quality MCP server tools.
- Evaluates work through three ordered lenses: vision alignment first, architectural conformance second, quality compliance third.
- Returns structured findings to the orchestrator, who routes them back to workers.
- Can be spawned for on-demand review or chained after worker completion.

**KG Librarian Subagent: Memory Curator**
- A custom subagent defined in `.claude/agents/kg-librarian.md` with KG MCP server access.
- Curates institutional memory: consolidates observations, promotes patterns, removes stale entries.
- Ensures tier protection consistency (no vision entities modified by agents).
- Syncs important graph entries to archival files.
- Spawned periodically by the orchestrator after work sessions.

**Governance Reviewer Subagent: Decision Validator**
- A custom subagent defined in `.claude/agents/governance-reviewer.md`, invoked by the Governance MCP server via `claude --print` — not spawned directly by the orchestrator.
- Reviews decisions, plans, and completions against vision standards and institutional memory.
- Returns structured verdicts (approved, blocked, needs_human_review) with guidance.
- Operates as the internal reasoning engine for all governance checkpoints.
- This architectural distinction matters: the governance-reviewer is called synchronously within a tool call, ensuring that review is transactional and completes rapidly, not fire-and-forget.

**Researcher Subagent: Intelligence Gatherer**
- A custom subagent defined in `.claude/agents/researcher.md`, spawned by the orchestrator for investigative work.
- Gathers intelligence to inform development decisions: evaluates technologies, compares approaches, monitors external dependencies.
- Operates in two modes: periodic/maintenance research (tracking API changes, deprecations, security advisories) and exploratory/design research (deep investigation before architectural decisions).
- Outputs structured research briefs stored in `.avt/research-briefs/`.
- Uses Opus 4.6 for novel domains and architectural analysis, Sonnet 4.5 for routine changelog monitoring.
- Workers implement; researchers investigate. This separation keeps workers focused on execution.

**Project Steward Subagent: Hygiene Guardian**
- A custom subagent defined in `.claude/agents/project-steward.md`, spawned by the orchestrator for organizational reviews.
- Monitors project-level files, naming conventions, folder organization, documentation completeness, and cruft.
- Produces structured review reports and records conventions in the KG for future reference.
- Can apply mechanical fixes (renaming, cruft removal) when non-controversial.
- Spawned periodically for consistency reviews, before releases, or after major refactoring.

**VS Code Extension: Observability Layer**
- Does NOT spawn sessions, manage processes, or orchestrate agents.
- DOES connect to MCP servers to display state: KG entities, quality findings, agent activity.
- DOES watch the filesystem for task briefs and session state changes.
- Provides TreeView panels, diagnostics integration, and a monitoring dashboard.
- The system works fully from CLI without the extension.

---

## 2. Oversight Tiers: Vision, Architecture, and Quality

The system organizes its oversight responsibilities into three tiers, ordered by what matters most. This hierarchy is the organizing principle for everything that follows: how findings are prioritized, what memory protects, and how trust is calibrated.

### The Three Tiers

| Tier | Scope | Mutability | Verification |
|------|-------|------------|-------------|
| **T1: Vision** | Project identity, fundamental purpose, design philosophy. What the project IS and who it serves. | **Immutable by agents.** Only the human defines and modifies vision. Agents verify vision alignment but never propose changes to it. | Quality reviewer subagent checks all work against vision documents and vision-tier knowledge graph entities. Vision conflicts are the highest-severity finding and stop work immediately. |
| **T2: Architecture** | Established patterns, conventions, performance targets, resiliency standards, resource usage requirements. How the project is built to realize the vision. | **High-friction.** Agents can propose changes through structured proposals. Human must approve before any architectural standard changes. | Quality reviewer consults the knowledge graph for architectural entities before reviewing changes. Redirects deviations that lack an approved change proposal. Monitors for "ad-hoc pattern drift." |
| **T3: Quality** | Lint, syntax, security scanning, test coverage, formatting. The standards that code must meet. | **Low-friction, automated.** Agents fix deterministic issues autonomously. | Quality MCP server wraps linters, formatters, test runners. Quality reviewer auto-fixes deterministic violations. Goal: code passes all checks on first commit attempt. |

### Why This Ordering Matters

A perfectly linted function that violates the project's voice-first design is a failure, not a success. A well-architected service that ignores an established DI pattern creates maintenance debt, regardless of how clean its code is. The tiers ensure that agents address the most important concerns first:

1. **Vision lens** (first): Does this work align with project identity?
2. **Architecture lens** (second): Does this work follow established patterns?
3. **Quality lens** (third): Does the code pass automated checks?

A worker should never hear "fix your lint" when the real problem is "this feature contradicts the voice-first design."

### Change Protocols

**Tier 1 (Vision) Changes:**
- Vision documents are read-only for all agents
- The knowledge graph marks vision entities with `mutability: human_only`
- If a worker's output conflicts with a vision standard, the quality reviewer raises the conflict with severity `vision_conflict`
- Agents adapt their work to fit the vision. They never propose that the vision adapt to fit their work.

**Tier 2 (Architecture) Changes:**
- Architecture standards can evolve, but changes require a structured proposal
- An agent that believes an architectural standard should change creates a `change_proposal` returned to the orchestrator: current standard, proposed change, rationale, impact analysis
- The proposal is flagged for human review
- Until the human approves, the existing standard is enforced
- Approved changes update the knowledge graph entity and the corresponding living document
- The quality reviewer specifically monitors for "ad-hoc pattern drift": when a worker creates something new instead of using an existing established function or pattern

**Tier 3 (Quality) Changes:**
- Quality rules are largely automated and low-friction
- Tool configurations can be updated as part of normal work, subject to the Tool Trust Doctrine (never suppress findings without proof)
- The quality reviewer auto-fixes deterministic issues (formatting, simple lint violations) silently
- The goal is that code passes all quality checks on first commit, preventing the stop-and-fix cycle

### Conflict Resolution

| Conflict Tier | Response | Who Resolves |
|---|---|---|
| T1: Vision | **Stop.** Work must conform to vision. Escalate to human if ambiguous. | Human |
| T2: Architecture | **Pause.** Provide rationale and reference the established pattern. Worker adapts or submits a formal change proposal. | Worker + Human (for proposals) |
| T3: Quality | **Auto-fix** if deterministic. Report if judgment is needed. Low urgency. | Agent (autonomous) |

---

## 3. Communication: Native Primitives + Structured Files

Claude Code's subagent system provides the primary communication channel. MCP servers provide persistent memory. The filesystem provides auditable artifacts.

### How Agents Communicate

**Primary: Orchestrator as Communication Hub**

The orchestrator session is the natural communication hub. It spawns all subagents and receives all results. This replaces the need for a custom MCP-based message router:

```
Orchestrator spawns Worker → Worker returns results
Orchestrator spawns Quality Reviewer with Worker's diff → Reviewer returns findings
Orchestrator routes findings back to Worker (as task context) → Worker addresses them
Orchestrator spawns Quality Reviewer again to verify → Reviewer confirms resolution
```

Every finding includes a tier and severity so the orchestrator can prioritize correctly.

**Secondary: Knowledge Graph (Persistent Asynchronous Memory)**

The MCP Knowledge Graph serves as the persistent communication channel that survives across sessions:

```
Worker queries KG → discovers vision constraints for current component
Quality reviewer writes finding outcomes to KG → future sessions learn from them
Librarian curates KG → consolidates observations, promotes patterns
Next session queries KG → starts with institutional knowledge, not a blank slate
```

**Tertiary: Structured Files (Artifacts and Archives)**

Some content is naturally suited to files: task briefs, research reports, architecture reviews, and other artifacts that benefit from version control, human readability, and persistence independent of any running service:

```
.avt/
├── session-state.md          # Current goals, progress, blockers
├── task-briefs/              # Task assignments for worker sessions
│   ├── task-001-auth-fix.md
│   └── task-002-test-coverage.md
├── artifacts/                # Larger documents, reports, plans
└── memory/                   # Archival copies of KG knowledge
    ├── architectural-decisions.md
    ├── troubleshooting-log.md
    ├── solution-patterns.md
    └── research-findings.md  # Baseline knowledge from research
```

**Quaternary: Git as Code State Protocol**

Git coordinates code-level changes:
- Workers stage changes on feature branches in worktrees
- The orchestrator examines branch state to understand progress
- Git's conflict detection handles cases where workers touch the same file
- Every code change is versioned and reversible

### The Protocol-First Principle

Structured protocols beat unstructured chat for multi-agent coordination:
- **Every inter-agent exchange is structured** — findings returned as typed objects with tier, severity, component, rationale, suggestion
- **The orchestrator is the message broker** — routes findings, aggregates results, manages flow
- **The KG handles persistent knowledge** — institutional memory, not ephemeral messages
- **Files handle artifacts** — auditable, version-controlled, human-readable
- **Git is the code transaction log** — every change is versioned and reversible
- **No free-text chat between agents** — all communication uses structured returns or typed KG entries

---

## 4. Orchestration: CLAUDE.md as the Brain

The project's CLAUDE.md and custom subagent definitions provide declarative orchestration. This replaces the imperative process management that the v1 extension was designed to handle.

### How It Works

The orchestrator session's CLAUDE.md contains instructions for:
- How to decompose tasks into worker subagents
- When and how to invoke quality review
- How to use the Knowledge Graph for institutional memory
- Checkpoint protocol (git tag + session state update)
- Drift detection heuristics

Custom subagent definitions in `.claude/agents/` specify:
- Each subagent's system prompt and role
- Which tools it can access (KG MCP, Quality MCP, Governance MCP, or restricted)
- Which model to use
- What hooks to run on lifecycle events

This is **declarative orchestration** — the behavior is specified in configuration files, not in TypeScript code managing processes. It's simpler, more maintainable, and evolves with the platform.

### Session State and Checkpoint-Resume

```yaml
# .avt/session-state.md
session_id: "2026-01-29-feature-sprint"
started: "2026-01-29T09:00:00Z"
goals:
  - id: G1
    description: "Implement hands-free voice navigation"
    acceptance_criteria:
      - "All voice commands recognized with >95% accuracy"
      - "Zero UI taps required during oral practice"
    status: in_progress
current_phase: "implementation"
checkpoints:
  - id: CP1
    timestamp: "2026-01-29T10:30:00Z"
    description: "Voice command protocol defined and tested"
    git_ref: "abc1234"
blockers: []
```

Checkpoint creation: After each meaningful unit of work, the orchestrator updates `session-state.md` and tags the git state. If something goes wrong, work resumes from the last checkpoint. Claude Code's session resume handles conversation context; git handles code state.

### Model Routing

| Task Type | Model | Rationale |
|---|---|---|
| Orchestrator session | Opus 4.6 | Strategic decisions, cross-session coordination, judgment calls |
| Quality reviewer subagent | Opus 4.6 | Vision enforcement and architectural review require deep reasoning |
| Governance reviewer subagent | Sonnet 4.5 | Standards verification is structured; invoked by Governance server via `claude --print` |
| Complex code generation | Opus 4.6 | Novel implementations, architectural decisions |
| Routine code generation | Sonnet 4.5 | Well-defined tasks following established patterns |
| Research (novel domains) | Opus 4.6 | Architectural decisions, security analysis, ambiguous requirements |
| Research (routine monitoring) | Sonnet 4.5 | Changelog monitoring, version updates, API documentation |
| Fast exploration | Haiku 4.5 (Explore subagent) | Speed is the advantage; exploration is about breadth |
| KG librarian | Sonnet 4.5 | Curation is structured and pattern-based |
| Project steward | Sonnet 4.5 | Hygiene checks are pattern-based and well-defined |

### Drift Detection

The orchestrator monitors for drift signals:
- **Time drift**: Worker has been on a single task exceeding threshold without progress
- **Loop drift**: Repeated failures on the same issue
- **Scope drift**: Worker producing artifacts not related to session goals
- **Quality drift**: New findings accumulating faster than they're resolved

On detection, the orchestrator intervenes — redirecting the worker, suggesting a different approach, or escalating to the human.

---

## 5. Memory Architecture: MCP-Backed Institutional Knowledge

Simple vector storage fails for code development. The problems: no temporal reasoning, no relational context, "context clutter" as similar-looking but outdated information pollutes retrieval. The solution is structured, actively curated memory served by a persistent MCP server.

### The Memory Stack

**Layer 1: MCP Knowledge Graph (Active, Queryable Memory)**

All sessions connect to the same KG MCP server and access the same knowledge graph. The KG stores:
- **Entities**: Components, services, patterns, decisions, problems, vision standards, architectural standards
- **Relations**: "depends_on", "implements_pattern", "was_fixed_by", "rejected_in_favor_of", "governed_by", "follows_pattern"
- **Observations**: Atomic facts attached to entities (timestamps, outcomes, rationale, protection tier, mutability)

Every entity carries a `protection_tier` observation encoding its position in the oversight hierarchy:
- `protection_tier: vision` / `mutability: human_only` for vision standards
- `protection_tier: architecture` / `mutability: human_approved_only` for architectural standards and established components
- `protection_tier: quality` / `mutability: automated` for quality rules

Example interactions via MCP tools:
```
# Record a vision standard (Tier 1, immutable by agents)
→ create_entities([{name: "hands_free_first_design", entityType: "vision_standard",
    observations: ["protection_tier: vision",
                   "mutability: human_only",
                   "source_document: docs/design/HANDS_FREE_FIRST_DESIGN.md",
                   "Voice is PRIMARY interaction mode within activities",
                   "IMMUTABLE BY AGENTS."]}])

# Record an architectural component (Tier 2, human-approved changes only)
→ create_entities([{name: "KBOralSessionView", entityType: "component",
    observations: ["protection_tier: architecture",
                   "mutability: human_approved_only",
                   "Uses protocol-based DI via init injection",
                   "GUARD: Fix targeted, don't rewrite."]}])

# Query before modifying a component
→ search_nodes("KBOralSessionView")
← {entities: [{name: "KBOralSessionView",
    observations: ["protection_tier: architecture", ...],
    relations: [{to: "ServiceRegistry", type: "follows_pattern"},
                {to: "hands_free_first_design", type: "governed_by"}]}]}
```

**Layer 2: Structured Files (Archival, Human-Readable Memory)**

Some memory is better as files: version-controlled, human-reviewable, and readable without an MCP server running.

```
.avt/memory/
├── architectural-decisions.md   # ADR-style decision log
├── troubleshooting-log.md       # Append-only problem/attempt/outcome log
├── solution-patterns.md         # Curated patterns extracted from experience
└── research-findings.md         # Key discoveries establishing baselines
```

The KG is the live, queryable interface agents use during work. The files are the durable archive. The librarian subagent syncs between them.

### Three Memory Types

**1. Architectural Memory** — Protect established components from casual rewriting. Components as entities with observations about their architecture, effort invested, and guard notes. Relations map dependencies and pattern adherence.

**2. Troubleshooting Memory** — When a problem recurs, know what was tried before. Problems as entities with observations for each attempt and its outcome. Relations link problems to components and successful fixes.

**3. Solution Memory** — Recognize when a current situation matches a previously-solved class of problem. Patterns as entities with observations about when they apply. Relations link patterns to components that exemplify them.

### The Librarian Principle

Active curation is essential. The librarian subagent:
- Reviews what happened after work sessions and updates the KG
- Consolidates observations (multiple attempts become one coherent entry)
- Promotes recurring troubleshooting patterns to solution memory
- Flags stale entries and removes obsolete observations
- Syncs important graph entries to archival files
- Validates protection tiers remain consistent
- Does NOT save everything — failed approaches are noted briefly; successful patterns get detailed entries

### Memory Consultation Protocol

Every worker subagent's startup should include:
1. Query the KG for `vision_standard` entities that govern the task's components (Tier 1 check)
2. Query for `architectural_standard` and `component` entities related to the task, noting their `protection_tier` and established patterns (Tier 2 check)
3. Check for solution patterns that match the task type
4. If the task involves a component with troubleshooting history, review those entries

This is encoded in the subagent system prompt and CLAUDE.md, so it happens automatically.

---

## 6. Mutual Confidence: Earned Trust Through Verification

"Blind trust" between agents leads to catastrophic error propagation. But LLMs are also terrible at self-assessing their own confidence. The solution is externally grounded trust.

### The Zero-Trust-with-Verification Model

**a) Deterministic Verification (The Primary Trust Mechanism)**
The most reliable trust signal is a compiler, linter, or test suite — not another LLM's opinion.
- Code must compile before review
- Lint must pass before review
- Tests must pass before merge
- Coverage must meet threshold before marking complete

The Quality MCP server is the embodiment of this principle.

**b) Track Record (Observable Outcomes)**
Each agent-to-agent interaction has an observable outcome. The KG tracks these:
- Was the architectural concern legitimate? (11/12 = high trust)
- Did the suggested fix work? (8/10 = good track record)

This is context that informs how the orchestrator allocates work and how much scrutiny to apply.

**c) Explanation Quality (Show Your Work)**
Findings with project-specific rationale carry more weight than generic lint rules:
- HIGH: "This force unwrap is dangerous because KBOralSessionView can receive nil from the STT pipeline during network transitions"
- LOW: "Force unwrapping should be avoided"

The quality reviewer's findings must include rationale tied to this specific codebase.

**d) Proportional Response (Calibrated Scrutiny)**

| Severity | Tier | Response |
|---|---|---|
| Vision conflict | T1 | **Work stops.** Must conform to vision. Escalate to human. |
| Security | T2/T3 | Immediate escalation to human |
| Architectural | T2 | Direct finding, requires resolution before proceeding |
| Logic | T3 | Finding with rationale, blocks task completion |
| Style | T3 | Note, no urgency |
| Formatting | T3 | Auto-fix silently |

### Circuit Breakers

- **Claude Code PreToolUse hooks**: Verify operations and coordinate work sequencing during holistic review
- **Holistic review checkpoint**: PreToolUse on Write|Edit|Bash|Task coordinates work while collective review completes (typically seconds)
- **Git guards**: Pre-commit hooks verify quality gates
- **Token budgets**: Natural session limits prevent infinite loops
- **Drift detection**: Orchestrator monitors for time/loop/scope/quality drift
- **The human**: Always in the loop at the orchestrator level

---

## 7. Extended Session Coherence

Research identifies "Context Drift" and "Goal Drift" as primary failure modes. Five mechanisms address this:

**a) Session Goals + Acceptance Criteria** — Set once, reference always. Every subagent can reference session-state.md. When the quality reviewer pushes back, it's grounded in "this doesn't meet acceptance criterion #3."

**b) Checkpoint-Resume via Git** — After each meaningful unit, update session-state.md and tag the git state. Claude Code's session resume handles conversation context; git handles code state.

**c) Drift Detection** — The orchestrator monitors for drift signals and intervenes.

**d) Context Hygiene** — Session segmentation (new sessions for new phases), subagent delegation (verbose operations stay in subagent context), structured summaries between phases.

**e) Progressive Confidence** — Early: more scrutiny. Mid-session with good track record: lighter touch. Late or after regressions: increase scrutiny.

---

## 8. The Enabling Role

The quality system's primary purpose is making the dev agent produce better work than it would alone.

**Pattern Memory**: "In this codebase, new services always implement the protocol pattern. Here's TTSService as an example." Proactive guidance, not reactive checking.

**Architectural Guardrails as Navigation Aids**: Instead of "you violated the layer boundary," the message is: "The pattern for accessing the data layer from a view model is through the ServiceRegistry. Here's how SessionManager does it."

**Suggestion, Not Just Rejection**: When a finding requires a non-obvious fix, the quality reviewer suggests HOW, not just WHAT.

**Coaching Over Replacement**: The quality system explains WHY patterns exist, not just enforcing them.

---

## 9. Specialist Routing

**Capability Registry** (static YAML, extended when needed):

```yaml
specialists:
  - id: swiftlint
    domains: [swift, ios]
    capabilities: [lint, style]
    strength: high

  - id: ruff
    domains: [python]
    capabilities: [lint, style, security]
    strength: high

  - id: coderabbit
    domains: [all]
    capabilities: [review, architecture, patterns]
    strength: high
    type: external
    latency: async
```

**Routing logic**: Determine domain → determine concern type → route to highest-strength specialist → fall back to generalist if no specialist exists.

---

## 10. What We Build vs. What We Don't

### What We Build (Custom MCP Servers)

| Server | Purpose | Why Custom |
|---|---|---|
| **Knowledge Graph** | Persistent institutional memory with tier-aware protection | No existing MCP server provides tier-based access control (vision=immutable, architecture=human-gated, quality=open). This is our core differentiator. |
| **Quality** | Unified quality tool interface + trust engine | Wraps ruff, eslint, swiftlint, pytest, etc. behind MCP with trust engine for finding management. No existing server does this. |
| **Governance** | Transactional decision review + governed task lifecycle | Provides synchronous governance checkpoints where every key decision is reviewed against vision standards before implementation. Integrates with Claude Code's Task List for governed task creation and blocker management. No existing server provides this transactional review pattern. |

### What We Configure (Claude Code Native)

| Artifact | Purpose |
|---|---|
| `.claude/agents/worker.md` | Worker subagent definition |
| `.claude/agents/quality-reviewer.md` | Quality reviewer subagent definition |
| `.claude/agents/kg-librarian.md` | Memory curator subagent definition |
| `.claude/agents/governance-reviewer.md` | Governance reviewer subagent definition (invoked by Governance server) |
| `.claude/agents/researcher.md` | Researcher subagent definition |
| `.claude/agents/project-steward.md` | Project steward subagent definition |
| `CLAUDE.md` | Orchestrator instructions |
| `.claude/settings.json` | Hooks for SubagentStart/SubagentStop events |

### What We Don't Build

| Idea | Verdict | Reasoning |
|---|---|---|
| Communication Hub MCP server | Partially addressed | The Governance MCP server provides transactional review checkpoints (synchronous tool-call-based, not a message router). Its SQLite database serves as the decision audit trail. A general-purpose message router remains unnecessary — Claude Code's Task tool handles coordination. |
| Extension-driven session management | Skip | Claude Code spawns and manages subagents natively. |
| Custom agent registry | Skip | Orchestrator tracks who it spawned. SubagentStart hooks can log events. |
| External orchestration frameworks | Skip | Requires API keys. Incompatible with Claude Code Max. |
| Kafka / Redis event bus | Skip | Overkill for <10 agents on one machine. |
| Quantified confidence scores | Skip | LLM self-assessment is unreliable. Use structural trust instead. |

### The Decision Principle

Before building anything custom, ask: "Does Claude Code already do this natively?" If yes, use the native capability. Then ask: "Does an MCP server already exist that does this?" If yes, evaluate it. Only build custom when the platform genuinely lacks the capability AND it's critical enough to warrant the maintenance burden.

---

## 11. Implementation Approach

### Phase 1: MCP Servers -- COMPLETE

Stood up the Knowledge Graph and Quality MCP servers with full functionality:

**Knowledge Graph Server (port 3101):** JSONL persistence, full CRUD for entities/relations/observations, tier protection enforced at server level.

**Quality Server (port 3102):** Wraps ruff, eslint, swiftlint, pytest, and more behind a unified MCP interface. Trust engine with SQLite-backed finding history. Quality gate aggregation.

### Phase 2: Subagents + End-to-End Validation -- COMPLETE

Created Claude Code subagent definitions and validated the full orchestrator-worker-reviewer loop from CLI:
- Defined all six subagent files in `.claude/agents/`
- Wrote orchestrator CLAUDE.md with task decomposition, quality review, memory, and governance protocols
- Validated: orchestrator spawns worker, worker queries KG, implements, quality reviewer evaluates, findings route back, worker fixes, gates pass

### Phase 3: VS Code Extension -- COMPLETE

Built the extension as an observability layer:
- MCP HTTP client connecting to all three servers
- TreeView providers wired to real data (agents, findings, memory, tasks)
- Dashboard webview with setup wizard and multi-step workflow tutorial
- Filesystem watchers for session state and task briefs

### Phase 4: Governance + E2E Testing -- COMPLETE

Added the Governance MCP server and comprehensive end-to-end testing:

**Governance Server (port 3103):** Transactional decision review, governed task lifecycle (create, verify, release), holistic collective-intent review with settle/debounce detection, plan and completion verification. Integrates with Claude Code's Task List for persistence. Uses the governance-reviewer subagent internally via `claude --print`. Two-layer assurance: PostToolUse detection + PreToolUse coordination on Write|Edit|Bash|Task. Reliable verification enables safe multi-agent parallelism.

**E2E Testing Harness:** 14 scenarios with 292+ structural assertions exercising all three MCP servers. Random domain generation, parallel execution with full isolation, domain-agnostic validation.

### Phase 5: Expand -- IN PROGRESS

- Cross-project memory (KG entities that travel between projects)
- Multi-worker parallelism at scale
- Research automation (scheduled research prompts)
- FastMCP 3.0 migration when stable

---

## What This Experiment Will Teach Us

This platform-native architecture is partially an experiment. We expect to learn:

1. **Where subagent coordination breaks down** — at what complexity level does the orchestrator-as-hub pattern become insufficient? When do we need a persistent message bus?

2. **How background subagent MCP limitations affect workflow** — if workers can't access MCP tools when running in background, how much does that constrain parallelism?

3. **Whether declarative orchestration scales** — can CLAUDE.md + subagent definitions express all the coordination behavior we need, or will we eventually need imperative logic?

4. **What the right persistence granularity is** — does the KG capture enough for cross-session continuity, or do we need something between "ephemeral subagent" and "persistent KG entity"?

These answers will inform whether and how to expand the architecture — potentially reintroducing elements from the v1 design (Hub server, active extension orchestration) with precise knowledge of where they're needed rather than speculative engineering.

---

## Vision Summary

This system exists to preserve and serve the project's vision. Everything it does -- quality verification, institutional memory, multi-agent coordination -- serves that purpose.

**Three-tiered oversight** is the organizing principle. Vision standards are immutable by agents and verified as the highest priority. Architectural standards evolve through structured proposals requiring human approval. Quality standards are automated and low-friction.

A human developer, working through a primary Claude Code session, orchestrates six specialized subagents: workers implement tasks in isolated worktrees, a quality reviewer evaluates through the three-lens model (vision first, architecture second, quality third), a governance reviewer validates decisions against vision standards, a researcher gathers intelligence before architectural decisions, a librarian curates institutional memory, and a project steward maintains organizational hygiene.

Three custom MCP servers provide what Claude Code cannot: the Knowledge Graph stores persistent, tier-protected institutional memory queryable by all sessions. The Quality server wraps deterministic verification tools behind a unified interface with a trust engine for finding management. The Governance server provides transactional decision review and holistic collective-intent review, ensuring every key decision is checked against vision standards before implementation proceeds, both individually and as a group.

Everything else uses Claude Code's native capabilities: subagent spawning, background execution, lifecycle hooks, Task List persistence, session resume, model routing, permission control.

**The confidence mechanism**: Confidence emerges from deterministic verification first (does it compile? do tests pass?), then from track record (did previous suggestions work?), then from explanation quality (is the rationale project-specific?). Never from self-assessment.

**The team relationship**: Workers and the quality reviewer have each other's back. The quality system provides vision verification, architectural guidance, institutional memory, and quality automation that makes workers dramatically more effective. Workers aren't being policed; they're being supported by a teammate that remembers everything, knows the codebase patterns, guards the project's vision, and can bring fresh perspective when things get stuck.

**The platform**: Everything runs on Claude Code Max. Custom infrastructure is limited to three MCP servers that provide capabilities the platform genuinely cannot. The architecture leverages native primitives aggressively, building only what it must. The result is a system that is practically powerful, readily extensible, and honest about what it knows and what it's still learning.

---

*This vision document is the conceptual foundation. The v1 full-infrastructure design is preserved in `docs/v1-full-architecture/` for reference. This document answers "why this system exists, what it's shaped like, how the pieces relate, and what principles govern it." The architecture document (`ARCHITECTURE.md`) answers "how to build it."*
