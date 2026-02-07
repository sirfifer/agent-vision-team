"""Client for reading Knowledge Graph data directly from JSONL storage."""

import json
import sys
from pathlib import Path
from typing import Optional

# Import metadata helpers from the KG server package.
# The KG server is a sibling directory; add it to sys.path if needed.
_KG_LIB = Path(__file__).resolve().parent.parent.parent / "knowledge-graph"
if str(_KG_LIB) not in sys.path:
    sys.path.insert(0, str(_KG_LIB))

from collab_kg.metadata import (  # noqa: E402
    get_intent,
    get_outcome_metrics,
    get_vision_alignments,
    get_metadata_completeness,
)


DEFAULT_KG_PATH = Path(".avt/knowledge-graph.jsonl")


class KGClient:
    """Reads KG JSONL file directly (same filesystem, no network needed)."""

    def __init__(self, kg_path: Optional[Path] = None):
        self.kg_path = kg_path or DEFAULT_KG_PATH

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
        """Get all vision-tier entities."""
        entities = self._load_entities()
        return [
            e
            for e in entities
            if e.get("entityType") == "vision_standard"
            or any("vision" in obs.lower() for obs in e.get("observations", []))
        ]

    def get_architecture_entities(self) -> list[dict]:
        """Get all architecture-tier entities."""
        entities = self._load_entities()
        return [
            e
            for e in entities
            if e.get("entityType")
            in ("architectural_standard", "pattern", "component")
        ]

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

    def get_entity_with_metadata(self, entity_name: str) -> Optional[dict]:
        """Fetch an entity and parse its structured intent metadata.

        Returns a dict with the raw entity fields plus parsed metadata:
        ``intent``, ``metrics``, ``vision_alignments``, ``completeness``.
        Returns None if entity not found.
        """
        entities = self._load_entities()
        for e in entities:
            if e.get("name") == entity_name:
                obs = e.get("observations", [])
                return {
                    **e,
                    "intent": get_intent(obs),
                    "metrics": get_outcome_metrics(obs),
                    "vision_alignments": get_vision_alignments(obs),
                    "completeness": get_metadata_completeness(obs),
                }
        return None

    def get_entities_serving_vision(self, vision_name: str) -> list[dict]:
        """Find architecture entities that declare alignment to a vision standard.

        Scans ``vision_alignment:`` observations and ``serves_vision`` relations.
        """
        entities = self._load_entities()
        relations = self._load_relations()

        # Collect entity names linked via serves_vision relation
        related_names: set[str] = set()
        for r in relations:
            if r.get("relationType") == "serves_vision" and r.get("to") == vision_name:
                related_names.add(r.get("from", ""))

        results = []
        for e in entities:
            name = e.get("name", "")
            obs = e.get("observations", [])
            # Check observation-level alignment
            has_alignment = any(
                o.startswith("vision_alignment: ") and o.split("|")[0].removeprefix("vision_alignment: ").strip() == vision_name
                for o in obs
            )
            if has_alignment or name in related_names:
                results.append({
                    **e,
                    "intent": get_intent(obs),
                    "metrics": get_outcome_metrics(obs),
                    "vision_alignments": get_vision_alignments(obs),
                    "completeness": get_metadata_completeness(obs),
                })
        return results

    def record_decision(
        self, decision_id: str, summary: str, verdict: str, agent: str
    ) -> None:
        """Append a governance observation to the KG JSONL file."""
        self.kg_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "type": "entity",
            "name": f"governance_decision_{decision_id}",
            "entityType": "solution_pattern",
            "observations": [
                f"Governance decision by {agent}: {summary}",
                f"Verdict: {verdict}",
            ],
        }
        with open(self.kg_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
