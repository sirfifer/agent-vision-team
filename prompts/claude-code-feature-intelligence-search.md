# Tech Search: Claude Code Feature Intelligence for Collaborative Intelligence System

## Objective

Systematically investigate new Claude Code features, changes, and ecosystem developments to identify **conflicts** (things that could break us), **opportunities** (things we should adopt), and **general intelligence** (ecosystem trajectory) relevant to this multi-agent orchestration project.

## Our Exposure Surface

These are the exact Claude Code extension points we depend on:

| Extension Point | Our Usage | Key Files |
|---|---|---|
| Custom Agents (`.claude/agents/`) | 4 agents with YAML frontmatter (`model:`, `tools:` fields, `mcp:` prefixes) | `.claude/agents/*.md` |
| MCP Servers (FastMCP + SSE) | 3 servers on ports 3101-3103 via `mcpServers` in settings.json | `mcp-servers/*/collab_*/server.py` |
| PreToolUse Hooks | 1 hook on `ExitPlanMode` matcher, exit code 2 = block, JSON feedback | `scripts/hooks/verify-governance-review.sh` |
| `claude --print` subprocess | Governance reviewer invokes `claude --print -p <prompt>` with 60-120s timeout | `mcp-servers/governance/collab_governance/reviewer.py` |
| Settings format | `settings.json` with custom `agents`, `workspace` keys; `settings.local.json` with `Bash(pattern:*)` permissions | `.claude/settings.json`, `.claude/settings.local.json` |
| VS Code Extension | Custom extension alongside Claude Code's own extension | `extension/` |
| Model shorthands | `opus` and `sonnet` in agent configs | `.claude/agents/*.md`, `.claude/settings.json` |

---

## PHASE 1: Official Channels

### 1.1 Claude Code Documentation

**URL**: `https://docs.anthropic.com/en/docs/claude-code`

Search queries:
- `site:docs.anthropic.com "claude code" changelog 2026`
- `site:docs.anthropic.com "claude code" agents`
- `site:docs.anthropic.com "claude code" MCP`
- `site:docs.anthropic.com "claude code" hooks`
- `site:docs.anthropic.com "claude code" settings.json`
- `site:docs.anthropic.com "claude code" subagent OR "custom agent"`
- `site:docs.anthropic.com "claude --print"`

**Extract**: Changes to `.claude/agents/` YAML format, `settings.json` schema, hook types, `claude --print` flags, new CLI modes.

### 1.2 Claude Code GitHub Repository

**URL**: `https://github.com/anthropics/claude-code`

```bash
# Releases
gh release list --repo anthropics/claude-code --limit 20

# Targeted issue/discussion searches
gh search issues "MCP SSE transport" --repo anthropics/claude-code --limit 20
gh search issues "custom agents" --repo anthropics/claude-code --limit 20
gh search issues "PreToolUse hook" --repo anthropics/claude-code --limit 20
gh search issues "settings.json" --repo anthropics/claude-code --limit 20
gh search issues "subagent" --repo anthropics/claude-code --limit 20
gh search issues "claude --print" --repo anthropics/claude-code --limit 20
gh search issues "multi-agent OR orchestrator" --repo anthropics/claude-code --limit 20
gh search issues "breaking change" --repo anthropics/claude-code --limit 20
```

### 1.3 Anthropic Blog

**URL**: `https://www.anthropic.com/news`

- `site:anthropic.com "claude code" 2026`
- `site:anthropic.com "claude code" agents OR MCP OR multi-agent`
- `site:anthropic.com "model context protocol" 2026`

### 1.4 npm Package

- `"@anthropic-ai/claude-code" release notes 2026`
- Check npmjs.com for version history, deprecation notices, new dependencies

### 1.5 Claude Code SDK / Agent SDK

- `"claude agent sdk" OR "@anthropic-ai/claude-code-sdk" 2026`
- `site:docs.anthropic.com "agent sdk"`
- `Anthropic "agent SDK" multi-agent`

---

## PHASE 2: Feature-Specific Deep Dives

### 2.1 Agent/Subagent System

**Our risk**: YAML frontmatter schema change, `mcp:` tool prefix change, Task tool interface change, model shorthand change.

Searches:
- `"claude code" custom agents YAML frontmatter 2026`
- `"claude code" ".claude/agents" format OR schema`
- `"claude code" subagent spawn Task tool`
- `"claude code" agent model routing opus sonnet`
- `"claude code" agent tools permission`

**Check**: New agent capabilities (memory sharing, context passing, structured output, parallel execution primitives) that could simplify our orchestration.

### 2.2 MCP Server Support (HIGHEST PRIORITY)

**Our risk**: SSE transport deprecation, `mcpServers` config format change, FastMCP breaking changes.

Searches:
- `"claude code" MCP server configuration 2026`
- `"claude code" MCP SSE transport deprecation OR stdio`
- `"model context protocol" SSE deprecation "streamable HTTP" 2026`
- `FastMCP version 3 OR "fastmcp 3" breaking changes`
- `"claude code" MCP server authentication OR security`
- `MCP specification update 2026`

```bash
gh search issues "SSE transport" --repo modelcontextprotocol/specification --limit 10
gh search issues "streamable HTTP" --repo modelcontextprotocol/specification --limit 10
gh search issues "breaking" --repo jlowin/fastmcp --limit 10
gh release list --repo jlowin/fastmcp --limit 10
```

**Check**: New MCP features (subscriptions, sampling, resource templates, health monitoring) we could adopt.

### 2.3 Hooks System

**Our risk**: Exit code convention change, JSON feedback format change, `ExitPlanMode` tool rename/removal.

Searches:
- `"claude code" hooks PreToolUse PostToolUse 2026`
- `"claude code" hooks new types`
- `"claude code" hooks ExitPlanMode`
- `"claude code" hooks format schema`

**Check**: New hook types (PostToolUse, PreMessage, PostMessage, etc.) that could strengthen governance enforcement.

### 2.4 Settings Format

**Our risk**: Schema validation rejecting our custom `agents` and `workspace` keys.

Searches:
- `"claude code" settings.json schema validation 2026`
- `"claude code" settings.local.json permissions format`
- `"claude code" permission allowlist syntax`

### 2.5 CLI (`claude --print`)

**Our risk**: Flag deprecation, output format change, authentication change.

Searches:
- `"claude --print" flags options 2026`
- `"claude code" CLI headless batch mode`
- `"claude code" "--print" deprecation replacement`
- `"claude code" CLI JSON output mode`
- `"claude code" SDK API programmatic`

**Check**: Structured JSON output mode (simplifies verdict parsing), proper SDK/API (replaces subprocess), model flags.

### 2.6 VS Code Integration

**Our risk**: Claude Code's own VS Code extension claiming conflicting UI real estate or APIs.

Searches:
- `"claude code" VS Code extension API 2026`
- `"claude code" VS Code sidebar panel webview`
- `"claude code" VS Code MCP integration`

### 2.7 Max Account & Model Routing

Searches:
- `"claude code" Max subscription features 2026`
- `"claude code" model routing opus sonnet haiku`
- `Claude "Opus 4.5" OR "Opus 5" "claude code" model ID`
- `"claude code" rate limits Max plan concurrent`

### 2.8 Multi-Agent Patterns (STRATEGIC)

Searches:
- `"claude code" multi-agent pattern workflow 2026`
- `"claude code" orchestrator pattern`
- `"claude code" agent coordination communication`
- `"claude code" git worktree agent isolation`
- `Anthropic "agentic coding" multi-agent 2026`
- `"claude code" "agent sdk" orchestration`

**Check**: Official multi-agent primitives that could replace or enhance our custom orchestration.

---

## PHASE 3: Community Intelligence

### 3.1 Reddit

- `site:reddit.com/r/ClaudeAI "claude code" agents OR MCP OR hooks 2026`
- `site:reddit.com/r/ClaudeAI "claude code" multi-agent OR orchestration`
- `site:reddit.com/r/ClaudeAI "claude code" breaking change OR update`
- `site:reddit.com/r/ClaudeAI "claude code" custom agent`
- `site:reddit.com/r/ClaudeAI "claude code" Max tips OR techniques`
- `site:reddit.com/r/AnthropicAI "claude code" 2026`

### 3.2 Hacker News

Use `https://hn.algolia.com` with "last 3 months" filter:
- `claude code MCP`
- `claude code agents`
- `claude code update`
- `anthropic claude code` (sort by points)

### 3.3 Twitter/X

- `"claude code" MCP update -is:retweet since:2025-11-01`
- `"claude code" agents custom -is:retweet since:2025-11-01`
- `"claude code" hooks -is:retweet since:2025-11-01`
- `"claude code" breaking -is:retweet since:2025-11-01`
- Search posts from known Anthropic engineers and Claude Code maintainers

### 3.4 Broader GitHub Ecosystem

```bash
gh search issues "SSE transport" --repo modelcontextprotocol/specification --limit 10
gh release list --repo modelcontextprotocol/specification --limit 10
gh release list --repo jlowin/fastmcp --limit 10
```

- `github.com modelcontextprotocol SSE deprecation "streamable HTTP"`
- `github.com modelcontextprotocol/specification changes 2026`

### 3.5 Blogs and Tutorials

- `"claude code" multi-agent tutorial 2026`
- `"claude code" MCP server advanced 2026`
- `"claude code" hooks tutorial`
- `"claude code" Max workflow power user`
- `site:dev.to "claude code" 2026`
- `site:medium.com "claude code" 2026`

### 3.6 YouTube

- `"claude code" multi-agent demo 2026`
- `"claude code" MCP server setup advanced`
- `"claude code" custom agents workflow`

### 3.7 Discord

- Check Anthropic's official Discord for #claude-code channels
- Check MCP community Discord for transport/protocol discussions
- Search for power user workflow discussions and tips

---

## PHASE 4: Evaluation Framework

### Classification Matrix

For every finding, record:

| Field | Values |
|---|---|
| **Category** | Conflict / Opportunity / General Intelligence |
| **Severity** | P0 Critical / P1 High / P2 Medium / P3 Low |
| **Affected Component** | MCP Servers / Agent Definitions / Hooks / Settings / CLI / VS Code Extension / Governance Flow |
| **Confidence** | Confirmed (official) / Likely (credible report) / Rumor (unverified) |
| **Action** | Immediate fix / Plan migration / Evaluate adoption / Monitor / None |

### Priority Definitions

- **P0 -- Immediate**: Confirmed conflict with `settings.json` parsing, MCP SSE transport, `claude --print` flags, or agent YAML format. System breaks on update.
- **P1 -- Near-term**: Deprecation notices, changes to hook semantics, new agent capabilities that obsolete our patterns.
- **P2 -- Strategic**: Official multi-agent primitives, new MCP features, new hook types. Opportunities to simplify or enhance.
- **P3 -- Track**: Pricing changes, ecosystem direction, community patterns.

### Breaking Change Signatures

These specific technical signals indicate a breaking change for us:

| Signal | Impact |
|---|---|
| `settings.json` schema validation added | Custom `agents` and `workspace` keys rejected |
| `mcpServers` config format change | All 3 MCP server configs need updating |
| SSE transport deprecated for MCP | Must migrate servers to stdio or streamable HTTP |
| `claude --print` flag changes | `reviewer.py` subprocess calls break |
| Agent YAML frontmatter schema change | All 4 `.claude/agents/*.md` files need updating |
| `mcp:` tool prefix syntax change | Tool lists in agent YAML and settings.json break |
| `ExitPlanMode` tool rename | Hook matcher and governance script stop working |
| Hook exit code semantics change | Governance hook stops blocking correctly |
| Model shorthand changes | Agent configs in YAML and settings.json break |
| FastMCP v2 API changes | All 3 `server.py` implementations need updating |
| Permission allowlist syntax change | `settings.local.json` entries stop working |

---

## PHASE 5: Output Report

### Report Location

All output reports **MUST** be saved to: `docs/reports/`

### Report File Naming

Use this naming convention:
```
docs/reports/claude-code-intel-YYYY-MM-DD.md
```

Example: `docs/reports/claude-code-intel-2026-02-02.md`

### Report Structure

The output report must follow this exact structure:

```markdown
# Claude Code Feature Intelligence Report

**Generated**: YYYY-MM-DD
**Claude Code Version Checked**: [version if known]
**Search Scope**: [Official only / Official + Community / Full sweep]

## Executive Summary

[2-3 sentences: Key findings, any P0/P1 issues, overall ecosystem health]

---

## P0 — Critical (Immediate Action Required)

### [Finding Title]
- **Category**: Conflict / Opportunity
- **Affected Component**: [component]
- **Confidence**: Confirmed / Likely / Rumor
- **Source**: [URL or reference]
- **Details**: [Description of the finding]
- **Impact on Our System**: [Specific impact]
- **Files to Modify**:
  - `path/to/file.py` — [what needs to change]
  - `path/to/other.md` — [what needs to change]
- **Recommended Action**: [Specific steps]

[Repeat for each P0 finding, or "None identified" if clear]

---

## P1 — High Priority (Near-term Action)

### [Finding Title]
- **Category**: Conflict / Opportunity
- **Affected Component**: [component]
- **Confidence**: Confirmed / Likely / Rumor
- **Source**: [URL or reference]
- **Details**: [Description]
- **Impact on Our System**: [Impact]
- **Files to Modify**: [if applicable]
- **Recommended Action**: [Steps]
- **Timeline**: [Suggested timeframe]

[Repeat for each P1 finding]

---

## P2 — Strategic (Evaluate for Adoption)

### [Finding Title]
- **Category**: Opportunity / General Intelligence
- **Affected Component**: [component]
- **Confidence**: Confirmed / Likely / Rumor
- **Source**: [URL or reference]
- **Details**: [Description]
- **Potential Benefit**: [How this could improve our system]
- **Implementation Effort**: Low / Medium / High
- **Recommended Action**: [Evaluate / Plan adoption / Monitor]

[Repeat for each P2 finding]

---

## P3 — Track (Monitor Only)

| Finding | Category | Source | Notes |
|---------|----------|--------|-------|
| [Brief description] | General Intelligence | [source] | [key takeaway] |

[Table format for lower-priority items]

---

## Ecosystem Health Assessment

### Claude Code Platform Stability
- **Breaking changes in last 3 months**: [count and summary]
- **Deprecation warnings active**: [list]
- **Our compatibility status**: Green / Yellow / Red

### MCP Ecosystem
- **Transport protocol status**: SSE stable / SSE deprecated / Migration required
- **FastMCP compatibility**: [version we use] vs [latest version]
- **Spec changes**: [any relevant MCP specification updates]

### Community Sentiment
- **Common pain points**: [themes from Reddit/HN/Discord]
- **Power user patterns worth adopting**: [any valuable techniques discovered]

---

## Action Items Summary

### Immediate (This Week)
- [ ] [Action item with file path if applicable]

### Near-term (This Month)
- [ ] [Action item]

### Strategic (This Quarter)
- [ ] [Action item]

---

## Sources Consulted

### Official
- [ ] Anthropic Documentation — [date checked]
- [ ] Claude Code GitHub Releases — [latest version seen]
- [ ] Anthropic Blog — [date checked]
- [ ] npm package changelog — [version checked]

### Community
- [ ] Reddit r/ClaudeAI — [date checked]
- [ ] Hacker News — [date range]
- [ ] Twitter/X — [date range]
- [ ] Discord — [channels checked]
- [ ] Blogs/Tutorials — [count reviewed]

---

## Appendix: Raw Findings Log

[Optional: Include raw notes, URLs, and quotes from sources for future reference]
```

### Report Requirements

1. **Actionable**: Every P0 and P1 finding MUST include specific file paths and concrete next steps
2. **Traceable**: Every finding MUST include a source URL or reference
3. **Prioritized**: Findings MUST be sorted by priority (P0 first)
4. **Timestamped**: Report MUST include generation date for tracking freshness
5. **Comprehensive**: Include "None identified" sections rather than omitting empty priority levels

### Using the Report

After generating the report:

1. **P0 findings** → Create task briefs immediately, spawn workers to address
2. **P1 findings** → Add to project backlog with timeline
3. **P2 findings** → Review in next planning session
4. **P3 findings** → Archive for future reference

The report serves as input for:
- `.avt/task-briefs/` — Generate task briefs from P0/P1 findings
- `ARCHITECTURE.md` — Update if architectural changes needed
- `.claude/settings.json` — Update if configuration changes needed
- `mcp-servers/` — Modify servers if MCP changes required

---

## Execution Plan

1. **Run official channel searches** (Phase 1) — web searches and `gh` CLI commands against Anthropic repos
2. **Run feature-specific deep dives** (Phase 2) — targeted searches per extension point
3. **Run community scans** (Phase 3) — Reddit, HN, Twitter, Discord, blogs
4. **Classify all findings** using the evaluation matrix (Phase 4)
5. **Generate report** following the template above and save to `docs/reports/claude-code-intel-YYYY-MM-DD.md` (Phase 5)

### Recommended Cadence

- **Initial sweep**: Run all phases end-to-end
- **Monthly**: Re-run Phases 1.1 (docs), 1.2 (GitHub releases), and 2.2 (MCP transport) as highest-signal sources
- **On Claude Code version update**: Full re-run focusing on changelog and breaking changes

### Post-Execution

After saving the report to `docs/reports/`:
1. Review P0/P1 items with project lead
2. Create task briefs for any required changes
3. Update this prompt if new extension points are discovered
