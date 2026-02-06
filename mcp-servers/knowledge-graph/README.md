# Knowledge Graph MCP Server

Tier-protected persistent institutional memory for the Collaborative Intelligence System.

## Overview

The Knowledge Graph server provides persistent storage of:
- **Entities**: Components, patterns, decisions, problems, vision standards
- **Relations**: Dependencies, pattern adherence, governance relationships
- **Observations**: Facts, notes, and context about entities

All data is protected by a three-tier system preventing accidental corruption of critical information.

## Quick Start

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Start server (SSE on port 3101)
uv run python -m collab_kg.server
```

## Protection Tiers

| Tier | Mutability | Use Case | Example |
|------|-----------|----------|---------|
| **vision** | Human-only | Fundamental principles | "Voice is primary interaction mode" |
| **architecture** | Human-approved | Established patterns | "Use protocol-based DI pattern" |
| **quality** | Automated | Implementation details | "Fixed race condition in auth" |

The server **enforces** tier protection at the tool level — a misbehaving agent cannot corrupt vision-tier data.

## MCP Tools

### `create_entities`

```typescript
create_entities(entities: [{
  name: string,
  entityType: "component" | "vision_standard" | "architectural_standard" |
               "pattern" | "problem" | "solution_pattern",
  observations: string[]  // Must include "protection_tier: <tier>" for protected entities
}]) → { created: number }
```

### `create_relations`

```typescript
create_relations(relations: [{
  from: string,
  to: string,
  relationType: "depends_on" | "follows_pattern" | "governed_by" |
                "fixed_by" | "exemplified_by" | "rejected_in_favor_of"
}]) → { created: number }
```

### `add_observations`

```typescript
add_observations(
  entityName: string,
  observations: string[],
  callerRole: "human" | "orchestrator" | "worker" | "quality",
  changeApproved: boolean = false
) → { added: number, error?: string }
```

**Tier Protection:**
- Vision tier: Only `callerRole="human"` allowed
- Architecture tier: Requires `changeApproved=true`
- Quality tier: All callers allowed

### `delete_observations`

```typescript
delete_observations(
  entityName: string,
  observations: string[],
  callerRole: string,
  changeApproved: boolean = false
) → { deleted: number, error?: string }
```

Same tier protection as `add_observations`.

### `delete_entity`

```typescript
delete_entity(
  entityName: string,
  callerRole: string
) → { deleted: boolean, error?: string }
```

Only quality-tier entities can be deleted by agents. Vision/architecture require human.

### `delete_relations`

```typescript
delete_relations(relations: [{
  from: string,
  to: string,
  relationType: string
}]) → { deleted: number }
```

### `search_nodes`

```typescript
search_nodes(query: string) → EntityWithRelations[]
```

Searches entity names and observations for substring match.

### `get_entity`

```typescript
get_entity(name: string) → EntityWithRelations
```

### `get_entities_by_tier`

```typescript
get_entities_by_tier(tier: "vision" | "architecture" | "quality") → EntityWithRelations[]
```

### `validate_tier_access`

```typescript
validate_tier_access(
  entityName: string,
  operation: "read" | "write",
  callerRole: string
) → { allowed: boolean, reason?: string }
```

## Data Models

### Entity

```python
@dataclass
class Entity:
    name: str
    entityType: EntityType  # Enum
    observations: list[str]
```

### Relation

```python
@dataclass
class Relation:
    from_entity: str
    to: str
    relationType: str
```

### EntityWithRelations

```python
@dataclass
class EntityWithRelations(Entity):
    relations: list[Relation]
```

## Storage

- **Format**: JSONL (one entity or relation per line)
- **Path**: `.avt/knowledge-graph.jsonl` (configurable)
- **Loading**: Entire file loaded into memory on startup
- **Writing**: Append-only for new entities/relations
- **Compaction**: Automatic after 1000 writes (rewrites file with current state only)

### Example JSONL

```json
{"type": "entity", "name": "hands_free_first_design", "entityType": "vision_standard", "observations": ["protection_tier: vision", "Voice is PRIMARY interaction mode"]}
{"type": "relation", "from": "KBOralSessionView", "to": "hands_free_first_design", "relationType": "governed_by"}
{"type": "entity", "name": "KBOralSessionView", "entityType": "component", "observations": ["protection_tier: architecture", "Uses protocol-based DI"]}
```

## Usage Example

```python
# Create vision-tier standard
create_entities([{
    "name": "accessibility_first",
    "entityType": "vision_standard",
    "observations": [
        "protection_tier: vision",
        "mutability: human_only",
        "All features must be accessible without mouse"
    ]
}])

# Create component governed by standard
create_entities([{
    "name": "MainMenuView",
    "entityType": "component",
    "observations": [
        "protection_tier: architecture",
        "Keyboard navigation implemented",
        "All actions have keyboard shortcuts"
    ]
}])

# Link component to vision standard
create_relations([{
    "from": "MainMenuView",
    "to": "accessibility_first",
    "relationType": "governed_by"
}])

# Worker tries to add observation (succeeds for quality, fails for vision)
add_observations(
    "MainMenuView",
    ["Added new menu item"],
    caller_role="worker",
    change_approved=True  # Required for architecture tier
)
```

## Testing

```bash
# Run all tests (18 tests)
uv run pytest

# With coverage (74% overall, 98% for graph.py)
uv run pytest --cov=collab_kg --cov-report=term-missing
```

## Implementation Details

### Tier Protection Enforcement

`tier_protection.py` provides:
- `get_entity_tier(observations)`: Extracts tier from "protection_tier: X" observation
- `validate_write_access(tier, caller_role, change_approved)`: Returns (allowed, reason)

Protection is checked in `graph.py` for all write operations before modifying data.

### Storage Architecture

- `JSONLStorage` class handles all file I/O
- `KnowledgeGraph` class holds in-memory graph and delegates persistence
- Compaction threshold prevents JSONL from growing indefinitely
- Atomic file replacement during compaction (write to `.tmp`, then replace)

## Architecture Integration

This server is used by:
- **Worker subagents**: Query for patterns and constraints before implementing
- **Quality reviewer subagents**: Load vision/architecture standards for evaluation
- **KG librarian subagent**: Curate and consolidate observations after sessions
- **Orchestrator**: Query for constraints when decomposing tasks

## Future Enhancements

- Cross-project memory (entities that travel between projects)
- Full-text search with ranking
- Relation traversal queries (find all components governed by a standard)
- Graph visualization export
- Migration to FastMCP 3.0 when stable

## See Also

- [Collaborative Intelligence Vision](../../COLLABORATIVE_INTELLIGENCE_VISION.md)
- [Technical Architecture](../../ARCHITECTURE.md)
- [Quality MCP Server](../quality/README.md)
