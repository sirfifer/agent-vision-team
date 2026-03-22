"""Data migration from legacy storage formats to SurrealDB.

Each migrate_* function reads from the old format, writes to SurrealDB,
and renames the old file to .bak. Safe to call multiple times (skips
if .bak already exists or source file is missing).
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from surrealdb import Surreal


def _sanitize_record_id(name: str) -> str:
    """Convert an entity name to a safe SurrealDB record ID.

    Replaces non-alphanumeric chars with underscores, lowercases.
    """
    return re.sub(r"[^a-zA-Z0-9_]", "_", name).lower().strip("_")


def migrate_kg(db: Surreal, jsonl_path: str = ".avt/knowledge-graph.jsonl") -> dict:
    """Migrate JSONL knowledge graph to SurrealDB.

    Returns: {"entities": count, "relations": count, "skipped": bool}
    """
    path = Path(jsonl_path)
    if not path.exists():
        return {"entities": 0, "relations": 0, "skipped": True}
    if path.with_suffix(".jsonl.bak").exists():
        return {"entities": 0, "relations": 0, "skipped": True}

    entities_created = 0
    relations_created = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            record_type = record.get("type")

            if record_type == "entity":
                name = record["name"]
                rid = _sanitize_record_id(name)
                entity_type = record.get("entityType", "component")
                observations = record.get("observations", [])

                # Extract protection_tier from observations
                protection_tier = None
                for obs in observations:
                    if obs.startswith("protection_tier: "):
                        protection_tier = obs.split("protection_tier: ", 1)[1].strip()
                        break

                db.query(
                    "CREATE type::thing('entity', $rid) SET "
                    "name = $name, "
                    "entity_type = $etype, "
                    "observations = $obs, "
                    "protection_tier = $tier, "
                    "created_at = time::now()",
                    {
                        "rid": rid,
                        "name": name,
                        "etype": entity_type,
                        "obs": observations,
                        "tier": protection_tier,
                    },
                )
                entities_created += 1

            elif record_type == "relation":
                from_name = record["from"]
                to_name = record["to"]
                rel_type = record["relationType"]
                from_rid = _sanitize_record_id(from_name)
                to_rid = _sanitize_record_id(to_name)

                db.query(
                    "LET $from = type::thing('entity', $from_rid); "
                    "LET $to = type::thing('entity', $to_rid); "
                    "RELATE $from->relates_to->$to "
                    "SET relation_type = $rtype, created_at = time::now()",
                    {"from_rid": from_rid, "to_rid": to_rid, "rtype": rel_type},
                )
                relations_created += 1

    # Rename old file to .bak
    path.rename(path.with_suffix(".jsonl.bak"))

    return {
        "entities": entities_created,
        "relations": relations_created,
        "skipped": False,
    }


def migrate_governance(
    db: Surreal, sqlite_path: str = ".avt/governance.db"
) -> dict:
    """Migrate governance SQLite database to SurrealDB.

    Returns: {"decisions": count, "reviews": count, ...}
    """
    path = Path(sqlite_path)
    if not path.exists():
        return {"skipped": True}
    bak = path.with_suffix(".db.bak")
    if bak.exists():
        return {"skipped": True}

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    counts: dict[str, int] = {}

    # Migrate each table
    for table, surreal_table in [
        ("decisions", "decision"),
        ("reviews", "review"),
        ("governed_tasks", "governed_task"),
        ("task_reviews", "task_review"),
        ("holistic_reviews", "holistic_review"),
        ("token_usage", "token_usage"),
    ]:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            counts[surreal_table] = 0
            continue

        for row in rows:
            row_dict = dict(row)
            # Parse JSON-serialized columns
            for key in ("findings", "standards_verified", "vision_references",
                        "components_affected", "alternatives_considered",
                        "task_ids", "task_subjects", "metric_values", "context"):
                if key in row_dict and isinstance(row_dict[key], str):
                    try:
                        row_dict[key] = json.loads(row_dict[key])
                    except (json.JSONDecodeError, TypeError):
                        pass

            # Build SET clause from row data
            sets = ", ".join(f"{k} = ${k}" for k in row_dict.keys())
            db.query(
                f"CREATE {surreal_table} SET {sets}",
                row_dict,
            )

        counts[surreal_table] = len(rows)

    conn.close()
    path.rename(bak)
    return counts


def migrate_trust_engine(
    db: Surreal, sqlite_path: str = ".avt/trust-engine.db"
) -> dict:
    """Migrate quality/trust engine SQLite to SurrealDB.

    Returns: {"findings": count, "dismissals": count}
    """
    path = Path(sqlite_path)
    if not path.exists():
        return {"skipped": True}
    bak = path.with_suffix(".db.bak")
    if bak.exists():
        return {"skipped": True}

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    counts: dict[str, int] = {}

    for table, surreal_table in [
        ("findings", "finding"),
        ("dismissal_history", "dismissal_history"),
    ]:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            counts[surreal_table] = 0
            continue

        for row in rows:
            row_dict = dict(row)
            sets = ", ".join(f"{k} = ${k}" for k in row_dict.keys())
            db.query(f"CREATE {surreal_table} SET {sets}", row_dict)

        counts[surreal_table] = len(rows)

    conn.close()
    path.rename(bak)
    return counts
