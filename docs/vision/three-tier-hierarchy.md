# Three-Tier Governance Hierarchy

## Statement

The governance system shall enforce a strict three-tier hierarchy: Vision (human-only modification) > Architecture (human or orchestrator with approval) > Quality (any agent). Lower tiers shall never modify higher tiers. Vision conflicts shall override all other work.

## Rationale

Without a clear hierarchy, governance becomes ambiguous. Which standard takes precedence when two conflict? The three-tier system resolves this definitively: vision standards are inviolable, architecture patterns are stable but adaptable, and quality observations are fluid. This is enforced at the KG level through `tier_protection.py` and at the governance level through review verdicts that check for vision conflicts first.

## Source Evidence

- `mcp-servers/knowledge-graph/collab_kg/tier_protection.py`: Tier enforcement
- `mcp-servers/knowledge-graph/collab_kg/models.py`: Tier enum definition
- `CLAUDE.md`: Three-Tier Governance Hierarchy table
- `docs/project-overview.md`: Hierarchy description
- All agent definitions: Reference tier constraints
