"""JSONL storage for knowledge graph persistence (stub)."""

import json
from pathlib import Path
from typing import Optional


class GraphStorage:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = Path(path) if path else None

    def save(self, entities: list[dict], relations: list[dict]) -> None:
        if self.path is None:
            return
        # TODO: Write entities and relations as JSONL
        with self.path.open("w") as f:
            for entity in entities:
                f.write(json.dumps({"type": "entity", **entity}) + "\n")
            for relation in relations:
                f.write(json.dumps({"type": "relation", **relation}) + "\n")

    def load(self) -> tuple[list[dict], list[dict]]:
        if self.path is None or not self.path.exists():
            return [], []
        entities = []
        relations = []
        with self.path.open() as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry.get("type") == "entity":
                    entry.pop("type")
                    entities.append(entry)
                elif entry.get("type") == "relation":
                    entry.pop("type")
                    relations.append(entry)
        return entities, relations
