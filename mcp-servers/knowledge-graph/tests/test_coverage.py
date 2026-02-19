"""Additional tests to improve coverage for Knowledge Graph server."""

import tempfile
from pathlib import Path

from collab_kg.graph import KnowledgeGraph


def test_delete_entity():
    """Test entity deletion with tier protection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = KnowledgeGraph(storage_path=str(Path(tmpdir) / "test.jsonl"))

        # Create entities at different tiers
        graph.create_entities(
            [
                {"name": "quality_entity", "entityType": "component", "observations": ["protection_tier: quality"]},
                {"name": "arch_entity", "entityType": "component", "observations": ["protection_tier: architecture"]},
                {"name": "vision_entity", "entityType": "vision_standard", "observations": ["protection_tier: vision"]},
            ]
        )

        # Quality tier entity can be deleted by agent
        deleted, error = graph.delete_entity("quality_entity", caller_role="worker")
        assert deleted
        assert error is None

        # Architecture tier entity cannot be deleted by agent
        deleted, error = graph.delete_entity("arch_entity", caller_role="worker")
        assert not deleted
        assert "cannot delete" in error.lower()

        # Vision tier entity cannot be deleted by agent
        deleted, error = graph.delete_entity("vision_entity", caller_role="worker")
        assert not deleted
        assert "cannot delete" in error.lower()

        # Human can delete any tier
        deleted, error = graph.delete_entity("arch_entity", caller_role="human")
        assert deleted
        assert error is None


def test_delete_entity_nonexistent():
    """Test deleting non-existent entity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = KnowledgeGraph(storage_path=str(Path(tmpdir) / "test.jsonl"))
        deleted, error = graph.delete_entity("nonexistent", caller_role="human")
        assert not deleted
        assert "not found" in error.lower()


def test_delete_relations():
    """Test relation deletion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = KnowledgeGraph(storage_path=str(Path(tmpdir) / "test.jsonl"))

        # Create entities and relations
        graph.create_entities(
            [
                {"name": "A", "entityType": "component", "observations": []},
                {"name": "B", "entityType": "pattern", "observations": []},
                {"name": "C", "entityType": "component", "observations": []},
            ]
        )
        graph.create_relations(
            [
                {"from": "A", "to": "B", "relationType": "follows_pattern"},
                {"from": "A", "to": "C", "relationType": "depends_on"},
            ]
        )

        # Delete one relation
        deleted = graph.delete_relations([{"from": "A", "to": "B", "relationType": "follows_pattern"}])
        assert deleted == 1

        # Verify relation is gone
        entity = graph.get_entity("A")
        assert len(entity.relations) == 1
        assert entity.relations[0].to == "C"


def test_delete_observations_with_approval():
    """Test observation deletion with tier approval."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = KnowledgeGraph(storage_path=str(Path(tmpdir) / "test.jsonl"))

        # Create architecture tier entity
        graph.create_entities(
            [
                {
                    "name": "TestComp",
                    "entityType": "component",
                    "observations": ["protection_tier: architecture", "initial obs"],
                }
            ]
        )

        # Agent cannot delete without approval
        deleted, error = graph.delete_observations(
            "TestComp", ["initial obs"], caller_role="worker", change_approved=False
        )
        assert deleted == 0
        assert error is not None

        # Agent can delete with approval
        deleted, error = graph.delete_observations(
            "TestComp", ["initial obs"], caller_role="worker", change_approved=True
        )
        assert deleted == 1
        assert error is None


def test_delete_observations_nonexistent_entity():
    """Test deleting observations from nonexistent entity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = KnowledgeGraph(storage_path=str(Path(tmpdir) / "test.jsonl"))
        deleted, error = graph.delete_observations("nonexistent", ["some obs"], caller_role="human")
        assert deleted == 0
        assert "not found" in error.lower()


def test_persistence_across_restarts():
    """Test that data persists across graph restarts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test.jsonl")

        # Create graph and add data
        graph1 = KnowledgeGraph(storage_path=storage_path)
        graph1.create_entities(
            [
                {
                    "name": "PersistentEntity",
                    "entityType": "component",
                    "observations": ["test observation"],
                }
            ]
        )
        graph1.create_relations(
            [
                {
                    "from": "PersistentEntity",
                    "to": "PersistentEntity",
                    "relationType": "self_reference",
                }
            ]
        )

        # Create new graph instance (simulates restart)
        graph2 = KnowledgeGraph(storage_path=storage_path)

        # Verify data was loaded
        entity = graph2.get_entity("PersistentEntity")
        assert entity is not None
        assert "test observation" in entity.observations
        assert len(entity.relations) > 0


def test_compaction_threshold():
    """Test automatic compaction after threshold writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test.jsonl")
        graph = KnowledgeGraph(storage_path=storage_path)
        graph._compaction_threshold = 5  # Lower threshold for testing

        # Add entities to trigger compaction
        for i in range(6):
            graph.create_entities(
                [
                    {
                        "name": f"entity_{i}",
                        "entityType": "component",
                        "observations": [],
                    }
                ]
            )

        # Compaction should have happened
        assert graph._write_count < 6  # Reset after compaction


def test_add_observations_to_quality_tier():
    """Test adding observations to quality tier entity (no restrictions)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = KnowledgeGraph(storage_path=str(Path(tmpdir) / "test.jsonl"))

        graph.create_entities(
            [
                {
                    "name": "QualityEntity",
                    "entityType": "component",
                    "observations": ["protection_tier: quality"],
                }
            ]
        )

        # Any role can add to quality tier
        added, error = graph.add_observations("QualityEntity", ["new observation"], caller_role="worker")
        assert added == 1
        assert error is None


def test_search_nodes_by_observation():
    """Test searching nodes by observation content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = KnowledgeGraph(storage_path=str(Path(tmpdir) / "test.jsonl"))

        graph.create_entities(
            [
                {"name": "A", "entityType": "component", "observations": ["uses protocol-based DI"]},
                {"name": "B", "entityType": "component", "observations": ["uses singleton pattern"]},
            ]
        )

        # Search by observation keyword
        results = graph.search_nodes("protocol")
        assert len(results) == 1
        assert results[0].name == "A"


def test_get_entities_by_tier_with_no_tier():
    """Test getting entities when some have no tier."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = KnowledgeGraph(storage_path=str(Path(tmpdir) / "test.jsonl"))

        graph.create_entities(
            [
                {"name": "WithTier", "entityType": "component", "observations": ["protection_tier: quality"]},
                {"name": "WithoutTier", "entityType": "component", "observations": ["some observation"]},
            ]
        )

        results = graph.get_entities_by_tier("quality")
        assert len(results) == 1
        assert results[0].name == "WithTier"
