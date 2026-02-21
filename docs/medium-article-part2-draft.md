# Agent Vision Team: What Changed in Twelve Days

Richard Amerman
___ min read · Feb 2026

---

Two weeks ago I published a piece about building a governed multi-agent coding system on top of Claude Code. The motivations were personal: a complex open-source project that kept regressing, architectural decisions that agents would silently reinvent, and the nagging feeling that the investment I'd put into mature, working code was invisible to the models doing the work. I built a system with three MCP servers (Knowledge Graph, Quality, Governance), six specialized agents, and a hook-based governance layer that intercepted decisions before work began.

That was February 8th. It's now February 20th. A lot has changed.

The core philosophy hasn't moved. Vision standards are still immutable by agents. The three-tier hierarchy (Vision, Architecture, Quality) still governs everything. The "intercept early, redirect early" pattern still underpins the governance system. But the system itself has grown substantially, both in capability and in the problems it's now trying to solve. What follows is a tour of the major changes and additions, and the thinking behind them.

## From Subagents to Teammates

The first article described agents spawned via Claude Code's Task tool as subagents. That's been replaced entirely by Agent Teams, a newer Claude Code capability that changes the orchestration model in meaningful ways.

A subagent was essentially a fire-and-forget subprocess. You'd give it a prompt, it would do its work, and it would report back. Agent Teams teammates are something different: full Claude Code sessions with independent MCP access, shared task lists, and the ability to message each other directly, not just report to the lead.

This matters because the governance system depends on agents having live access to the Knowledge Graph and Governance servers. A subagent that hallucinated MCP results (a real issue I hit, tracked as Issue #13898 in Claude Code) could produce work that appeared to pass governance checks but actually hadn't. Teammates don't have that problem. Each one loads CLAUDE.md, connects to all three MCP servers, and inherits the full hook layer independently.

The shared task list is the other major shift. Instead of the orchestrator manually assigning work to specific agents, teammates self-claim tasks. The orchestrator creates governed tasks, the governance system reviews and unblocks them, and teammates pick up whatever's available. This is closer to how a real development team works: the tech lead doesn't micromanage who picks up which ticket; people pull work from the queue.

Direct messaging between teammates also means the quality reviewer can send findings straight to the worker who produced the code, without routing through the orchestrator. It makes the feedback loop tighter and reduces the lead's coordination burden.

## Context Drift: The Problem I Couldn't Ignore

This is the biggest addition to the system and the one that required the most research. Context drift, the gradual divergence of an agent's behavior from its original goals over the course of a long session, is one of those problems that everyone working with agentic coding has felt but that doesn't have an obvious solution.

I spent time reviewing the literature on this, and the findings were instructive. Chroma Research showed that 11 of 12 models drop below 50% of their short-context performance around 32,000 tokens. The "Lost in the Middle" paper from MIT found models perform roughly 30% worse on information placed in the middle of context versus at the beginning or end. And perhaps most usefully, Dongre et al. challenged the assumption that drift is an inevitable, unbounded decay. Their research suggests it's actually a bounded stochastic process with restoring forces: simple, targeted reminders can reliably reduce divergence.

That last finding was the green light for the approach I took. The system now has a three-layer context reinforcement mechanism:

The first layer is active session context. When a session begins working on a task, a background process distills the user's original prompt, the active goals, and key discoveries into a compact session context file. This runs asynchronously using Claude's headless mode with Haiku (fast and cheap), so it never blocks the main workflow. As the session progresses and governance reviews complete, the context file gets updated with goal completions and new findings.

The second layer is a static context router derived from the Knowledge Graph. Vision standards, architecture patterns, and project rules are compiled into a JSON lookup table with Jaccard-based keyword matching. When an agent is about to write, edit, or run code, a PreToolUse hook matches the current activity against this router and injects the most relevant standards into the agent's context. This is deterministic, fast (milliseconds), and doesn't require an AI call.

The third layer is post-compaction recovery. Claude Code periodically compacts conversation history to free up context space. This is lossy; research suggests post-compaction compliance drops to 60-70% because paraphrased instructions lose precision. The system now has a SessionStart hook that fires on compaction events and reinjects the session context file and vision standards, putting the agent back on track immediately after the context window gets trimmed.

One insight from Google's research (Leviathan et al.) was particularly validating: simply repeating prompts consistently improves performance across all tested models, winning 47 of 70 benchmark-model combinations with zero losses. The mechanism is straightforward: causal attention is left-to-right, so repetition allows every token to attend to every other. The latency cost is minimal because repetition only affects the parallelizable prefill stage.

The whole system adds two hooks (bringing the total from five to seven), 13 tunable settings with UI controls, and 120 unit tests across 10 test groups. It's the most tested component in the system.

## The Audit Agent: Watching the Watchers

The governance system intercepts decisions. The quality system runs deterministic checks. But neither of them answers a more fundamental question: is the system itself working well?

The audit agent is a passive observer that watches all AVT activity and produces actionable intelligence over time. The design metaphor comes from hardware networking: a Network TAP (Test Access Point) sits on a link, copies all traffic to a monitoring port, and the original traffic is completely unaffected. If the TAP fails, the network continues operating.

This is exactly how the audit agent works. It piggybacks on the existing governance hooks, appending lightweight events to an append-only log. Each event is a single JSON line, about half a millisecond to write. No indexing, no transactions, no network calls. The audit agent has its own isolated storage and cannot write to any operational store (the governance database, the knowledge graph, nothing). If it crashes, every other part of the system continues working.

Processing uses a settle/debounce pattern similar to the holistic review system. After hooks stop firing for 5 seconds, a processor reads the new events, updates rolling statistics in SQLite, and runs threshold checks. These are pure Python, sub-millisecond, no AI involved. About 85% of processing cycles complete in roughly 5 milliseconds with no LLM call at all.

Only when an anomaly is detected does the system escalate to AI analysis, and it does so through a tiered chain: Haiku for initial triage (about half a cent), Sonnet for deeper analysis if warranted (about three cents), and Opus for a full deep dive only in serious cases (about fifteen cents). Each tier is a detached subprocess that spawns the next only if the previous tier determines escalation is needed.

What does it detect? Things like a high governance block rate (more than 50% of decisions in a session getting blocked, which suggests either the agent is fundamentally misaligned or the standards need updating), repeated idle blocks (a teammate spinning its wheels), high context reinforcement skip rates (the reinforcement system isn't getting through), or event rate spikes that could indicate a runaway loop.

The anomalies produce actionable recommendations, things like "lower the tool call threshold from 8 to 6" or "review vision standard X, which is blocking 60% of worker decisions." Recommendations have a lifecycle (active, stale, dismissed, superseded, resolved) and a TTL-based expiry, so they don't accumulate indefinitely.

Five editable observation directives guide what the escalation chain looks for, and new directives can be added without code changes. The dashboard includes an Audit tab showing health status, active recommendations with dismiss actions, and a recent events feed.

## The Project Bootstrapper: Meeting Codebases Where They Are

The original system assumed you'd set up governance from scratch: define vision standards, design architecture, configure rules through the setup wizard. But the most compelling use case is the opposite: bringing governance to a project that already exists, has been growing organically, and has accumulated implicit conventions, undocumented architectural decisions, and tribal knowledge scattered across code comments and README files.

The project bootstrapper is a new agent (bringing the total from six to eight, along with the architect agent that was formalized separately) designed specifically for this. It's a discoverer, not a creator. It surfaces what already exists and presents it for human review.

The process starts with a cheap, CLI-based scale assessment, file counts, lines of code, package boundaries, all completed in under five seconds. This classifies the project into a scale tier and builds a partition map of natural code boundaries. Then it spawns discovery waves of sub-agents (up to 15 concurrent) focused on four concerns: documentation analysis, structure analysis, pattern detection, and convention detection.

Convention detection turned out to be one of the more interesting research areas. While tools for enforcing conventions are mature (ESLint, Prettier, Ruff), automated detection and extraction of implicit conventions from existing code is not well-served by off-the-shelf tooling. The bootstrapper reads existing linter and formatter configs as the primary source, then uses stratified sampling across the codebase to detect conventions not captured by configs. Convention agents report frequency counts ("45 of 50 files use kebab-case") rather than assertions, giving the human reviewer real data to work with.

The output is a set of draft artifacts: a bootstrap report with approve/reject/revise actions for each finding, draft vision standard documents, architecture documentation with Mermaid diagrams, a discovered style guide, and draft project rules. Everything goes through human review. Nothing is committed to the Knowledge Graph automatically. The bootstrapper's job is to do the tedious discovery work and present its findings clearly enough that a developer can make informed decisions quickly.

## CI/CD and the Quality Pipeline

The system now has a proper continuous integration pipeline, which sounds unremarkable until you consider that the quality gates enforced by the Quality MCP server during agent work are the same scripts that run in CI. A unified script layer in `scripts/ci/` handles linting, typechecking, building, testing, and coverage enforcement. Pre-commit hooks (via Husky and lint-staged) run formatting on staged files. Pre-push hooks run the full pipeline: typecheck, build, test, coverage with clear error reporting if anything fails. GitHub Actions runs the same checks on every push to every branch.

The principle is that agent-produced code and human-produced code go through the exact same quality pipeline. There's no separate standard for AI-generated work.

## Token Efficiency: Less Is More

The CLAUDE.md file that drives the orchestrator went from 963 lines to 284. The detailed protocol documentation that used to be loaded into every session now lives in seven on-demand skill files that are loaded only when needed. With five teammates running simultaneously, that saves over 17,000 tokens that would otherwise be consumed before any actual work begins.

The Governance server's KG client now caches vision standards and architecture queries with a 5-minute TTL, avoiding repeated JSONL file reads during review bursts. And a new token usage tracking system records every AI call the governance system makes: input tokens, output tokens, cache reads, duration, prompt size, and model used. A dashboard panel visualizes this data with period selection and prompt size trend analysis, making it easy to spot context bloat before it becomes a problem.

## By the Numbers

The system went from 292 end-to-end test assertions to 537 total: 44 unit tests, 120 hook tests, 53 audit tests, 15 MCP access tests, 13 capability matrix tests, and the original 292 E2E assertions across 14 scenarios. The hook tests alone cover 10 test groups spanning both the governance layer and the context reinforcement system.

Seven lifecycle hooks now fire for all agents with no exceptions. Eight specialized agents operate as Agent Teams teammates (or, in the governance reviewer's case, as an isolated subprocess inside the governance server). Two deployment modes: local via the VS Code extension, or remote via a standalone web gateway with 35 REST endpoints, WebSocket push, and job submission from any device including phones.

## What's Next

The planned work includes cross-project memory (so institutional knowledge from one project can inform another), multi-worker parallelism patterns, an installation script for target projects to make onboarding easier, and native `.claude/agents/` teammate loading once Claude Code resolves Issue #24316, which will eliminate the need to embed full system prompts when spawning teammates.

## The Honest Assessment, Continued

Everything I said in the first article still holds. This might be over-engineered. It might turn out that the utility I'm extracting doesn't justify the complexity. And it's still as much an exercise in building a multi-agent system as it is a product.

But twelve days in, what I can say is that the problems this system is trying to solve have not gotten less real. Context drift is still a fundamental limitation of how these models work. Agents still silently reinvent architecture. Quality still degrades over long sessions. And the pace of change in the underlying platform (Claude Code went from subagents to Agent Teams in the time I was building this) means that systems like this one need to be built with the assumption that the ground underneath them is going to keep moving.

The code is open source, the story is ongoing, and I'll keep sharing what I learn. The most interesting things tend to happen at the intersection of theoretical architecture and practical use, and that's exactly where this project lives.
