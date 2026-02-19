"""Data models for the Knowledge Graph."""

from enum import Enum

from pydantic import BaseModel, Field


class ProtectionTier(str, Enum):
    VISION = "vision"
    ARCHITECTURE = "architecture"
    QUALITY = "quality"


class Mutability(str, Enum):
    HUMAN_ONLY = "human_only"
    HUMAN_APPROVED_ONLY = "human_approved_only"
    AUTOMATED = "automated"


class EntityType(str, Enum):
    COMPONENT = "component"
    VISION_STANDARD = "vision_standard"
    ARCHITECTURAL_STANDARD = "architectural_standard"
    PATTERN = "pattern"
    PROBLEM = "problem"
    SOLUTION_PATTERN = "solution_pattern"
    GOVERNANCE_DECISION = "governance_decision"


class Relation(BaseModel):
    from_entity: str = Field(alias="from")
    to: str
    relation_type: str = Field(alias="relationType")

    model_config = {"populate_by_name": True}


class Entity(BaseModel):
    name: str
    entity_type: EntityType = Field(alias="entityType")
    observations: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class EntityWithRelations(Entity):
    relations: list[Relation] = Field(default_factory=list)
