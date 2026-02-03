"""Knowledge Graph MCP server."""

from fastmcp import FastMCP

from .graph import KnowledgeGraph

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
        folder: Path to folder containing .md files (default: .avt/vision/ or .avt/architecture/)
        tier: 'vision' or 'architecture'

    Returns:
        {ingested: count, entities: [names], errors: [messages], skipped: [files]}
    """
    from .ingestion import ingest_folder

    # Default folders based on tier
    if not folder:
        folder = f".avt/{tier}/" if tier in ("vision", "architecture") else folder

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


if __name__ == "__main__":
    mcp.run(transport="sse", port=3101)
