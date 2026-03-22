"""Smoke tests for the SurrealDB-backed Knowledge Graph.

These tests mirror the JSONL backend tests in test_server.py to verify
that both backends produce identical behavior through the same public
interface.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

try:
    from surrealdb import Surreal

    HAS_SURREALDB = True
except ImportError:
    HAS_SURREALDB = False

pytestmark = pytest.mark.skipif(not HAS_SURREALDB, reason="surrealdb package not installed")


@pytest.fixture
def graph():
    """Create a fresh SurrealKnowledgeGraph in a temp directory."""
    from collab_kg.surreal_graph import SurrealKnowledgeGraph

    tmpdir = tempfile.mkdtemp()
    db_path = str(Path(tmpdir) / "test_kg")
    g = SurrealKnowledgeGraph(db_path=db_path)
    yield g
    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)


# ------------------------------------------------------------------
# Entity CRUD
# ------------------------------------------------------------------


def test_create_entity(graph):
    created = graph.create_entities(
        [
            {
                "name": "TestComponent",
                "entityType": "component",
                "observations": ["protection_tier: architecture", "Uses DI pattern"],
            }
        ]
    )
    assert created == 1

    entity = graph.get_entity("TestComponent")
    assert entity is not None
    assert entity.name == "TestComponent"
    assert len(entity.observations) == 2


def test_create_multiple_entities(graph):
    created = graph.create_entities(
        [
            {"name": "A", "entityType": "component", "observations": ["obs1"]},
            {"name": "B", "entityType": "pattern", "observations": ["obs2"]},
        ]
    )
    assert created == 2

    a = graph.get_entity("A")
    b = graph.get_entity("B")
    assert a is not None
    assert b is not None
    assert a.entity_type.value == "component"
    assert b.entity_type.value == "pattern"


def test_get_entity_not_found(graph):
    entity = graph.get_entity("Nonexistent")
    assert entity is None


# ------------------------------------------------------------------
# Relations
# ------------------------------------------------------------------


def test_create_relations(graph):
    graph.create_entities(
        [
            {"name": "A", "entityType": "component", "observations": []},
            {"name": "B", "entityType": "pattern", "observations": []},
        ]
    )
    created = graph.create_relations(
        [
            {"from": "A", "to": "B", "relationType": "follows_pattern"},
        ]
    )
    assert created == 1

    entity = graph.get_entity("A")
    assert entity is not None
    assert len(entity.relations) == 1
    assert entity.relations[0].relation_type == "follows_pattern"


def test_delete_relations(graph):
    graph.create_entities(
        [
            {"name": "X", "entityType": "component", "observations": []},
            {"name": "Y", "entityType": "pattern", "observations": []},
        ]
    )
    graph.create_relations(
        [
            {"from": "X", "to": "Y", "relationType": "uses"},
        ]
    )

    deleted = graph.delete_relations(
        [{"from": "X", "to": "Y", "relationType": "uses"}]
    )
    assert deleted == 1

    entity = graph.get_entity("X")
    assert entity is not None
    assert len(entity.relations) == 0


# ------------------------------------------------------------------
# Observations
# ------------------------------------------------------------------


def test_add_observations(graph):
    graph.create_entities(
        [
            {
                "name": "Svc",
                "entityType": "component",
                "observations": ["Initial obs"],
            }
        ]
    )

    added, error = graph.add_observations("Svc", ["New fact", "Another fact"])
    assert added == 2
    assert error is None

    entity = graph.get_entity("Svc")
    assert entity is not None
    assert len(entity.observations) == 3
    assert "New fact" in entity.observations


def test_add_observations_entity_not_found(graph):
    added, error = graph.add_observations("Ghost", ["obs"])
    assert added == 0
    assert error is not None
    assert "not found" in error.lower()


def test_delete_observations(graph):
    graph.create_entities(
        [
            {
                "name": "Svc",
                "entityType": "component",
                "observations": ["keep", "remove_me"],
            }
        ]
    )

    deleted, error = graph.delete_observations("Svc", ["remove_me"])
    assert deleted == 1
    assert error is None

    entity = graph.get_entity("Svc")
    assert "remove_me" not in entity.observations
    assert "keep" in entity.observations


# ------------------------------------------------------------------
# Tier protection
# ------------------------------------------------------------------


def test_tier_protection_vision(graph):
    graph.create_entities(
        [
            {
                "name": "VisionStandard",
                "entityType": "vision_standard",
                "observations": ["protection_tier: vision", "mutability: human_only"],
            }
        ]
    )

    # Agent cannot write to vision-tier entity
    added, error = graph.add_observations(
        "VisionStandard", ["new observation"], caller_role="worker"
    )
    assert added == 0
    assert error is not None
    assert "immutable" in error.lower()

    # Human can write to vision-tier entity
    added, error = graph.add_observations(
        "VisionStandard", ["human observation"], caller_role="human"
    )
    assert added == 1
    assert error is None


def test_tier_protection_architecture(graph):
    graph.create_entities(
        [
            {
                "name": "ArchComponent",
                "entityType": "component",
                "observations": ["protection_tier: architecture"],
            }
        ]
    )

    # Agent without approval cannot write
    added, error = graph.add_observations(
        "ArchComponent", ["new obs"], caller_role="worker"
    )
    assert added == 0

    # Agent with approval can write
    added, error = graph.add_observations(
        "ArchComponent",
        ["approved obs"],
        caller_role="worker",
        change_approved=True,
    )
    assert added == 1


def test_delete_entity_tier_protection(graph):
    graph.create_entities(
        [
            {
                "name": "ProtectedEntity",
                "entityType": "vision_standard",
                "observations": ["protection_tier: vision"],
            }
        ]
    )

    # Agent cannot delete vision-tier entity
    deleted, error = graph.delete_entity("ProtectedEntity", caller_role="worker")
    assert not deleted
    assert error is not None

    # Human can delete
    deleted, error = graph.delete_entity("ProtectedEntity", caller_role="human")
    assert deleted
    assert error is None
    assert graph.get_entity("ProtectedEntity") is None


# ------------------------------------------------------------------
# Search and filter
# ------------------------------------------------------------------


def test_search_nodes(graph):
    graph.create_entities(
        [
            {
                "name": "KBOralSessionView",
                "entityType": "component",
                "observations": ["Uses DI"],
            },
            {
                "name": "ServiceRegistry",
                "entityType": "pattern",
                "observations": ["Core pattern"],
            },
        ]
    )

    results = graph.search_nodes("Oral")
    assert len(results) == 1
    assert results[0].name == "KBOralSessionView"


def test_search_nodes_in_observations(graph):
    graph.create_entities(
        [
            {
                "name": "AuthService",
                "entityType": "component",
                "observations": ["Handles token refresh"],
            },
        ]
    )

    results = graph.search_nodes("token refresh")
    assert len(results) == 1
    assert results[0].name == "AuthService"


def test_get_entities_by_tier(graph):
    graph.create_entities(
        [
            {
                "name": "V1",
                "entityType": "vision_standard",
                "observations": ["protection_tier: vision"],
            },
            {
                "name": "A1",
                "entityType": "component",
                "observations": ["protection_tier: architecture"],
            },
            {
                "name": "Q1",
                "entityType": "problem",
                "observations": ["protection_tier: quality"],
            },
        ]
    )

    vision = graph.get_entities_by_tier("vision")
    assert len(vision) == 1
    assert vision[0].name == "V1"

    arch = graph.get_entities_by_tier("architecture")
    assert len(arch) == 1

    quality = graph.get_entities_by_tier("quality")
    assert len(quality) == 1


def test_get_entities_by_type(graph):
    graph.create_entities(
        [
            {"name": "C1", "entityType": "component", "observations": []},
            {"name": "C2", "entityType": "component", "observations": []},
            {"name": "P1", "entityType": "pattern", "observations": []},
        ]
    )

    components = graph.get_entities_by_type("component")
    assert len(components) == 2

    patterns = graph.get_entities_by_type("pattern")
    assert len(patterns) == 1


# ------------------------------------------------------------------
# Entity deletion
# ------------------------------------------------------------------


def test_delete_entity(graph):
    graph.create_entities(
        [
            {"name": "ToDelete", "entityType": "problem", "observations": []},
            {"name": "Other", "entityType": "component", "observations": []},
        ]
    )
    graph.create_relations(
        [{"from": "ToDelete", "to": "Other", "relationType": "related_to"}]
    )

    deleted, error = graph.delete_entity("ToDelete")
    assert deleted
    assert error is None
    assert graph.get_entity("ToDelete") is None

    # Relations involving deleted entity should be removed
    other = graph.get_entity("Other")
    assert other is not None
    assert len(other.relations) == 0


def test_delete_entity_not_found(graph):
    deleted, error = graph.delete_entity("Nonexistent")
    assert not deleted
    assert "not found" in error.lower()
