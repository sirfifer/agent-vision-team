# Architecture Documents

This folder contains architecture documents. Each `.md` file defines an architectural standard, pattern, or component that will be ingested into the Knowledge Graph.

## Format

Each document should follow this format:

```markdown
# <Name>

## Type
<One of: architectural_standard, pattern, component>

## Description
<What this represents>

## Rationale
<Why this exists or why this pattern was chosen>

## Usage
<How to use this pattern or interact with this component>
```

## Document Types

- **Architectural Standard**: Design rules enforced across the codebase
- **Pattern**: Established implementation patterns agents should follow
- **Component**: Tracked system components with state and behavior

## Important Notes

- Architecture documents can be modified with human approval
- Deviations require governance review
- Components track state through observations in the Knowledge Graph

## Examples

- `service-registry.md` — Pattern for service discovery and registration
- `auth-service.md` — Component definition for authentication service
- `api-versioning.md` — Architectural standard for API versioning
