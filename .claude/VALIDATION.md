# Phase 2 Validation: Subagents + End-to-End Flow

This document describes how to validate that the Collaborative Intelligence System is correctly configured and operational.

## System Components

### ✅ MCP Servers (Phase 1)
- **Knowledge Graph Server**: `mcp-servers/knowledge-graph/`
  - JSONL persistence in `.avt/knowledge-graph.jsonl` (MCP server manages this)
  - Tier protection (Vision > Architecture > Quality)
  - 18 tests passing, 74% coverage
- **Quality Server**: `mcp-servers/quality/`
  - SQLite trust engine in `.avt/trust-engine.db` (MCP server manages this)
  - Language-agnostic tool wrapping (ruff, eslint, pytest, etc.)
  - 26 tests passing, 48% coverage

### ✅ Subagent Definitions (Phase 2)
- **Worker**: `.claude/agents/worker.md`
  - Model: Opus
  - Tools: Read, Write, Edit, Bash, Glob, Grep, KG, Quality
  - Role: Implements scoped tasks with quality checks
- **Quality Reviewer**: `.claude/agents/quality-reviewer.md`
  - Model: Opus
  - Tools: Read, Glob, Grep, Bash, KG, Quality (read-only)
  - Role: Three-lens review (Vision → Architecture → Quality)
- **KG Librarian**: `.claude/agents/kg-librarian.md`
  - Model: Sonnet
  - Tools: Read, Write, Glob, Grep, KG
  - Role: Curates institutional memory after work sessions

### ✅ Orchestration
- **CLAUDE.md**: Root-level orchestrator instructions
  - Task decomposition protocol
  - Quality review protocol
  - Memory protocol
  - Drift detection
- **Settings**: `.claude/settings.json`
  - MCP server configurations
  - Lifecycle hooks
  - Agent tool mappings
  - Workspace paths

### ✅ Workspace Structure
```
.claude/
├── agents/                          # Subagent definitions
│   ├── worker.md
│   ├── quality-reviewer.md
│   ├── kg-librarian.md
│   ├── researcher.md
│   └── project-steward.md
├── collab/
│   └── knowledge-graph.jsonl        # KG persistence (created on first use)
└── settings.json                    # MCP and agent configuration

.avt/
├── task-briefs/                     # Task briefs for workers
│   └── example-001-add-feature.md
├── memory/                          # Archival memory files
│   ├── architectural-decisions.md
│   ├── troubleshooting-log.md
│   ├── solution-patterns.md
│   └── research-findings.md
├── research-prompts/                # Research prompt definitions
├── research-briefs/                 # Research output briefs
├── session-state.md                 # Current session progress
└── project-config.json              # Project configuration
```

## Validation Steps

### 1. Verify MCP Servers Start

**Terminal 1: Knowledge Graph Server**
```bash
cd mcp-servers/knowledge-graph
uv run python -m collab_kg.server
# Expected: Server starts on SSE transport, port 3101
```

**Terminal 2: Quality Server**
```bash
cd mcp-servers/quality
uv run python -m collab_quality.server
# Expected: Server starts on SSE transport, port 3102
```

### 2. Verify Subagent Definitions

```bash
# Check all subagent files exist and have valid YAML frontmatter
cat .claude/agents/worker.md | head -15
cat .claude/agents/quality-reviewer.md | head -15
cat .claude/agents/kg-librarian.md | head -15
```

Expected: Each file should have:
- YAML frontmatter with `model` and `tools` fields
- Clear role description
- Protocols and constraints

### 3. Verify Settings Configuration

```bash
cat .claude/settings.json
```

Expected:
- `mcpServers` section with `collab-kg` and `collab-quality`
- `agents` section with configurations for worker, quality-reviewer, kg-librarian
- `workspace` section with paths to task-briefs, memory, session-state

### 4. Run Tests

```bash
# Knowledge Graph tests
cd mcp-servers/knowledge-graph
uv run pytest -v
# Expected: 18 tests passing

# Quality server tests
cd mcp-servers/quality
uv run pytest -v
# Expected: 26 tests passing
```

### 5. Simulate End-to-End Flow

This is a manual walkthrough to verify the system is operational:

#### Step 1: Start MCP Servers
Start both servers in separate terminals (see step 1 above).

#### Step 2: Populate Vision Standards (via orchestrator)
In a new Claude Code CLI session:
```
Create a vision standard entity in the KG:
- name: "protocol_based_di"
- entityType: "vision_standard"
- observations: ["protection_tier: vision", "All services must use protocol-based dependency injection"]
```

#### Step 3: Spawn a Worker
```
Task tool → subagent_type: worker
prompt: "Read the task brief in .avt/task-briefs/example-001-add-feature.md and query the KG for vision standards"
```

Expected: Worker should:
1. Read the task brief
2. Query `get_entities_by_tier("vision")`
3. Report the vision standards it found

#### Step 4: Spawn Quality Reviewer
```
Task tool → subagent_type: quality-reviewer
prompt: "Review a hypothetical change that adds a new service using singleton pattern instead of DI"
```

Expected: Quality reviewer should:
1. Query vision standards
2. Detect the pattern violation
3. Report a vision-tier finding with rationale and suggestion

#### Step 5: Spawn KG Librarian
```
Task tool → subagent_type: kg-librarian
prompt: "Curate the KG after the session. Consolidate observations and sync to archival files."
```

Expected: Librarian should:
1. Query recent KG entities
2. Consolidate observations
3. Update memory files in `.avt/memory/`

## Success Criteria

✅ Phase 2 is complete when:
1. Both MCP servers start without errors
2. All 44 tests pass (18 KG + 26 Quality)
3. Subagent definitions are valid and complete
4. Settings.json correctly references MCP servers and agents
5. Workspace directory structure is complete with example files
6. Manual end-to-end flow successfully demonstrates:
   - Worker querying KG for vision standards
   - Quality reviewer detecting vision conflicts
   - KG librarian curating memory

## Known Limitations

- **MCP server startup**: Servers must be started manually before Claude Code sessions
- **Extension not built**: Phase 3 (observability extension) is not yet started
- **No git worktrees**: Worker isolation via worktrees not yet demonstrated
- **Coverage gaps**: Some integration branches not tested (require external tools)

## Next Phase

**Phase 3: VS Code Extension (Observability)**
- Memory Browser (TreeView) — displays KG entities grouped by tier
- Findings Panel (TreeView) — displays quality findings with diagnostics
- Tasks Panel (TreeView) — displays task briefs from filesystem
- Session Dashboard (Webview) — React-based overview
- Status bar integration
- Read-only MCP client for monitoring

See [ARCHITECTURE.md](../ARCHITECTURE.md) section 8 for extension details.
