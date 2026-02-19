"""Client for reading Knowledge Graph data directly from JSONL storage."""

import json
import time
from pathlib import Path
from typing import Optional

DEFAULT_KG_PATH = Path(".avt/knowledge-graph.jsonl")

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300


class KGClient:
    """Reads KG JSONL file directly (same filesystem, no network needed)."""

    def __init__(self, kg_path: Optional[Path] = None):
        self.kg_path = kg_path or DEFAULT_KG_PATH
        self._cache: dict[str, tuple[float, list[dict]]] = {}

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

    def _load_entities(self) -> list[dict]:
        if not self.kg_path.exists():
            return []
        entities = []
        with open(self.kg_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("type") == "entity":
                    entities.append(record)
        return entities

    def _load_relations(self) -> list[dict]:
        if not self.kg_path.exists():
            return []
        relations = []
        with open(self.kg_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("type") == "relation":
                    relations.append(record)
        return relations

    def get_vision_standards(self) -> list[dict]:
        """Get all vision-tier entities (cached, 5 min TTL)."""
        cached = self._get_cached("vision_standards")
        if cached is not None:
            return cached
        entities = self._load_entities()
        result = [
            e
            for e in entities
            if e.get("entityType") == "vision_standard"
            or any("vision" in obs.lower() for obs in e.get("observations", []))
        ]
        self._set_cached("vision_standards", result)
        return result

    def get_architecture_entities(self) -> list[dict]:
        """Get all architecture-tier entities (cached, 5 min TTL)."""
        cached = self._get_cached("architecture_entities")
        if cached is not None:
            return cached
        entities = self._load_entities()
        result = [e for e in entities if e.get("entityType") in ("architectural_standard", "pattern", "component")]
        self._set_cached("architecture_entities", result)
        return result

    def search_entities(self, names: list[str]) -> list[dict]:
        """Search for entities matching any of the given names."""
        entities = self._load_entities()
        results = []
        for entity in entities:
            entity_name = entity.get("name", "").lower()
            observations = " ".join(entity.get("observations", [])).lower()
            for name in names:
                if name.lower() in entity_name or name.lower() in observations:
                    results.append(entity)
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
        """Append a governance observation to the KG JSONL file."""
        self.kg_path.parent.mkdir(parents=True, exist_ok=True)
        observations = [
            f"Governance decision by {agent}: {summary}",
            f"Verdict: {verdict}",
        ]
        if intent:
            observations.append(f"Intent: {intent}")
        if expected_outcome:
            observations.append(f"Expected outcome: {expected_outcome}")
        record = {
            "type": "entity",
            "name": f"governance_decision_{decision_id}",
            "entityType": "governance_decision",
            "observations": observations,
        }
        with open(self.kg_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
