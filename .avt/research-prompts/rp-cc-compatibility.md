---
type: periodic
topic: "Claude Code Platform Compatibility Check"
context: "AVT depends on Claude Code features (hooks, Agent Teams, MCP, CLI, tasks, settings). Track changes that affect us."
scope: "Claude Code releases, hooks, agents, MCP, CLI, settings, task system"
model_hint: sonnet
output: change_report
schedule:
  type: daily
  time: "08:07"
related_entities:
  - "Claude Code Platform"
---

# Claude Code Compatibility Check

## Objective

Detect Claude Code changes that affect AVT: breaking changes, deprecations, new features worth adopting, and ecosystem shifts. Compare findings against the AVT dependency manifest and produce a prioritized report.

## Startup

1. Load the dependency manifest from `scripts/validation/platform-deps.yaml`. This lists every Claude Code feature AVT depends on, organized by category (model_resolution, cli, agent_teams, hooks, mcp, tasks, environment), with criticality flags and `used_by` file references.

2. Query the Knowledge Graph for existing baseline:
   - `search_nodes("Claude Code Platform")` to get previous findings
   - `get_entities_by_tier("architecture")` for current architectural context
   Note what is already known so you only report net-new information.

3. Read the full search playbook at `prompts/claude-code-feature-intelligence-search.md` for detailed search queries, evaluation matrix, and report template.

## Research Protocol

### Phase 1: Official Channels (Always Run)

Execute the Phase 1 searches from the intelligence search playbook:

1. **Claude Code documentation** (docs.anthropic.com): Check for changes to hooks, agents, MCP, settings.json, CLI flags
2. **Claude Code GitHub** (github.com/anthropics/claude-code): Check recent releases, issues tagged "breaking change"
3. **Anthropic Blog** (anthropic.com/news): Check for Claude Code announcements
4. **npm package**: Check @anthropic-ai/claude-code version history
5. **Claude Agent SDK**: Check for SDK changes that affect our orchestration

### Phase 2: Feature-Specific Deep Dives (If Phase 1 Finds Signals)

If Phase 1 reveals changes or hints of changes, run targeted deep dives from the playbook's Phase 2:
- Agent/Subagent system (YAML frontmatter, Task tool, model routing)
- MCP server support (transport, config format, FastMCP)
- Hooks system (new types, exit code semantics, matchers)
- Settings format (schema validation, permissions syntax)
- CLI (`claude --print` flags, output format)
- Multi-agent patterns (official primitives, Agent Teams changes)

### Phase 3: Community Intelligence (Weekly or On Signal)

Run community searches from the playbook's Phase 3 weekly, or immediately if Phase 1/2 found signals:
- Reddit r/ClaudeAI, r/AnthropicAI
- Hacker News (hn.algolia.com)
- GitHub ecosystem (MCP specification, FastMCP)
- Developer blogs and tutorials

## Classification

Use the P0-P3 priority system from the intelligence search playbook:

- **P0 (Critical)**: Confirmed conflict with settings.json parsing, MCP transport, `claude --print` flags, hook semantics, or agent YAML format. System breaks on update.
- **P1 (High)**: Deprecation notices, changes to hook semantics, new agent capabilities that obsolete our patterns.
- **P2 (Strategic)**: Official multi-agent primitives, new MCP features, new hook types. Opportunities to simplify or enhance.
- **P3 (Track)**: Pricing changes, ecosystem direction, community patterns.

For each finding, record: category (Conflict/Opportunity/General Intelligence), severity (P0-P3), affected component, confidence (Confirmed/Likely/Rumor), and action (Immediate fix/Plan migration/Evaluate adoption/Monitor/None).

## Delta Detection

Before reporting a finding, check the KG baseline:
- If the finding is already recorded as an observation on `Claude Code Platform`, skip it
- If the finding updates a previously recorded item (e.g., a rumored change is now confirmed), update the observation and report the status change
- Only generate report entries for genuinely new or changed findings

## Output

### If No New Findings

1. Update the last-run timestamp: write current epoch to `.avt/compatibility-monitor/.last-run-ts`
2. Add a brief observation to the KG: `add_observations("Claude Code Platform", ["YYYY-MM-DD: Compatibility check completed, no new findings"])`
3. Produce no report file. Return a brief message: "Compatibility check complete. No new findings."

### If New Findings Exist

1. Generate the report following the template from the intelligence search playbook (Phase 5)
2. Write the report to `.avt/compatibility-reports/cr-YYYY-MM-DD-cc-compat.md`
3. If any P0/P1 findings exist, also write to `docs/reports/claude-code-intel-YYYY-MM-DD.md` (promoted, committed)
4. Update the KG:
   - Add observations to `Claude Code Platform` entity
   - For P0/P1 findings: create dedicated entities (type `problem` for conflicts, `solution_pattern` for opportunities) with `affects` relations to relevant AVT component entities
5. Update last-run timestamp
6. Return a summary with priority counts and key findings

### Adaptive Follow-up

If you detect signals of impending changes (release candidate, pending announcement, beta feature):
- Note this in your return message with a recommended follow-up time (e.g., "Suggest follow-up in 4 hours to check for release notes")
- The orchestrator will use CronCreate to schedule the follow-up

## Constraints

- Do not modify vision-tier or architecture-tier KG entities (observations only)
- Cite sources for all findings
- Clearly distinguish confirmed facts from speculation
- Keep the report actionable: every P0/P1 finding must include specific file paths and concrete next steps
- Reference the `used_by` field from `platform-deps.yaml` to identify affected files
