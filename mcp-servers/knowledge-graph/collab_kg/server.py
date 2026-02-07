"""Knowledge Graph MCP server."""

from fastmcp import FastMCP

from .graph import KnowledgeGraph
from .tier_protection import get_entity_tier, validate_write_access

mcp = FastMCP("Collab Intelligence Knowledge Graph")

graph = KnowledgeGraph()


@mcp.tool()
def create_entities(entities: list[dict]) -> dict:
    """Create entities in the knowledge graph."""
    created = graph.create_entities(entities)
    return {"created": created}


@mcp.tool()
def create_relations(relations: list[dict]) -> dict:
    """Create relations between entities."""
    created = graph.create_relations(relations)
    return {"created": created}


@mcp.tool()
def add_observations(
    entity_name: str,
    observations: list[str],
    caller_role: str = "agent",
    change_approved: bool = False,
) -> dict:
    """Add observations to an entity. Respects tier protection."""
    added, error = graph.add_observations(
        entity_name, observations, caller_role, change_approved
    )
    if error:
        return {"added": 0, "error": error}
    return {"added": added}


@mcp.tool()
def search_nodes(query: str) -> list[dict]:
    """Search for entities matching a query string."""
    results = graph.search_nodes(query)
    return [r.model_dump(by_alias=True) for r in results]


@mcp.tool()
def get_entity(name: str) -> dict:
    """Get a specific entity with its observations and relations."""
    entity = graph.get_entity(name)
    if entity is None:
        return {"error": f"Entity '{name}' not found."}
    return entity.model_dump(by_alias=True)


@mcp.tool()
def get_entities_by_tier(tier: str) -> list[dict]:
    """Get all entities for a specific protection tier (vision/architecture/quality)."""
    results = graph.get_entities_by_tier(tier)
    return [r.model_dump(by_alias=True) for r in results]


@mcp.tool()
def delete_observations(
    entity_name: str,
    observations: list[str],
    caller_role: str = "agent",
    change_approved: bool = False,
) -> dict:
    """Delete specific observations from an entity. Respects tier protection."""
    deleted, error = graph.delete_observations(
        entity_name, observations, caller_role, change_approved
    )
    if error:
        return {"deleted": 0, "error": error}
    return {"deleted": deleted}


@mcp.tool()
def delete_entity(
    entity_name: str,
    caller_role: str = "agent",
) -> dict:
    """Delete an entire entity. Only allowed for quality-tier or by humans."""
    deleted, error = graph.delete_entity(entity_name, caller_role)
    if error:
        return {"deleted": False, "error": error}
    return {"deleted": deleted}


@mcp.tool()
def delete_relations(relations: list[dict]) -> dict:
    """Delete specific relations from the graph."""
    deleted = graph.delete_relations(relations)
    return {"deleted": deleted}


@mcp.tool()
def ingest_documents(folder: str, tier: str) -> dict:
    """Ingest markdown documents from a folder into KG entities.

    Args:
        folder: Path to folder containing .md files (default: docs/vision/ or docs/architecture/)
        tier: 'vision' or 'architecture'

    Returns:
        {ingested: count, entities: [names], errors: [messages], skipped: [files]}
    """
    from .ingestion import ingest_folder

    # Default folders based on tier
    if not folder:
        folder = f"docs/{tier}/" if tier in ("vision", "architecture") else folder

    return ingest_folder(graph, folder, tier)


@mcp.tool()
def validate_tier_access(
    entity_name: str,
    operation: str,
    caller_role: str,
) -> dict:
    """Check if an operation is permitted given the entity's tier and caller's role."""
    from .tier_protection import get_entity_tier, validate_write_access

    entity = graph.get_entity(entity_name)
    if entity is None:
        return {"allowed": False, "reason": f"Entity '{entity_name}' not found."}

    if operation == "read":
        return {"allowed": True}

    tier = get_entity_tier(entity.observations)
    allowed, reason = validate_write_access(tier, caller_role)
    result: dict = {"allowed": allowed}
    if reason:
        result["reason"] = reason
    return result


@mcp.tool()
def get_architecture_completeness() -> dict:
    """Get all architecture-tier entities with their metadata completeness status.

    Returns a report showing which entities have complete intent and vision-alignment
    and which ones need enrichment.

    Returns:
        {
            total: int,
            complete: int,
            partial: int,
            missing: int,
            entities: [{name, entityType, completeness, missing_fields}]
        }
    """
    from .metadata import get_intent, get_vision_alignments

    arch_entities = graph.get_entities_by_tier("architecture")
    report_entities = []
    counts = {"complete": 0, "partial": 0, "missing": 0}

    for entity in arch_entities:
        obs = entity.observations
        has_intent = get_intent(obs) is not None
        has_vision = len(get_vision_alignments(obs)) > 0

        missing_fields = []
        if not has_intent:
            missing_fields.append("intent")
        if not has_vision:
            missing_fields.append("vision_alignment")

        if not missing_fields:
            completeness = "full"
            counts["complete"] += 1
        elif len(missing_fields) < 2:
            completeness = "partial"
            counts["partial"] += 1
        else:
            completeness = "none"
            counts["missing"] += 1

        report_entities.append({
            "name": entity.name,
            "entityType": entity.entity_type.value,
            "completeness": completeness,
            "missing_fields": missing_fields,
        })

    return {
        "total": len(arch_entities),
        "complete": counts["complete"],
        "partial": counts["partial"],
        "missing": counts["missing"],
        "entities": report_entities,
    }


@mcp.tool()
def set_entity_metadata(
    entity_name: str,
    intent: str = "",
    metrics: list[dict] | None = None,
    vision_alignments: list[dict] | None = None,
    caller_role: str = "agent",
    change_approved: bool = False,
) -> dict:
    """Set structured intent and vision-alignment metadata on an entity.

    Replaces any existing metadata observations with the new values.
    Respects tier protection (architecture tier requires human approval for agents).

    Args:
        entity_name: Name of the entity to update.
        intent: Why this architectural decision exists.
        metrics: Optional list of dicts with keys: name, criteria, baseline.
        vision_alignments: List of dicts with keys: vision_entity, explanation.
        caller_role: "human" or "agent".
        change_approved: Whether human has approved this change.

    Returns:
        {updated: bool, observations_added: int} or {error: str}
    """
    from .metadata import build_intent_observations, strip_metadata_observations

    entity = graph.get_entity(entity_name)
    if entity is None:
        return {"updated": False, "error": f"Entity '{entity_name}' not found."}

    tier = get_entity_tier(entity.observations)
    allowed, reason = validate_write_access(tier, caller_role, change_approved)
    if not allowed:
        return {"updated": False, "error": reason}

    # Strip old metadata observations, build new ones
    cleaned = strip_metadata_observations(entity.observations)
    new_metadata = build_intent_observations(
        intent=intent,
        metrics=metrics,
        vision_alignments=vision_alignments,
    )

    # Update the entity's observations in-place
    raw_entity = graph._entities.get(entity_name)
    if raw_entity is None:
        return {"updated": False, "error": f"Entity '{entity_name}' not found."}

    raw_entity.observations = cleaned + new_metadata
    graph.storage.compact(graph._entities, graph._relations)

    # Create serves_vision relations if vision alignments are provided
    if vision_alignments:
        relations_to_create = []
        for va in vision_alignments:
            vision_entity = va.get("vision_entity", "")
            if vision_entity and graph.get_entity(vision_entity) is not None:
                relations_to_create.append({
                    "from": entity_name,
                    "to": vision_entity,
                    "relationType": "serves_vision",
                })
        if relations_to_create:
            graph.create_relations(relations_to_create)

    return {"updated": True, "observations_added": len(new_metadata)}


@mcp.tool()
def validate_ingestion(tier: str) -> dict:
    """Validate all entities of a tier for metadata completeness.

    For architecture entities, checks intent and vision alignment.
    For vision entities, returns a simple count (they don't need intent metadata).

    Args:
        tier: 'architecture' or 'vision'

    Returns:
        {
            total: int,
            complete: int,
            partial: int,
            missing: int,
            entities: [{name, completeness, missing_fields, existing_observations}]
        }
    """
    from .metadata import (
        get_intent,
        get_vision_alignments,
    )

    entities = graph.get_entities_by_tier(tier)

    if tier == "vision":
        return {
            "total": len(entities),
            "complete": len(entities),
            "partial": 0,
            "missing": 0,
            "entities": [
                {
                    "name": e.name,
                    "completeness": "full",
                    "missing_fields": [],
                    "existing_observations": e.observations,
                }
                for e in entities
            ],
        }

    report_entities = []
    counts = {"complete": 0, "partial": 0, "missing": 0}

    for entity in entities:
        obs = entity.observations
        has_intent = get_intent(obs) is not None
        has_vision = len(get_vision_alignments(obs)) > 0

        missing_fields = []
        if not has_intent:
            missing_fields.append("intent")
        if not has_vision:
            missing_fields.append("vision_alignment")

        if not missing_fields:
            completeness = "full"
            counts["complete"] += 1
        elif len(missing_fields) < 2:
            completeness = "partial"
            counts["partial"] += 1
        else:
            completeness = "none"
            counts["missing"] += 1

        report_entities.append({
            "name": entity.name,
            "completeness": completeness,
            "missing_fields": missing_fields,
            "existing_observations": obs,
        })

    return {
        "total": len(entities),
        "complete": counts["complete"],
        "partial": counts["partial"],
        "missing": counts["missing"],
        "entities": report_entities,
    }


if __name__ == "__main__":
    mcp.run(transport="sse", port=3101)
