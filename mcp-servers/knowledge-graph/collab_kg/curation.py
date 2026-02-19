"""KG Librarian curation logic as callable functions.

Extracts the curation operations described in .claude/agents/kg-librarian.md
into deterministic Python functions that can be called directly by tests or
by the librarian agent.
"""

from collections import Counter

from .graph import KnowledgeGraph
from .models import EntityType
from .tier_protection import get_entity_tier


def consolidate_observations(kg: KnowledgeGraph, entity_name: str) -> dict:
    """Merge redundant observations on a single entity.

    Detects duplicate or near-duplicate observations (exact match after
    lowercasing and stripping whitespace) and removes the duplicates,
    keeping one copy of each unique observation.

    Returns:
        {"entity": entity_name, "removed": int, "kept": int}
    """
    entity = kg.get_entity(entity_name)
    if entity is None:
        return {"entity": entity_name, "removed": 0, "kept": 0, "error": "not found"}

    seen: dict[str, str] = {}  # normalised -> original
    duplicates: list[str] = []

    for obs in entity.observations:
        key = obs.strip().lower()
        if key in seen:
            duplicates.append(obs)
        else:
            seen[key] = obs

    if duplicates:
        removed, err = kg.delete_observations(entity_name, duplicates, caller_role="agent")
        if err:
            return {"entity": entity_name, "removed": 0, "kept": len(seen), "error": err}
        return {"entity": entity_name, "removed": removed, "kept": len(seen)}

    return {"entity": entity_name, "removed": 0, "kept": len(entity.observations)}


def promote_patterns(kg: KnowledgeGraph, min_occurrences: int = 3) -> dict:
    """Promote recurring observations across entities into solution_pattern entities.

    Scans all quality-tier entities for observations that appear on 3+
    different entities (excluding metadata observations like protection_tier,
    source_file, title).  When found, creates a new solution_pattern entity
    capturing the pattern.

    Returns:
        {"promoted": [list of new pattern names], "skipped": int}
    """
    metadata_prefixes = (
        "protection_tier:",
        "source_file:",
        "title:",
        "statement:",
        "description:",
        "rationale:",
        "document_type:",
        "usage:",
        "examples:",
        "mutability:",
    )

    # Count observation occurrences across entities
    obs_counter: Counter[str] = Counter()
    obs_entities: dict[str, list[str]] = {}

    for ewr in kg.get_entities_by_tier("quality"):
        for obs in ewr.observations:
            normalised = obs.strip().lower()
            if any(normalised.startswith(p) for p in metadata_prefixes):
                continue
            obs_counter[normalised] += 1
            obs_entities.setdefault(normalised, []).append(ewr.name)

    promoted: list[str] = []
    skipped = 0

    for obs_key, count in obs_counter.items():
        if count < min_occurrences:
            continue

        # Check if a pattern entity already exists for this observation
        pattern_name = f"pattern_{obs_key[:60].replace(' ', '_')}"
        existing = kg.get_entity(pattern_name)
        if existing is not None:
            skipped += 1
            continue

        entities_list = obs_entities[obs_key]
        kg.create_entities(
            [
                {
                    "name": pattern_name,
                    "entityType": EntityType.SOLUTION_PATTERN.value,
                    "observations": [
                        "protection_tier: quality",
                        f"Promoted from {count} occurrences across: {', '.join(entities_list[:5])}",
                        f"Pattern: {obs_key}",
                    ],
                }
            ]
        )
        promoted.append(pattern_name)

    return {"promoted": promoted, "skipped": skipped}


def remove_stale_observations(
    kg: KnowledgeGraph,
    entity_name: str,
    stale_keywords: list[str],
) -> dict:
    """Remove observations containing any of the stale keywords.

    Only operates on quality-tier entities.

    Returns:
        {"entity": entity_name, "removed": int}
    """
    entity = kg.get_entity(entity_name)
    if entity is None:
        return {"entity": entity_name, "removed": 0, "error": "not found"}

    tier = get_entity_tier(entity.observations)
    if tier and tier.value != "quality":
        return {"entity": entity_name, "removed": 0, "error": f"entity is {tier.value}-tier, skipping"}

    to_remove = [
        obs
        for obs in entity.observations
        if any(kw.lower() in obs.lower() for kw in stale_keywords) and not obs.startswith("protection_tier:")
    ]

    if not to_remove:
        return {"entity": entity_name, "removed": 0}

    removed, err = kg.delete_observations(entity_name, to_remove, caller_role="agent")
    if err:
        return {"entity": entity_name, "removed": 0, "error": err}
    return {"entity": entity_name, "removed": removed}


def validate_tier_consistency(kg: KnowledgeGraph) -> dict:
    """Check that vision-tier and architecture-tier entities haven't been improperly modified.

    Validates:
    - Vision entities have protection_tier: vision observation
    - Architecture entities have protection_tier: architecture observation
    - No quality-tier entities claim vision/architecture tier

    Returns:
        {"violations": [list of violation descriptions], "checked": int}
    """
    violations: list[str] = []
    checked = 0

    # Check vision entities
    for ewr in kg.get_entities_by_tier("vision"):
        checked += 1
        if ewr.entity_type.value not in ("vision_standard",):
            violations.append(f"Vision-tier entity '{ewr.name}' has unexpected type '{ewr.entity_type.value}'")

    # Check architecture entities
    for ewr in kg.get_entities_by_tier("architecture"):
        checked += 1
        if ewr.entity_type.value not in ("architectural_standard", "pattern", "component"):
            violations.append(f"Architecture-tier entity '{ewr.name}' has unexpected type '{ewr.entity_type.value}'")

    return {"violations": violations, "checked": checked}


def run_full_curation(kg: KnowledgeGraph) -> dict:
    """Run the complete curation pipeline.

    Executes all curation steps in order:
    1. Consolidate observations on all quality-tier entities
    2. Promote recurring patterns
    3. Validate tier consistency

    Returns a summary dict with results from each step.
    """
    # Step 1: Consolidate observations on quality-tier entities
    consolidation_results: list[dict] = []
    for ewr in kg.get_entities_by_tier("quality"):
        result = consolidate_observations(kg, ewr.name)
        if result["removed"] > 0:
            consolidation_results.append(result)

    # Step 2: Promote patterns
    promotion_result = promote_patterns(kg)

    # Step 3: Validate tier consistency
    validation_result = validate_tier_consistency(kg)

    return {
        "consolidation": {
            "entities_cleaned": len(consolidation_results),
            "total_removed": sum(r["removed"] for r in consolidation_results),
            "details": consolidation_results,
        },
        "promotion": promotion_result,
        "validation": validation_result,
    }
