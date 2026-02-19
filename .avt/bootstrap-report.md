# Bootstrap Report: Agent Vision Team

**Generated**: 2026-02-18
**Scale Tier**: Medium (35,530 LOC across ~210 source files)
**Status**: DRAFT (pending human review)

---

## Scale Assessment

| Metric | Value |
|--------|-------|
| Source files | ~210 (95 Python, 49 TSX, 36 TS, 22 Bash, 8 JS) |
| Total source LOC | 35,530 |
| Documentation files | 149 Markdown |
| Top-level directories | 9 (docs, e2e, extension, mcp-servers, prompts, scripts, server, templates, work) |
| Package boundaries | 7 (root, extension, extension/webview-dashboard, 3 MCP servers, server, e2e) |
| Monorepo | Yes (multi-language, multiple package.json/pyproject.toml) |
| Languages | TypeScript, Python, Bash, React/JSX |
| Config files | 12 (tsconfig x2, vite.config, esbuild.config, tailwind.config, pyproject.toml x5, Dockerfile, settings.json) |

**Classification**: Medium tier (10K-100K LOC, 100-1K files). Analysis performed inline without sub-agent waves.

---

## Partition Map

| Partition | Path | Language | LOC (est.) | Role |
|-----------|------|----------|------------|------|
| Extension Backend | `extension/src/` | TypeScript | ~3,500 | VS Code extension host, MCP clients, providers, commands |
| Dashboard Webview | `extension/webview-dashboard/src/` | React/TSX | ~6,000 | React dashboard, 29+ components, dual-mode transport |
| KG MCP Server | `mcp-servers/knowledge-graph/collab_kg/` | Python | ~1,200 | Knowledge graph CRUD, tier protection, JSONL persistence |
| Quality MCP Server | `mcp-servers/quality/collab_quality/` | Python | ~1,800 | Quality gates, trust engine, multi-language tool wrapping |
| Governance MCP Server | `mcp-servers/governance/collab_governance/` | Python | ~3,500 | Decision review, governed tasks, AI reviewer, usage tracking |
| AVT Gateway | `server/avt_gateway/` | Python | ~3,000 | FastAPI backend, REST API, WebSocket, job runner, MCP SSE client |
| E2E Tests | `e2e/` | Python | ~4,500 | 14 scenarios, project generator, parallel executor |
| Hook Scripts | `scripts/hooks/` | Bash/Python | ~2,500 | 5 lifecycle hooks, test harnesses |
| Agent Definitions | `.claude/agents/` | Markdown | ~3,000 | 8 agent role specifications |

---

## Vision Standard Candidates

| # | Draft Vision Standard | Source Evidence | Confidence |
|---|----------------------|-----------------|------------|
| V1 | **Vision First**: Vision standards are immutable by agents; only humans define the vision | `tier_protection.py`, `CLAUDE.md`, `project-overview.md` | HIGH |
| V2 | **Build Only What the Platform Cannot Do**: Custom infrastructure limited to capabilities Claude Code genuinely lacks | `project-overview.md` (Platform-Native Philosophy), `CLAUDE.md` | HIGH |
| V3 | **Intercept Early, Redirect Early**: Tasks governed from creation, verified before work begins | `governance-task-intercept.py`, `CLAUDE.md`, `project-overview.md` | HIGH |
| V4 | **Deterministic Verification Over AI Judgment**: Quality gates use real tools (compilers, linters, test suites), not LLM opinions | `quality/server.py`, `gates.py`, `project-overview.md` | HIGH |
| V5 | **No Silent Dismissals**: Every dismissed finding requires justification and identity | `trust_engine.py`, `project-overview.md` | HIGH |
| V6 | **Research Before Implementing**: Unfamiliar domains require researcher agent before workers implement | `CLAUDE.md`, `project-overview.md`, `researcher.md` agent definition | HIGH |
| V7 | **Three-Tier Governance Hierarchy**: Vision (human-only) > Architecture (human-gated) > Quality (automated) | `tier_protection.py`, `models.py`, `CLAUDE.md`, `project-overview.md` | HIGH |
| V8 | **No Em Dashes in Generated Prose**: Replace with commas, semicolons, colons, or parentheses | `CLAUDE.md` (Writing Style), all agent definitions | MEDIUM |

---

## Architecture Candidates

| # | Component/Pattern | Type | Source Evidence |
|---|------------------|------|-----------------|
| A1 | Knowledge Graph MCP Server | component | `collab_kg/server.py`, port 3101, JSONL persistence |
| A2 | Quality MCP Server | component | `collab_quality/server.py`, port 3102, SQLite trust engine |
| A3 | Governance MCP Server | component | `collab_governance/server.py`, port 3103, SQLite decision store |
| A4 | AVT Gateway | component | `server/avt_gateway/app.py`, FastAPI, port 8080 |
| A5 | VS Code Extension | component | `extension/src/extension.ts`, dashboard webview |
| A6 | React Dashboard | component | `extension/webview-dashboard/`, dual-mode transport |
| A7 | Five-Hook Verification Layer | pattern | `settings.json` hooks config, 5 hook scripts |
| A8 | Governed Task Lifecycle | pattern | `task_integration.py`, `governance-task-intercept.py` |
| A9 | Three-Tier Protection | pattern | `tier_protection.py`, enforced at KG tool level |
| A10 | Dual-Mode Transport | pattern | `useTransport.ts`, VS Code postMessage vs HTTP/WebSocket |
| A11 | Temp File I/O for CLI | pattern | `reviewer.py`, `DashboardWebviewProvider.ts` |
| A12 | PIN Review Methodology | pattern | `reviewer.py` prompts, `CLAUDE.md`, agent definitions |
| A13 | Session-Scoped Holistic Review | pattern | `governance-task-intercept.py`, flag files, settle checker |
| A14 | Agent Teams Orchestration | pattern | `CLAUDE.md`, `settings.json`, `.claude/agents/` |
| A15 | E2E Testing Harness | component | `e2e/`, 14 scenarios, project generator |

---

## Code Structure

### Layered Architecture

1. **Presentation Layer**: VS Code Extension + React Dashboard (dual-mode)
2. **API Layer**: AVT Gateway (FastAPI REST + WebSocket) OR VS Code postMessage bridge
3. **Service Layer**: Three MCP Servers (KG, Quality, Governance)
4. **Persistence Layer**: JSONL (KG), SQLite (Governance, Quality/Trust), JSON files (task system, jobs, config)
5. **Hook Layer**: Five lifecycle hooks providing platform-level governance verification
6. **Agent Layer**: Eight specialized agents with distinct roles and MCP access profiles

### Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| Extension activation | `extension/src/extension.ts` | `activate()` function |
| Dashboard app | `extension/webview-dashboard/src/main.tsx` | React root |
| KG Server | `mcp-servers/knowledge-graph/collab_kg/server.py` | `__main__` block |
| Quality Server | `mcp-servers/quality/collab_quality/server.py` | `__main__` block |
| Governance Server | `mcp-servers/governance/collab_governance/server.py` | `__main__` block |
| Gateway | `server/avt_gateway/app.py` | FastAPI `app` instance |
| E2E Runner | `e2e/run-e2e.py` | `main()` function |
| Hook intercept | `scripts/hooks/governance-task-intercept.py` | `main()` function |

---

## Discovered Patterns

| Pattern | Description | Frequency | Tier |
|---------|-------------|-----------|------|
| P1: FastMCP Server | Identical structure across all 3 MCP servers | 3/3 | Architecture |
| P2: Pydantic Aliases | Field aliases for JSON serialization, Python names in code | Universal | Architecture |
| P3: Temp File I/O | Claude CLI uses temp files, not args/pipes | 2/2 sites | Architecture |
| P4: SSE MCP Connection | GET /sse + JSON-RPC 2.0 + SSE streaming | 2/2 clients | Architecture |
| P5: Context Provider | React Context for dashboard state management | Universal | Architecture |
| P6: Hook Verification | JSON stdin, fast-path, SQLite, exit codes | 5/5 hooks | Architecture |
| P7: E2E Scenario | BaseScenario, isolation, structural assertions | 14/14 | Architecture |
| P8: PIN Review | Positive, Innovative, Negative methodology | Universal | Vision |

---

## Convention Discovery

### Naming Conventions

| Context | Convention | Examples |
|---------|-----------|----------|
| Python packages | snake_case | `collab_kg`, `collab_quality`, `avt_gateway` |
| Python modules | snake_case | `tier_protection.py`, `trust_engine.py` |
| Python classes | PascalCase | `KnowledgeGraph`, `GovernanceStore` |
| TypeScript files | PascalCase | `McpClientService.ts`, `DashboardWebviewProvider.ts` |
| React components | PascalCase | `AgentCards.tsx`, `GovernancePanel.tsx` |
| Agent definitions | kebab-case | `quality-reviewer.md`, `kg-librarian.md` |
| Hook scripts | kebab-case | `governance-task-intercept.py` |
| MCP tool names | snake_case | `create_entities`, `submit_decision` |
| Config keys | camelCase (JSON) | `entityType`, `setupComplete` |

### Error Handling

- **Python MCP servers**: Return error dicts `{"error": "message"}`, not exceptions
- **TypeScript extension**: Try-catch with `vscode.window.showErrorMessage()`
- **Hook scripts**: Never crash; exit silently on parse errors

### Build Conventions

- Python: `uv`, `pyproject.toml`, hatchling, Python 3.12+
- TypeScript: `npm`, esbuild (extension), Vite (dashboard)
- Extension build: `node esbuild.config.js` (not `npm run compile`)
- Webview build: `cd extension/webview-dashboard && npm run build`

---

## Discovered Rules (Draft)

| # | Rule | Level | Scope |
|---|------|-------|-------|
| R1 | No em dashes in generated prose; use commas, semicolons, colons, or parentheses | ENFORCE | all |
| R2 | Use temp file I/O (not CLI args or pipes) for claude CLI invocations | ENFORCE | worker, governance-reviewer |
| R3 | All quality gates must pass before task completion | ENFORCE | worker |
| R4 | Workers must call `submit_decision` before implementing key decisions | ENFORCE | worker |
| R5 | MCP servers return error dicts rather than raising exceptions | PREFER | worker, architect |
| R6 | Hook scripts must never crash; fail silently with logging | ENFORCE | all |
| R7 | Run the build before reporting task completion | ENFORCE | worker |
| R8 | Extension backend build: `node esbuild.config.js` (not `npm run compile`) | ENFORCE | worker |
| R9 | Python uses `uv` for package management, not pip directly | PREFER | worker |
| R10 | Access Pydantic alias fields by Python name (`.entity_type`), not alias (`.entityType`) | ENFORCE | worker |

---

## Contradictions and Ambiguities

1. **Language configuration**: `project-config.json` lists only `["typescript"]` but the codebase is ~45% Python, ~40% TypeScript, ~10% Bash
2. **PIN methodology scope**: Documentation says PIN is for "all reviews" but quality gates are purely deterministic; PIN applies only to governance AI reviews

---

## Recommended Actions

1. **APPROVE** vision standards V1-V8 for KG ingestion
2. **APPROVE** architecture candidates A1-A15 for KG ingestion
3. **APPROVE** rules R1-R10 for project-config.json
4. **REVIEW** architecture docs with Mermaid diagrams
5. **REVIEW** style guide
6. **UPDATE** project-config.json languages to include Python and Bash

---

## Output Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Bootstrap Report | `.avt/bootstrap-report.md` | This file |
| Vision Standards | `docs/vision/*.md` | 8 files generated |
| Architecture Overview | `docs/architecture/overview.md` | Generated |
| Architecture Components | `docs/architecture/components/*.md` | Generated |
| Architecture Patterns | `docs/architecture/patterns/*.md` | Generated |
| Architecture Flows | `docs/architecture/flows/*.md` | Generated |
| Style Guide | `docs/style/style-guide.md` | Generated |
| Draft Rules | `.avt/bootstrap-rules-draft.json` | Generated |
