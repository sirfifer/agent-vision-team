# Deterministic Verification Over AI Judgment

## Statement

Quality gates shall use real tools (compilers, linters, test suites, coverage analyzers) for verification, not LLM-based opinions. AI judgment is reserved for governance review of alignment and intent; quality verification must be deterministic and reproducible.

## Rationale

LLM-based code review is non-deterministic: the same code may receive different assessments on different runs. Real tools provide consistent, reproducible results. The Quality MCP server wraps actual compilers, linters (ESLint, Ruff), test runners (pytest, Mocha), and coverage tools. The trust engine tracks dismissals deterministically. Only governance reviews (alignment, vision conformance) use AI judgment, and even those follow the structured PIN methodology.

## Source Evidence

- `mcp-servers/quality/collab_quality/server.py`: Tool-based quality gates
- `mcp-servers/quality/collab_quality/gates.py`: Gate implementations
- `docs/project-overview.md`: Quality verification philosophy
- `CLAUDE.md`: Quality Gates section
