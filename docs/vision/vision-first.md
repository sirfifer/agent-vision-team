# Vision First

## Statement

Vision standards are immutable by agents; only humans may define, modify, or remove vision-tier principles. No automated process, agent, or governance mechanism may alter vision standards regardless of context.

## Rationale

The entire collaborative intelligence system depends on a stable, human-defined foundation of principles. If agents could modify their own governing principles, the system would lack a reliable anchor for decision-making. This is enforced technically through `tier_protection.py` in the Knowledge Graph server, which rejects any non-human caller attempting to modify vision-tier entities. Every agent definition and the orchestrator instructions (`CLAUDE.md`) reinforce this principle.

## Source Evidence

- `mcp-servers/knowledge-graph/collab_kg/tier_protection.py`: Programmatic enforcement
- `CLAUDE.md`: "Vision standards are inviolable"
- `docs/project-overview.md`: Guiding Principles section
- All `.claude/agents/*.md`: Reference three-tier hierarchy with vision at top
