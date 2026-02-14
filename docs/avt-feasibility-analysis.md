# AVT System Feasibility Analysis
## Can the Agent Vision Team Work With Claude Code Max (No API)?

**Date**: February 13, 2026  
**Status**: Deep Research Complete  
**For**: Richard / Agent Vision Team Project

---

## Executive Summary

**The honest answer: AVT as designed will not work reliably today with Claude Code Max alone. But there are viable paths forward — they just require architectural adaptation, not abandonment.**

The core tension is this: AVT was designed around a model where specialized subagents get differentiated tool access and reliable MCP server connectivity. Claude Code's actual permission and MCP propagation model doesn't deliver that. However, several recent developments — Agent Teams (Feb 5, 2026), native sandboxing, the `mcpServers` field in agent definitions, and the Agent SDK — create new options that didn't exist when AVT's architecture was set.

Here's the bottom line on each of your three requirements:

| Requirement | Status | Assessment |
|---|---|---|
| Agents reliably use tools | **Achievable with workarounds** | Foreground subagents + sandbox mode + permission pre-approval works. Background subagents are problematic. |
| Per-agent-type permissions & tool access | **Not enforceable today** | `tools` field in agent YAML is advisory for custom subagents with MCP. Permission inheritance is broken in multiple documented ways. |
| Per-agent-type MCP access | **Partially broken** | Issue #13898 (custom subagents hallucinate MCP results from project-scoped servers) is still open. Global MCP config works. |
| All on Claude Code Max, no API | **Constraining but possible** | Agent Teams + interactive orchestration works. Headless/autonomous operation without API requires `claude -p` with `--dangerously-skip-permissions`, losing permission safety. |

---

## Part 1: The Three Showstopper Bugs

These are the issues that, as of today, prevent AVT from working as originally designed.

### Bug 1: Custom Subagents Hallucinate MCP Results (Issue #13898)

**This is AVT's biggest problem.** When a custom subagent (defined in `.claude/agents/`) tries to call an MCP tool from a project-scoped server (`.mcp.json`), it doesn't get an error — it fabricates a plausible-looking response. The worker thinks governance approved, but no actual review happened.

- **Status**: Open, confirmed, has repro steps, tagged `area:mcp` + `area:tools`
- **Workaround available**: MCP servers configured at **user scope** (`~/.claude/mcp.json`) work correctly. The built-in `general-purpose` subagent also works with project-scoped MCP.
- **Impact on AVT**: Your three MCP servers (KG :3101, Quality :3102, Governance :3103) would need to be registered at user scope, not project scope, for custom subagents to use them reliably.

### Bug 2: Background Subagents Cannot Access MCP Tools (Issue #13254)

The docs explicitly state: *"MCP tools are not available in background subagents."* This isn't a bug — it's a known limitation. Background subagents auto-deny anything not pre-approved, and MCP tools fall into that category.

- **Impact on AVT**: Any agent that needs MCP (worker, quality reviewer, KG librarian, researcher) must run in the **foreground**. This means no true parallel execution of MCP-dependent agents via the Task tool in background mode.

### Bug 3: Permission Inheritance Is Broken in Multiple Ways

Your permission research already identified this, and the landscape hasn't improved:

- **Issue #18950**: Subagents don't inherit `permissions.allow` from parent
- **Issue #2148**: Denying permission for ONE subagent halts ALL parallel subagents
- **Issue #5465**: Task subagents fail to inherit permissions in MCP server mode
- **Issue #24073**: Teammates in Agent Teams inherit the *lead's* permission restrictions (can't give a teammate MORE access than the lead)
- **Issue #25037**: Delegate mode breaks agent teams entirely (teammates lose tool access)

The practical consequence: there is no middle ground between "everything prompted" (unusable for autonomous operation) and `--dangerously-skip-permissions` (no safety net).

---

## Part 2: What Has Changed Since Your Research

### Agent Teams (Released February 5, 2026)

This is the biggest development. Agent Teams are fundamentally different from subagents:

- **Independent Claude Code instances** (not child processes within a session)
- **Each teammate loads project context independently** (CLAUDE.md, MCP servers, skills)
- **Teammates can communicate directly** with each other (not just report to parent)
- **Shared task list** with states (pending, in_progress, completed) and dependencies
- **Self-claim**: teammates pick up the next unassigned task automatically
- **Hooks support**: `TeammateIdle` and `TaskCompleted` hooks for quality gates

**Critical for AVT**: Teammates auto-load MCP servers from project configuration. Because each teammate is a full Claude Code session (not a subagent), they should have the same MCP access as a regular interactive session. This potentially bypasses Issue #13898 entirely.

**Limitations**:
- Still experimental (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`)
- All teammates inherit the lead's permission settings (no per-teammate differentiation)
- No session resumption
- No nested teams
- Can't spawn teammates from `.claude/agents/` definitions (Issue #24316, open 5 days ago)
- Token cost multiplies with each teammate
- Requires Claude Code Max (which you have)

### Native Sandboxing (Released ~January 2026)

Claude Code now has built-in OS-level sandboxing:

- **Filesystem isolation**: Read/write to CWD only, blocked from sensitive dirs
- **Network isolation**: Only approved domains via proxy
- Uses macOS Seatbelt / Linux bubblewrap — OS-enforced, not model-enforced
- Reduces permission prompts by ~84% in Anthropic's testing
- Enable with `/sandbox` command
- **Auto-allow mode**: Sandboxed commands run without permission prompts

**Critical for AVT**: This replaces the need for `--dangerously-skip-permissions` in many scenarios. Sandbox + auto-allow gives you autonomous execution within defined boundaries, with OS-level enforcement that can't be bypassed by the model.

### `mcpServers` Field in Agent Definitions

The CLI `--agents` flag now accepts `mcpServers` in the JSON configuration. The docs reference it as a valid frontmatter field. However, the YAML frontmatter docs for `.claude/agents/` files do NOT list `mcpServers` as a supported field — only `name`, `description`, `tools`, `model`, `permissionMode`, `skills`, and `disallowedTools`.

This means: per-agent MCP scoping is supported via `--agents` JSON flag or Agent SDK, but **NOT** via `.claude/agents/` markdown files. This is an important distinction for AVT.

### Agent SDK (Formerly Claude Code SDK)

Anthropic renamed the SDK and made it a first-class product. The Agent SDK provides:

- Programmatic `query()` with `mcpServers` option per call
- `permissionMode` control per query
- `canUseTool` callback for runtime approval
- Subagent spawning with full control
- Structured outputs

**BUT**: The Agent SDK requires API access. It's not Claude Code Max. Your "no API" constraint rules this out as a primary approach, though it could be used for specific headless components if you later relax that constraint.

---

## Part 3: Viable Architecture Options

### Option A: Agent Teams as Primary Orchestration (Recommended)

**Concept**: Replace Task-tool-based subagent spawning with Agent Teams for all MCP-dependent agents. Keep the Task tool only for agents that don't need MCP (or use the built-in `general-purpose` subagent type which does get MCP).

**Architecture**:
```
Human (Lead Session)
├── MCP Servers: KG, Quality, Governance (registered at user scope)
├── Sandbox: enabled with auto-allow
├── Agent Teams enabled
│
├── Teammate: Architect (spawned with rich prompt from CLAUDE.md)
│   └── Has full MCP access (loads from user-scope config)
├── Teammate: Worker-1 (spawned with task brief)
│   └── Has full MCP access
├── Teammate: Quality Reviewer (spawned with review scope)
│   └── Has full MCP access
├── Teammate: KG Librarian (spawned for curation)
│   └── Has full MCP access
│
└── Hooks: TeammateIdle, TaskCompleted (quality gates)
```

**Pros**:
- Each teammate is a full session — MCP works (bypasses #13898)
- Teammates can self-claim tasks from shared task list
- `TeammateIdle` hook can redirect idle agents
- `TaskCompleted` hook enforces quality gates
- Sandbox provides safety without `--dangerously-skip-permissions`
- Human lead can interact with any teammate directly

**Cons**:
- All teammates get same permissions (no per-agent tool restriction)
- Can't currently spawn from `.claude/agents/` definitions (Issue #24316)
- Specialization is prompt-only (fragile — the model can ignore it)
- Significantly higher token cost (each teammate = separate context window)
- Experimental — API may change
- No session resumption for teammates
- Governance reviewer (currently `claude --print`) would need rethinking

**What you'd need to change**:
1. Move MCP server config from `.mcp.json` to `~/.claude/mcp.json` (user scope)
2. Replace Task-tool spawning with Agent Teams spawning
3. Embed agent system prompts in spawn prompts (since `.claude/agents/` definitions aren't used by teammates yet)
4. Replace holistic review hooks (PostToolUse/PreToolUse) with TeammateIdle/TaskCompleted hooks
5. The governance reviewer (currently `claude --print`) can remain as-is — it's text-only and doesn't need MCP

### Option B: Hybrid — Agent Teams + Task Tool Subagents

**Concept**: Use Agent Teams for agents that NEED MCP (worker, quality reviewer, researcher), and keep Task tool subagents for agents that DON'T need MCP or that work fine with built-in tools only.

**Architecture**:
```
Human (Lead Session)
├── MCP Servers at user scope
├── Sandbox enabled
│
├── Agent Teams (MCP-dependent agents):
│   ├── Worker teammates (full MCP)
│   ├── Quality reviewer teammate (full MCP)
│   └── Researcher teammate (full MCP)
│
├── Task Tool Subagents (no MCP needed):
│   ├── KG Librarian (uses Bash to call MCP via curl/HTTP)
│   ├── Project Steward (read-only, no MCP needed)
│   └── Explore subagent (built-in, read-only)
│
└── claude --print (text-only):
    ├── Governance Reviewer
    └── Holistic settle checker
```

**Pros**:
- More economical (only MCP-dependent agents get full sessions)
- Non-MCP agents run as lightweight subagents
- Governance reviewer stays as `claude --print` (proven pattern)

**Cons**:
- Two coordination mechanisms to manage
- Agent Teams task list doesn't integrate with Task tool subagents
- More complex orchestration logic

### Option C: All Subagents + MCP at User Scope + Foreground Only

**Concept**: Keep the current Task-tool-based architecture, but fix the MCP issue by moving servers to user scope and ensuring all subagents run in the foreground.

**Architecture**:
```
Human (Orchestrator Session)
├── MCP Servers at ~/.claude/mcp.json (user scope)
├── --dangerously-skip-permissions OR sandbox
│
├── Task Tool (foreground, sequential):
│   ├── Architect (custom subagent, gets MCP via user scope)
│   ├── Worker (custom subagent, gets MCP)
│   ├── Quality Reviewer (custom subagent, gets MCP)
│   └── KG Librarian (custom subagent, gets MCP)
│
└── claude --print (text-only):
    └── Governance Reviewer
```

**Pros**:
- Minimal architectural change from current design
- Known behavior — your experiments characterized this path
- `tools` field in agent definitions at least controls built-in tools
- Hooks (PostToolUse, PreToolUse) continue working as designed

**Cons**:
- **Must verify**: Does user-scope MCP actually work with custom subagents? Your #13898 research confirmed project-scope fails. User-scope reportedly works, but needs verification for YOUR specific MCP servers (stdio transport, `uv run` commands).
- Sequential execution only (no parallel workers with MCP)
- `--dangerously-skip-permissions` eliminates safety — sandbox is the better option
- Background execution is off the table for MCP-dependent agents

**Critical test needed**: Register your three MCP servers at `~/.claude/mcp.json` and verify a custom subagent can actually call tools from all three without hallucination.

### Option D: The Nick Carlini / Docker Approach (Long-term)

Anthropic's own researcher built the 100,000-line C compiler using a completely different pattern: Docker containers per agent, git-based coordination, and a shell-script harness. No Claude Code subagent system at all.

**Architecture**:
```
Harness Script (shell/Python)
├── Creates bare git repo
├── For each agent:
│   ├── Docker container with Claude Code
│   ├── --dangerously-skip-permissions (safe inside container)
│   ├── MCP servers running inside the container
│   ├── Agent clones repo to /workspace
│   ├── Works independently
│   └── Pushes to upstream when done
│
├── Coordination via:
│   ├── File-based locks (git)
│   ├── Progress files and READMEs
│   └── Test harness as "oracle"
│
└── Your governance as test harness:
    ├── Hook scripts → run inside each container
    ├── MCP servers → local to each container
    └── Governance DB → shared volume
```

**Pros**:
- Complete isolation — each agent has its own MCP servers, no sharing bugs
- `--dangerously-skip-permissions` is safe inside Docker
- Proven at scale (2 billion tokens, 2000 sessions, 100K LOC)
- Your governance hooks and MCP servers work exactly as designed
- Fully autonomous — no human interaction needed
- Survives all the bugs in the current issue tracker

**Cons**:
- Requires Docker (not pure Claude Code Max interactive)
- Requires Anthropic API keys (not Claude Code Max subscription)
- Significant engineering effort to build the harness
- Higher latency (container startup)
- Coordination is primitive (file locks, not real-time messaging)

**Wait** — the "no API" constraint kills this for now. Unless you run `claude -p` inside Docker with Claude Code Max auth, which... might actually work. Claude Code Max authenticates via the CLI login, and `claude -p` in a Docker container would use that auth. Worth testing.

---

## Part 4: What to Do Right Now

### Immediate Experiments (This Week)

1. **Test user-scope MCP with custom subagents**  
   Move your three MCP servers from `.mcp.json` to `~/.claude/mcp.json`. Spawn a custom subagent and verify it can call all three servers without hallucination. This is the single most important validation — if it works, Option C becomes viable today.

2. **Test Agent Teams with MCP**  
   Enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. Spawn a teammate and verify it loads your MCP servers and can call tools reliably. If yes, Option A opens up.

3. **Test sandbox + auto-allow**  
   Run `/sandbox` and enable auto-allow mode. Verify your MCP servers still function (they need network access to localhost ports). Verify hooks still fire. This replaces `--dangerously-skip-permissions` with a safer alternative.

4. **Test `claude -p` with Claude Code Max auth inside Docker**  
   If this works, Option D becomes viable without API keys. `claude -p --dangerously-skip-permissions` inside a Docker container with your MCP servers running locally would give you fully autonomous, isolated agents.

### Recommended Path

**Start with Option C (user-scope MCP + foreground subagents + sandbox)** for immediate viability. This requires the least architectural change and keeps your governance system intact.

**Evolve toward Option A (Agent Teams)** as that feature matures. When Issue #24316 is resolved (allowing `.claude/agents/` definitions as teammates), your existing agent definitions become directly usable. The TeammateIdle and TaskCompleted hooks map naturally to your governance gates.

**Keep Option D in your back pocket** as the long-term autonomous architecture. When you're ready for fully headless, multi-hour autonomous operation, Docker-isolated agents with per-container MCP is the most robust approach.

### What to Watch

| Issue/Feature | Why It Matters | Status |
|---|---|---|
| #13898 (MCP hallucination) | Blocks all custom subagent + MCP workflows | Open |
| #24316 (agent defs as teammates) | Would let Agent Teams use your `.claude/agents/` definitions | Open (5 days old) |
| #13254 (background MCP) | Blocks parallel MCP-dependent subagents | Confirmed limitation |
| #18950 (permission inheritance) | Blocks meaningful per-agent permissions | Open |
| Sandbox auto-allow + MCP | If sandbox blocks localhost MCP, it's a problem | Needs testing |
| Agent Teams stability | Currently "research preview" / experimental | Active development |

---

## Part 5: Honest Assessment

**Can you make this work?** Yes, with adaptation. The core vision of AVT — specialized agents with governance, quality gates, and institutional memory — is sound and increasingly aligned with where Anthropic is taking Claude Code. Agent Teams, hooks, sandboxing, and the expanding subagent system are all moving in your direction.

**What won't work as designed?** The assumption that Claude Code's permission model provides meaningful per-agent tool isolation. It doesn't, and there's no indication it will soon. Your hook-based governance gates are actually more reliable than the permission system — your research already proved this.

**What's the real risk?** MCP reliability in subagents. If user-scope MCP works with custom subagents, you have a viable path today. If it doesn't, you're stuck waiting for #13898 to be fixed, or you need to move to Agent Teams or Docker isolation.

**The strongest parts of AVT's design are the parts that DON'T depend on Claude Code's permission model**: the three MCP servers, the hook-based governance gates, the file-system-level holistic review coordination, and the `claude --print` isolation for governance reviewers. These work regardless of permission bugs. Build on those strengths.
