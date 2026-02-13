"""Archival file generation from KG data.

Syncs important KG entries to human-readable `.avt/memory/*.md` files.
This is the "Step 6" from the KG Librarian curation protocol, extracted
into callable functions.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .graph import KnowledgeGraph


def sync_archival_files(
    kg: KnowledgeGraph,
    memory_dir: Path,
) -> dict:
    """Sync KG content to all four archival memory files.

    Writes:
    - architectural-decisions.md: governance_decision entities
    - troubleshooting-log.md: problem entities
    - solution-patterns.md: solution_pattern entities
    - research-findings.md: entities with research-related observations

    Returns:
        {"files_written": int, "details": {filename: entry_count}}
    """
    memory_dir.mkdir(parents=True, exist_ok=True)

    details = {}

    details["architectural-decisions.md"] = _write_architectural_decisions(kg, memory_dir)
    details["troubleshooting-log.md"] = _write_troubleshooting_log(kg, memory_dir)
    details["solution-patterns.md"] = _write_solution_patterns(kg, memory_dir)
    details["research-findings.md"] = _write_research_findings(kg, memory_dir)

    files_written = sum(1 for count in details.values() if count > 0)

    return {"files_written": files_written, "details": details}


def _write_architectural_decisions(kg: KnowledgeGraph, memory_dir: Path) -> int:
    """Write governance decisions to architectural-decisions.md."""
    decisions = kg.search_nodes("governance decision")
    # Also include entities explicitly typed as governance_decision
    gov_entities = [
        ewr for ewr in _all_entities_by_type(kg, "governance_decision")
        if ewr.name not in {d.name for d in decisions}
    ]
    all_entries = list(decisions) + list(gov_entities)

    lines = [
        "# Architectural Decisions",
        "",
        f"*Auto-generated from KG on {_now()}*",
        "",
    ]

    if not all_entries:
        lines.append("No decisions recorded yet.")
    else:
        for entry in all_entries:
            lines.append(f"## {entry.name}")
            lines.append("")
            for obs in entry.observations:
                if obs.startswith("protection_tier:"):
                    continue
                if obs.startswith("Intent:"):
                    lines.append(f"- **Intent**: {obs[7:].strip()}")
                elif obs.startswith("Expected outcome:"):
                    lines.append(f"- **Expected Outcome**: {obs[17:].strip()}")
                else:
                    lines.append(f"- {obs}")
            lines.append("")

    (memory_dir / "architectural-decisions.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return len(all_entries)


def _write_troubleshooting_log(kg: KnowledgeGraph, memory_dir: Path) -> int:
    """Write problem entities to troubleshooting-log.md."""
    problems = _all_entities_by_type(kg, "problem")

    lines = [
        "# Troubleshooting Log",
        "",
        f"*Auto-generated from KG on {_now()}*",
        "",
    ]

    if not problems:
        lines.append("No entries yet.")
    else:
        for entry in problems:
            lines.append(f"## {entry.name}")
            lines.append("")
            for obs in entry.observations:
                if obs.startswith("protection_tier:"):
                    continue
                lines.append(f"- {obs}")
            lines.append("")

    (memory_dir / "troubleshooting-log.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return len(problems)


def _write_solution_patterns(kg: KnowledgeGraph, memory_dir: Path) -> int:
    """Write solution_pattern entities to solution-patterns.md."""
    patterns = _all_entities_by_type(kg, "solution_pattern")

    lines = [
        "# Solution Patterns",
        "",
        f"*Auto-generated from KG on {_now()}*",
        "",
    ]

    if not patterns:
        lines.append("No patterns promoted yet.")
    else:
        for entry in patterns:
            lines.append(f"## {entry.name}")
            lines.append("")
            for obs in entry.observations:
                if obs.startswith("protection_tier:"):
                    continue
                lines.append(f"- {obs}")
            lines.append("")

    (memory_dir / "solution-patterns.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return len(patterns)


def _write_research_findings(kg: KnowledgeGraph, memory_dir: Path) -> int:
    """Write research-related entries to research-findings.md."""
    research = kg.search_nodes("research")
    # Deduplicate by name
    seen = set()
    unique = []
    for entry in research:
        if entry.name not in seen:
            seen.add(entry.name)
            unique.append(entry)

    lines = [
        "# Research Findings",
        "",
        f"*Auto-generated from KG on {_now()}*",
        "",
    ]

    if not unique:
        lines.append("No findings recorded yet.")
    else:
        for entry in unique:
            lines.append(f"## {entry.name}")
            lines.append("")
            for obs in entry.observations:
                if obs.startswith("protection_tier:"):
                    continue
                lines.append(f"- {obs}")
            lines.append("")

    (memory_dir / "research-findings.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return len(unique)


def _all_entities_by_type(kg: KnowledgeGraph, entity_type: str):
    """Get all entities matching a specific entityType by scanning the KG."""
    results = []
    for name, entity in kg._entities.items():
        if entity.entity_type.value == entity_type:
            relations = [
                r for r in kg._relations
                if r.from_entity == name or r.to == name
            ]
            from .models import EntityWithRelations
            results.append(EntityWithRelations(
                name=entity.name,
                entityType=entity.entity_type,
                observations=entity.observations,
                relations=relations,
            ))
    return results


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
