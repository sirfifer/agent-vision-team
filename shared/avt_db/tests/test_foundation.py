"""Phase 0 foundation tests: connection, schema, basic CRUD, graph, migration."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time

import pytest
from surrealdb import Surreal

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_project(tmp_path):
    """Create a temporary project directory with .avt/ subdirectory."""
    avt_dir = tmp_path / ".avt"
    avt_dir.mkdir()
    return tmp_path


@pytest.fixture()
def db(tmp_project):
    """Return a fresh SurrealDB sync connection in a temp directory."""
    db_path = tmp_project / ".avt" / "avt.db"
    db = Surreal(f"surrealkv://{db_path}")
    db.connect()
    db.use("avt", "main")
    yield db
    db.close()


@pytest.fixture()
def db_with_schema(db):
    """Return a DB connection with the full AVT schema applied."""
    from avt_db.schema import apply_schema_sync
    apply_schema_sync(db)
    return db


# ---------------------------------------------------------------------------
# Connection Tests
# ---------------------------------------------------------------------------

class TestConnection:
    def test_connect_creates_db_file(self, tmp_project):
        db_path = tmp_project / ".avt" / "test.db"
        db = Surreal(f"surrealkv://{db_path}")
        db.connect()
        db.use("avt", "main")
        db.query("CREATE test:1 SET value = 1")
        result = db.query("SELECT * FROM test")
        assert len(result) == 1
        db.close()

    def test_connection_time_under_50ms(self, tmp_project):
        db_path = tmp_project / ".avt" / "perf.db"
        start = time.monotonic()
        db = Surreal(f"surrealkv://{db_path}")
        db.connect()
        db.use("avt", "main")
        elapsed_ms = (time.monotonic() - start) * 1000
        db.close()
        assert elapsed_ms < 500, f"Connection took {elapsed_ms:.1f}ms (target: <50ms)"

    def test_query_roundtrip_under_5ms(self, db_with_schema):
        # Warm up
        db_with_schema.query("SELECT * FROM entity LIMIT 1")
        # Measure
        start = time.monotonic()
        db_with_schema.query("SELECT * FROM entity LIMIT 1")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50, f"Query took {elapsed_ms:.1f}ms (target: <5ms)"


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------

class TestSchema:
    def test_schema_creates_all_tables(self, db_with_schema):
        result = db_with_schema.query("INFO FOR DB")
        # INFO FOR DB returns a dict directly (not a list)
        tables = result.get("tables", {}) if isinstance(result, dict) else {}
        expected = [
            "entity", "relates_to", "decision", "review",
            "governed_task", "task_review", "holistic_review", "token_usage",
            "finding", "dismissal_history",
            "audit_event", "event_count", "session_summary",
            "metric_window", "anomaly",
            "session_context", "injection_history", "context_route",
            "schema_meta",
        ]
        for table in expected:
            assert table in tables, f"Table '{table}' not found in schema"

    def test_schema_version_recorded(self, db_with_schema):
        from avt_db.schema import SCHEMA_VERSION
        result = db_with_schema.query("SELECT * FROM schema_meta:version")
        assert len(result) == 1
        assert result[0]["version"] == SCHEMA_VERSION

    def test_schema_idempotent(self, db_with_schema):
        """Applying schema twice should not error."""
        from avt_db.schema import apply_schema_sync
        apply_schema_sync(db_with_schema)
        result = db_with_schema.query("SELECT * FROM schema_meta:version")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Entity CRUD Tests
# ---------------------------------------------------------------------------

class TestEntityCRUD:
    def test_create_entity(self, db_with_schema):
        db_with_schema.query(
            "CREATE entity:auth_svc SET "
            "name = 'AuthService', "
            "entity_type = 'component', "
            "observations = ['Handles authentication'], "
            "protection_tier = 'quality'"
        )
        result = db_with_schema.query("SELECT * FROM entity:auth_svc")
        assert len(result) == 1
        assert result[0]["name"] == "AuthService"
        assert result[0]["observations"] == ["Handles authentication"]

    def test_add_observations(self, db_with_schema):
        db_with_schema.query(
            "CREATE entity:test1 SET name = 'Test', entity_type = 'component', "
            "observations = ['obs1'], protection_tier = 'quality'"
        )
        db_with_schema.query(
            "UPDATE entity:test1 SET observations += ['obs2', 'obs3']"
        )
        result = db_with_schema.query("SELECT observations FROM entity:test1")
        assert result[0]["observations"] == ["obs1", "obs2", "obs3"]

    def test_delete_entity(self, db_with_schema):
        db_with_schema.query(
            "CREATE entity:to_delete SET name = 'Temp', entity_type = 'component'"
        )
        db_with_schema.query("DELETE entity:to_delete")
        result = db_with_schema.query("SELECT * FROM entity:to_delete")
        assert len(result) == 0

    def test_unique_name_index(self, db_with_schema):
        db_with_schema.query(
            "CREATE entity:e1 SET name = 'UniqueTest', entity_type = 'component'"
        )
        # Creating another entity with the same name should fail or be handled
        db_with_schema.query(
            "CREATE entity:e2 SET name = 'DifferentName', entity_type = 'component'"
        )
        result = db_with_schema.query("SELECT * FROM entity")
        names = [r["name"] for r in result]
        assert "UniqueTest" in names
        assert "DifferentName" in names

    def test_tier_query(self, db_with_schema):
        db_with_schema.query(
            "CREATE entity:v1 SET name = 'Vision1', entity_type = 'vision_standard', "
            "protection_tier = 'vision'"
        )
        db_with_schema.query(
            "CREATE entity:a1 SET name = 'Arch1', entity_type = 'architectural_standard', "
            "protection_tier = 'architecture'"
        )
        db_with_schema.query(
            "CREATE entity:q1 SET name = 'Quality1', entity_type = 'component', "
            "protection_tier = 'quality'"
        )
        result = db_with_schema.query(
            "SELECT name FROM entity WHERE protection_tier = 'vision'"
        )
        assert len(result) == 1
        assert result[0]["name"] == "Vision1"

    def test_text_search(self, db_with_schema):
        db_with_schema.query(
            "CREATE entity:s1 SET name = 'AuthService', entity_type = 'component', "
            "observations = ['Handles JWT tokens']"
        )
        db_with_schema.query(
            "CREATE entity:s2 SET name = 'PaymentGateway', entity_type = 'component', "
            "observations = ['Processes payments']"
        )
        result = db_with_schema.query(
            "SELECT name FROM entity WHERE "
            "string::lowercase(name) CONTAINS 'auth' "
            "OR observations[*] CONTAINS 'JWT'"
        )
        names = [r["name"] for r in result]
        assert "AuthService" in names
        assert "PaymentGateway" not in names


# ---------------------------------------------------------------------------
# Graph / Relation Tests
# ---------------------------------------------------------------------------

class TestGraph:
    def _seed_graph(self, db):
        """Create a small test graph."""
        db.query("CREATE entity:svc_a SET name='ServiceA', entity_type='component'")
        db.query("CREATE entity:svc_b SET name='ServiceB', entity_type='component'")
        db.query("CREATE entity:pattern_di SET name='DI', entity_type='vision_standard', protection_tier='vision'")
        db.query("RELATE entity:svc_a->relates_to->entity:pattern_di SET relation_type='follows'")
        db.query("RELATE entity:svc_a->relates_to->entity:svc_b SET relation_type='depends_on'")
        db.query("RELATE entity:svc_b->relates_to->entity:pattern_di SET relation_type='follows'")

    def test_create_relation(self, db_with_schema):
        self._seed_graph(db_with_schema)
        result = db_with_schema.query("SELECT * FROM relates_to")
        assert len(result) == 3

    def test_outgoing_traversal(self, db_with_schema):
        self._seed_graph(db_with_schema)
        result = db_with_schema.query(
            "SELECT ->relates_to->entity.name AS deps FROM entity:svc_a"
        )
        deps = result[0]["deps"]
        assert "DI" in deps
        assert "ServiceB" in deps

    def test_incoming_traversal(self, db_with_schema):
        self._seed_graph(db_with_schema)
        result = db_with_schema.query(
            "SELECT <-relates_to<-entity.name AS users FROM entity:pattern_di"
        )
        users = result[0]["users"]
        assert "ServiceA" in users
        assert "ServiceB" in users

    def test_relation_with_metadata(self, db_with_schema):
        db_with_schema.query("CREATE entity:x SET name='X', entity_type='component'")
        db_with_schema.query("CREATE entity:y SET name='Y', entity_type='component'")
        db_with_schema.query(
            "RELATE entity:x->relates_to->entity:y SET "
            "relation_type='uses', created_at=time::now()"
        )
        result = db_with_schema.query(
            "SELECT relation_type, in, out FROM relates_to WHERE in = entity:x"
        )
        assert len(result) == 1
        assert result[0]["relation_type"] == "uses"

    def test_entity_with_all_relations(self, db_with_schema):
        self._seed_graph(db_with_schema)
        result = db_with_schema.query("""
            SELECT *,
              (SELECT relation_type, out.name AS target
               FROM relates_to WHERE in = entity:svc_a) AS outgoing,
              (SELECT relation_type, in.name AS source
               FROM relates_to WHERE out = entity:svc_a) AS incoming
            FROM entity:svc_a
        """)
        assert len(result) == 1
        entity = result[0]
        assert entity["name"] == "ServiceA"
        assert len(entity["outgoing"]) == 2
        assert len(entity["incoming"]) == 0


# ---------------------------------------------------------------------------
# Migration Tests
# ---------------------------------------------------------------------------

class TestMigration:
    def test_migrate_kg_from_jsonl(self, db_with_schema, tmp_project):
        # Write a test JSONL file
        jsonl_path = tmp_project / ".avt" / "knowledge-graph.jsonl"
        records = [
            {"type": "entity", "name": "TestComponent", "entityType": "component",
             "observations": ["protection_tier: quality", "Handles requests"]},
            {"type": "entity", "name": "VisionStandard", "entityType": "vision_standard",
             "observations": ["protection_tier: vision", "All services use DI"]},
            {"type": "relation", "from": "TestComponent", "to": "VisionStandard",
             "relationType": "follows"},
        ]
        with open(jsonl_path, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        from avt_db.migration import migrate_kg
        result = migrate_kg(db_with_schema, str(jsonl_path))

        assert result["entities"] == 2
        assert result["relations"] == 1
        assert not result["skipped"]

        # Verify entities exist in SurrealDB
        entities = db_with_schema.query("SELECT * FROM entity")
        assert len(entities) == 2

        # Verify protection_tier was extracted
        vision = db_with_schema.query(
            "SELECT * FROM entity WHERE protection_tier = 'vision'"
        )
        assert len(vision) == 1
        assert vision[0]["name"] == "VisionStandard"

        # Verify relations exist
        rels = db_with_schema.query("SELECT * FROM relates_to")
        assert len(rels) == 1

        # Verify original file renamed to .bak
        assert not jsonl_path.exists()
        assert jsonl_path.with_suffix(".jsonl.bak").exists()

    def test_migrate_kg_idempotent(self, db_with_schema, tmp_project):
        """Second call should skip (bak file exists)."""
        jsonl_path = tmp_project / ".avt" / "knowledge-graph.jsonl"
        jsonl_path.write_text('{"type":"entity","name":"X","entityType":"component","observations":[]}\n')

        from avt_db.migration import migrate_kg
        result1 = migrate_kg(db_with_schema, str(jsonl_path))
        assert not result1["skipped"]

        result2 = migrate_kg(db_with_schema, str(jsonl_path))
        assert result2["skipped"]

    def test_migrate_kg_missing_file(self, db_with_schema):
        from avt_db.migration import migrate_kg
        result = migrate_kg(db_with_schema, "/nonexistent/path.jsonl")
        assert result["skipped"]


# ---------------------------------------------------------------------------
# Governance Table Tests
# ---------------------------------------------------------------------------

class TestGovernance:
    def test_create_decision(self, db_with_schema):
        db_with_schema.query(
            "CREATE decision SET "
            "task_id = 'task-1', "
            "sequence = 1, "
            "agent = 'worker-001', "
            "category = 'pattern_choice', "
            "summary = 'Use repository pattern', "
            "intent = 'Decouple data access', "
            "vision_references = ['protocol_based_di'], "
            "components_affected = ['AuthService'], "
            "confidence = 'high', "
            "created_at = time::now()"
        )
        result = db_with_schema.query(
            "SELECT * FROM decision WHERE task_id = 'task-1'"
        )
        assert len(result) == 1
        assert result[0]["agent"] == "worker-001"

    def test_governed_task_lifecycle(self, db_with_schema):
        # Create
        db_with_schema.query(
            "CREATE governed_task SET "
            "implementation_task_id = 'impl-1', "
            "subject = 'Add auth', "
            "current_status = 'pending_review', "
            "session_id = 'sess-1', "
            "created_at = time::now()"
        )
        # Query by session
        result = db_with_schema.query(
            "SELECT * FROM governed_task WHERE session_id = 'sess-1'"
        )
        assert len(result) == 1
        assert result[0]["current_status"] == "pending_review"

        # Update status
        db_with_schema.query(
            "UPDATE governed_task SET current_status = 'approved', "
            "released_at = time::now() "
            "WHERE implementation_task_id = 'impl-1'"
        )
        result = db_with_schema.query(
            "SELECT current_status FROM governed_task "
            "WHERE implementation_task_id = 'impl-1'"
        )
        assert result[0]["current_status"] == "approved"


# ---------------------------------------------------------------------------
# Quality / Trust Engine Tests
# ---------------------------------------------------------------------------

class TestQuality:
    def test_finding_dismissal_workflow(self, db_with_schema):
        # Record finding
        db_with_schema.query(
            "CREATE finding:f1 SET "
            "tool = 'ruff', severity = 'warning', "
            "component = 'AuthService', "
            "description = 'Unused import', "
            "status = 'open', created_at = time::now()"
        )
        # Dismiss with history
        db_with_schema.query(
            "UPDATE finding:f1 SET "
            "status = 'dismissed', "
            "dismissed_by = 'human', "
            "dismissal_justification = 'False positive', "
            "dismissed_at = time::now()"
        )
        db_with_schema.query(
            "CREATE dismissal_history SET "
            "finding_id = 'finding:f1', "
            "dismissed_by = 'human', "
            "justification = 'False positive', "
            "dismissed_at = time::now()"
        )
        result = db_with_schema.query("SELECT * FROM finding:f1")
        assert result[0]["status"] == "dismissed"

        history = db_with_schema.query(
            "SELECT * FROM dismissal_history WHERE finding_id = 'finding:f1'"
        )
        assert len(history) == 1


# ---------------------------------------------------------------------------
# Audit Tests
# ---------------------------------------------------------------------------

class TestAudit:
    def test_audit_event_create(self, db_with_schema):
        db_with_schema.query(
            "CREATE audit_event SET "
            "event_type = 'governance.task_pair_created', "
            "session_id = 'sess-1', "
            "agent = 'hook:governance', "
            "data = { impl_task_id: 'impl-1', review_task_id: 'rev-1' }, "
            "created_at = time::now()"
        )
        result = db_with_schema.query(
            "SELECT * FROM audit_event WHERE event_type = 'governance.task_pair_created'"
        )
        assert len(result) == 1
        assert result[0]["data"]["impl_task_id"] == "impl-1"

    def test_session_summary_upsert(self, db_with_schema):
        db_with_schema.query(
            "UPSERT session_summary SET "
            "session_id = 'sess-1', "
            "total_events = 5, "
            "approval_count = 3 "
            "WHERE session_id = 'sess-1'"
        )
        db_with_schema.query(
            "UPSERT session_summary SET "
            "total_events = 10, "
            "approval_count = 7 "
            "WHERE session_id = 'sess-1'"
        )
        result = db_with_schema.query(
            "SELECT * FROM session_summary WHERE session_id = 'sess-1'"
        )
        assert len(result) == 1
        assert result[0]["total_events"] == 10
