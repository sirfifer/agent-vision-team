# Bootstrap Report — agent-vision-team-devhost

## Scale Assessment

| Metric | Value |
|--------|-------|
| Scale Tier | **Medium** |
| Source LOC | 37,913 |
| Source Files | 209 |
| Documentation Files | 97 |
| Languages | Python (95), TypeScript (36), TSX (47), Shell (22), JS (9) |
| Package Boundaries | 8 |
| Top-Level Directories | 9 |

## Knowledge Graph Seed

**30 entities seeded** into `.avt/knowledge-graph.jsonl`:

### Vision Tier (11 entities)
These are the inviolable principles discovered from documentation:

1. **three_tier_hierarchy**: Lower tiers cannot modify higher tiers
2. **vision_tier_human_only**: Only humans modify vision entities
3. **every_task_governed**: Every task gets automatic governance review
4. **quality_is_deterministic**: Use tools, not subjective judgment
5. **no_silent_dismissals**: Every dismissal requires justification
6. **pin_review_methodology**: All reviews follow Positive, Innovative, Negative
7. **platform_native_philosophy**: Build only what the platform cannot do
8. **workers_must_submit_decision**: submit_decision before key choices
9. **governance_reviewer_isolation**: Isolation is a security feature
10. **no_em_dashes**: Writing style prohibition
11. **five_quality_gates**: Build, lint, tests, coverage, findings

### Architecture Tier (15 entities)
Key patterns and components:

1. **hook_based_governance**: 5 lifecycle hooks for deterministic verification
2. **holistic_review_settle_debounce**: 3s settle, session-scoped flags
3. **knowledge_graph_mcp_server**: 11 tools, JSONL, port 3101
4. **quality_mcp_server**: 10 tools, SQLite trust engine, port 3102
5. **governance_mcp_server**: 12 tools, AI review, port 3103
6. **agent_teams_orchestration**: Full sessions, shared task list, self-claim
7. **eight_specialized_agents**: Worker, QR, KG-lib, Gov-rev, Researcher, Steward, Architect, Bootstrapper
8. **governed_task_lifecycle**: Blocked-from-birth, multi-blocker stacking
9. **vscode_extension**: Observability layer, MCP clients
10. **webview_dashboard**: React + Tailwind, dual-mode transport
11. **avt_gateway**: FastAPI, 35 endpoints, WebSocket
12. **e2e_testing_harness**: 14 scenarios, 292+ assertions
13. **temp_file_io_pattern**: Temp files for CLI invocations
14. **checkpoint_resume_pattern**: git tag checkpoints
15. **drift_detection**: Time, loop, scope, quality

### Quality Tier (4 entities)
Conventions and observations:

1. **python_conventions**: snake_case, Pydantic, FastMCP, uv
2. **typescript_conventions**: camelCase, React hooks, Context, esbuild/Vite
3. **shell_conventions**: set -e, CLAUDE_PROJECT_DIR, exit codes
4. **bootstrap_scale_assessment**: Medium tier metrics

## Infrastructure Setup

### MCP Configuration
- **Project-scope** `.claude/mcp.json` created with devhost paths
- All three servers configured: collab-kg, collab-quality, collab-governance
- Transport: stdio (uv run python -m ...)
- Each server's `cwd` points to devhost's MCP server directory

### Settings
- `.claude/settings.json` updated: Read/Write/Edit permissions for devhost path
- Hook configuration uses `$CLAUDE_PROJECT_DIR` (resolves automatically)
- Agent Teams enabled via env var

### Data State
- `.avt/knowledge-graph.jsonl`: Seeded with 30 entities
- `.avt/governance.db`: Backed up to .pre-bootstrap (fresh DB created on first use)
- `.avt/trust-engine.db`: Backed up to .pre-bootstrap (fresh DB created on first use)
- `.avt/hook-governance.log`: Backed up to .pre-bootstrap
- `.avt/hook-holistic.log`: Backed up to .pre-bootstrap

## Component Inventory

| Component | Path | Language | MCP Tools |
|-----------|------|----------|-----------|
| Knowledge Graph Server | mcp-servers/knowledge-graph/ | Python | 11 |
| Quality Server | mcp-servers/quality/ | Python | 10 |
| Governance Server | mcp-servers/governance/ | Python | 12 |
| VS Code Extension | extension/ | TypeScript | - |
| Webview Dashboard | extension/webview-dashboard/ | TS/React | - |
| AVT Gateway | server/ | Python | - |
| Lifecycle Hooks | scripts/hooks/ | Python/Shell | - |
| E2E Test Harness | e2e/ | Python | - |
| Agent Definitions | .claude/agents/ | Markdown | - |

## Cross-Component Dependencies

```
Orchestrator (CLAUDE.md)
  |-- reads --> Agent Definitions (.claude/agents/)
  |-- spawns --> Worker, QR, KG-lib, Architect, Researcher, Steward, Bootstrapper
  |-- invokes --> Governance Reviewer (claude --print)

PostToolUse Hook --> Governance MCP Server
                 --> Holistic Settle Checker (background)
                 --> Holistic Review Gate (flag file)

Worker Agent --> KG MCP (query standards)
            --> Quality MCP (run gates)
            --> Governance MCP (submit decisions)

Quality Reviewer --> KG MCP (load standards for three-lens review)
                --> Quality MCP (record findings)

KG Librarian --> KG MCP (curate entities)
             --> .avt/memory/ (sync archival files)

VS Code Extension --> All 3 MCP Servers (client connections)
                  --> Webview Dashboard (postMessage transport)

AVT Gateway --> All 3 MCP Servers (manages instances)
            --> React Dashboard (HTTP + WebSocket)
```

## Verification Checklist

To verify the bootstrap from a Claude Code session in devhost:

1. [ ] `get_entities_by_tier("vision")` returns 11 entities
2. [ ] `get_entities_by_tier("architecture")` returns 15 entities
3. [ ] `search_nodes("governance")` returns relevant results
4. [ ] `get_governance_status()` returns empty/fresh state
5. [ ] Hooks fire on TaskCreate (check .avt/hook-governance.log)
6. [ ] Holistic review gate passes when no flag file exists
7. [ ] Quality gates can be invoked via `check_all_gates()`

## Notes

- **Project-scope MCP config**: Created at `.claude/mcp.json` in devhost. Per Issue #13898, project-scope MCP may cause subagents to hallucinate MCP results. If this occurs, migrate to user-scope by updating `~/.claude/mcp.json` to point to devhost paths.
- **Shared repo**: Both agent-vision-team and agent-vision-team-devhost point to the same Git remote. They share code but have independent KG, governance, and trust data.
- **Example vision standards**: CLAUDE.md lists 4 example vision standards (protocol-based DI, no singletons, public API tests, Result types). These were NOT seeded as they are labeled as examples to populate, not confirmed project standards.

## Bootstrap Timestamp
2026-02-18
