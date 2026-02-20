# Research Brief: Project Bootstrapper Agent Design

**Question**: How to build an agent that discovers and backfills governance artifacts (vision standards, architecture patterns, components, rules, conventions) from an existing mature codebase?
**Date**: 2026-02-12
**Sources**: Architecture recovery literature, Claude Code subagent best practices, multi-agent code review systems, enterprise codebase analysis patterns

## Context

The AVT system currently assumes projects are bootstrapped from scratch: vision standards defined upfront, architecture designed intentionally, rules configured via the setup wizard. But the critical use case is onboarding an **existing mature project** where these artifacts already exist implicitly in the codebase and documentation. A developer might have inherited a large codebase, cloned an ambitious project, or want to bring governance to a project that has grown organically. The bootstrapper must discover what's already there and present it for human confirmation.

## Research Findings

### 1. Architecture Recovery is a Mature Discipline

Architecture recovery (extracting architectural information from source code) is a well-established software engineering discipline with 151+ primary studies in systematic mapping reviews. Key approaches:

- **Clustering**: Group source code entities (files, classes, functions) into subsystems using dependency analysis
- **Mining Software Repositories**: Extract architecture from source code, issue trackers, and commit history
- **LLM-Enhanced Recovery**: Recent work (ArchAgent, 2025) uses adaptive grouping and enhanced summarization to recover business-aligned architecture from legacy systems, handling LLM context window limitations

**Key insight**: The bootstrapper should use a hybrid approach: deterministic analysis (imports, directory structure, config files) combined with LLM reasoning (understanding intent, classifying tiers, generating diagrams).

Sources:
- "Generating Software Architecture Description from Source Code using Reverse Engineering and LLM" (arxiv.org/html/2511.05165v1)
- "Mining software repositories for software architecture: Systematic mapping study" (sciencedirect.com)
- "ArchAgent: Scalable Legacy Software Architecture Recovery with LLMs" (arxiv.org/html/2601.13007)

### 2. Multi-Agent Decomposition for Codebase Analysis

Analyzing a large codebase with a single agent is impractical. Context windows overflow, analysis quality degrades, and wall time becomes unacceptable. The proven approach is **specialist sub-agents with focused mandates**:

- Each sub-agent gets a scoped task (specific directories, specific files, specific analysis type)
- Sub-agents output structured JSON, not prose (enables reliable aggregation)
- Context isolation prevents one agent's analysis from polluting another's
- Parallel execution dramatically reduces wall time

From VS Code's multi-agent development blog (2026) and the OpenCode multi-agent code review system: "Analyze diffs from multiple expert perspectives simultaneously, invoking only the specialists needed."

**Key insight**: The bootstrapper should have four types of specialist agents (documentation analyzer, structure analyzer, pattern analyzer, convention analyzer) that each get a precisely scoped mandate from the partition map.

### 3. Claude Code Subagent Best Practices

From Anthropic's documentation and community patterns:

- Subagents use YAML frontmatter (model, tools) + Markdown instructions
- Quality depends entirely on system prompt quality: "detailed instruction manuals with step-by-step processes, rules, positive/negative examples"
- Better separation of concerns = better performance
- Include positive AND negative examples (LLMs excel at pattern recognition from examples)
- Begin with carefully scoped tools, progressively expand after validating

**Key insight**: The bootstrapper's sub-agents should be inline Task prompts (not separate agent files) with very specific output JSON schemas, concrete examples of correct and incorrect classification, and READ-ONLY tool constraints.

### 4. Convention Detection is an Open Problem

While tools for *enforcing* coding conventions are mature (ESLint, Black, Prettier, etc.), automated *detection and extraction* of implicit conventions from existing code is not well-served by off-the-shelf tools. The closest approaches:

- `clang-format` can generate a config from existing code
- Linter configs encode explicit conventions but miss implicit ones
- Pattern frequency counting (sampling files, counting naming patterns) is the practical approach

**Key insight**: The bootstrapper should read existing linter/formatter configs as the primary convention source, then use stratified sampling across the codebase to detect conventions not captured by configs. Convention agents should report frequency counts ("45 of 50 files use kebab-case") not just assertions.

### 5. The "Style" Artifact Question

AVT currently has no first-class "style" artifact type. Three options were evaluated:

1. **Extend project rules only**: Capture all conventions as enforce/prefer rules in project-config.json
2. **Style guide document + rules**: New docs/style/style-guide.md for human reference, enforceable subset extracted into project rules
3. **New KG entity type + document**: Add a coding_convention entity type to the KG

**Decision**: Option 2 (style guide document + rules). Rationale:
- The style guide serves as a human-readable reference that's richer than individual rules
- The machine-enforceable subset naturally maps to the existing project rules system
- No KG model changes needed; the existing `naming_convention` observation pattern (used by project-steward) covers KG needs
- The document is not ingested into the KG (it's a reference), so no ingestion pipeline changes needed for style

## Scaling Analysis

### The Scale Problem

The bootstrapper could face anything from a 5K-line hobby project to a 4M+ line enterprise monorepo. The naive approach of spawning more concurrent agents breaks at scale because:

1. There's a practical ceiling on concurrent agents (~15-20 due to system resources and API rate limits)
2. Each agent has a context window limit (~200K tokens); a single agent can't analyze 40K files
3. Aggregating results from 150+ agents would overflow the synthesizer's context

### The Wave Solution

**Bounded parallelism with work queues**:
- Concurrency limit: 15 agents (configurable)
- Work items are queued and executed in waves
- Each wave completes before the next starts (barrier synchronization)
- No hard cap on total work items; large codebases simply require more waves

This pattern is already used in the AVT e2e test executor (ThreadPoolExecutor + as_completed barrier).

### Concrete Scenario Analysis

All scenarios assume: concurrency limit = 15, average agent time = 2 min, phases 1+2+4 overlap, phase 3 waits for phase 2.

#### Scenario A: Medium (50K LOC, 8 packages)

| Phase | Work Items | Waves | Wall Time |
|-------|-----------|-------|-----------|
| Docs (30 files) | 2 | 1 | 2 min |
| Structure (8 pkgs) | 8 | 1 | 2 min |
| Patterns (500 files) | 2 | 1 | 2 min |
| Conventions (2 langs) | 2 | 1 | 2 min |
| Aggregation | 5 | 1 | 2 min |

**Total: ~8-10 min, 19 agent invocations**

This is the sweet spot. Everything fits in one wave per phase. No hierarchical aggregation needed (all phases produce ≤ 20 results). The overhead of the wave system is negligible.

#### Scenario B: Large (500K LOC, 40 packages)

| Phase | Work Items | Waves | Wall Time |
|-------|-----------|-------|-----------|
| Docs (100 files) | 4 | 1 | 2 min |
| Structure (40 pkgs) | 40 | 3 | 6 min |
| Patterns (5K files) | 13 | 1 | 2 min |
| Conventions (3 langs) | 3 | 1 | 2 min |

Structure is the bottleneck (3 waves of 15+15+10).
Aggregation: Structure has 40 results (> 20 threshold), so 3 wave aggregators + 1 phase aggregator.

**Total: ~12-15 min, ~66 agent invocations**

The wave system handles this cleanly. Structure analysis produces results fast enough that patterns can start promptly after. Hierarchical aggregation kicks in for the structure phase but adds minimal overhead (3 wave aggregators are quick since they only process ~15 JSON objects each).

#### Scenario C: Massive (2M LOC, 150 packages)

| Phase | Work Items | Waves | Wall Time |
|-------|-----------|-------|-----------|
| Docs (300 files) | 12 | 1 | 2 min |
| Structure (150 pkgs) | 150 | 10 | 20 min |
| Patterns (20K files) | 50 | 4 | 8 min |
| Conventions (4 langs) | 4 | 1 | 2 min |

Structure: 10 waves of 15 each.
Patterns: 4 waves of 13-15 each.
Aggregation: Structure needs 10 wave aggregators + 1 phase aggregator. Patterns needs 4 wave aggregators + 1 phase aggregator.

**Total: ~35 min, ~230 agent invocations**

This is where the wave system really proves its value. Without it, you'd need 150 concurrent agents (impossible). With waves, the wall time is dominated by the 10 structure waves (20 min). The patterns phase adds 8 min after structure completes.

**Token budget estimate**: 230 agents x ~50K tokens average = ~11.5M tokens. At $3/M input + $15/M output (Opus pricing), the total cost for bootstrapping a 2M LOC codebase is roughly $50-100. This is a one-time cost for onboarding a major project.

#### Scenario D: Enterprise (4M LOC, 300+ packages)

| Phase | Work Items | Waves | Wall Time |
|-------|-----------|-------|-----------|
| Docs (500 files) | 20 | 2 | 4 min |
| Structure (150 partitions*) | 150 | 10 | 20 min |
| Patterns (40K files) | 100 | 7 | 14 min |
| Conventions (5 langs) | 5 | 1 | 2 min |

*300 packages grouped into ~150 partitions of 2 each (small packages clustered).

Structure: 10 waves. Patterns: 7 waves. Docs: 2 waves.
Aggregation: Hierarchical for structure (10 wave aggs), patterns (7 wave aggs), and docs (2 wave aggs).

**Total: ~41 min, ~300 agent invocations**

**Why wall time doesn't double with double the code**: Going from 2M to 4M LOC (2x) increases patterns from 50 to 100 items (2x) but structure stays at 150 partitions (packages are grouped). The patterns phase goes from 4 waves to 7 waves, adding only 6 min. Total goes from 35 to 41 min (1.17x for 2x code). This is sub-linear scaling.

### Scaling Properties

| Property | Value |
|----------|-------|
| **Concurrency limit** | 15 agents (configurable) |
| **Min wall time** (Small) | ~5 min |
| **Max wall time** (Enterprise) | ~45 min |
| **Wall time growth** | Sub-linear: 8x code = ~2.7x time |
| **Agent invocation growth** | Linear with work items |
| **Context per agent** | Bounded by partition scope (max 400 files / 60K LOC) |
| **Aggregation context** | Bounded: max 22K tokens per wave aggregator, ~30K per phase aggregator |
| **Synthesizer context** | Fixed: ~20K tokens (4 phase reports) regardless of scale |

### Hierarchical Aggregation Design

The aggregation threshold is **20 results per aggregator**. Below this, a single phase aggregator handles all results. Above this, wave-level aggregators compress each wave's results before the phase aggregator.

```
Wave 1 (15 results, ~22K tokens) → Wave Aggregator 1 → summary (~3K tokens)
Wave 2 (15 results, ~22K tokens) → Wave Aggregator 2 → summary (~3K tokens)
...
Wave 10 (15 results, ~22K tokens) → Wave Aggregator 10 → summary (~3K tokens)
                                                            ↓
                                          Phase Aggregator (10 × 3K = 30K tokens)
                                                            ↓
                                          Phase Report (~5K tokens)
```

Each analysis agent outputs ~1-2K tokens of structured JSON. A wave aggregator handles 15 × 1.5K = ~22K tokens (well within context). A phase aggregator handles 10 wave summaries × 3K = ~30K tokens (also fine). The final synthesizer receives 4 phase reports × 5K = ~20K tokens (trivially within context).

**This architecture guarantees no context overflow at any scale.** Even if a phase had 1000 work items (67 waves), the phase aggregator would only see 67 wave summaries × 3K = ~200K tokens (within Opus context limit).

## Architecture Documentation Design

### The Problem with Flat Architecture Docs

A large codebase's architecture can't be understood from a single document of prose. Someone who inherited the project needs:
1. A high-level overview first (what does this system do? what are the major pieces?)
2. The ability to drill down into specific components
3. Visual diagrams showing how things connect
4. Flow diagrams for key interactions

### Multi-Level Approach (inspired by C4 model)

| Level | Document | Contents | Diagrams |
|-------|----------|----------|----------|
| **0: Overview** | overview.md | System summary, component inventory | System context diagram, component map |
| **1: Components** | components/<name>.md | One per component: responsibility, API, internal structure | Component internal diagram, dependency diagram |
| **2: Patterns** | patterns/<name>.md | Cross-cutting patterns: DI, repository, etc. | Class diagrams showing pattern structure |
| **3: Flows** | flows/<name>.md | Key interaction sequences | Sequence diagrams |

### Dual-Purpose Document Format

The architecture docs serve two audiences:
1. **Humans** reading markdown (need diagrams, tables, visual structure)
2. **KG ingestion pipeline** parsing specific sections (needs plain text in ## Type, ## Description, ## Usage, ## Examples)

The ingestion pipeline's `_extract_section()` function collapses whitespace (`re.sub(r'\s+', ' ', text)`), which destroys Mermaid code blocks. The solution: put Mermaid diagrams in sections the ingestion pipeline doesn't extract (e.g., `## Diagram`, `## Internal Structure`, `## Dependencies`). The KG gets clean text from the extracted sections; humans get beautiful rendered diagrams from the non-extracted sections.

### Mermaid Diagram Types Used

| Context | Mermaid Type | Purpose |
|---------|-------------|---------|
| System overview | `graph TD/LR` with `subgraph` | Show components and their grouping |
| Component internals | `graph TD` | Show internal modules and data flow |
| Pattern structure | `classDiagram` | Show interfaces, implementations, relationships |
| Interaction flows | `sequenceDiagram` | Show step-by-step request/response flows |

### Scaling Architecture Docs

| Component Count | Docs Generated | Estimated Pages |
|----------------|---------------|----------------|
| < 5 | overview + 5 component docs | ~6 pages |
| 5-15 | overview + components + 2-3 patterns | ~20 pages |
| 15-30 | overview + components + patterns + flows | ~40 pages |
| 30-100 | Same but overview uses subsystem grouping | ~60-100 pages |
| 100+ | Subsystem-level overviews + component docs | ~100-200 pages |

For 100+ components, the overview.md groups components into subsystems (e.g., "Authentication", "Billing", "Notifications") with a subsystem-level diagram. Each subsystem gets its own sub-overview linking to individual component docs.

## Governance Integration

### The Holistic Review Consideration

The bootstrapper spawns many sub-agent tasks. The PostToolUse hook on TaskCreate fires for every task, and the holistic review system evaluates all tasks from a session as a group. With 15+ tasks created rapidly:

1. The settle checker debounces (3s), so only the last task triggers the review
2. The holistic review evaluates collective intent of all bootstrap tasks
3. Since all tasks are READ-ONLY analysis, the holistic review should approve quickly
4. The PreToolUse gate (holistic-review-gate.sh) blocks Write/Edit/Bash/Task while review is pending

**Mitigation**: The bootstrapper should create all analysis tasks in rapid succession. The settle checker debounces correctly and the holistic review sees them as a coherent "read-only bootstrap analysis" group. For subsequent waves, the same pattern applies.

### Draft-First, Ingest-After-Approval

Nothing enters the KG as vision or architecture tier until the human reviews the bootstrap report and approves specific items. This is critical because:
- Vision standards are immutable once ingested (human-only modification)
- Incorrect architecture patterns would mislead all future agents
- The human might know context that the code analysis can't capture (e.g., "that pattern is legacy, we're migrating away from it")

The bootstrapper uses `caller_role: "human"` for ingestion only after explicit human approval, since the entire bootstrap process is human-initiated and human-approved.

## Open Questions

1. **Should the bootstrapper generate an initial CLAUDE.md for the target project?** Many mature projects already have one, but if the bootstrapper is being used to onboard a project into AVT, generating a project-specific CLAUDE.md with the discovered standards and patterns could be valuable.

2. **How to handle very stale documentation?** If README.md says "this project uses Express" but the code has been rewritten in Fastify, the bootstrapper flags the contradiction. But should it suggest updating the docs, or leave that entirely to the human?

3. **Cost estimation and user approval**: For Enterprise-scale codebases (~300 agent invocations at Opus), the token cost could be $100+. Should the bootstrapper present a cost estimate and get approval before proceeding?

4. **Incremental re-bootstrap**: After the initial bootstrap, the codebase evolves. Should there be a "refresh" mode that re-runs discovery and diffs against the existing KG state? This is a future enhancement but worth considering in the architecture.

## Recommendations

1. **Start with the agent prompt file** as the primary deliverable. It encodes the complete protocol.
2. **Keep sub-agents as inline Task prompts**, not separate agent files. This avoids file proliferation and gives the bootstrapper full control over sub-agent context.
3. **Use the existing ingestion pipeline** for KG population. The bootstrapper produces documents in the exact format the pipeline expects.
4. **Enhance the ingestion pipeline defensively**: add Mermaid-safe whitespace handling and Dependencies section extraction, but don't require these changes for the bootstrapper to function (the bootstrapper puts diagrams in non-extracted sections).
5. **Test against this project first** (agent-vision-team) as a smoke test, then ideally test against a large open-source project for scale validation.
