"""SurrealDB-backed client for reading Knowledge Graph data.

Replaces KGClient (JSONL direct file access) with SurrealDB queries,
eliminating the compaction race condition documented in MEMORY.md.
"""

import time
from pathlib import Path
from typing import Optional

from surrealdb import Surreal

DEFAULT_DB_PATH = Path(".avt/avt.db")
_NAMESPACE = "avt"
_DATABASE = "main"

# Cache TTL in seconds (5 minutes, matching the JSONL KGClient)
_CACHE_TTL = 300


class SurrealKGClient:
    """Reads KG data from SurrealDB (same embedded DB as the governance store)."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._db: Optional[Surreal] = None
        self._cache: dict[str, tuple[float, list[dict]]] = {}

    def _get_db(self) -> Surreal:
        if self._db is None:
            self._db = Surreal(f"surrealkv://{self.db_path}")
            self._db.use(_NAMESPACE, _DATABASE)
        return self._db

    def invalidate_cache(self) -> None:
        """Explicitly clear all cached data."""
        self._cache.clear()

    def _get_cached(self, key: str) -> Optional[list[dict]]:
        """Return cached value if present and not expired."""
        if key in self._cache:
            ts, data = self._cache[key]
            if time.monotonic() - ts < _CACHE_TTL:
                return data
            del self._cache[key]
        return None

    def _set_cached(self, key: str, data: list[dict]) -> None:
        """Store data in cache with current timestamp."""
        self._cache[key] = (time.monotonic(), data)

    def get_vision_standards(self) -> list[dict]:
        """Get all vision-tier entities (cached, 5 min TTL)."""
        cached = self._get_cached("vision_standards")
        if cached is not None:
            return cached

        db = self._get_db()
        result = db.query(
            """SELECT * FROM entity
               WHERE protection_tier = 'vision'
               OR entity_type = 'vision_standard'"""
        )
        rows = _extract_rows(result)
        # Normalise to the dict format the governance reviewer expects
        entities = [_normalise_entity(r) for r in rows]
        self._set_cached("vision_standards", entities)
        return entities

    def get_architecture_entities(self) -> list[dict]:
        """Get all architecture-tier entities (cached, 5 min TTL)."""
        cached = self._get_cached("architecture_entities")
        if cached is not None:
            return cached

        db = self._get_db()
        result = db.query(
            """SELECT * FROM entity
               WHERE entity_type IN ['architectural_standard', 'pattern', 'component']"""
        )
        rows = _extract_rows(result)
        entities = [_normalise_entity(r) for r in rows]
        self._set_cached("architecture_entities", entities)
        return entities

    def search_entities(self, names: list[str]) -> list[dict]:
        """Search for entities matching any of the given names.

        Uses a parameterised query with string::lowercase for case-insensitive
        matching against entity name and observations.
        """
        if not names:
            return []

        db = self._get_db()
        # SurrealDB does not support parameterised LIKE patterns well with
        # arrays, so we query all entities and filter in Python (same approach
        # as the JSONL client). The entity table is small enough for this.
        result = db.query("SELECT * FROM entity")
        all_rows = _extract_rows(result)

        results = []
        lower_names = [n.lower() for n in names]
        for row in all_rows:
            entity_name = (row.get("name") or "").lower()
            observations = row.get("observations") or []
            obs_text = " ".join(str(o) for o in observations).lower()
            for name in lower_names:
                if name in entity_name or name in obs_text:
                    results.append(_normalise_entity(row))
                    break
        return results

    def record_decision(
        self,
        decision_id: str,
        summary: str,
        verdict: str,
        agent: str,
        intent: str = "",
        expected_outcome: str = "",
    ) -> None:
        """Write a governance decision entity to the KG via SurrealDB.

        Unlike the JSONL KGClient, this goes through the database so there
        is no compaction race condition.
        """
        db = self._get_db()
        observations = [
            f"Governance decision by {agent}: {summary}",
            f"Verdict: {verdict}",
        ]
        if intent:
            observations.append(f"Intent: {intent}")
        if expected_outcome:
            observations.append(f"Expected outcome: {expected_outcome}")

        rid = f"governance_decision_{decision_id}"
        db.query(
            """UPSERT type::thing('entity', $rid) SET
                name = $name,
                entity_type = 'governance_decision',
                observations = $observations
            """,
            {
                "rid": rid,
                "name": rid,
                "observations": observations,
            },
        )
        # Invalidate cache since we just wrote
        self.invalidate_cache()


# =============================================================================
# Helpers
# =============================================================================


def _extract_rows(result) -> list[dict]:
    """Extract row dicts from SurrealDB query result (same logic as surreal_store)."""
    if result is None:
        return []
    if isinstance(result, list):
        if not result:
            return []
        first = result[0]
        if isinstance(first, dict) and "result" in first:
            inner = first["result"]
            return inner if isinstance(inner, list) else []
        if isinstance(first, dict):
            return result
    if isinstance(result, dict):
        inner = result.get("result", [])
        return inner if isinstance(inner, list) else []
    return []


def _normalise_entity(row: dict) -> dict:
    """Normalise a SurrealDB entity row to the dict format expected by the reviewer.

    The governance reviewer and KGClient consumers expect dicts with keys:
    name, entityType, observations, and optionally protection_tier.
    SurrealDB stores entity_type (snake_case field) but the JSONL format
    used camelCase entityType. We provide both for compatibility.
    """
    rid = row.get("id")
    name = row.get("name", "")
    if not name and rid:
        name = str(rid).split(":", 1)[-1] if ":" in str(rid) else str(rid)

    entity_type = row.get("entity_type") or row.get("entityType") or ""
    observations = row.get("observations") or []

    return {
        "name": name,
        "entityType": entity_type,
        "entity_type": entity_type,
        "observations": observations,
        "protection_tier": row.get("protection_tier", ""),
    }
