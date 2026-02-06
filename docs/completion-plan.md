# Completion Plan — Agent Vision Team

**Date**: 2026-02-06
**Baseline**: ARCHITECTURE.md v2 (source of truth, all internal inconsistencies fixed)
**Goal**: Nothing stepped out, nothing unfinished, nothing lacks functionality, nothing not wired up.

---

## Summary

The implementation audit confirms **all core infrastructure is operational**: 3 MCP servers (29 tools), 6 subagent definitions, E2E testing harness (11 scenarios, 172+ assertions), VS Code extension (dashboard, wizard, tutorial, walkthrough, 3 MCP clients, 4 TreeViews). The remaining work falls into three categories:

1. **Path consistency bugs** — code and docs still reference the legacy `.claude/collab/` path instead of `.avt/`
2. **Unwired functionality** — implemented config layers not yet connected to runtime behavior
3. **Quality server stubs** — two gate implementations are TODO placeholders

There is also **Phase 5** work (cross-project memory, installation script) which is explicitly scoped as future and is NOT part of this plan.

---

## Work Items

### WI-1: Fix `.claude/collab/` → `.avt/` path references (CODE)

**Priority**: P0 — functional correctness
**Effort**: Small
**Risk**: E2E tests may break if paths change without updating assertions

The MCP servers all default to `.avt/` paths, but the E2E project generator and the installation template still create/reference `.claude/collab/`. This creates inconsistency — generated test projects put data in a different location than the servers expect.

#### Files to change:

| File | Line(s) | Change |
|------|---------|--------|
| `e2e/generator/project_generator.py` | 158, 181-184 | Change docstring and directory creation from `.claude/collab/` to `.avt/` |
| `e2e/generator/project_generator.py` | 315 | Change governance.db path from `.claude/collab/governance.db` to `.avt/governance.db` |
| `e2e/generator/project_generator.py` | 376 | KG path should use `.avt/` not `dirs["collab"]` |
| `templates/collab/mcp-config.json` | 8 | Change `KG_STORAGE_PATH` from `.claude/collab/knowledge-graph.jsonl` to `.avt/knowledge-graph.jsonl` |
| `scripts/dogfood-test.sh` | 50 | Update path reference |

#### Validation:
- Run `./e2e/run-e2e.sh` — all 11 scenarios must pass
- Verify generated projects put data files under `.avt/`

---

### WI-2: Fix `.claude/collab/` → `.avt/` path references (DOCS)

**Priority**: P1 — documentation accuracy
**Effort**: Small
**Risk**: None

#### Files to change:

| File | Line(s) | Change |
|------|---------|--------|
| `CLAUDE.md` | 361 | `.claude/collab/governance.db` → `.avt/governance.db` |
| `e2e/README.md` | 129, 661 | `.claude/collab/` → `.avt/` |
| `.claude/VALIDATION.md` | 9, 13 | `.claude/collab/knowledge-graph.jsonl` → `.avt/knowledge-graph.jsonl`, `.claude/collab/trust-engine.db` → `.avt/trust-engine.db` |
| `mcp-servers/governance/README.md` | 116 | `.claude/collab/governance.db` → `.avt/governance.db` |
| `mcp-servers/quality/README.md` | 173 | `.claude/collab/trust-engine.db` → `.avt/trust-engine.db` |
| `mcp-servers/knowledge-graph/README.md` | 174 | `.claude/collab/knowledge-graph.jsonl` → `.avt/knowledge-graph.jsonl` |
| `extension/media/walkthrough/05-knowledge-graph.md` | 16 | `.claude/collab/kg.jsonl` → `.avt/knowledge-graph.jsonl` |
| `.claude/commands/project-overview.md` | 33 | `.claude/collab/` → `.avt/` |
| `prompts/claude-code-feature-intelligence-search.md` | 447 | `.claude/collab/task-briefs/` → `.avt/task-briefs/` |

#### Validation:
- `grep -r '\.claude/collab' . --include='*.md' --include='*.sh' --include='*.json' --include='*.py'` returns zero matches (excluding `docs/v1-full-architecture/` and `docs/arch-v2-*`)

---

### WI-3: Wire project rules auto-injection into orchestrator

**Priority**: P1 — described in CLAUDE.md but not functional
**Effort**: Medium
**Risk**: Low — additive change, no existing behavior modified

#### Current state:
- `RulesConfig` and `RuleEntry` interfaces are fully defined in the extension's `ProjectConfig.ts`
- `RulesStep.tsx` wizard step allows creating/editing rules with enforcement levels (enforce/prefer/guide) and agent scoping
- Rules are stored in `.avt/project-config.json` under the `rules` field
- CLAUDE.md Section "Project Rules Protocol" describes the injection format

#### What's missing:
The orchestrator (CLAUDE.md instructions) tells the orchestrator to compile rules and prepend them to agent prompts, but there's no automated mechanism. When the human + orchestrator spawns a subagent via the Task tool, they must manually read `.avt/project-config.json`, filter rules by agent scope, and format the preamble.

#### Implementation options:

**Option A: Document the manual protocol (minimal)**
Add a concrete code example to CLAUDE.md showing exactly how to compile and inject rules. The orchestrator follows this as part of its "spawn worker" protocol. No code changes needed.

**Option B: Create a rules compilation utility (recommended)**
Add a small utility (Python script or shell script) that reads `.avt/project-config.json` and outputs the compiled preamble for a given agent role. The orchestrator calls this before spawning agents.

```bash
# Example usage:
./scripts/compile-rules.sh worker
# Output:
# ## Project Rules
# ENFORCE:
# - All services use protocol-based DI
# PREFER (explain if deviating):
# - Prefer composition over inheritance
```

**Option C: MCP tool on one of the servers**
Add a `compile_rules(agent_role)` tool to the Governance or Quality MCP server. The orchestrator calls this tool before spawning agents and includes the result in the prompt.

#### Recommendation: Option B
- Simple, testable, no server changes
- Can be validated in E2E tests
- Falls within the "platform-native" philosophy (scripts, not infrastructure)

---

### WI-4: Implement quality server build gate

**Priority**: P2 — functional but low-impact (currently returns `passed: true` with "not yet implemented")
**Effort**: Small
**Risk**: Low

#### Current state (gates.py:20-23):
```python
if enabled_gates.get("build", True):
    # TODO: Run build command and check exit code
    build = GateResult(name="build", passed=True, detail="Build check not yet implemented")
```

#### Implementation:
1. Read `.avt/project-config.json` for the configured build command (e.g., `npm run build`, `cargo build`, `uv run python -m py_compile`)
2. Execute the command via `subprocess.run()` with timeout
3. Return `passed=True` if exit code is 0, `passed=False` with stderr detail otherwise
4. Handle missing config gracefully (skip gate with "No build command configured")

#### Quality config schema addition needed:
```json
{
  "settings": {
    "qualityGates": {
      "build": { "enabled": true, "command": "npm run build" }
    }
  }
}
```

#### Validation:
- Add unit test for build gate with mock subprocess
- E2E scenario s06 (Quality Gates) should verify the gate runs

---

### WI-5: Implement quality server findings gate

**Priority**: P2 — functional but low-impact (currently returns `passed: true` with "No critical findings")
**Effort**: Small
**Risk**: Low

#### Current state (gates.py:63-65):
```python
if enabled_gates.get("findings", True):
    # TODO: Check for unresolved critical findings
    findings = GateResult(name="findings", passed=True, detail="No critical findings")
```

#### Implementation:
1. Import the `TrustEngine` and query for unresolved findings with severity `critical` or `high`
2. Return `passed=False` if any critical/high findings exist that haven't been dismissed
3. Include finding count in the detail message

```python
if enabled_gates.get("findings", True):
    engine = TrustEngine()
    unresolved = engine.get_unresolved_findings(min_severity="high")
    if unresolved:
        findings = GateResult(
            name="findings",
            passed=False,
            detail=f"{len(unresolved)} unresolved critical/high findings"
        )
    else:
        findings = GateResult(name="findings", passed=True, detail="No critical findings")
```

#### Dependencies:
- TrustEngine may need a `get_unresolved_findings()` method (or equivalent query)
- Check if the trust engine schema supports severity levels

#### Validation:
- Add unit test with seeded findings
- E2E scenario s07 (Trust Engine) could be extended to verify this gate

---

### WI-6: Update ARCHITECTURE.md command count

**Priority**: P2 — documentation accuracy
**Effort**: Trivial

#### Current state:
ARCHITECTURE.md Section 18 (Implementation Status) says "12 commands" in two places (lines 3825 and 3869).

#### Actual commands registered in package.json:
1. `collab.refreshMemory`
2. `collab.refreshFindings`
3. `collab.refreshTasks`
4. `collab.searchMemory`
5. `collab.viewDashboard`
6. `collab.validateAll`
7. `collab.connectMcpServers`
8. `collab.openSetupWizard`
9. `collab.openWalkthrough`
10. `collab.openWorkflowTutorial`
11. `collab.runResearch`
12. `collab.createTaskBrief`

Plus commands registered only in extension.ts (not in package.json contributes):
13. `collab.ingestDocuments`
14. `collab.startSystem` (if present)
15. `collab.stopSystem` (if present)

#### Action:
- Audit exact command count (package.json contributes.commands + extension.ts-only registrations)
- Update ARCHITECTURE.md lines 3825 and 3869 with correct count
- If commands 13-15 exist only in extension.ts, either add them to package.json contributes or document them as internal commands

---

### WI-7: Template modernization

**Priority**: P2 — affects target project installation
**Effort**: Small

#### Current state:
`templates/collab/mcp-config.json` is missing the Governance server entry and uses `.claude/collab/` paths.

#### Changes:
1. Add Governance server configuration (port 3103)
2. Update `KG_STORAGE_PATH` to `.avt/knowledge-graph.jsonl`
3. Verify all template files in `templates/` match current architecture
4. Ensure `ProjectConfigService.ensureFolderStructure()` creates `.avt/` data directories (not `.claude/collab/`)

#### Validation:
- Run wizard in Extension Development Host
- Verify created folder structure matches architecture spec

---

## Execution Order

```
Phase A (P0 — Do First):
  WI-1  Fix code paths (.claude/collab → .avt)
  └── Run E2E to validate

Phase B (P1 — Do Second, parallelizable):
  WI-2  Fix doc paths (.claude/collab → .avt)      ← can run in parallel
  WI-3  Wire rules auto-injection                   ← can run in parallel
  WI-7  Template modernization                      ← can run in parallel

Phase C (P2 — Do Third, parallelizable):
  WI-4  Build gate implementation                   ← can run in parallel
  WI-5  Findings gate implementation                ← can run in parallel
  WI-6  ARCHITECTURE.md command count fix            ← can run in parallel
```

---

## Out of Scope (Phase 5 — Future)

These items are defined in ARCHITECTURE.md Phase 5 but are explicitly deferred:

- **Cross-project memory**: Share institutional memory across multiple projects
- **Installation script for target projects**: `npx create-collab-intelligence` or similar

---

## Definition of Done

When this plan is complete:

1. `grep -r '\.claude/collab' . --include='*.md' --include='*.sh' --include='*.json' --include='*.py'` returns zero matches (excluding archived docs in `docs/v1-full-architecture/` and working drafts in `docs/arch-v2-*`)
2. `./e2e/run-e2e.sh` passes all 11 scenarios with data files under `.avt/`
3. `cd mcp-servers/knowledge-graph && uv run pytest` — all tests pass
4. `cd mcp-servers/quality && uv run pytest` — all tests pass (including new gate tests)
5. `cd extension && npm test` — all tests pass
6. Quality server `check_all_gates()` returns real results for all 5 gates (build, lint, tests, coverage, findings)
7. A mechanism exists for compiling and injecting project rules into agent prompts
8. Templates in `templates/` match the current architecture (3 servers, `.avt/` paths)
9. ARCHITECTURE.md command count matches actual implementation
