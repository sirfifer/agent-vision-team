# Quality MCP Server

Deterministic quality verification with language-agnostic tool wrapping and trust engine for the Collaborative Intelligence System.

## Overview

The Quality server provides:
- **Unified Tool Interface**: Single MCP tools for format, lint, test, coverage across languages
- **Language Detection**: Automatic routing to appropriate tools (ruff, eslint, pytest, etc.)
- **Trust Engine**: SQLite-backed finding tracking with dismissal audit trail
- **Quality Gates**: Aggregated results across all verification dimensions
- **No Silent Dismissals**: Every dismissed finding requires justification

## Quick Start

```bash
# Install dependencies
uv sync

# Run tests (26 tests)
uv run pytest

# Start server (SSE on port 3102)
uv run python -m collab_quality.server
```

## Supported Languages

| Language | Formatter | Linter | Test Runner |
|----------|-----------|--------|-------------|
| Python | `ruff format` | `ruff check` | `pytest` |
| TypeScript/JS | `prettier` | `eslint` | `npm test` |
| Swift | `swiftformat` | `swiftlint` | `xcodebuild test` |
| Rust | `rustfmt` | `clippy` | `cargo test` |

## MCP Tools

### `auto_format`

```typescript
auto_format(
  files?: string[],      // Specific files, or detects from git if omitted
  language?: string      // Auto-detected from extension if omitted
) → {
  formatted: string[],
  unchanged: string[],
  error?: string
}
```

**Example:**
```python
auto_format(files=["src/main.py", "src/utils.py"], language="python")
# → { formatted: ["src/main.py"], unchanged: ["src/utils.py"] }
```

### `run_lint`

```typescript
run_lint(
  files?: string[],
  language?: string
) → {
  findings: LintFinding[],
  auto_fixable: number,
  total: number,
  error?: string
}
```

**LintFinding:**
```typescript
{
  file: string,
  line: number,
  column: number,
  severity: string,
  message: string,
  rule: string
}
```

### `run_tests`

```typescript
run_tests(
  scope?: string,        // "all" | "changed" | specific path
  language?: string
) → {
  passed: number,
  failed: number,
  skipped: number,
  failures: string[],
  error?: string
}
```

### `check_coverage`

```typescript
check_coverage(
  language?: string
) → {
  percentage: number,
  target: number,
  met: boolean,
  uncovered_files: string[],
  error?: string
}
```

Default target: 80%

### `check_all_gates`

```typescript
check_all_gates() → {
  build: GateResult,
  lint: GateResult,
  tests: GateResult,
  coverage: GateResult,
  findings: GateResult,
  all_passed: boolean
}
```

**GateResult:**
```typescript
{
  name: string,
  passed: boolean,
  detail: string
}
```

### `validate`

```typescript
validate() → {
  gates: GateResults,
  summary: string,
  all_passed: boolean
}
```

Comprehensive validation — all gates plus human-readable summary.

### `get_trust_decision`

```typescript
get_trust_decision(finding_id: string) → {
  decision: "BLOCK" | "INVESTIGATE" | "TRACK",
  rationale: string
}
```

- **BLOCK**: Cannot proceed until resolved (default for all findings)
- **INVESTIGATE**: Needs human/orchestrator review
- **TRACK**: Note it, don't block (e.g., previously dismissed findings)

### `record_dismissal`

```typescript
record_dismissal(
  finding_id: string,
  justification: string,  // Required — no silent dismissals
  dismissed_by: string    // Agent or human identifier
) → { recorded: boolean }
```

## Trust Engine

SQLite database (`.avt/trust-engine.db`) with two tables:

### findings

```sql
CREATE TABLE findings (
    id TEXT PRIMARY KEY,
    tool TEXT NOT NULL,
    severity TEXT NOT NULL,
    component TEXT,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'open',  -- open, fixed, dismissed
    dismissed_by TEXT,
    dismissal_justification TEXT,
    dismissed_at TEXT
);
```

### dismissal_history

```sql
CREATE TABLE dismissal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id TEXT NOT NULL,
    dismissed_by TEXT NOT NULL,
    justification TEXT NOT NULL,
    dismissed_at TEXT NOT NULL,
    FOREIGN KEY (finding_id) REFERENCES findings(id)
);
```

**Key Principle**: No silent dismissals. Every dismissed finding has:
- Justification (why it was dismissed)
- Identity (who dismissed it)
- Timestamp (when it was dismissed)
- Audit trail (history table for re-dismissals)

## Usage Example

### Worker Subagent

```python
# Before reporting completion, run quality checks
result = check_all_gates()

if not result["all_passed"]:
    # Report findings to orchestrator
    print(f"Quality gates failed: {result['summary']}")
    return

# All gates passed
print("Work complete, all quality gates passed")
```

### Quality Reviewer Subagent

```python
# Run three-lens review

# Lens 1: Vision (check KG)
vision_entities = get_entities_by_tier("vision")
# ... check for conflicts ...

# Lens 2: Architecture (check KG)
arch_entities = get_entities_by_tier("architecture")
# ... check for pattern adherence ...

# Lens 3: Quality (use this server)
lint_result = run_lint(files=changed_files)
test_result = run_tests(scope="changed")
coverage_result = check_coverage()

# Return structured findings
findings = []
for lint_finding in lint_result["findings"]:
    findings.append({
        "tier": "quality",
        "severity": "style" if lint_finding["severity"] == "warning" else "logic",
        "component": lint_finding["file"],
        "finding": lint_finding["message"],
        "rationale": f"Linter rule {lint_finding['rule']} violated",
        "suggestion": "Run auto_format() to fix"
    })
```

### Trust Engine Workflow

```python
# Record a finding
engine.record_finding(
    finding_id="ESL-001",
    tool="eslint",
    severity="warning",
    component="AuthService",
    description="Missing semicolon at line 42"
)

# Get trust decision
decision = engine.get_trust_decision("ESL-001")
# → { decision: "BLOCK", rationale: "Default: all findings presumed legitimate" }

# Human dismisses it
engine.record_dismissal(
    "ESL-001",
    "Semicolons not required in our TypeScript style guide",
    "tech_lead"
)

# Future occurrences
decision = engine.get_trust_decision("ESL-001")
# → { decision: "TRACK", rationale: "Previously dismissed by tech_lead: ..." }

# Get audit trail
history = engine.get_dismissal_history("ESL-001")
# → [{ dismissed_by: "tech_lead", justification: "...", dismissed_at: "..." }]
```

## Tool Implementation Details

### Language Detection

```python
def detect_language(filepath: str) -> Optional[str]:
    """Detect language from file extension."""
    ext = Path(filepath).suffix.lower()
    language_map = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".swift": "swift",
        ".rs": "rust",
    }
    return language_map.get(ext)
```

### Tool Execution

All tools use `subprocess.run` with:
- Capture output (`capture_output=True`)
- Timeout protection (30s for format/lint, 300s for tests)
- Error handling (FileNotFoundError if tool not installed)
- JSON output parsing for structured results

### Error Handling

If a tool is not installed:
```python
{
    "formatted": [],
    "unchanged": files,
    "error": "Formatter 'ruff' not found. Install it to use formatting."
}
```

## Testing

```bash
# Run all tests
uv run pytest  # 26 tests

# With coverage (48% overall, 100% for trust_engine.py)
uv run pytest --cov=collab_quality --cov-report=term-missing
```

### Test Coverage Notes

- Trust engine: 100% coverage
- Tool wrappers: 58-72% (branches requiring actual tool execution not hit)
- Server.py: 0% (MCP integration points, tested via integration)
- Gates.py: 0% (would require pytest recursion in tests)

## Architecture Integration

This server is used by:
- **Worker subagents**: Run `check_all_gates()` before reporting completion
- **Quality reviewer subagents**: Run `run_lint()`, `run_tests()`, `check_coverage()` for Lens 3 evaluation
- **Orchestrator**: Aggregate quality state across multiple workers

## Configuration

Tools are configurable per language. To add a new language:

```python
# In tools/formatting.py
FORMATTERS = {
    "mylang": ["mylang-fmt", "--check"],
}

# In tools/linting.py
LINTERS = {
    "mylang": ["mylang-lint", "--format=json"],
}

# In tools/testing.py
TEST_RUNNERS = {
    "mylang": ["mylang-test", "--verbose"],
}
```

## Future Enhancements

- Build gate implementation (currently stub)
- Configurable coverage targets per project
- Parallel execution of independent tools
- Caching of lint/test results
- Integration with CI/CD for historical trend tracking
- FastMCP 3.0 migration when stable

## See Also

- [Collaborative Intelligence Vision](../../COLLABORATIVE_INTELLIGENCE_VISION.md)
- [Technical Architecture](../../ARCHITECTURE.md)
- [Knowledge Graph MCP Server](../knowledge-graph/README.md)
