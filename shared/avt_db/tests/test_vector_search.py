"""Tests for vector search and embedding capabilities.

These tests verify the embedding storage and vector similarity search
work correctly with SurrealDB. They use synthetic embeddings (not the
real sentence-transformers model) to avoid the 80MB model download.
"""

import pytest
from surrealdb import Surreal

from avt_db.schema import apply_schema_sync


@pytest.fixture()
def db(tmp_path):
    db_path = tmp_path / ".avt" / "avt.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Surreal(f"surrealkv://{db_path}")
    db.connect()
    db.use("avt", "main")
    apply_schema_sync(db)
    yield db
    db.close()


def _fake_embedding(seed: float, dim: int = 8) -> list[float]:
    """Generate a deterministic fake embedding for testing."""
    import math
    return [math.sin(seed * (i + 1)) for i in range(dim)]


class TestEmbeddingStorage:
    def test_store_embedding_on_entity(self, db):
        emb = _fake_embedding(1.0)
        db.query(
            "CREATE entity:test1 SET name='Test', entity_type='component', "
            "observations=['obs1'], embedding=$emb",
            {"emb": emb},
        )
        result = db.query("SELECT embedding FROM entity:test1")
        assert len(result) == 1
        stored_emb = result[0]["embedding"]
        assert len(stored_emb) == 8
        assert abs(stored_emb[0] - emb[0]) < 0.001

    def test_update_embedding(self, db):
        db.query("CREATE entity:test2 SET name='Test2', entity_type='component'")
        emb = _fake_embedding(2.0)
        db.query("UPDATE entity:test2 SET embedding = $emb", {"emb": emb})
        result = db.query("SELECT embedding FROM entity:test2")
        assert result[0]["embedding"] is not None
        assert len(result[0]["embedding"]) == 8

    def test_filter_entities_with_embeddings(self, db):
        db.query("CREATE entity:with_emb SET name='A', entity_type='component', embedding=$emb",
                 {"emb": _fake_embedding(1.0)})
        db.query("CREATE entity:without_emb SET name='B', entity_type='component'")
        result = db.query("SELECT name FROM entity WHERE embedding != NONE AND embedding != []")
        names = [r["name"] for r in result]
        assert "A" in names
        assert "B" not in names


class TestVectorSimilarity:
    def test_cosine_similarity_returns_score(self, db):
        emb1 = _fake_embedding(1.0)
        emb2 = _fake_embedding(1.1)  # Similar
        emb3 = _fake_embedding(5.0)  # Different

        db.query("CREATE entity:sim1 SET name='Similar', entity_type='component', embedding=$emb",
                 {"emb": emb1})
        db.query("CREATE entity:sim2 SET name='AlsoSimilar', entity_type='component', embedding=$emb",
                 {"emb": emb2})
        db.query("CREATE entity:diff SET name='Different', entity_type='component', embedding=$emb",
                 {"emb": emb3})

        result = db.query(
            "SELECT name, vector::similarity::cosine(embedding, $query) AS score "
            "FROM entity WHERE embedding != NONE AND embedding != [] "
            "ORDER BY score DESC",
            {"query": emb1},
        )
        assert len(result) == 3
        # First result should be the exact match (score ~1.0)
        assert result[0]["name"] == "Similar"
        assert result[0]["score"] > 0.99
        # Second should be the similar one
        assert result[1]["name"] == "AlsoSimilar"
        assert result[1]["score"] > 0.8

    def test_vector_search_with_limit(self, db):
        for i in range(5):
            db.query(
                f"CREATE entity:e{i} SET name='Entity{i}', entity_type='component', embedding=$emb",
                {"emb": _fake_embedding(float(i))},
            )
        # ORDER BY requires the computed field in SELECT
        result = db.query(
            "SELECT name, vector::similarity::cosine(embedding, $q) AS score "
            "FROM entity WHERE embedding != NONE AND embedding != [] "
            "ORDER BY score DESC LIMIT 2",
            {"q": _fake_embedding(0.0)},
        )
        assert len(result) == 2


class TestContextRouteEmbeddings:
    def test_store_route_embedding(self, db):
        emb = _fake_embedding(3.0)
        db.query(
            "CREATE context_route SET route_id='route-1', "
            "keywords=['auth', 'login'], context='Authentication context', "
            "embedding=$emb",
            {"emb": emb},
        )
        result = db.query(
            "SELECT route_id, context, "
            "vector::similarity::cosine(embedding, $q) AS score "
            "FROM context_route WHERE embedding != NONE "
            "ORDER BY score DESC LIMIT 1",
            {"q": emb},
        )
        assert len(result) == 1
        assert result[0]["route_id"] == "route-1"
        assert result[0]["score"] > 0.99
