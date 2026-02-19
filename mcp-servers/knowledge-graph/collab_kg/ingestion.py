"""Document ingestion — parse markdown files into KG entities."""

import re
from pathlib import Path
from typing import Optional

from .models import EntityType


def parse_document(filepath: Path, tier: str) -> Optional[dict]:
    """Parse a markdown document into a KG entity dict.

    Args:
        filepath: Path to the markdown file
        tier: 'vision' or 'architecture'

    Returns:
        Entity dict with name, entityType, observations, or None if parsing fails
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    # Extract title from first H1
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if not title_match:
        return None

    raw_title = title_match.group(1).strip()

    # Clean up title - remove common prefixes
    name = raw_title
    for prefix in ["Vision Standard:", "Architectural Standard:", "Pattern:", "Component:"]:
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix) :].strip()
            break

    # Convert to snake_case for entity name
    entity_name = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    if not entity_name:
        entity_name = filepath.stem.replace("-", "_")

    # Determine entity type based on tier and document content
    entity_type = _determine_entity_type(content, tier)

    # Build observations from document sections
    observations = [f"protection_tier: {tier}"]

    # Extract Statement section
    statement = _extract_section(content, "Statement")
    if statement:
        observations.append(f"statement: {statement}")

    # Extract Description section (for architecture docs)
    description = _extract_section(content, "Description")
    if description:
        observations.append(f"description: {description}")

    # Extract Rationale section
    rationale = _extract_section(content, "Rationale")
    if rationale:
        observations.append(f"rationale: {rationale}")

    # Extract Type section (for architecture docs)
    type_section = _extract_section(content, "Type")
    if type_section:
        observations.append(f"document_type: {type_section}")

    # Extract Usage section
    usage = _extract_section(content, "Usage")
    if usage:
        observations.append(f"usage: {usage}")

    # Extract Examples section
    examples = _extract_section(content, "Examples")
    if examples:
        observations.append(f"examples: {examples}")

    # Extract Dependencies section (for architecture component docs)
    dependencies = _extract_section(content, "Dependencies")
    if dependencies:
        observations.append(f"dependencies: {dependencies}")

    # Add the full document title as an observation
    observations.append(f"title: {raw_title}")

    # Add source file reference
    observations.append(f"source_file: {filepath.name}")

    return {
        "name": entity_name,
        "entityType": entity_type.value,
        "observations": observations,
    }


def _determine_entity_type(content: str, tier: str) -> EntityType:
    """Determine the appropriate entity type based on document content and tier."""
    content_lower = content.lower()

    if tier == "vision":
        return EntityType.VISION_STANDARD

    # For architecture tier, check the Type section or keywords
    type_section = _extract_section(content, "Type")
    if type_section:
        type_lower = type_section.lower()
        if "pattern" in type_lower:
            return EntityType.PATTERN
        if "component" in type_lower:
            return EntityType.COMPONENT
        if "standard" in type_lower:
            return EntityType.ARCHITECTURAL_STANDARD

    # Fallback to keywords in content
    if "pattern" in content_lower:
        return EntityType.PATTERN
    if "component" in content_lower:
        return EntityType.COMPONENT

    return EntityType.ARCHITECTURAL_STANDARD


def _extract_section(content: str, section_name: str) -> Optional[str]:
    """Extract content from a markdown section.

    Looks for ## Section Name and extracts content until the next ## or end.
    Strips fenced code blocks (e.g. Mermaid diagrams) before collapsing
    whitespace so they don't get mangled into the observation text.
    """
    pattern = rf"^##\s+{re.escape(section_name)}\s*\n(.*?)(?=^##|\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
        # Remove fenced code blocks (```...```) so Mermaid diagrams
        # and other code blocks don't get collapsed into gibberish
        text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
        # Collapse multiple whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip() if text.strip() else None
    return None


def ingest_folder(
    graph,  # KnowledgeGraph instance
    folder_path: str,
    tier: str,
) -> dict:
    """Ingest all markdown documents from a folder into the KG.

    Args:
        graph: KnowledgeGraph instance
        folder_path: Path to folder containing .md files
        tier: 'vision' or 'architecture'

    Returns:
        {
            "ingested": count,
            "entities": [list of entity names],
            "errors": [list of error messages],
            "skipped": [list of skipped files],
        }
    """
    folder = Path(folder_path)
    if not folder.exists():
        return {
            "ingested": 0,
            "entities": [],
            "errors": [f"Folder does not exist: {folder_path}"],
            "skipped": [],
        }

    entities_to_create = []
    errors = []
    skipped = []

    # Find all .md files recursively (excluding README.md)
    md_files = [f for f in folder.rglob("*.md") if f.name.lower() != "readme.md"]

    for md_file in md_files:
        entity = parse_document(md_file, tier)
        if entity:
            entities_to_create.append(entity)
        else:
            errors.append(f"Failed to parse: {md_file.name}")

    if not entities_to_create:
        return {
            "ingested": 0,
            "entities": [],
            "errors": errors if errors else ["No valid documents found"],
            "skipped": skipped,
        }

    # Delete existing entities with same names (re-ingestion support)
    # Using caller_role="human" since ingestion is human-initiated
    for entity in entities_to_create:
        existing = graph.get_entity(entity["name"])
        if existing:
            success, err = graph.delete_entity(entity["name"], caller_role="human")
            if not success:
                errors.append(f"Could not delete existing entity {entity['name']}: {err}")

    # Create entities
    created = graph.create_entities(entities_to_create)

    return {
        "ingested": created,
        "entities": [e["name"] for e in entities_to_create],
        "errors": errors,
        "skipped": skipped,
    }
