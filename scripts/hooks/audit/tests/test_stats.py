"""Tests for StatsAccumulator."""

from __future__ import annotations

import pytest


@pytest.fixture
def stats_db(tmp_path):
    """Create a StatsAccumulator with a temporary DB."""
    from audit.stats import StatsAccumulator

    db_path = tmp_path / "test-stats.db"
    acc = StatsAccumulator(db_path=db_path)
    yield acc
    acc.close()


def _make_events(types_and_sessions, base_ts=1000):
    """Helper to create test events."""
    events = []
    for i, (etype, sid, data) in enumerate(types_and_sessions):
        events.append(
            {
                "type": etype,
                "ts": base_ts + i,
                "session_id": sid,
                "data": data or {},
            }
        )
    return events


class TestIngestEvents:
    def test_empty_batch(self, stats_db):
        result = stats_db.ingest_events([])
        assert result["total"] == 0
        assert result["by_type"] == {}

    def test_single_event(self, stats_db):
        events = [{"type": "test.event", "ts": 1000, "session_id": "s1", "data": {}}]
        result = stats_db.ingest_events(events)
        assert result["total"] == 1
        assert result["by_type"]["test.event"] == 1

    def test_multiple_types(self, stats_db):
        events = _make_events(
            [
                ("governance.task_pair_created", "s1", {}),
                ("governance.task_pair_created", "s1", {}),
                ("governance.individual_review_completed", "s1", {"verdict": "approved"}),
                ("agent.idle_blocked", "s2", {}),
            ]
        )
        result = stats_db.ingest_events(events)
        assert result["total"] == 4
        assert result["by_type"]["governance.task_pair_created"] == 2
        assert result["by_type"]["agent.idle_blocked"] == 1
        assert set(result["sessions_touched"]) == {"s1", "s2"}

    def test_session_summary_counts(self, stats_db):
        events = _make_events(
            [
                ("governance.task_pair_created", "s1", {}),
                ("governance.task_pair_created", "s1", {}),
                ("governance.individual_review_completed", "s1", {"verdict": "approved"}),
                ("governance.individual_review_completed", "s1", {"verdict": "blocked", "status": "blocked"}),
                ("task.completion_attempted", "s1", {"allowed": False}),
            ]
        )
        stats_db.ingest_events(events)
        summary = stats_db.get_session_summary("s1")
        assert summary is not None
        assert summary["total_events"] == 5
        assert summary["task_count"] == 2
        assert summary["approval_count"] == 1
        assert summary["block_count"] == 1
        assert summary["gate_block_count"] == 1

    def test_incremental_ingestion(self, stats_db):
        batch1 = [{"type": "test.a", "ts": 1000, "session_id": "s1", "data": {}}]
        batch2 = [{"type": "test.a", "ts": 1001, "session_id": "s1", "data": {}}]
        stats_db.ingest_events(batch1)
        stats_db.ingest_events(batch2)
        summary = stats_db.get_session_summary("s1")
        assert summary["total_events"] == 2


class TestAnomalyRecording:
    def test_record_and_retrieve(self, stats_db):
        stats_db.record_anomaly("a1", "high_block_rate", "warning", "Test anomaly", {"rate": 0.7})
        anomalies = stats_db.get_recent_anomalies(hours=1)
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_type"] == "high_block_rate"

    def test_unescalated(self, stats_db):
        stats_db.record_anomaly("a1", "type_a", "warning", "desc1")
        stats_db.record_anomaly("a2", "type_b", "info", "desc2")
        unesc = stats_db.get_unescalated_anomalies()
        assert len(unesc) == 2

        stats_db.mark_anomaly_escalated("a1")
        unesc = stats_db.get_unescalated_anomalies()
        assert len(unesc) == 1
        assert unesc[0]["id"] == "a2"


class TestMetricWindows:
    def test_update_and_baseline(self, stats_db):
        stats_db.update_metric_window("events_per_hour", 10.0)
        baseline = stats_db.get_baseline_rate("events_per_hour", window_hours=1)
        assert baseline == 10.0

    def test_no_baseline_returns_none(self, stats_db):
        baseline = stats_db.get_baseline_rate("nonexistent", window_hours=1)
        assert baseline is None


class TestPruning:
    def test_prune_removes_old_data(self, stats_db):
        stats_db.record_anomaly("old", "type", "info", "old anomaly")
        # Manually set detected_at to long ago
        conn = stats_db._get_conn()
        conn.execute("UPDATE anomalies SET detected_at = 1000")
        conn.commit()

        deleted = stats_db.prune_old_data(max_age_days=1)
        assert deleted >= 1
        assert len(stats_db.get_recent_anomalies(hours=99999)) == 0
