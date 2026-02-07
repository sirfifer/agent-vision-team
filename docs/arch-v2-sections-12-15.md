## 12. Data Flow Architecture

This section traces end-to-end data paths through the system for key workflows. Each flow is grounded in actual code paths across the three MCP servers, the agent definitions, and the E2E harness.

---

### 12.1 Task Execution Flow

The governed task lifecycle is the core execution primitive. Every implementation task is "blocked from birth" -- it cannot execute until all governance reviews approve it.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Orchestrator                                                            │
│  calls: create_governed_task(subject, description, context, review_type) │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Governance Server (server.py → create_governed_task tool)               │
│                                                                          │
│  1. GovernanceStore.record_governed_task(task_id, review_type, context)  │
│     → INSERT into governed_tasks table (SQLite)                          │
│                                                                          │
│  2. TaskFileManager.create_governed_task_pair(subject, description, ...) │
│     → Acquires fcntl.LOCK_EX on .task-lock file                         │
│     → Writes review task JSON: {id: "review-{uuid}", status: "pending"} │
│     → Writes impl task JSON:   {id: "impl-{uuid}",                      │
│     │                            status: "blocked",                      │
│     │                            blockedBy: ["review-{uuid}"]}           │
│     → Releases lock                                                      │
│                                                                          │
│  3. GovernanceStore.record_task_review(review_id, impl_id, review_type) │
│     → INSERT into task_reviews table                                     │
│                                                                          │
│  Returns: {review_task_id, implementation_task_id}                       │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
┌──────────────────┐             ┌──────────────────────┐
│ review-{uuid}    │   blocks    │ impl-{uuid}          │
│ status: pending  │────────────▶│ status: blocked      │
│ type: governance │             │ blockedBy:           │
└────────┬─────────┘             │  ["review-{uuid}"]   │
         │                       │ CANNOT EXECUTE       │
         ▼                       └──────────────────────┘
┌──────────────────────────────────────────────────────┐
│  Governance Reviewer (manual or automated)            │
│                                                       │
│  complete_task_review(review_task_id, verdict, ...)   │
│                                                       │
│  1. GovernanceStore.complete_task_review(...)          │
│     → UPDATE task_reviews SET status, verdict         │
│                                                       │
│  2. If verdict == "approved" AND no other blockers:   │
│     TaskFileManager.release_task(impl_task_id)        │
│     → Acquires fcntl.LOCK_EX                          │
│     → Removes review from blockedBy array             │
│     → If blockedBy empty: status → "pending"          │
│     → Releases lock                                   │
│                                                       │
│  3. If verdict == "blocked":                          │
│     Task stays blocked; guidance returned to caller   │
└──────────────────────────────────────────────────────┘
                           │
                           ▼ (on approval, all blockers cleared)
┌──────────────────────────────────────────────────────┐
│ impl-{uuid}                                           │
│ status: pending  (now available for worker pickup)    │
│ blockedBy: []                                         │
│ CAN EXECUTE                                          │
└──────────────────────────────────────────────────────┘
```

**Key code paths:**
- `server.py`: `create_governed_task` tool handler orchestrates store + file manager
- `task_integration.py`: `TaskFileManager.create_governed_task_pair()` uses `fcntl.LOCK_EX` for atomicity
- `task_integration.py`: `TaskFileManager.release_task()` conditionally unblocks
- `store.py`: `GovernanceStore` persists to SQLite tables `governed_tasks` and `task_reviews`

---

### 12.2 Memory Flow

The Knowledge Graph serves as institutional memory. Data flows through JSONL persistence with in-memory indexing for reads.

```
┌──────────────┐     create_entities()     ┌─────────────────────────────┐
│  Any Agent   │──────────────────────────▶│  KnowledgeGraph (graph.py)  │
│  (via MCP)   │     add_observations()    │                             │
│              │──────────────────────────▶│  1. validate_write_access() │
│              │     search_nodes()        │     (tier_protection.py)    │
│              │──────────────────────────▶│                             │
│              │     get_entity()          │  2. Update in-memory dict   │
│              │──────────────────────────▶│     entities: dict[str, E]  │
│              │     get_entities_by_tier()│                             │
│              │──────────────────────────▶│  3. Append to JSONL         │
└──────────────┘                           │     (storage.py)            │
                                           └──────────────┬──────────────┘
                                                          │
                                                          ▼
                                           ┌─────────────────────────────┐
                                           │  JSONLStorage (storage.py)  │
                                           │                             │
                                           │  append_entity(entity)      │
                                           │  → Append one JSON line     │
                                           │  → Increment write_count    │
                                           │                             │
                                           │  If write_count >= 1000:    │
                                           │    compact()                │
                                           │    → Write all entities to  │
                                           │      temp file              │
                                           │    → Atomic rename over     │
                                           │      original               │
                                           │    → Reset write_count      │
                                           │                             │
                                           │  File: knowledge-graph.jsonl│
                                           │  Path: .claude/collab/      │
                                           └─────────────────────────────┘

Tier Protection Check (on every write):

  ┌─────────────────────────────────────────────────────────────────────┐
  │  validate_write_access(entity, caller_role, change_approved)       │
  │                                                                     │
  │  tier = get_entity_tier(entity)                                    │
  │    → Scans observations for "protection_tier: <tier>"              │
  │    → Falls back to entityType mapping                              │
  │                                                                     │
  │  Vision tier:                                                       │
  │    → REJECT all agent writes (only human can modify)               │
  │    → Raises TierProtectionError                                    │
  │                                                                     │
  │  Architecture tier:                                                 │
  │    → REJECT unless change_approved=True                            │
  │    → Raises TierProtectionError if not approved                    │
  │                                                                     │
  │  Quality tier:                                                      │
  │    → ALLOW all writes                                              │
  └─────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `graph.py`: `KnowledgeGraph` class -- in-memory dict with JSONL backing store
- `storage.py`: `JSONLStorage.compact()` -- temp file + atomic rename after 1000 writes
- `tier_protection.py`: `validate_write_access()` -- enforces tier hierarchy
- `tier_protection.py`: `get_entity_tier()` -- extracts tier from `"protection_tier: "` observations or entityType fallback

---

### 12.3 Vision Conflict Flow

When a worker's action conflicts with a vision-tier standard, the system blocks execution at the earliest possible point.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Worker Agent                                                           │
│  calls: submit_decision(category="pattern_choice", summary="Use X")    │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Governance Server (server.py → submit_decision tool)                   │
│                                                                         │
│  1. Store decision in SQLite                                            │
│     GovernanceStore.record_decision(Decision(...))                      │
│                                                                         │
│  2. Auto-flag check (server.py):                                        │
│     if category in (deviation, scope_change):                           │
│       → Skip AI review                                                  │
│       → Return verdict: needs_human_review                              │
│       → Guidance: "Deviation/scope change requires human approval"      │
│                                                                         │
│  3. Load vision standards from KG                                       │
│     KGClient.get_vision_standards()                                     │
│     → Reads knowledge-graph.jsonl directly                              │
│     → Filters for entityType == "vision_standard"                       │
│                                                                         │
│  4. Load architecture entities from KG                                  │
│     KGClient.get_architecture_entities()                                │
│     → Filters for protection_tier == "architecture"                     │
│                                                                         │
│  5. AI Review via GovernanceReviewer.review_decision()                  │
│     → Builds prompt with standards + architecture + decision details    │
│     → Runs claude --print (temp file I/O pattern)                       │
│     → Parses JSON verdict from response                                 │
│                                                                         │
│  6. Store verdict in SQLite                                             │
│     GovernanceStore.record_review(ReviewVerdict(...))                   │
│                                                                         │
│  7. Record decision in KG for institutional memory                      │
│     KGClient.record_decision(decision, verdict)                        │
│     → Creates entity in knowledge-graph.jsonl                           │
│                                                                         │
│  Returns: ReviewVerdict {verdict, findings, guidance, standards_verified}│
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
         "approved"   "blocked"    "needs_human_review"
              │            │                │
              ▼            ▼                ▼
         Worker        Worker MUST      Worker includes
         proceeds      revise and       context when
         with impl     resubmit         presenting to
                                        human
```

**Key code paths:**
- `server.py`: `submit_decision` tool -- category auto-flag logic at top of handler
- `kg_client.py`: `KGClient.get_vision_standards()` -- reads JSONL, filters by entityType
- `reviewer.py`: `GovernanceReviewer.review_decision()` -> `_build_decision_prompt()` -> `_run_claude()`
- `reviewer.py`: `_run_claude()` -- temp file I/O with `tempfile.mkstemp()`, `GOVERNANCE_MOCK_REVIEW` bypass
- `reviewer.py`: `_parse_verdict()` -> `_extract_json()` -- handles raw JSON, ```json blocks, and brace extraction

---

### 12.4 Governance Decision Flow

This flow details the internal mechanics of a single governance review, from prompt construction through AI evaluation to verdict storage.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  GovernanceReviewer._run_claude(prompt, timeout)                        │
│  (reviewer.py)                                                           │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Check: GOVERNANCE_MOCK_REVIEW env var set?                      │    │
│  │   YES → Return deterministic JSON:                              │    │
│  │         {"verdict":"approved","findings":[],"guidance":"Mock..."}│    │
│  │   NO  → Continue to claude invocation                           │    │
│  └─────────────────────┬───────────────────────────────────────────┘    │
│                        │                                                 │
│                        ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Temp File I/O Pattern:                                          │    │
│  │                                                                  │    │
│  │ input_fd, input_path = tempfile.mkstemp(                        │    │
│  │     prefix="avt-gov-", suffix="-input.md")                      │    │
│  │ output_fd, output_path = tempfile.mkstemp(                      │    │
│  │     prefix="avt-gov-", suffix="-output.md")                     │    │
│  │                                                                  │    │
│  │ Write prompt → input_path                                       │    │
│  │ Close output_fd (so subprocess can write)                       │    │
│  │                                                                  │    │
│  │ subprocess.run(                                                  │    │
│  │     ["claude", "--print"],                                      │    │
│  │     stdin=open(input_path),                                     │    │
│  │     stdout=open(output_path, "w"),                              │    │
│  │     stderr=subprocess.PIPE,                                     │    │
│  │     timeout=timeout                                             │    │
│  │ )                                                                │    │
│  │                                                                  │    │
│  │ Read response ← output_path                                    │    │
│  │ Clean up both temp files in finally block                       │    │
│  └─────────────────────┬───────────────────────────────────────────┘    │
│                        │                                                 │
│                        ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Error Handling:                                                  │    │
│  │   returncode != 0  → verdict: needs_human_review                │    │
│  │   TimeoutExpired   → verdict: needs_human_review                │    │
│  │   FileNotFoundError→ verdict: needs_human_review                │    │
│  │                      ("claude CLI not found")                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  _parse_verdict(raw_response)                                            │
│                                                                          │
│  1. _extract_json(raw):                                                  │
│     a. If starts with "{" → return whole string                          │
│     b. Regex for ```json ... ``` blocks → return match                   │
│     c. Find first "{" to last "}" → return substring                     │
│     d. None → fallback                                                   │
│                                                                          │
│  2. Parse JSON → build ReviewVerdict:                                    │
│     - verdict: Verdict enum (approved | blocked | needs_human_review)    │
│     - findings: list[Finding] (tier, severity, description, suggestion)  │
│     - guidance: str                                                      │
│     - standards_verified: list[str]                                      │
│                                                                          │
│  3. Fallback (unparseable):                                              │
│     → verdict: needs_human_review                                        │
│     → guidance: "Could not parse... Raw response: {first 1000 chars}"   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `reviewer.py`: `_run_claude()` -- lines 64-150, complete temp file lifecycle
- `reviewer.py`: `_extract_json()` -- lines 200-220, three-stage JSON extraction
- `reviewer.py`: `_parse_verdict()` -- lines 152-198, JSON to ReviewVerdict conversion
- `models.py`: `Verdict` enum -- `approved`, `blocked`, `needs_human_review`
- `models.py`: `Finding` -- `tier`, `severity`, `description`, `suggestion`

---

### 12.5 Research Flow

The researcher subagent gathers intelligence to inform development decisions. It operates in two modes: periodic maintenance and exploratory design research.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Orchestrator                                                            │
│  Spawns researcher subagent via Task tool                                │
│  prompt: "Execute research prompt in .avt/research-prompts/rp-xxx.md"   │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Researcher Agent (.claude/agents/researcher.md)                         │
│  Model: opus (novel domains) or sonnet (changelog monitoring)            │
│  Tools: Read, Glob, Grep, WebSearch, WebFetch, collab-kg, collab-gov    │
│                                                                          │
│  Startup:                                                                │
│  1. Read research prompt from .avt/research-prompts/rp-xxx.md           │
│  2. Query KG: search_nodes("<topic>") for existing knowledge            │
│  3. Query KG: get_entities_by_tier("vision") for constraints            │
│                                                                          │
│  Execution (mode-dependent):                                             │
│                                                                          │
│  ┌─────────────────────────┐    ┌─────────────────────────────────┐     │
│  │ Periodic/Maintenance    │    │ Exploratory/Design              │     │
│  │                         │    │                                  │     │
│  │ - Monitor APIs/deps     │    │ - Deep investigation            │     │
│  │ - Detect breaking chgs  │    │ - Compare alternatives          │     │
│  │ - Track deprecations    │    │ - Evaluate technologies         │     │
│  │ - Security advisories   │    │ - Architecture research         │     │
│  │                         │    │                                  │     │
│  │ Output: Change Report   │    │ Output: Research Brief          │     │
│  │ Model: sonnet preferred │    │ Model: opus preferred           │     │
│  └─────────────┬───────────┘    └────────────────┬────────────────┘     │
│                │                                  │                      │
│                └──────────┬───────────────────────┘                      │
│                           ▼                                              │
│  Write output to .avt/research-briefs/rb-xxx.md                         │
│  Record key findings in KG via create_entities / add_observations       │
│                                                                          │
│  Governance integration:                                                 │
│  - Submit architectural recommendations as decisions                     │
│  - Vision-impacting findings flagged for human review                    │
└──────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Consumers                                                               │
│                                                                          │
│  - Orchestrator references briefs in task briefs for workers             │
│  - Workers read .avt/research-briefs/ for implementation context         │
│  - KG retains findings as searchable institutional memory                │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `.claude/agents/researcher.md`: Agent definition with dual-mode operation
- Research prompts stored in `.avt/research-prompts/rp-xxx.md`
- Research briefs output to `.avt/research-briefs/rb-xxx.md`
- KG integration via `collab-kg` MCP tools for persistent memory

---

### 12.6 Project Hygiene Flow

The project-steward subagent maintains project organization, naming conventions, and completeness.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Orchestrator                                                            │
│  Spawns project-steward subagent via Task tool                           │
│  prompt: "Perform a full project hygiene review"                         │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Project Steward (.claude/agents/project-steward.md)                     │
│  Model: sonnet                                                           │
│  Tools: Read, Write, Edit, Bash, Glob, Grep, collab-kg, collab-quality  │
│                                                                          │
│  Review Areas:                                                           │
│  ┌───────────────────────┬───────────────────────────────────────────┐  │
│  │ Area                  │ What Is Checked                           │  │
│  ├───────────────────────┼───────────────────────────────────────────┤  │
│  │ Project Files         │ LICENSE, README, CONTRIBUTING, CHANGELOG, │  │
│  │                       │ CODE_OF_CONDUCT, SECURITY                 │  │
│  │ Naming Conventions    │ File/dir/variable/type casing consistency │  │
│  │ Folder Organization   │ Logical grouping, depth, orphaned files   │  │
│  │ Documentation         │ README sections, API docs, config docs    │  │
│  │ Cruft Detection       │ Unused files, duplicates, outdated config │  │
│  │ Consistency           │ Indentation, line endings, encoding,      │  │
│  │                       │ import ordering                           │  │
│  └───────────────────────┴───────────────────────────────────────────┘  │
│                                                                          │
│  Schedule:                                                               │
│  - Weekly: cruft detection                                               │
│  - Monthly: naming convention audits                                     │
│  - Quarterly: deep comprehensive reviews                                 │
│                                                                          │
│  Outputs:                                                                │
│  - Review reports (structured findings by priority)                      │
│  - KG entities (naming conventions, structure patterns)                  │
│  - Direct mechanical fixes (renaming, cruft removal)                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `.claude/agents/project-steward.md`: Agent definition with review areas and schedule
- Quality server integration via `collab-quality` MCP tools
- KG integration via `collab-kg` for recording conventions and patterns

---

## 13. E2E Testing Architecture

The project includes an autonomous end-to-end testing harness that exercises all three MCP servers across 14 scenarios with 292+ structural assertions. Every run generates a unique project from a pool of 8 domains, ensuring tests validate structural properties rather than domain-specific content.

---

### 13.1 Design Philosophy

The E2E harness is built on three principles:

1. **Structural assertions, not domain assertions.** "A governed task is blocked from birth" is true regardless of whether the domain is Pet Adoption or Fleet Management. All 292+ assertions check structural properties of the system.

2. **Unique project per run.** Each execution randomly selects a domain, fills templates with randomized components, and generates a fresh workspace. This prevents tests from passing due to hardcoded values.

3. **No live model dependency.** The `GOVERNANCE_MOCK_REVIEW` environment variable causes `GovernanceReviewer._run_claude()` to return a deterministic "approved" verdict without invoking the `claude` binary. Tests exercise the full governance pipeline except the AI reasoning step.

---

### 13.2 Unique Project Generation

The project generator creates a complete workspace from domain-specific templates.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  generate_project(workspace, seed=None)                                  │
│  (e2e/generator/project_generator.py)                                    │
│                                                                          │
│  1. rng = random.Random(seed)     <- Reproducible when seed provided    │
│                                                                          │
│  2. domain = _pick_domain(rng)    <- Random from 8 domain pool          │
│     (e2e/generator/domain_templates.py)                                  │
│                                                                          │
│  3. vision_standards = _materialise_vision_standards(domain, rng)        │
│     -> For each of 5 vision templates:                                   │
│       - Pick random component from domain.components                     │
│       - Fill {domain}, {prefix}, {component} placeholders                │
│       - Assign archetype label (protocol_di, no_singletons, etc.)       │
│                                                                          │
│  4. architecture_patterns = _materialise_architecture_patterns(...)      │
│     -> For each of 2-3 architecture templates:                           │
│       - Pick random component, fill placeholders                         │
│       - Assign pattern label (service_registry, communication, etc.)     │
│                                                                          │
│  5. Write directory structure:                                           │
│     .avt/{task-briefs, memory, research-prompts, research-briefs}       │
│     docs/{vision, architecture}                                          │
│     .claude/{collab, agents}                                             │
│                                                                          │
│  6. Write knowledge-graph.jsonl (seeded with vision + arch entities)     │
│  7. Write .avt/project-config.json                                       │
│  8. Write .avt/session-state.md                                          │
│  9. Write memory stubs (4 archival .md files)                            │
│  10. Create governance.db placeholder                                    │
│                                                                          │
│  Returns: GeneratedProject dataclass                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Domain Pool (8 domains):**

| Domain | Prefix | Components |
|--------|--------|------------|
| Pet Adoption Platform | pet | AdoptionService, ShelterRegistry, PetProfileManager |
| Restaurant Reservation System | resto | ReservationEngine, TableManager, WaitlistService |
| Fitness Tracking App | fit | WorkoutTracker, NutritionEngine, GoalManager |
| Online Learning Platform | learn | CourseEngine, EnrollmentService, ProgressTracker |
| Smart Home Controller | home | DeviceManager, AutomationEngine, EnergyMonitor |
| Inventory Management System | inv | StockTracker, OrderProcessor, SupplierGateway |
| Event Ticketing Platform | tix | EventCatalog, TicketEngine, VenueManager |
| Fleet Management System | fleet | VehicleTracker, RouteOptimizer, MaintenanceScheduler |

Each domain provides:
- **3 components**: service/module names used in template filling
- **5 vision templates**: parameterized vision standards with `{domain}`, `{prefix}`, `{component}` placeholders
- **2-3 architecture templates**: parameterized architecture patterns

**Key code paths:**
- `project_generator.py`: `generate_project()` -- main entry point, lines 325-406
- `project_generator.py`: `_materialise_vision_standards()` -- template filling, lines 105-129
- `domain_templates.py`: `get_domain_pool()` -- returns all 8 `DomainTemplate` instances
- `domain_templates.py`: `DomainTemplate` dataclass -- `name`, `prefix`, `components`, `vision_templates`, `architecture_templates`

---

### 13.3 Scenario Inventory

All 14 scenarios inherit from `BaseScenario` (in `e2e/scenarios/base.py`) which provides assertion helpers and timing/error-handling wrappers.

| ID | Scenario | Assertions | What It Validates |
|----|----------|------------|-------------------|
| s01 | KG Tier Protection | 12 | CRUD at all three tiers. Vision entities immutable by worker-role agents. Architecture entities require `change_approved=True`. Quality entities freely writable. |
| s02 | Governance Decision Flow | ~15 | Decision storage in SQLite, AI review verdict flow, status queries, decision history filtering. |
| s03 | Governed Task Lifecycle | 27 | Task pair creation (`create_governed_task_pair`), blocking from birth (`blockedBy` array), release on approval, multi-blocker stacking, blocked verdict behavior. |
| s04 | Vision Violation | ~12 | Attempts to modify vision-tier entities are rejected with `TierProtectionError`. Workers cannot delete, add observations to, or modify vision standards. |
| s05 | Architecture Deviation | ~14 | `deviation` and `scope_change` decision categories are stored and auto-flagged as `needs_human_review` without AI review. |
| s06 | Quality Gates | ~10 | `GovernanceStore.get_status()` returns accurate aggregate counts. Gate configuration read from `.avt/project-config.json`. |
| s07 | Trust Engine | ~12 | Finding record -> dismiss (requires justification) -> audit trail lifecycle. `TrustDecision.BLOCK` for new findings, `TrustDecision.TRACK` for previously dismissed. |
| s08 | Multi-Blocker Task | 19 | 3 stacked review blockers on a single task. Blockers released one at a time. Task stays blocked until ALL are approved. |
| s09 | Scope Change Detection | ~10 | `scope_change` and `deviation` categories -> automatic `needs_human_review` verdict. No AI review invoked. |
| s10 | Completion Guard | ~15 | Unresolved review blocks prevent completion. Missing plan reviews are caught. `submit_completion_review` validates all decisions were reviewed. |
| s12 | Cross-Server Integration | 25 | KG + Governance + Task system interplay. Vision standards loaded from KG for governance review. Decisions recorded back to KG. Task lifecycle spans all three servers. |
| s13 | Hook Pipeline at Scale | ~24 | 50 rapid + 20 concurrent tasks with 100% hook interception rate. Validates governance enforcement under load. |
| s14 | Persistence Lifecycle | ~71 | Two-phase test: populates all 6 persistence stores via all data flow paths (ingestion, agent CRUD, governance decisions, trust engine, curation, archival sync, session state), then validates cleanup. |

**BaseScenario assertion helpers** (from `e2e/scenarios/base.py`):
- `assert_true(condition, message)` -- basic boolean assertion
- `assert_equal(actual, expected, message)` -- equality check
- `assert_contains(collection, item, message)` -- membership check
- `assert_error(callable, error_type, message)` -- expected exception
- `assert_no_error(callable, message)` -- no exception expected

**Key code paths:**
- `base.py`: `BaseScenario` -- `execute()` wrapper with timing, `ScenarioResult` dataclass
- Each scenario file: `e2e/scenarios/s{NN}_{name}.py` -- class inheriting `BaseScenario`
- `run-e2e.py`: Imports all 11 scenario classes and passes them to the executor

---

### 13.4 Execution Model

Scenarios run in parallel with full isolation. The `ParallelExecutor` provides each scenario with its own KG, governance store, and task directory.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  run-e2e.sh                                                              │
│                                                                          │
│  1. WORKSPACE=$(mktemp -d /tmp/avt-e2e-XXXXXX)                         │
│  2. export GOVERNANCE_MOCK_REVIEW=true                                   │
│  3. trap cleanup EXIT                                                    │
│  4. cd e2e/ && uv run python run-e2e.py --workspace $WORKSPACE          │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  run-e2e.py                                                              │
│                                                                          │
│  1. generate_project(workspace, seed=args.seed)                          │
│     -> Returns GeneratedProject with vision, architecture, paths         │
│                                                                          │
│  2. Instantiate all 11 scenario classes                                   │
│  3. executor = ParallelExecutor(scenarios, project, workspace)           │
│  4. results = executor.run_all()                                         │
│  5. generate_report(results, workspace / "e2e-report.json")             │
│  6. print_summary(results)                                               │
│  7. sys.exit(0 if all passed else 1)                                     │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  ParallelExecutor (e2e/parallel/executor.py)                             │
│                                                                          │
│  Route by isolation_mode:                                                │
│  - "library" scenarios -> ThreadPoolExecutor(max_workers=4)             │
│  - Other modes -> sequential execution                                   │
│                                                                          │
│  Per-scenario isolation setup:                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  scenario_dir = workspace / "scenarios" / scenario.id              │ │
│  │                                                                     │ │
│  │  KnowledgeGraph:                                                    │ │
│  │    kg_path = scenario_dir / "knowledge-graph.jsonl"                │ │
│  │    Pre-seeded with project's 5 vision + 2-3 arch entities          │ │
│  │                                                                     │ │
│  │  GovernanceStore:                                                   │ │
│  │    db_path = scenario_dir / "governance.db"                        │ │
│  │    Fresh SQLite database per scenario                               │ │
│  │                                                                     │ │
│  │  TaskFileManager:                                                   │ │
│  │    task_dir = scenario_dir / "tasks"                                │ │
│  │    Empty directory per scenario                                      │ │
│  │                                                                     │ │
│  │  Injected into scenario as constructor arguments                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  Results collected via futures, exceptions caught per-scenario           │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `run-e2e.sh`: Shell wrapper -- workspace creation, env vars, cleanup trap
- `run-e2e.py`: Python orchestrator -- project generation, scenario instantiation, execution, reporting
- `executor.py`: `ParallelExecutor` -- `ThreadPoolExecutor(max_workers=4)`, per-scenario isolation
- `executor.py`: Isolation setup -- KG JSONL copy, fresh SQLite, fresh task dir, pre-seeded entities

---

### 13.5 Assertion Engine

The assertion engine (`e2e/validation/assertion_engine.py`) provides domain-agnostic assertion helpers that return `(bool, str)` tuples for structured reporting.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  AssertionEngine                                                         │
│  (e2e/validation/assertion_engine.py)                                    │
│                                                                          │
│  Structural Assertions (all return (bool, str)):                         │
│                                                                          │
│  assert_tier_protected(entity, operation, caller_role)                  │
│    -> Verifies tier protection enforcement                               │
│                                                                          │
│  assert_verdict(review_verdict, expected_verdict)                       │
│    -> Checks governance verdict matches expected                         │
│                                                                          │
│  assert_task_blocked(task_status)                                       │
│    -> Confirms task has non-empty blockedBy array                        │
│                                                                          │
│  assert_task_released(task_status)                                      │
│    -> Confirms task has empty blockedBy and status "pending"             │
│                                                                          │
│  assert_has_findings(review_verdict, min_count)                         │
│    -> Checks findings list length >= min_count                           │
│                                                                          │
│  assert_finding_severity(finding, expected_severity)                    │
│    -> Verifies a specific finding has expected severity                  │
│                                                                          │
│  All assertions are domain-agnostic -- they check structure,             │
│  not content. "Task is blocked" is true for Pet Adoption                 │
│  and Fleet Management alike.                                             │
└──────────────────────────────────────────────────────────────────────────┘
```

**Report Generation** (`e2e/validation/report_generator.py`):

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ReportGenerator                                                         │
│                                                                          │
│  generate_report(results, output_path):                                  │
│    -> JSON report with per-scenario results                              │
│    -> Overall pass/fail summary                                          │
│    -> Timing data                                                        │
│                                                                          │
│  print_summary(results):                                                 │
│    -> ANSI-colored console output                                        │
│    -> Pass/fail counts                                                   │
│    -> Failure details with assertion messages                            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key code paths:**
- `assertion_engine.py`: `AssertionEngine` class -- all assertion methods
- `report_generator.py`: `ReportGenerator` -- JSON + console output
- `report_generator.py`: `generate_report()` and `print_summary()` convenience functions

---

### 13.6 When to Run

| Trigger | Reason |
|---------|--------|
| After modifying any MCP server code | Catches contract drift between servers |
| Before significant releases | Confirms all three servers work together |
| After governance or task system changes | s03, s08, s10 specifically test governed task flow |
| After KG tier protection changes | s01, s04 test tier enforcement |
| After trust engine changes | s07 tests the full finding lifecycle |
| Periodically (CI or manual) | Random domain selection means each run is a uniqueness test |

**Running the harness:**

```bash
./e2e/run-e2e.sh              # Standard run (workspace auto-cleaned)
./e2e/run-e2e.sh --keep       # Preserve workspace for debugging
./e2e/run-e2e.sh --seed 42    # Reproducible project generation
./e2e/run-e2e.sh --verbose    # Enable debug logging
```

**Interpreting failures:** If a scenario fails, the problem is in the server code, not the test. Scenarios call actual Python library APIs directly. The E2E report includes per-assertion pass/fail with descriptive messages to trace the failure to a specific code path.

---

## 14. Research System

The research system provides structured intelligence gathering through the researcher subagent, operating in two distinct modes with governance integration.

---

### 14.1 Dual-Mode Operation

The researcher subagent (`.claude/agents/researcher.md`) operates in two modes, each with different characteristics:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Research System                                   │
│                                                                          │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────┐ │
│  │  Periodic / Maintenance     │    │  Exploratory / Design           │ │
│  │                             │    │                                  │ │
│  │  Purpose:                   │    │  Purpose:                       │ │
│  │  Track external changes     │    │  Inform new development         │ │
│  │                             │    │                                  │ │
│  │  Activities:                │    │  Activities:                    │ │
│  │  - Monitor API changes      │    │  - Evaluate technologies        │ │
│  │  - Detect breaking changes  │    │  - Compare alternatives         │ │
│  │  - Track deprecations       │    │  - Research unfamiliar domains  │ │
│  │  - Security advisories      │    │  - Architecture investigation   │ │
│  │                             │    │                                  │ │
│  │  Model: sonnet (preferred)  │    │  Model: opus (preferred)        │ │
│  │  Output: Change Report      │    │  Output: Research Brief         │ │
│  │                             │    │                                  │ │
│  │  Schedule: configurable     │    │  Trigger: on-demand by          │ │
│  │  (weekly, monthly, etc.)    │    │  orchestrator                   │ │
│  └─────────────────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

**Model selection criteria:**

| Criterion | Use Opus 4.6 | Use Sonnet 4.5 |
|-----------|--------------|----------------|
| Novel or unfamiliar domain | Yes | |
| Architectural decision research | Yes | |
| Security analysis | Yes | |
| Ambiguous requirements | Yes | |
| Changelog monitoring | | Yes |
| Version update tracking | | Yes |
| Straightforward API documentation | | Yes |
| Known domain, factual lookup | | Yes |

---

### 14.2 Research Workflow

```
┌──────────────────────────────────────────────────────────────────────────┐
│  1. Create Research Prompt                                               │
│     Location: .avt/research-prompts/rp-{id}.md                          │
│     Created by: Orchestrator (via dashboard or manually)                 │
│                                                                          │
│     Content:                                                             │
│     - type: periodic | exploratory                                       │
│     - topic: what to research                                            │
│     - context: why this research matters                                 │
│     - scope: boundaries of the investigation                             │
│     - model_hint: opus | sonnet | auto                                   │
│     - output: change_report | research_brief                             │
│     - schedule: (for periodic only) type, frequency, time                │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  2. Spawn Researcher                                                     │
│     Orchestrator uses Task tool with subagent_type: researcher           │
│     prompt: "Execute research prompt in .avt/research-prompts/rp-xxx.md"│
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  3. Researcher Execution                                                 │
│                                                                          │
│  a. Read research prompt                                                 │
│  b. Query KG for existing knowledge on topic                             │
│     -> search_nodes("<topic>")                                           │
│     -> get_entities_by_tier("vision") for constraints                    │
│  c. Gather intelligence using available tools                            │
│     -> WebSearch for current information                                 │
│     -> WebFetch for specific documentation                               │
│     -> Read for local files and configs                                  │
│  d. Analyze and synthesize findings                                      │
│  e. Record key findings in KG                                            │
│     -> create_entities() for new knowledge                               │
│     -> add_observations() for updates to existing entities               │
│  f. Submit architectural recommendations as governance decisions          │
│     -> submit_decision() for vision-impacting findings                   │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  4. Output                                                               │
│     Location: .avt/research-briefs/rb-{id}.md                           │
│                                                                          │
│     Change Report (periodic):                                            │
│     - Structured list of detected changes                                │
│     - Impact assessment per change                                       │
│     - Actionable items for the team                                      │
│                                                                          │
│     Research Brief (exploratory):                                        │
│     - Comprehensive analysis                                             │
│     - Technology comparison matrix                                       │
│     - Recommendations with tradeoffs                                     │
│     - References and sources                                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 14.3 Governance Integration

The researcher integrates with the governance system when findings have architectural or vision implications:

- **Architectural recommendations** are submitted as `pattern_choice` or `component_design` decisions via `submit_decision()`, following the standard governance review flow.
- **Vision-impacting discoveries** (e.g., a dependency deprecation that forces a pattern change) are flagged with category `deviation` or `scope_change`, which auto-triggers `needs_human_review`.
- **KG updates** use the standard tier protection: the researcher can write quality-tier entities freely but cannot modify vision or architecture tiers.

---

### 14.4 Research Prompt Registry

Research prompts are managed in two locations:

1. **Individual prompt files**: `.avt/research-prompts/rp-{id}.md` -- full prompt definition with metadata
2. **Registry index**: `.avt/research-prompts.json` -- index of all prompts for dashboard display and scheduling

The registry tracks:
- Prompt ID and title
- Research type (periodic or exploratory)
- Schedule configuration (for periodic prompts)
- Last execution timestamp
- Associated research brief IDs

---

### 14.5 Consumer Integration

Research outputs feed into the broader system:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Research Brief (.avt/research-briefs/rb-xxx.md)                         │
│                                                                          │
│  Consumed by:                                                            │
│                                                                          │
│  ┌─────────────────┐  References briefs in task briefs                  │
│  │  Orchestrator    │────────────────────────────────────▶ Task Briefs   │
│  └─────────────────┘                                                     │
│                                                                          │
│  ┌─────────────────┐  Reads briefs for implementation context           │
│  │  Workers         │────────────────────────────────────▶ Code          │
│  └─────────────────┘                                                     │
│                                                                          │
│  ┌─────────────────┐  KG entities from research are searchable          │
│  │  Any Agent       │────────────────────────────────────▶ KG Search     │
│  └─────────────────┘                                                     │
│                                                                          │
│  ┌─────────────────┐  Reviews findings for governance impact            │
│  │  Gov Reviewer    │────────────────────────────────────▶ Verdicts      │
│  └─────────────────┘                                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Project Rules System

Project rules are concise behavioral guidelines that complement vision standards and architectural patterns. They cover behavioral guidance that tier-protected entities and quality gates cannot check.

---

### 15.1 Rule Structure

Rules live in `.avt/project-config.json` and are distinct from vision standards (KG tier-protected) and quality gates (deterministic checks).

```
┌─────────────────────────────────────────────────────────────────────────┐
│  .avt/project-config.json                                               │
│                                                                          │
│  {                                                                       │
│    "settings": {                                                         │
│      "autoGovernance": true,                <- governance integration    │
│      "qualityGates": { ... },              <- gate configuration         │
│      "kgAutoCuration": true                <- KG librarian trigger       │
│    },                                                                    │
│    "quality": {                                                          │
│      "testCommands": { ... },              <- per-language commands      │
│      "lintCommands": { ... },                                            │
│      "buildCommands": { ... },                                           │
│      "formatCommands": { ... }                                           │
│    },                                                                    │
│    "permissions": []                        <- rule definitions          │
│  }                                                                       │
│                                                                          │
│  Rule levels:                                                            │
│  - ENFORCE: Non-negotiable. Agent must comply.                           │
│  - PREFER:  Should follow unless specific reason documented.             │
│                                                                          │
│  Rule scopes:                                                            │
│  - Per-agent-type filtering (worker, researcher, steward, etc.)          │
│  - Only relevant rules are injected into each agent's context            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 15.2 Rule Injection Protocol

When the orchestrator spawns a subagent, it compiles applicable rules into a compact preamble prepended to the task prompt:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Orchestrator spawns agent                                               │
│                                                                          │
│  1. Read .avt/project-config.json                                        │
│  2. Filter rules by:                                                     │
│     a. Agent scope (worker, researcher, steward, etc.)                   │
│     b. Enabled status                                                    │
│  3. Compile into preamble (~200-400 tokens):                             │
│                                                                          │
│     ## Project Rules                                                     │
│     These rules govern how work is done in this project. Follow them.    │
│                                                                          │
│     ENFORCE:                                                             │
│     - [enabled enforce-level rules, filtered by agent scope]             │
│                                                                          │
│     PREFER (explain if deviating):                                       │
│     - [enabled prefer-level rules, filtered by agent scope]              │
│                                                                          │
│     ---                                                                  │
│                                                                          │
│  4. Prepend preamble to actual task prompt                               │
│  5. Spawn agent with combined prompt                                     │
│                                                                          │
│  Design constraints:                                                     │
│  - Preamble target: 200-400 tokens                                       │
│  - Rationale is NOT injected (lives in KG for deep context lookup)      │
│  - More rules = reduced agent effectiveness                              │
└──────────────────────────────────────────────────────────────────────────┘
```

**Worker agent compliance** (from `.claude/agents/worker.md`):

The worker startup protocol explicitly includes:
> "Check project rules injected at the top of your task context (under '## Project Rules'). Rules marked ENFORCE are non-negotiable. Rules marked PREFER should be followed unless you document a specific reason to deviate."

---

### 15.3 Relationship to Other Systems

Project rules complement but do not replace the other governance mechanisms:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Governance Layer Stack                                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Vision Standards (KG tier: vision, human-only modification)     │   │
│  │  "All services use protocol-based DI"                            │   │
│  │  -> Enforced by: tier protection + governance review AI          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Architecture Patterns (KG tier: architecture, approved changes) │   │
│  │  "ServiceRegistry pattern for service discovery"                 │   │
│  │  -> Enforced by: tier protection + governance decision review    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Project Rules (.avt/project-config.json, injected into prompts)│   │
│  │  "ENFORCE: Always run tests before committing"                   │   │
│  │  -> Enforced by: agent compliance (prompt-level instruction)    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Quality Gates (deterministic, automated checks)                 │   │
│  │  build: pass, lint: pass, tests: pass, coverage: >= 80%         │   │
│  │  -> Enforced by: Quality MCP server check_all_gates()           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Each layer covers a different enforcement mechanism:                    │
│  - Vision/Architecture: KG tier protection (prevents writes)            │
│  - Project Rules: Prompt injection (guides agent behavior)              │
│  - Quality Gates: Deterministic tooling (blocks on failure)             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 15.4 KG Integration for Rule Rationale

Rule rationale is intentionally not injected into the agent prompt (to keep the preamble compact). Instead, rationale is stored in the KG:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Rule: "ENFORCE: No direct database queries outside repository classes" │
│                                                                          │
│  Prompt Injection (what agents see):                                     │
│  "No direct database queries outside repository classes"                │
│                                                                          │
│  KG Entity (for agents that need deeper context):                        │
│  {                                                                       │
│    "name": "rule_no_direct_db",                                         │
│    "entityType": "project_rule",                                        │
│    "observations": [                                                     │
│      "protection_tier: quality",                                        │
│      "level: enforce",                                                   │
│      "scope: worker",                                                    │
│      "rationale: Direct DB access in services creates tight coupling    │
│       and makes testing difficult. Repository pattern allows mocking    │
│       and query optimization in isolation.",                             │
│      "configured_by: human via setup wizard"                            │
│    ]                                                                     │
│  }                                                                       │
│                                                                          │
│  Agents can query: search_nodes("project rules") for full rationale    │
└──────────────────────────────────────────────────────────────────────────┘
```

This separation ensures:
- **Prompt compactness**: Agents get concise instructions without rationale bloat
- **Deep context available**: Agents that need to understand "why" can query the KG
- **Rationale is curated**: The KG librarian maintains and updates rationale alongside other institutional memory
