# Vision Standards

This folder contains vision standard documents. Each `.md` file defines one vision standard that will be ingested into the Knowledge Graph.

## Format

Each document should follow this format:

```markdown
# <Standard Name>

## Statement
<Clear, actionable statement of the standard>

## Rationale
<Why this standard exists>

## Examples
- Compliant: <example of code/behavior that follows the standard>
- Violation: <example of code/behavior that violates the standard>
```

## Important Notes

- Vision standards are **immutable** once ingested — only humans can modify them
- Violations of vision standards **block all related work**
- Standards should be clear, specific, and actionable
- One file per standard

## Examples

- `protocol-based-di.md` — "All services use protocol-based dependency injection"
- `no-singletons.md` — "No singletons in production code"
- `error-handling.md` — "Error handling uses Result types, not exceptions"
