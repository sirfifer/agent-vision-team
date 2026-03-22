"""SurrealDB-backed Knowledge Graph implementation.

Drop-in replacement for KnowledgeGraph (graph.py) that stores entities,
relations, and observations in SurrealDB instead of JSONL + in-memory dicts.

Activated via the AVT_STORAGE_BACKEND=surreal environment variable.
"""

import os
import re
from typing import Optional, Tuple

from surrealdb import Surreal

from .models import EntityWithRelations, Relation
from .tier_protection import get_entity_tier_from_field, validate_write_access


def _name_to_rid(name: str) -> str:
    """Convert an entity name to a valid SurrealDB record ID segment.

    Example: "My Service (v2)" -> "my_service__v2_"
    """
    return re.sub(r"[^a-zA-Z0-9_]", "_", name).lower().strip("_")


def _extract_protection_tier(observations: list[str]) -> Optional[str]:
    """Extract protection_tier value from observations list, if present."""
    for obs in observations:
        if obs.startswith("protection_tier: "):
            return obs.split("protection_tier: ", 1)[1].strip()
    return None


class SurrealKnowledgeGraph:
    """Knowledge Graph backed by SurrealDB (embedded surrealkv mode).

    Provides the same public interface as KnowledgeGraph in graph.py.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            db_path = os.environ.get(
                "AVT_SURREAL_DB_PATH",
                ".avt/surreal_kg",
            )
        self._db_path = db_path
        self._db = Surreal(f"surrealkv://{db_path}")
        # Embedded mode (surrealkv://) does not require signin.
        self._db.use("avt", "kg")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        self._db.query(
            """
            DEFINE TABLE IF NOT EXISTS entity SCHEMAFULL;
            DEFINE FIELD IF NOT EXISTS name ON entity TYPE string;
            DEFINE FIELD IF NOT EXISTS entity_type ON entity TYPE string;
            DEFINE FIELD IF NOT EXISTS observations ON entity TYPE array;
            DEFINE FIELD IF NOT EXISTS observations.* ON entity TYPE string;
            DEFINE FIELD IF NOT EXISTS protection_tier ON entity TYPE option<string>;
            DEFINE INDEX IF NOT EXISTS idx_entity_name ON entity FIELDS name UNIQUE;
            DEFINE INDEX IF NOT EXISTS idx_entity_type ON entity FIELDS entity_type;
            DEFINE INDEX IF NOT EXISTS idx_entity_tier ON entity FIELDS protection_tier;

            DEFINE TABLE IF NOT EXISTS relates_to SCHEMAFULL TYPE RELATION
                FROM entity TO entity;
            DEFINE FIELD IF NOT EXISTS relation_type ON relates_to TYPE string;
            """
        )

    # ------------------------------------------------------------------
    # Entity CRUD
    # ------------------------------------------------------------------

    def create_entities(self, entities: list[dict]) -> int:
        """Create entities in the graph. Returns count of entities created."""
        created = 0
        for entry in entities:
            name = entry["name"]
            entity_type = entry["entityType"]
            observations = entry.get("observations", [])
            protection_tier = _extract_protection_tier(observations)
            rid = _name_to_rid(name)

            self._db.query(
                """
                CREATE type::thing('entity', $rid) SET
                    name = $name,
                    entity_type = $entity_type,
                    observations = $observations,
                    protection_tier = $protection_tier;
                """,
                {
                    "rid": rid,
                    "name": name,
                    "entity_type": entity_type,
                    "observations": observations,
                    "protection_tier": protection_tier,
                },
            )
            created += 1
        return created

    def create_relations(self, relations: list[dict]) -> int:
        """Create relations between entities. Returns count created."""
        created = 0
        for entry in relations:
            from_name = entry["from"]
            to_name = entry["to"]
            relation_type = entry["relationType"]
            from_rid = _name_to_rid(from_name)
            to_rid = _name_to_rid(to_name)

            self._db.query(
                """
                LET $from = type::thing('entity', $from_rid);
                LET $to = type::thing('entity', $to_rid);
                RELATE $from->relates_to->$to SET
                    relation_type = $relation_type;
                """,
                {
                    "from_rid": from_rid,
                    "to_rid": to_rid,
                    "relation_type": relation_type,
                },
            )
            created += 1
        return created

    # ------------------------------------------------------------------
    # Observation management
    # ------------------------------------------------------------------

    def add_observations(
        self,
        entity_name: str,
        observations: list[str],
        caller_role: str = "agent",
        change_approved: bool = False,
    ) -> Tuple[int, Optional[str]]:
        """Add observations to an entity. Respects tier protection."""
        entity_row = self._fetch_entity_row(entity_name)
        if entity_row is None:
            return 0, f"Entity '{entity_name}' not found."

        tier = get_entity_tier_from_field(entity_row.get("protection_tier"))
        allowed, reason = validate_write_access(tier, caller_role, change_approved)
        if not allowed:
            return 0, reason

        rid = _name_to_rid(entity_name)

        # Check if any new observation sets a protection tier
        new_tier = _extract_protection_tier(observations)

        for obs in observations:
            self._db.query(
                """
                UPDATE type::thing('entity', $rid) SET
                    observations += [$obs];
                """,
                {"rid": rid, "obs": obs},
            )

        # Update protection_tier field if a new tier observation was added
        if new_tier is not None:
            self._db.query(
                """
                UPDATE type::thing('entity', $rid) SET
                    protection_tier = $tier;
                """,
                {"rid": rid, "tier": new_tier},
            )

        return len(observations), None

    def delete_observations(
        self,
        entity_name: str,
        observations: list[str],
        caller_role: str = "agent",
        change_approved: bool = False,
    ) -> Tuple[int, Optional[str]]:
        """Delete specific observations from an entity. Respects tier protection."""
        entity_row = self._fetch_entity_row(entity_name)
        if entity_row is None:
            return 0, f"Entity '{entity_name}' not found."

        tier = get_entity_tier_from_field(entity_row.get("protection_tier"))
        allowed, reason = validate_write_access(tier, caller_role, change_approved)
        if not allowed:
            return 0, reason

        current_obs: list[str] = entity_row.get("observations", [])
        deleted = 0
        new_obs = list(current_obs)
        for obs in observations:
            if obs in new_obs:
                new_obs.remove(obs)
                deleted += 1

        if deleted > 0:
            rid = _name_to_rid(entity_name)
            # Recalculate protection tier from remaining observations
            new_tier = _extract_protection_tier(new_obs)
            self._db.query(
                """
                UPDATE type::thing('entity', $rid) SET
                    observations = $obs,
                    protection_tier = $tier;
                """,
                {"rid": rid, "obs": new_obs, "tier": new_tier},
            )

        return deleted, None

    # ------------------------------------------------------------------
    # Entity deletion
    # ------------------------------------------------------------------

    def delete_entity(
        self,
        entity_name: str,
        caller_role: str = "agent",
    ) -> Tuple[bool, Optional[str]]:
        """Delete an entity entirely. Respects tier protection."""
        entity_row = self._fetch_entity_row(entity_name)
        if entity_row is None:
            return False, f"Entity '{entity_name}' not found."

        tier_str = entity_row.get("protection_tier")
        if tier_str in ("vision", "architecture") and caller_role != "human":
            return (
                False,
                f"Cannot delete {tier_str}-tier entity '{entity_name}' without human approval.",
            )

        rid = _name_to_rid(entity_name)

        # Delete relations involving this entity, then the entity itself
        self._db.query(
            """
            DELETE relates_to WHERE in = type::thing('entity', $rid)
                OR out = type::thing('entity', $rid);
            """,
            {"rid": rid},
        )
        self._db.query(
            """
            DELETE type::thing('entity', $rid);
            """,
            {"rid": rid},
        )
        return True, None

    def delete_relations(self, relations: list[dict]) -> int:
        """Delete specific relations."""
        deleted = 0
        for entry in relations:
            from_rid = _name_to_rid(entry["from"])
            to_rid = _name_to_rid(entry["to"])
            relation_type = entry["relationType"]

            self._db.query(
                """
                DELETE relates_to
                    WHERE in = type::thing('entity', $from_rid)
                      AND out = type::thing('entity', $to_rid)
                      AND relation_type = $relation_type;
                """,
                {
                    "from_rid": from_rid,
                    "to_rid": to_rid,
                    "relation_type": relation_type,
                },
            )
            deleted += 1
        return deleted

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def search_nodes(self, query: str) -> list[EntityWithRelations]:
        """Search for entities whose name or observations contain the query string.

        Uses Python-side filtering after fetching all entities, since SurrealDB
        array element text matching with parameterized queries is unreliable.
        """
        result = self._db.query("SELECT * FROM entity;")
        all_rows = self._extract_rows(result)
        query_lower = query.lower()
        matching = [
            r
            for r in all_rows
            if query_lower in r.get("name", "").lower()
            or any(query_lower in obs.lower() for obs in r.get("observations", []))
        ]
        return [self._row_to_entity_with_relations(r) for r in matching]

    def get_entity(self, name: str) -> Optional[EntityWithRelations]:
        """Get a specific entity with its observations and relations."""
        entity_row = self._fetch_entity_row(name)
        if entity_row is None:
            return None
        return self._row_to_entity_with_relations(entity_row)

    def get_entities_by_tier(self, tier: str) -> list[EntityWithRelations]:
        """Get all entities for a specific protection tier."""
        result = self._db.query(
            """
            SELECT * FROM entity WHERE protection_tier = $tier;
            """,
            {"tier": tier},
        )
        rows = self._extract_rows(result)
        return [self._row_to_entity_with_relations(r) for r in rows]

    def get_entities_by_type(self, entity_type: str) -> list[EntityWithRelations]:
        """Get all entities matching a specific entityType."""
        result = self._db.query(
            """
            SELECT * FROM entity WHERE entity_type = $entity_type;
            """,
            {"entity_type": entity_type},
        )
        rows = self._extract_rows(result)
        return [self._row_to_entity_with_relations(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_entity_row(self, name: str) -> Optional[dict]:
        """Fetch a single entity row by name. Returns None if not found."""
        result = self._db.query(
            """
            SELECT * FROM entity WHERE name = $name LIMIT 1;
            """,
            {"name": name},
        )
        rows = self._extract_rows(result)
        return rows[0] if rows else None

    def _fetch_relations_for(self, name: str) -> list[Relation]:
        """Fetch all relations where entity is source or target."""
        rid = _name_to_rid(name)
        result = self._db.query(
            """
            SELECT
                in.name AS from_name,
                out.name AS to_name,
                relation_type
            FROM relates_to
            WHERE in = type::thing('entity', $rid)
               OR out = type::thing('entity', $rid);
            """,
            {"rid": rid},
        )
        rows = self._extract_rows(result)
        relations = []
        for r in rows:
            from_name = r.get("from_name", "")
            to_name = r.get("to_name", "")
            rel_type = r.get("relation_type", "")
            if from_name and to_name and rel_type:
                relations.append(
                    Relation(
                        **{"from": from_name},
                        to=to_name,
                        relationType=rel_type,
                    )
                )
        return relations

    def _row_to_entity_with_relations(self, row: dict) -> EntityWithRelations:
        """Convert a SurrealDB entity row to EntityWithRelations model."""
        name = row["name"]
        relations = self._fetch_relations_for(name)
        return EntityWithRelations(
            name=name,
            entityType=row["entity_type"],
            observations=row.get("observations", []),
            relations=relations,
        )

    @staticmethod
    def _extract_rows(result) -> list[dict]:
        """Extract row dicts from a SurrealDB query result.

        In SDK v1.0.8 embedded mode, query() returns a flat list[dict]
        for SELECT/CREATE/UPDATE, or None for statements like RELATE/DELETE.
        """
        if result is None:
            return []

        if isinstance(result, list):
            # SDK v1.0.8 returns list[dict] directly for data queries
            return [item for item in result if isinstance(item, dict)]

        return []
