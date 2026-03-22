#!/usr/bin/env python3
"""Quick integration test for SurrealDB backends across all MCP servers.

Run from project root:
    python scripts/validation/test-surreal-integration.py

Tests that the SurrealDB backends can be imported and basic operations work.
"""

import os
import sys
import tempfile
from pathlib import Path

# Set up project dir for testing
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_DIR)

# Add shared package to path
sys.path.insert(0, str(PROJECT_DIR / "shared"))

PASS = 0
FAIL = 0


def check(name: str, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  PASS: {name}")
        PASS += 1
    except Exception as e:
        print(f"  FAIL: {name} -- {e}")
        FAIL += 1


def test_avt_db_foundation():
    """Test shared avt_db package."""
    print("\n=== avt_db Foundation ===")

    from surrealdb import Surreal

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Surreal(f"surrealkv://{db_path}")
        db.connect()
        db.use("avt", "main")

        from avt_db.schema import apply_schema_sync
        check("Schema applies without error", lambda: apply_schema_sync(db))
        check("Schema is idempotent", lambda: apply_schema_sync(db))

        def crud_test():
            db.query("CREATE entity:test1 SET name='Test', entity_type='component', observations=['obs1'], protection_tier='quality'")
            result = db.query("SELECT * FROM entity:test1")
            assert len(result) == 1
            assert result[0]["name"] == "Test"
            db.query("DELETE entity:test1")
            result = db.query("SELECT * FROM entity:test1")
            assert len(result) == 0

        check("Entity CRUD", crud_test)

        def graph_test():
            db.query("CREATE entity:a SET name='A', entity_type='component'")
            db.query("CREATE entity:b SET name='B', entity_type='component'")
            db.query("RELATE entity:a->relates_to->entity:b SET relation_type='uses'")
            result = db.query("SELECT ->relates_to->entity.name AS deps FROM entity:a")
            assert "B" in result[0]["deps"]
            db.query("DELETE entity:a; DELETE entity:b")

        check("Graph traversals", graph_test)

        db.close()


def test_kg_surreal_backend():
    """Test KG SurrealDB backend if it exists."""
    print("\n=== KG SurrealDB Backend ===")
    sys.path.insert(0, str(PROJECT_DIR / "mcp-servers" / "knowledge-graph"))

    try:
        from collab_kg.surreal_graph import SurrealKnowledgeGraph
        check("SurrealKnowledgeGraph imports", lambda: None)

        # Additional tests would go here once the class is implemented
    except ImportError as e:
        print(f"  SKIP: KG SurrealDB backend not yet created ({e})")


def test_governance_surreal_backend():
    """Test Governance SurrealDB backend if it exists."""
    print("\n=== Governance SurrealDB Backend ===")
    sys.path.insert(0, str(PROJECT_DIR / "mcp-servers" / "governance"))

    try:
        from collab_governance.surreal_store import SurrealGovernanceStore
        check("SurrealGovernanceStore imports", lambda: None)
    except ImportError as e:
        print(f"  SKIP: Governance SurrealDB backend not yet created ({e})")


def test_quality_surreal_backend():
    """Test Quality SurrealDB backend if it exists."""
    print("\n=== Quality SurrealDB Backend ===")
    sys.path.insert(0, str(PROJECT_DIR / "mcp-servers" / "quality"))

    try:
        from collab_quality.surreal_trust_engine import SurrealTrustEngine
        check("SurrealTrustEngine imports", lambda: None)
    except ImportError as e:
        print(f"  SKIP: Quality SurrealDB backend not yet created ({e})")


def test_audit_surreal_backend():
    """Test Audit SurrealDB backend if it exists."""
    print("\n=== Audit SurrealDB Backend ===")
    sys.path.insert(0, str(PROJECT_DIR / "scripts" / "hooks"))

    try:
        from audit.surreal_stats import SurrealStatsAccumulator
        check("SurrealStatsAccumulator imports", lambda: None)
    except ImportError as e:
        print(f"  SKIP: Audit SurrealDB backend not yet created ({e})")


if __name__ == "__main__":
    test_avt_db_foundation()
    test_kg_surreal_backend()
    test_governance_surreal_backend()
    test_quality_surreal_backend()
    test_audit_surreal_backend()

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL > 0:
        sys.exit(1)
    print("All checks passed!")
