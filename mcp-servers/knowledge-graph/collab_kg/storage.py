"""JSONL persistence for the knowledge graph."""

import json
from pathlib import Path

from .models import Entity, Relation


class JSONLStorage:
    """Handles loading and saving the knowledge graph to a JSONL file."""

    def __init__(self, filepath: str = ".avt/knowledge-graph.jsonl"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> tuple[dict[str, Entity], list[Relation]]:
        """Load entities and relations from JSONL file."""
        entities: dict[str, Entity] = {}
        relations: list[Relation] = []

        if not self.filepath.exists():
            return entities, relations

        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                record_type = record.get("type")

                if record_type == "entity":
                    entity = Entity(
                        name=record["name"],
                        entityType=record["entityType"],
                        observations=record.get("observations", []),
                    )
                    entities[entity.name] = entity
                elif record_type == "relation":
                    relation = Relation(
                        **{"from": record["from"]},
                        to=record["to"],
                        relationType=record["relationType"],
                    )
                    relations.append(relation)

        return entities, relations

    def append_entity(self, entity: Entity) -> None:
        """Append a single entity to the JSONL file."""
        with open(self.filepath, "a", encoding="utf-8") as f:
            record = {
                "type": "entity",
                "name": entity.name,
                "entityType": entity.entity_type.value,
                "observations": entity.observations,
            }
            f.write(json.dumps(record) + "\n")

    def append_relation(self, relation: Relation) -> None:
        """Append a single relation to the JSONL file."""
        with open(self.filepath, "a", encoding="utf-8") as f:
            record = {
                "type": "relation",
                "from": relation.from_entity,
                "to": relation.to,
                "relationType": relation.relation_type,
            }
            f.write(json.dumps(record) + "\n")

    def compact(self, entities: dict[str, Entity], relations: list[Relation]) -> None:
        """Rewrite the JSONL file with only current state (removes deleted items)."""
        # Write to temporary file first
        temp_path = self.filepath.with_suffix(".jsonl.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            # Write all entities
            for entity in entities.values():
                record = {
                    "type": "entity",
                    "name": entity.name,
                    "entityType": entity.entity_type.value,
                    "observations": entity.observations,
                }
                f.write(json.dumps(record) + "\n")

            # Write all relations
            for relation in relations:
                record = {
                    "type": "relation",
                    "from": relation.from_entity,
                    "to": relation.to,
                    "relationType": relation.relation_type,
                }
                f.write(json.dumps(record) + "\n")

        # Replace original file with compacted version
        temp_path.replace(self.filepath)
