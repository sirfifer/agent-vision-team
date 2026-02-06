## 4. Knowledge Graph MCP Server (Port 3101)

**Purpose**: Persistent institutional memory with tier-aware protection. Stores entities (components, patterns, decisions, problems, vision standards), relations, and observations. All sessions and agents share the same graph. The KG is the system's single source of truth for what the project believes, what it has decided, and what it has learned.

**Transport**: SSE on port 3101 (FastMCP)

**Storage**: JSONL file at `.avt/knowledge-graph.jsonl`. Each line is a self-contained JSON record (entity or relation). The server loads the full file into memory on startup and appends new records on writes. Periodic compaction rewrites the file with only current state, discarding deleted entities and stale entries.

### 4.1 Tool Interface (11 tools)

```
create_entities(
  entities: list[dict]           # [{name, entityType, observations}]
                                 # entityType: "component" | "vision_standard" | "architectural_standard"
                                 #             | "pattern" | "problem" | "solution_pattern"
                                 # observations: include "protection_tier: <tier>" for tier-protected entities
) -> { created: int }

create_relations(
  relations: list[dict]          # [{from, to, relationType}]
                                 # relationType: "depends_on" | "follows_pattern" | "governed_by"
                                 #               | "fixed_by" | "exemplified_by" | "rejected_in_favor_of"
) -> { created: int }

add_observations(
  entity_name: str,
  observations: list[str],
  caller_role: str = "agent",    # "human" | "orchestrator" | "worker" | "agent" | "quality"
  change_approved: bool = False  # Required true for architecture-tier writes by non-humans
) -> { added: int }
  | { added: 0, error: str }
  # REJECTS if entity has protection_tier: vision and caller is not "human"
  # REJECTS if entity has protection_tier: architecture and change_approved is false
  #   and caller is not "human"

search_nodes(
  query: str                     # Substring match against entity names and observations
                                 # (case-insensitive)
) -> list[EntityWithRelations]

get_entity(
  name: str                      # Exact entity name
) -> EntityWithRelations
  | { error: "Entity '<name>' not found." }

get_entities_by_tier(
  tier: str                      # "vision" | "architecture" | "quality"
) -> list[EntityWithRelations]

delete_observations(
  entity_name: str,
  observations: list[str],       # Exact strings to remove
  caller_role: str = "agent",
  change_approved: bool = False
) -> { deleted: int }
  | { deleted: 0, error: str }
  # Same tier protection as add_observations

delete_entity(
  entity_name: str,
  caller_role: str = "agent"
) -> { deleted: bool }
  | { deleted: false, error: str }
  # REJECTS if entity has protection_tier: vision or architecture and caller is not "human"
  # Also removes all relations involving the deleted entity

delete_relations(
  relations: list[dict]          # [{from, to, relationType}] -- exact match required
) -> { deleted: int }

ingest_documents(
  folder: str,                   # Path to folder containing .md files
                                 # Defaults to "docs/vision/" or "docs/architecture/" based on tier
  tier: str                      # "vision" | "architecture"
) -> { ingested: int, entities: list[str], errors: list[str], skipped: list[str] }
  # Parses markdown files: extracts H1 title, Statement, Description, Rationale, Usage, Examples
  # Converts titles to snake_case entity names
  # Sets protection_tier observation automatically
  # Supports re-ingestion: deletes existing entities with same name before creating
  #   (uses caller_role="human")

validate_tier_access(
  entity_name: str,
  operation: str,                # "read" | "write" | "delete"
  caller_role: str               # "human" | "orchestrator" | "worker" | "agent"
) -> { allowed: bool, reason?: str }
  # Read operations always return allowed: true
  # Write/delete operations check tier protection via get_entity_tier + validate_write_access
```

### 4.2 Data Models

```python
class ProtectionTier(str, Enum):
    VISION = "vision"
    ARCHITECTURE = "architecture"
    QUALITY = "quality"

class Mutability(str, Enum):
    HUMAN_ONLY = "human_only"
    HUMAN_APPROVED_ONLY = "human_approved_only"
    AUTOMATED = "automated"

class EntityType(str, Enum):
    COMPONENT = "component"
    VISION_STANDARD = "vision_standard"
    ARCHITECTURAL_STANDARD = "architectural_standard"
    PATTERN = "pattern"
    PROBLEM = "problem"
    SOLUTION_PATTERN = "solution_pattern"

class Relation(BaseModel):
    from_entity: str              # Serialized as "from" in JSON (Field alias)
    to: str
    relation_type: str            # Serialized as "relationType" in JSON (Field alias)

class Entity(BaseModel):
    name: str
    entity_type: EntityType       # Serialized as "entityType" in JSON (Field alias)
    observations: list[str]

class EntityWithRelations(Entity):
    relations: list[Relation]     # All relations where this entity is "from" or "to"
```

### 4.3 Tier Protection Enforcement

The server enforces tier protection at the tool level, not by convention. A misbehaving subagent cannot accidentally corrupt vision-tier data.

Protection tier is determined by scanning the entity's observations for a `"protection_tier: <tier>"` string. If no such observation exists, the entity is unprotected and freely writable.

| Entity Tier | Read | Write (add/delete observations) | Delete Entity |
|-------------|------|--------------------------------|---------------|
| `vision` | All callers | Human only | Human only |
| `architecture` | All callers | Human, or agent with `change_approved: true` | Human only |
| `quality` | All callers | All callers | All callers |
| *(untiered)* | All callers | All callers | All callers |

### 4.4 JSONL Persistence Format

Each line in the JSONL file is one of two record types:

**Entity record**:
```json
{"type": "entity", "name": "hands_free_first_design", "entityType": "vision_standard", "observations": ["protection_tier: vision", "statement: Voice is PRIMARY interaction mode"]}
```

**Relation record**:
```json
{"type": "relation", "from": "KBOralSessionView", "to": "hands_free_first_design", "relationType": "governed_by"}
```

**Write strategy**: New entities and relations are appended. Mutations (add/delete observations, delete entity) trigger a full compaction: the entire in-memory graph is rewritten to a `.jsonl.tmp` file and atomically renamed over the original. Compaction also runs automatically after every 1,000 append operations.

**Startup**: The server reads every line, deserializes, and populates the in-memory `dict[str, Entity]` and `list[Relation]`. Duplicate entity names are resolved by last-write-wins (later lines overwrite earlier ones during sequential loading).

### 4.5 Document Ingestion Pipeline

The `ingest_documents` tool enables bulk population of the KG from markdown files in `docs/vision/` and `docs/architecture/`. The ingestion module (`ingestion.py`) performs the following:

1. **Scan**: Find all `.md` files in the target folder (excluding `README.md`)
2. **Parse**: Extract H1 title, then extract named sections (`## Statement`, `## Description`, `## Rationale`, `## Usage`, `## Examples`) using regex
3. **Name**: Convert the H1 title to a `snake_case` entity name, stripping common prefixes like "Vision Standard:" or "Pattern:"
4. **Type**: Determine entity type from the `## Type` section content or keywords: vision tier always maps to `vision_standard`; architecture tier maps to `pattern`, `component`, or `architectural_standard` based on content
5. **Observations**: Build from extracted sections, prepended with `"protection_tier: <tier>"`, plus `"title: ..."` and `"source_file: ..."` metadata
6. **Re-ingestion**: If an entity with the same name already exists, delete it first (using `caller_role="human"` since ingestion is human-initiated)
7. **Create**: Batch-create all parsed entities via `graph.create_entities()`

### 4.6 Current Implementation Status

All 11 tools are implemented and operational:

- `graph.py`: Full entity/relation/observation CRUD with tier protection enforcement
- `tier_protection.py`: `get_entity_tier()` scans observations, `validate_write_access()` enforces the tier table
- `models.py`: Pydantic models with JSON field aliases for serialization compatibility
- `storage.py`: JSONL persistence with append, load, and atomic compaction
- `ingestion.py`: Markdown-to-entity parser with section extraction and re-ingestion support
- `server.py`: FastMCP server definition exposing all 11 tools on port 3101

**Note**: The storage path defaults to `.avt/knowledge-graph.jsonl` (updated from the original `.claude/collab/knowledge-graph.jsonl`). Search is substring-based (case-insensitive), not full-text or semantic.

---

## 5. Quality MCP Server (Port 3102)

**Purpose**: Wraps all quality tools (linters, formatters, test runners, coverage checkers) behind a unified MCP interface. Implements the Tool Trust Engine for finding management. Provides quality gate aggregation via `check_all_gates()` and a human-readable summary via `validate()`.

**Transport**: SSE on port 3102 (FastMCP)

**Storage**: SQLite at `.avt/trust-engine.db` for the Trust Engine (findings and dismissal history). Quality gate configuration is read from `.avt/project-config.json`.

### 5.1 Tool Interface (8 tools)

```
auto_format(
  files: list[str] | None = None,   # Specific file paths to format; returns error if omitted
  language: str | None = None        # "swift" | "python" | "rust" | "typescript" | "javascript"
                                     # Auto-detected from file extension if omitted
) -> { formatted: list[str], unchanged: list[str] }
  | { formatted: [], unchanged: [], error: str }

run_lint(
  files: list[str] | None = None,   # Specific file paths to lint
  language: str | None = None
) -> { findings: list[dict], auto_fixable: int, total: int }
  | { findings: [], auto_fixable: 0, total: 0, error: str }

run_tests(
  scope: str | None = None,         # "all" | specific test path; defaults to full suite
  language: str | None = None        # Defaults to "python" if omitted
) -> { passed: int, failed: int, skipped: int, failures: list[str] }

check_coverage(
  language: str | None = None        # Defaults to "python" if omitted
) -> { percentage: float, target: float, met: bool, uncovered_files: list[str] }
  # Target threshold read from project-config.json (default: 80%)

check_all_gates() -> {
  build:    { name: "build",    passed: bool, detail: str },
  lint:     { name: "lint",     passed: bool, detail: str },
  tests:    { name: "tests",    passed: bool, detail: str },
  coverage: { name: "coverage", passed: bool, detail: str },
  findings: { name: "findings", passed: bool, detail: str },
  all_passed: bool
}
  # Each gate can be disabled via .avt/project-config.json -> settings.qualityGates
  # Disabled gates return passed: true with detail: "Skipped (disabled)"

validate() -> {
  gates: GateResults,                # Same structure as check_all_gates()
  summary: str,                      # "All quality gates passed." or "Failed gates: lint, tests"
  all_passed: bool
}

get_trust_decision(
  finding_id: str
) -> { decision: "BLOCK" | "INVESTIGATE" | "TRACK", rationale: str }
  # Default for unknown findings: BLOCK ("all tool findings presumed legitimate")
  # Previously dismissed findings: TRACK (with rationale from dismissal record)

record_dismissal(
  finding_id: str,
  justification: str,               # Required -- empty string is rejected (returns false)
  dismissed_by: str                  # Agent or human identifier
) -> { recorded: bool }
  # Updates finding status to "dismissed" in findings table
  # Appends to dismissal_history table for audit trail
```

### 5.2 Specialist Routing

The Quality Server routes to language-specific tools via subprocess:

| Language | Formatter | Linter | Test Runner | Coverage |
|----------|-----------|--------|-------------|----------|
| Swift | `swiftformat` | `swiftlint lint --reporter json` | `xcodebuild test` | *(not configured)* |
| Python | `ruff format` | `ruff check --output-format=json` | `pytest -v --tb=short` | `pytest --cov --cov-report=term` |
| Rust | `rustfmt` | `cargo clippy --message-format=json` | `cargo test` | *(not configured)* |
| TypeScript | `prettier --write` | `eslint --format=json` | `npm test` | `npm run coverage` |
| JavaScript | `prettier --write` | `eslint --format=json` | `npm test` | `npm run coverage` |

Language detection uses file extension mapping: `.swift`, `.py`, `.rs`, `.ts`/`.tsx`, `.js`/`.jsx`. Custom commands can be configured via `.avt/project-config.json` under `quality.testCommands`, `quality.lintCommands`, `quality.buildCommands`, and `quality.formatCommands`.

### 5.3 Tool Trust Engine

The trust engine manages the lifecycle of quality findings. It uses a "guilty until proven innocent" philosophy: all findings from deterministic tools are presumed legitimate (`BLOCK`) until explicitly dismissed with justification.

**Trust decision classifications**:

| Decision | Meaning | When Applied |
|----------|---------|-------------|
| `BLOCK` | Cannot proceed until resolved | Default for all new/unknown findings |
| `INVESTIGATE` | Needs human or orchestrator review | *(Reserved for future use)* |
| `TRACK` | Note it, do not block on it | Previously dismissed findings |

**SQLite schema** (`.avt/trust-engine.db`):

```sql
CREATE TABLE findings (
    id TEXT PRIMARY KEY,
    tool TEXT NOT NULL,
    severity TEXT NOT NULL,
    component TEXT,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'open',          -- 'open' | 'dismissed'
    dismissed_by TEXT,
    dismissal_justification TEXT,
    dismissed_at TEXT
);

CREATE TABLE dismissal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id TEXT NOT NULL REFERENCES findings(id),
    dismissed_by TEXT NOT NULL,
    justification TEXT NOT NULL,
    dismissed_at TEXT NOT NULL
);
```

**No silent dismissals**: Every call to `record_dismissal` requires a non-empty `justification` string and a `dismissed_by` identifier. The dismissal is recorded both in the `findings` table (updating status) and in the `dismissal_history` table (append-only audit trail). Future occurrences of the same finding are classified as `TRACK` rather than `BLOCK`.

### 5.4 Quality Gate Configuration

Gates can be individually enabled or disabled via `.avt/project-config.json`:

```json
{
  "settings": {
    "qualityGates": {
      "build": true,
      "lint": true,
      "tests": true,
      "coverage": true,
      "findings": true
    },
    "coverageThreshold": 80
  }
}
```

### 5.5 Current Implementation Status

All 8 tools are implemented and operational:

- `server.py`: FastMCP server exposing all tools on port 3102
- `tools/formatting.py`: Real subprocess calls to `swiftformat`, `ruff format`, `rustfmt`, `prettier`
- `tools/linting.py`: Real subprocess calls with JSON output parsing for `ruff`, `eslint`, `swiftlint`; cargo clippy support
- `tools/testing.py`: Real subprocess calls to `pytest`, `npm test`, `xcodebuild test`, `cargo test`; output parsing for pass/fail counts
- `tools/coverage.py`: Real subprocess calls to `pytest --cov`, `npm run coverage`; percentage extraction from output
- `gates.py`: Aggregates all gates, respects per-gate enable/disable from project config
- `trust_engine.py`: SQLite-backed finding management with `record_finding`, `record_dismissal`, `get_trust_decision`, `get_dismissal_history`, `get_all_findings`
- `config.py`: Project configuration loader with defaults, merging, and per-language command overrides

**Partial stubs**: The build gate in `check_all_gates()` always returns `passed: true` with `"Build check not yet implemented"`. The findings gate always returns `passed: true` with `"No critical findings"`. These are TODOs for connecting to actual build commands and the trust engine's finding store respectively. Tool subprocess calls are real but depend on the corresponding tools being installed in the environment (`ruff`, `prettier`, `eslint`, etc.).

---

## 6. Governance MCP Server (Port 3103)

**Purpose**: Transactional decision review, governed task lifecycle management, and AI-powered review against vision and architecture standards. The governance server ensures that every significant agent decision is reviewed before implementation, every task is blocked from birth until governance approves it, and every completed task passes a final compliance check.

**Transport**: SSE on port 3103 (FastMCP)

**Storage**: SQLite at `.avt/governance.db` for decisions, reviews, governed tasks, and task review records. Task files are stored in Claude Code's native task directory (`~/.claude/tasks/<CLAUDE_CODE_TASK_LIST_ID>/`).

### 6.1 Tool Interface (10 tools)

#### Decision Review Tools

```
submit_decision(
  task_id: str,                      # The task this decision belongs to
  agent: str,                        # Name of the calling agent (e.g. "worker-1")
  category: str,                     # "pattern_choice" | "component_design" | "api_design"
                                     # | "deviation" | "scope_change"
  summary: str,                      # Brief summary of the decision
  detail: str = "",                  # Detailed explanation
  components_affected: list[str] | None = None,
  alternatives_considered: list[dict] | None = None,  # [{option, reason_rejected}]
  confidence: str = "high"           # "high" | "medium" | "low"
) -> {
  verdict: str,                      # "approved" | "blocked" | "needs_human_review"
  decision_id: str,
  findings: list[Finding],
  guidance: str,
  standards_verified: list[str]
}
  # BLOCKS until review completes (synchronous round-trip)
  # "deviation" and "scope_change" categories auto-return "needs_human_review"
  #   without AI review

submit_plan_for_review(
  task_id: str,
  agent: str,
  plan_summary: str,                 # Brief summary of the plan
  plan_content: str,                 # Full plan content (markdown)
  components_affected: list[str] | None = None
) -> {
  verdict: str,
  review_id: str,
  findings: list[Finding],
  guidance: str,
  decisions_reviewed: int,           # Count of prior decisions checked
  standards_verified: list[str]
}

submit_completion_review(
  task_id: str,
  agent: str,
  summary_of_work: str,
  files_changed: list[str] | None = None
) -> {
  verdict: str,
  review_id: str,
  unreviewed_decisions: list[str],   # Decision IDs that were never reviewed
  findings: list[Finding],
  guidance: str
}
  # Automatically BLOCKS if:
  #   - Any decisions for this task were never reviewed
  #   - Any blocked decisions remain unresolved
  # Otherwise runs AI review for final compliance check
```

#### Decision History Tools

```
get_decision_history(
  task_id: str | None = None,        # Filter by task
  agent: str | None = None,          # Filter by agent
  verdict: str | None = None         # Filter by verdict
) -> {
  decisions: list[{id, task_id, sequence, agent, category, summary,
                    confidence, verdict, guidance, created_at}]
}

get_governance_status() -> {
  total_decisions: int,
  approved: int,
  blocked: int,
  needs_human_review: int,
  pending: int,
  recent_activity: list[{summary, agent, category, verdict}],
  task_governance: {
    total_governed_tasks: int,
    pending_review: int,
    approved: int,
    blocked: int,
    pending_reviews: int
  }
}
```

#### Task Governance Tools

```
create_governed_task(
  subject: str,                      # The implementation task subject
  description: str,                  # Detailed description
  context: str,                      # Context for the governance review
  review_type: str = "governance"    # "governance" | "security" | "architecture"
                                     # | "memory" | "vision" | "custom"
) -> {
  implementation_task_id: str,       # The task that will do the work (prefixed "impl-")
  review_task_id: str,               # The review task blocking it (prefixed "review-")
  review_record_id: str,             # Internal governance record ID
  status: "pending_review",
  message: str
}
  # Atomically creates TWO Claude Code task files:
  #   1. Review task (created first): blocks the implementation task
  #   2. Implementation task (created second): blockedBy the review task
  # The implementation task CANNOT be picked up until the review completes

add_review_blocker(
  implementation_task_id: str,       # The implementation task to add a blocker to
  review_type: str,                  # "security" | "architecture" | "memory" | "vision" | "custom"
  context: str
) -> {
  review_task_id: str,
  review_record_id: str,
  status: "pending_review",
  message: str
}
  | { error: str, status: "failed" }
  # Adds an additional review blocker: task now has N blockers, ALL must complete

complete_task_review(
  review_task_id: str,               # The review task ID (from create_governed_task)
  verdict: str,                      # "approved" | "blocked" | "needs_human_review"
  guidance: str = "",
  findings: list[dict] | None = None,      # [{tier, severity, description, suggestion}]
  standards_verified: list[str] | None = None
) -> {
  verdict: str,
  implementation_task_id: str,
  task_released: bool,               # True only if ALL blockers are resolved
  remaining_blockers: int,
  message: str
}
  # If verdict is "approved", removes this review from blockedBy list
  # If verdict is "blocked", keeps the blocker and adds guidance to task description
  # Task is only released when blockedBy list is empty

get_task_review_status(
  implementation_task_id: str
) -> {
  task_id: str,
  subject: str,
  status: str,                       # "pending_review" | "approved" | "blocked"
  is_blocked: bool,
  can_execute: bool,
  reviews: list[{id, review_task_id, type, status, verdict, guidance,
                  created_at, completed_at}],
  blockers_from_files: list[{id, subject, status, review_type}],
  message: str
}

get_pending_reviews() -> {
  pending_reviews: list[{id, review_task_id, implementation_task_id,
                          type, context, created_at}],
  count: int
}
```

### 6.2 Decision Categories

| Category | When Used | Auto-Verdict |
|----------|-----------|-------------|
| `pattern_choice` | Choosing an implementation pattern | AI-reviewed |
| `component_design` | Designing a component's interface | AI-reviewed |
| `api_design` | Designing an API surface | AI-reviewed |
| `deviation` | Deviating from established patterns | `needs_human_review` (automatic) |
| `scope_change` | Working outside task brief scope | `needs_human_review` (automatic) |

### 6.3 Verdicts

| Verdict | Meaning | Effect |
|---------|---------|--------|
| `approved` | Decision/plan aligns with standards | Agent proceeds; review blocker removed |
| `blocked` | Decision conflicts with standards | Agent must revise and resubmit; blocker remains |
| `needs_human_review` | Requires human judgment | Include review context when presenting to human; auto-assigned for `deviation` and `scope_change` |

### 6.4 Data Models

```python
class DecisionCategory(str, Enum):
    PATTERN_CHOICE = "pattern_choice"
    COMPONENT_DESIGN = "component_design"
    API_DESIGN = "api_design"
    DEVIATION = "deviation"
    SCOPE_CHANGE = "scope_change"

class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Verdict(str, Enum):
    APPROVED = "approved"
    BLOCKED = "blocked"
    NEEDS_HUMAN_REVIEW = "needs_human_review"

class ReviewType(str, Enum):
    GOVERNANCE = "governance"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    MEMORY = "memory"
    VISION = "vision"
    CUSTOM = "custom"

class TaskReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    BLOCKED = "blocked"
    NEEDS_HUMAN_REVIEW = "needs_human_review"

class Alternative(BaseModel):
    option: str
    reason_rejected: str

class Decision(BaseModel):
    id: str                          # Auto-generated 12-char hex
    task_id: str
    sequence: int                    # Auto-incremented per task
    agent: str
    category: DecisionCategory
    summary: str
    detail: str
    components_affected: list[str]
    alternatives_considered: list[Alternative]
    confidence: Confidence
    created_at: str                  # ISO 8601 UTC

class Finding(BaseModel):
    tier: str                        # "vision" | "architecture" | "quality"
    severity: str                    # "vision_conflict" | "architectural" | "logic"
    description: str
    suggestion: str

class ReviewVerdict(BaseModel):
    id: str                          # Auto-generated 12-char hex
    decision_id: str | None          # Set for decision reviews
    plan_id: str | None              # Set for plan/completion reviews
    verdict: Verdict
    findings: list[Finding]
    guidance: str
    standards_verified: list[str]
    reviewer: str                    # Default: "governance-reviewer"
    created_at: str

class GovernedTaskRecord(BaseModel):
    id: str
    implementation_task_id: str      # Claude Code task file ID
    subject: str
    description: str
    context: str
    reviews: list[str]               # TaskReviewRecord IDs
    current_status: str              # "pending_review" | "approved" | "blocked"
    created_at: str
    released_at: str | None

class TaskReviewRecord(BaseModel):
    id: str
    review_task_id: str              # Claude Code task file ID for the review
    implementation_task_id: str      # Claude Code task file ID for the implementation
    review_type: ReviewType
    status: TaskReviewStatus
    context: str
    verdict: Verdict | None
    guidance: str
    findings: list[Finding]
    standards_verified: list[str]
    created_at: str
    completed_at: str | None
    reviewer: str                    # Default: "governance-reviewer"
```

### 6.5 AI Review Pipeline

The `GovernanceReviewer` class (`reviewer.py`) powers the AI review process. It constructs structured prompts, invokes `claude --print` via subprocess with temp file I/O, and parses JSON verdicts from the response.

**Three review modes**:

| Mode | Method | Timeout | Prompt Context |
|------|--------|---------|----------------|
| Decision review | `review_decision()` | 60s | Decision + vision standards + architecture entities |
| Plan review | `review_plan()` | 120s | Plan + all prior decisions + all prior reviews + vision + architecture |
| Completion review | `review_completion()` | 90s | Summary of work + files changed + all decisions + all reviews + vision |

**Execution flow** (for each review):

```
1. Build prompt
   |-- Format vision standards from KG
   |-- Format architecture entities from KG
   |-- Include decision/plan/completion details
   +-- Append JSON response schema instructions

2. Write prompt to temp file (tempfile.mkstemp)
   |-- Input:  /tmp/avt-gov-XXXX-input.md
   +-- Output: /tmp/avt-gov-XXXX-output.md

3. Execute: subprocess.run(
       ["claude", "--print"],
       stdin=<input file>,
       stdout=<output file>,
       timeout=<varies>
   )

4. Read response from output temp file

5. Parse JSON from response
   |-- Try: raw string starts with "{"
   |-- Try: extract from ```json ... ``` code blocks
   |-- Try: extract from first "{" to last "}"
   +-- Fallback: return needs_human_review with raw text

6. Clean up temp files (in finally block)
```

**Prompt structure** (decision review example):

```markdown
You are a governance reviewer. Evaluate this decision against the project's
vision and architecture standards.

## Vision Standards
- **standard_name**: observation1; observation2

## Architecture Patterns
- **component_name** (component): observation1; observation2

## Decision to Review
- **Agent**: worker-1
- **Category**: pattern_choice
- **Summary**: Use protocol-based DI for auth service
- **Detail**: ...
- **Components affected**: AuthService, ServiceRegistry
- **Alternatives considered**: ...
- **Confidence**: high

## Instructions
1. Check if this decision CONFLICTS with any vision standard.
2. Check if this decision deviates from established architecture patterns.
3. If deviation/scope_change, verdict should be "needs_human_review".
4. If aligned with standards, verdict is "approved".

Respond with ONLY a JSON object:
{ "verdict": "...", "findings": [...], "guidance": "...", "standards_verified": [...] }
```

**Error handling**: If `claude` CLI is not found, times out, or returns non-zero, the reviewer returns `needs_human_review` with an error description. The system degrades gracefully to manual review.

**Mock mode**: When the `GOVERNANCE_MOCK_REVIEW` environment variable is set, the reviewer skips the `claude` subprocess entirely and returns a deterministic `"approved"` verdict. This is used by the E2E test harness to avoid live `claude` binary dependency.

### 6.6 KG Integration

The `KGClient` class (`kg_client.py`) reads the Knowledge Graph JSONL file directly from the filesystem. It does not communicate with the KG MCP server over SSE -- it reads `.avt/knowledge-graph.jsonl` synchronously for zero-latency standard loading during review.

**Methods**:

| Method | What It Loads | How It Filters |
|--------|--------------|----------------|
| `get_vision_standards()` | All vision-tier entities | `entityType == "vision_standard"` OR observations containing "vision" |
| `get_architecture_entities()` | All architecture-tier entities | `entityType in ("architectural_standard", "pattern", "component")` |
| `search_entities(names)` | Entities matching component names | Case-insensitive substring match on name and observations |
| `record_decision(...)` | *(writes)* | Appends a `solution_pattern` entity to the JSONL file |

**Design choice**: Direct JSONL file reads avoid the latency and complexity of an MCP round-trip during synchronous governance review. Since the governance server runs on the same machine as the KG server, they share the same filesystem. The tradeoff is that KG writes during a governance review could produce stale reads, but governance reviews are short-lived (60-120 seconds) and standards change rarely.

### 6.7 Task Integration

The `task_integration.py` module manipulates Claude Code's native task file system to implement governance-gated task execution. Tasks are stored as JSON files in `~/.claude/tasks/<CLAUDE_CODE_TASK_LIST_ID>/`.

**Core principle**: Implementation tasks are ALWAYS created with a governance review blocker already in place. There is no window where a task exists without a blocker -- the review task is created first, the implementation task is created second with `blockedBy: [review_task_id]`.

**Task file format** (Claude Code native):

```json
{
  "id": "impl-a1b2c3d4",
  "subject": "Implement authentication service",
  "description": "Create JWT-based auth with refresh tokens",
  "status": "pending",
  "owner": null,
  "activeForm": "Working on Implement authentication service",
  "blockedBy": ["review-e5f6g7h8"],
  "blocks": [],
  "createdAt": 1738764000.0,
  "updatedAt": 1738764000.0
}
```

**Atomic operations**: All task file reads and writes use `fcntl.flock()` (exclusive file locks) to prevent race conditions when multiple agents access the same task simultaneously.

**TaskFileManager operations**:

| Operation | What It Does | Locking |
|-----------|-------------|---------|
| `create_task(task)` | Write new task JSON file | Exclusive lock on `.{task_id}.lock` |
| `read_task(task_id)` | Read and parse task JSON | No lock (read-only) |
| `update_task(task)` | Overwrite task JSON | Exclusive lock |
| `add_blocker(task_id, blocker_id)` | Add to `blockedBy` array | Exclusive lock |
| `remove_blocker(task_id, blocker_id)` | Remove from `blockedBy` array | Exclusive lock |
| `complete_task(task_id)` | Set `status: "completed"` | Via `update_task` |
| `list_tasks()` | Read all `.json` files in task directory | No lock |
| `get_pending_unblocked_tasks()` | Filter: pending, no blockers, no owner | No lock |

**Governed task pair creation** (`create_governed_task_pair`):

```
1. Generate IDs: review-{uuid8}, impl-{uuid8}
2. Create review task FIRST:
   - subject: "[GOVERNANCE] Review: <subject>"
   - blocks: [impl-id]
3. Create implementation task SECOND:
   - blockedBy: [review-id]
   - status: "pending" (but cannot execute due to blocker)
4. Both written atomically to task directory
```

**Task release** (`release_task`):

```
1. Read review task -> get implementation task ID from metadata or blocks list
2. Mark review task as completed
3. If verdict is "approved":
   - Remove review-id from implementation task's blockedBy
   - If blockedBy is now empty -> task can execute
4. If verdict is "blocked":
   - Keep blocker in place
   - Append guidance to implementation task description
```

### 6.8 Internal Architecture

```
+------------------------------------------------------------------+
| Agent calls submit_decision() / submit_plan_for_review()          |
+-------------------------------+----------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| server.py                                                         |
|  1. Store decision in SQLite (store.py)                           |
|  2. Auto-flag deviation/scope_change for human review             |
|  3. Load vision standards from KG (kg_client.py reads JSONL)      |
|  4. Load architecture entities from KG                            |
|  5. Call reviewer.review_decision() / review_plan()               |
+-------------------------------+----------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| reviewer.py (GovernanceReviewer)                                  |
|  1. Build prompt: decision + standards -> JSON response expected  |
|  2. Write prompt to temp file (mkstemp)                           |
|  3. Run: claude --print < input_tempfile > output_tempfile        |
|  4. Read response from output temp file                           |
|  5. Parse JSON into ReviewVerdict                                 |
|  6. Cleanup temp files in finally block                           |
|  (Mock mode: GOVERNANCE_MOCK_REVIEW returns deterministic OK)     |
+-------------------------------+----------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| Back in server.py                                                 |
|  6. Store review verdict in SQLite                                |
|  7. Record decision in KG (kg_client.record_decision)             |
|  8. Return verdict to calling agent                               |
+------------------------------------------------------------------+
```

### 6.9 SQLite Schema

The governance database (`.avt/governance.db`) contains four tables:

```sql
-- Decisions submitted by agents
CREATE TABLE decisions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,       -- Auto-incremented per task
    agent TEXT NOT NULL,
    category TEXT NOT NULL,          -- DecisionCategory enum value
    summary TEXT NOT NULL,
    detail TEXT,
    components_affected TEXT,        -- JSON array of strings
    alternatives TEXT,               -- JSON array of {option, reason_rejected}
    confidence TEXT,                 -- "high" | "medium" | "low"
    created_at TEXT NOT NULL         -- ISO 8601 UTC
);

-- Review verdicts (linked to decisions or plans)
CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    decision_id TEXT REFERENCES decisions(id),
    plan_id TEXT,                    -- Task ID for plan/completion reviews
    verdict TEXT NOT NULL,           -- "approved" | "blocked" | "needs_human_review"
    findings TEXT,                   -- JSON array of Finding objects
    guidance TEXT,
    standards_verified TEXT,         -- JSON array of standard names
    reviewer TEXT NOT NULL,          -- Default: "governance-reviewer"
    created_at TEXT NOT NULL
);

-- Governed task tracking
CREATE TABLE governed_tasks (
    id TEXT PRIMARY KEY,
    implementation_task_id TEXT UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    description TEXT,
    context TEXT,
    current_status TEXT NOT NULL DEFAULT 'pending_review',
    created_at TEXT NOT NULL,
    released_at TEXT                 -- Set when all review blockers are resolved
);

-- Individual review records for governed tasks
CREATE TABLE task_reviews (
    id TEXT PRIMARY KEY,
    review_task_id TEXT NOT NULL,
    implementation_task_id TEXT NOT NULL
        REFERENCES governed_tasks(implementation_task_id),
    review_type TEXT NOT NULL DEFAULT 'governance',
    status TEXT NOT NULL DEFAULT 'pending',
    context TEXT,
    verdict TEXT,                    -- Null until completed
    guidance TEXT,
    findings TEXT,                   -- JSON array of Finding objects
    standards_verified TEXT,         -- JSON array of standard names
    reviewer TEXT NOT NULL DEFAULT 'governance-reviewer',
    created_at TEXT NOT NULL,
    completed_at TEXT
);

-- Indexes for common query patterns
CREATE INDEX idx_decisions_task ON decisions(task_id);
CREATE INDEX idx_reviews_decision ON reviews(decision_id);
CREATE INDEX idx_reviews_plan ON reviews(plan_id);
CREATE INDEX idx_governed_tasks_impl ON governed_tasks(implementation_task_id);
CREATE INDEX idx_task_reviews_impl ON task_reviews(implementation_task_id);
CREATE INDEX idx_task_reviews_review ON task_reviews(review_task_id);
```

### 6.10 Current Implementation Status

All 10 tools are implemented and operational:

- `server.py`: FastMCP server exposing all tools on port 3103, including both decision review (5 tools) and task governance (5 tools) groups
- `store.py`: Full SQLite persistence with 4 tables, connection pooling via `sqlite3.Row`, and comprehensive CRUD for decisions, reviews, governed tasks, and task reviews
- `reviewer.py`: AI review engine with three review modes (decision, plan, completion), temp file I/O pattern, JSON parsing with multiple extraction strategies, and mock mode for testing
- `kg_client.py`: Direct JSONL reader with `get_vision_standards()`, `get_architecture_entities()`, `search_entities()`, and `record_decision()` for institutional memory
- `task_integration.py`: Claude Code task file manipulation with `fcntl` file locking, atomic governed task pair creation, blocker add/remove, and task release on approval
- `models.py`: Complete Pydantic model hierarchy for decisions, reviews, findings, verdicts, governed tasks, and task review records

**Extension point**: The `_queue_governance_review()` function in `server.py` is currently a pass-through placeholder. It records the review request (already stored in the `task_reviews` table) and serves as the extension point for future async job queue integration. Currently, reviews for governed tasks are triggered manually via `complete_task_review()` or processed by a governance-reviewer agent polling `get_pending_reviews()`.
