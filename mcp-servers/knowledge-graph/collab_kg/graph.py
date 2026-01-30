"""Graph operations — entity, relation, and observation management."""

from typing import Optional, Tuple

from .models import Entity, EntityWithRelations, Relation, EntityType
from .tier_protection import get_entity_tier, validate_write_access
from .storage import JSONLStorage


class KnowledgeGraph:
    def __init__(self, storage_path: str = ".claude/collab/knowledge-graph.jsonl") -> None:
        self.storage = JSONLStorage(storage_path)
        self._entities: dict[str, Entity] = {}
        self._relations: list[Relation] = []
        self._load_from_storage()
        self._write_count = 0
        self._compaction_threshold = 1000  # Compact after 1000 writes

    def _load_from_storage(self) -> None:
        """Load entities and relations from JSONL storage on startup."""
        self._entities, self._relations = self.storage.load()

    def _maybe_compact(self) -> None:
        """Compact storage if write threshold is reached."""
        self._write_count += 1
        if self._write_count >= self._compaction_threshold:
            self.storage.compact(self._entities, self._relations)
            self._write_count = 0

    def create_entities(self, entities: list[dict]) -> int:
        created = 0
        for entry in entities:
            entity = Entity(
                name=entry["name"],
                entityType=entry["entityType"],
                observations=entry.get("observations", []),
            )
            self._entities[entity.name] = entity
            self.storage.append_entity(entity)
            created += 1
        self._maybe_compact()
        return created

    def create_relations(self, relations: list[dict]) -> int:
        created = 0
        for entry in relations:
            relation = Relation(
                **{"from": entry["from"]},
                to=entry["to"],
                relationType=entry["relationType"],
            )
            self._relations.append(relation)
            self.storage.append_relation(relation)
            created += 1
        self._maybe_compact()
        return created

    def add_observations(
        self,
        entity_name: str,
        observations: list[str],
        caller_role: str = "agent",
        change_approved: bool = False,
    ) -> Tuple[int, Optional[str]]:
        entity = self._entities.get(entity_name)
        if entity is None:
            return 0, f"Entity '{entity_name}' not found."

        tier = get_entity_tier(entity.observations)
        allowed, reason = validate_write_access(tier, caller_role, change_approved)
        if not allowed:
            return 0, reason

        entity.observations.extend(observations)
        # Re-persist the entity with updated observations
        self.storage.compact(self._entities, self._relations)
        return len(observations), None

    def delete_observations(
        self,
        entity_name: str,
        observations: list[str],
        caller_role: str = "agent",
        change_approved: bool = False,
    ) -> Tuple[int, Optional[str]]:
        entity = self._entities.get(entity_name)
        if entity is None:
            return 0, f"Entity '{entity_name}' not found."

        tier = get_entity_tier(entity.observations)
        allowed, reason = validate_write_access(tier, caller_role, change_approved)
        if not allowed:
            return 0, reason

        deleted = 0
        for obs in observations:
            if obs in entity.observations:
                entity.observations.remove(obs)
                deleted += 1

        # Re-persist after deletion
        if deleted > 0:
            self.storage.compact(self._entities, self._relations)
        return deleted, None

    def delete_entity(
        self,
        entity_name: str,
        caller_role: str = "agent",
    ) -> Tuple[bool, Optional[str]]:
        """Delete an entity entirely. Respects tier protection."""
        entity = self._entities.get(entity_name)
        if entity is None:
            return False, f"Entity '{entity_name}' not found."

        tier = get_entity_tier(entity.observations)
        # Only allow deletion of quality-tier entities, or human deleting anything
        if tier and tier.value in ["vision", "architecture"] and caller_role != "human":
            return False, f"Cannot delete {tier.value}-tier entity '{entity_name}' without human approval."

        # Delete the entity
        del self._entities[entity_name]

        # Also remove any relations involving this entity
        self._relations = [
            r for r in self._relations
            if r.from_entity != entity_name and r.to != entity_name
        ]

        # Re-persist
        self.storage.compact(self._entities, self._relations)
        return True, None

    def delete_relations(
        self,
        relations: list[dict],
    ) -> int:
        """Delete specific relations."""
        deleted = 0
        for entry in relations:
            from_entity = entry["from"]
            to_entity = entry["to"]
            relation_type = entry["relationType"]

            # Find and remove matching relation
            for i, rel in enumerate(self._relations):
                if (rel.from_entity == from_entity and
                    rel.to == to_entity and
                    rel.relation_type == relation_type):
                    self._relations.pop(i)
                    deleted += 1
                    break

        if deleted > 0:
            self.storage.compact(self._entities, self._relations)
        return deleted

    def search_nodes(self, query: str) -> list[EntityWithRelations]:
        results = []
        query_lower = query.lower()
        for entity in self._entities.values():
            if (
                query_lower in entity.name.lower()
                or any(query_lower in obs.lower() for obs in entity.observations)
            ):
                relations = [
                    r for r in self._relations
                    if r.from_entity == entity.name or r.to == entity.name
                ]
                results.append(
                    EntityWithRelations(
                        name=entity.name,
                        entityType=entity.entity_type,
                        observations=entity.observations,
                        relations=relations,
                    )
                )
        return results

    def get_entity(self, name: str) -> Optional[EntityWithRelations]:
        entity = self._entities.get(name)
        if entity is None:
            return None
        relations = [
            r for r in self._relations
            if r.from_entity == entity.name or r.to == entity.name
        ]
        return EntityWithRelations(
            name=entity.name,
            entityType=entity.entity_type,
            observations=entity.observations,
            relations=relations,
        )

    def get_entities_by_tier(self, tier: str) -> list[EntityWithRelations]:
        results = []
        for entity in self._entities.values():
            entity_tier = get_entity_tier(entity.observations)
            if entity_tier and entity_tier.value == tier:
                relations = [
                    r for r in self._relations
                    if r.from_entity == entity.name or r.to == entity.name
                ]
                results.append(
                    EntityWithRelations(
                        name=entity.name,
                        entityType=entity.entity_type,
                        observations=entity.observations,
                        relations=relations,
                    )
                )
        return results
