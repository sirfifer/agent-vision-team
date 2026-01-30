"""Basic tests for the Knowledge Graph server."""

from collab_kg.graph import KnowledgeGraph
from collab_kg.tier_protection import get_entity_tier, validate_write_access, ProtectionTier


def test_create_entity():
    graph = KnowledgeGraph()
    created = graph.create_entities([{
        "name": "TestComponent",
        "entityType": "component",
        "observations": ["protection_tier: architecture", "Uses DI pattern"],
    }])
    assert created == 1

    entity = graph.get_entity("TestComponent")
    assert entity is not None
    assert entity.name == "TestComponent"
    assert len(entity.observations) == 2


def test_create_relations():
    graph = KnowledgeGraph()
    graph.create_entities([
        {"name": "A", "entityType": "component", "observations": []},
        {"name": "B", "entityType": "pattern", "observations": []},
    ])
    created = graph.create_relations([
        {"from": "A", "to": "B", "relationType": "follows_pattern"},
    ])
    assert created == 1

    entity = graph.get_entity("A")
    assert entity is not None
    assert len(entity.relations) == 1


def test_tier_protection_vision():
    graph = KnowledgeGraph()
    graph.create_entities([{
        "name": "VisionStandard",
        "entityType": "vision_standard",
        "observations": ["protection_tier: vision", "mutability: human_only"],
    }])

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


def test_tier_protection_architecture():
    graph = KnowledgeGraph()
    graph.create_entities([{
        "name": "ArchComponent",
        "entityType": "component",
        "observations": ["protection_tier: architecture"],
    }])

    # Agent without approval cannot write
    added, error = graph.add_observations(
        "ArchComponent", ["new obs"], caller_role="worker"
    )
    assert added == 0

    # Agent with approval can write
    added, error = graph.add_observations(
        "ArchComponent", ["approved obs"], caller_role="worker", change_approved=True
    )
    assert added == 1


def test_search_nodes():
    graph = KnowledgeGraph()
    graph.create_entities([
        {"name": "KBOralSessionView", "entityType": "component", "observations": ["Uses DI"]},
        {"name": "ServiceRegistry", "entityType": "pattern", "observations": ["Core pattern"]},
    ])

    results = graph.search_nodes("Oral")
    assert len(results) == 1
    assert results[0].name == "KBOralSessionView"


def test_get_entities_by_tier():
    graph = KnowledgeGraph()
    graph.create_entities([
        {"name": "V1", "entityType": "vision_standard", "observations": ["protection_tier: vision"]},
        {"name": "A1", "entityType": "component", "observations": ["protection_tier: architecture"]},
        {"name": "Q1", "entityType": "problem", "observations": ["protection_tier: quality"]},
    ])

    vision = graph.get_entities_by_tier("vision")
    assert len(vision) == 1
    assert vision[0].name == "V1"

    arch = graph.get_entities_by_tier("architecture")
    assert len(arch) == 1

    quality = graph.get_entities_by_tier("quality")
    assert len(quality) == 1


def test_get_entity_tier():
    observations = ["protection_tier: vision", "some other fact"]
    tier = get_entity_tier(observations)
    assert tier == ProtectionTier.VISION


def test_validate_write_access():
    # Vision tier: only human
    allowed, _ = validate_write_access(ProtectionTier.VISION, "worker")
    assert not allowed
    allowed, _ = validate_write_access(ProtectionTier.VISION, "human")
    assert allowed

    # Architecture tier: human or approved
    allowed, _ = validate_write_access(ProtectionTier.ARCHITECTURE, "worker", change_approved=False)
    assert not allowed
    allowed, _ = validate_write_access(ProtectionTier.ARCHITECTURE, "worker", change_approved=True)
    assert allowed

    # Quality tier: all allowed
    allowed, _ = validate_write_access(ProtectionTier.QUALITY, "worker")
    assert allowed
