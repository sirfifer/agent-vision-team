# No Silent Dismissals

## Statement

Every dismissed quality finding shall require a written justification and the identity of the dismisser. No finding may be silently ignored or suppressed.

## Rationale

Silent dismissals erode trust in the quality system. If findings can be dismissed without explanation, agents learn to dismiss inconvenient findings rather than fix them. The trust engine in the Quality MCP server requires a `justification` string and `dismissed_by` identifier for every dismissal. Dismissals are persisted in SQLite and are auditable. Patterns of unjustified dismissals trigger trust score degradation.

## Source Evidence

- `mcp-servers/quality/collab_quality/trust_engine.py`: Dismissal tracking with required fields
- `docs/project-overview.md`: Trust engine description
- `CLAUDE.md`: "Every dismissal needs a rationale"
