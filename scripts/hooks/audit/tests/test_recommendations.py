"""Tests for RecommendationManager."""

from __future__ import annotations

import time

import pytest


@pytest.fixture
def rec_mgr(tmp_path):
    from audit.recommendations import RecommendationManager

    path = tmp_path / "recommendations.json"
    return RecommendationManager(path=path)


def _make_anomaly(atype="high_block_rate", severity="warning"):
    return {
        "id": f"anom-{atype}",
        "type": atype,
        "severity": severity,
        "description": f"Test anomaly: {atype}",
        "metric_values": {"rate": 0.7},
    }


class TestCreateFromAnomaly:
    def test_creates_recommendation(self, rec_mgr):
        rec = rec_mgr.create_from_anomaly(_make_anomaly())
        assert rec is not None
        assert rec["status"] == "active"
        assert rec["evidence_count"] == 1
        assert rec["anomaly_type"] == "high_block_rate"

    def test_deduplicates_by_type(self, rec_mgr):
        rec1 = rec_mgr.create_from_anomaly(_make_anomaly())
        rec2 = rec_mgr.create_from_anomaly(_make_anomaly())
        assert rec1["id"] == rec2["id"]
        assert rec2["evidence_count"] == 2

    def test_different_types_create_separate(self, rec_mgr):
        rec1 = rec_mgr.create_from_anomaly(_make_anomaly("type_a"))
        rec2 = rec_mgr.create_from_anomaly(_make_anomaly("type_b"))
        assert rec1["id"] != rec2["id"]
        assert rec_mgr.active_count == 2

    def test_suggestion_stored(self, rec_mgr):
        rec = rec_mgr.create_from_anomaly(_make_anomaly(), suggestion="Lower threshold to 0.3")
        assert rec["suggestion"] == "Lower threshold to 0.3"


class TestLifecycle:
    def test_dismiss(self, rec_mgr):
        rec = rec_mgr.create_from_anomaly(_make_anomaly())
        assert rec_mgr.active_count == 1
        rec_mgr.dismiss(rec["id"], "not relevant")
        assert rec_mgr.active_count == 0
        dismissed = rec_mgr.get_by_id(rec["id"])
        assert dismissed["status"] == "dismissed"
        assert dismissed["dismissed_reason"] == "not relevant"

    def test_resolve(self, rec_mgr):
        rec = rec_mgr.create_from_anomaly(_make_anomaly())
        rec_mgr.resolve(rec["id"])
        assert rec_mgr.active_count == 0
        resolved = rec_mgr.get_by_id(rec["id"])
        assert resolved["status"] == "resolved"
        assert resolved["resolved_at"] is not None

    def test_supersede(self, rec_mgr):
        rec1 = rec_mgr.create_from_anomaly(_make_anomaly("type_a"))
        rec2 = rec_mgr.create_from_anomaly(_make_anomaly("type_b"))
        rec_mgr.supersede(rec1["id"], rec2["id"])
        old = rec_mgr.get_by_id(rec1["id"])
        assert old["status"] == "superseded"
        assert old["superseded_by"] == rec2["id"]

    def test_ttl_expiry(self, rec_mgr):
        rec = rec_mgr.create_from_anomaly(_make_anomaly(), ttl_seconds=0)
        # Force expiry
        time.sleep(0.01)
        pruned = rec_mgr.prune_expired()
        assert pruned == 1
        stale = rec_mgr.get_by_id(rec["id"])
        assert stale["status"] == "stale"
        assert rec_mgr.active_count == 0


class TestEscalationUpdate:
    def test_update_from_escalation(self, rec_mgr):
        rec_mgr.create_from_anomaly(_make_anomaly())
        updated = rec_mgr.update_from_escalation(
            "high_block_rate",
            suggestion="Lower threshold to 0.3",
            analysis="Detailed analysis...",
            tier="haiku",
        )
        assert updated is not None
        assert updated["suggestion"] == "Lower threshold to 0.3"
        assert updated["analysis"] == "Detailed analysis..."
        assert updated["escalation_tier"] == "haiku"

    def test_update_nonexistent_returns_none(self, rec_mgr):
        result = rec_mgr.update_from_escalation("nonexistent", "suggestion")
        assert result is None


class TestQueries:
    def test_get_active_sorted_by_evidence(self, rec_mgr):
        rec_mgr.create_from_anomaly(_make_anomaly("type_a"))
        rec_mgr.create_from_anomaly(_make_anomaly("type_b"))
        # Bump type_b evidence
        rec_mgr.create_from_anomaly(_make_anomaly("type_b"))

        active = rec_mgr.get_active()
        assert len(active) == 2
        assert active[0]["anomaly_type"] == "type_b"  # Higher evidence first

    def test_get_by_type(self, rec_mgr):
        rec_mgr.create_from_anomaly(_make_anomaly("type_a"))
        rec_mgr.create_from_anomaly(_make_anomaly("type_b"))
        results = rec_mgr.get_by_type("type_a")
        assert len(results) == 1

    def test_get_all(self, rec_mgr):
        rec_mgr.create_from_anomaly(_make_anomaly("type_a"))
        rec = rec_mgr.create_from_anomaly(_make_anomaly("type_b"))
        rec_mgr.dismiss(rec["id"], "test")
        all_recs = rec_mgr.get_all()
        assert len(all_recs) == 2


class TestPersistence:
    def test_survives_reload(self, tmp_path):
        from audit.recommendations import RecommendationManager

        path = tmp_path / "recs.json"

        mgr1 = RecommendationManager(path=path)
        mgr1.create_from_anomaly(_make_anomaly())
        assert mgr1.active_count == 1

        mgr2 = RecommendationManager(path=path)
        assert mgr2.active_count == 1
