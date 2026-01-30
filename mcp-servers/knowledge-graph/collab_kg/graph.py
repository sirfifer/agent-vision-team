"""Graph operations — entity, relation, and observation management."""

from typing import Optional, Tuple

from .models import Entity, EntityWithRelations, Relation, EntityType
from .tier_protection import get_entity_tier, validate_write_access


class KnowledgeGraph:
    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relations: list[Relation] = []

    def create_entities(self, entities: list[dict]) -> int:
        created = 0
        for entry in entities:
            entity = Entity(
                name=entry["name"],
                entityType=entry["entityType"],
                observations=entry.get("observations", []),
            )
            self._entities[entity.name] = entity
            created += 1
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
            created += 1
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
        return deleted, None

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
