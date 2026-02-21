"""Tests for AnomalyDetector."""

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


@pytest.fixture
def detector():
    from audit.anomaly import AnomalyDetector

    return AnomalyDetector(
        thresholds={
            "governance_block_rate": 0.5,
            "reinforcement_skip_rate": 0.7,
            "event_rate_spike_multiplier": 3.0,
            "idle_block_count": 3,
        }
    )


class TestHighBlockRate:
    def test_detects_high_block_rate(self, detector, stats_db):
        # Create session with 80% block rate
        events = [
            {"type": "governance.task_pair_created", "ts": 1000, "session_id": "s1", "data": {}},
            {"type": "governance.task_pair_created", "ts": 1001, "session_id": "s1", "data": {}},
            {"type": "x", "ts": 1002, "session_id": "s1", "data": {"verdict": "approved"}},
            {"type": "x", "ts": 1003, "session_id": "s1", "data": {"verdict": "blocked", "status": "blocked"}},
            {"type": "x", "ts": 1004, "session_id": "s1", "data": {"verdict": "blocked", "status": "blocked"}},
            {"type": "x", "ts": 1005, "session_id": "s1", "data": {"verdict": "blocked", "status": "blocked"}},
            {"type": "x", "ts": 1006, "session_id": "s1", "data": {"verdict": "blocked", "status": "blocked"}},
        ]
        summary = stats_db.ingest_events(events)
        anomalies = detector.check(summary, stats_db)
        block_anoms = [a for a in anomalies if a["type"] == "high_block_rate"]
        assert len(block_anoms) == 1
        assert block_anoms[0]["severity"] == "warning"

    def test_no_anomaly_when_below_threshold(self, detector, stats_db):
        events = [
            {"type": "governance.task_pair_created", "ts": 1000, "session_id": "s1", "data": {}},
            {"type": "governance.task_pair_created", "ts": 1001, "session_id": "s1", "data": {}},
            {"type": "x", "ts": 1002, "session_id": "s1", "data": {"verdict": "approved"}},
            {"type": "x", "ts": 1003, "session_id": "s1", "data": {"verdict": "approved"}},
        ]
        summary = stats_db.ingest_events(events)
        anomalies = detector.check(summary, stats_db)
        block_anoms = [a for a in anomalies if a["type"] == "high_block_rate"]
        assert len(block_anoms) == 0


class TestIdleBlocks:
    def test_detects_repeated_idle_blocks(self, detector, stats_db):
        events = [{"type": "agent.idle_blocked", "ts": 1000 + i, "session_id": "s1", "data": {}} for i in range(5)]
        summary = stats_db.ingest_events(events)
        anomalies = detector.check(summary, stats_db)
        idle_anoms = [a for a in anomalies if a["type"] == "repeated_idle_blocks"]
        assert len(idle_anoms) == 1
        assert idle_anoms[0]["metric_values"]["idle_blocks"] == 5

    def test_no_anomaly_below_threshold(self, detector, stats_db):
        events = [
            {"type": "agent.idle_blocked", "ts": 1000, "session_id": "s1", "data": {}},
            {"type": "agent.idle_blocked", "ts": 1001, "session_id": "s1", "data": {}},
        ]
        summary = stats_db.ingest_events(events)
        anomalies = detector.check(summary, stats_db)
        idle_anoms = [a for a in anomalies if a["type"] == "repeated_idle_blocks"]
        assert len(idle_anoms) == 0


class TestReinforcementSkips:
    def test_detects_high_skip_rate(self, detector, stats_db):
        events = [
            {"type": "context.reinforcement_skipped", "ts": 1000 + i, "session_id": "s1", "data": {}} for i in range(8)
        ] + [
            {"type": "context.reinforcement_injected", "ts": 1100, "session_id": "s1", "data": {}},
        ]
        summary = stats_db.ingest_events(events)
        anomalies = detector.check(summary, stats_db)
        skip_anoms = [a for a in anomalies if a["type"] == "high_reinforcement_skip_rate"]
        assert len(skip_anoms) == 1

    def test_no_anomaly_when_balanced(self, detector, stats_db):
        events = [
            {"type": "context.reinforcement_skipped", "ts": 1000, "session_id": "s1", "data": {}},
            {"type": "context.reinforcement_injected", "ts": 1001, "session_id": "s1", "data": {}},
            {"type": "context.reinforcement_injected", "ts": 1002, "session_id": "s1", "data": {}},
            {"type": "context.reinforcement_injected", "ts": 1003, "session_id": "s1", "data": {}},
        ]
        summary = stats_db.ingest_events(events)
        anomalies = detector.check(summary, stats_db)
        skip_anoms = [a for a in anomalies if a["type"] == "high_reinforcement_skip_rate"]
        assert len(skip_anoms) == 0


class TestEventRateSpike:
    def test_detects_spike_vs_baseline(self, detector, stats_db):
        # Set a low baseline
        stats_db.update_metric_window("events_per_hour", 2.0)

        # Batch with many events
        events = [{"type": "test.event", "ts": 1000 + i, "session_id": "s1", "data": {}} for i in range(10)]
        summary = stats_db.ingest_events(events)
        anomalies = detector.check(summary, stats_db)
        spike_anoms = [a for a in anomalies if a["type"] == "event_rate_spike"]
        assert len(spike_anoms) == 1

    def test_no_spike_when_no_baseline(self, detector, stats_db):
        events = [{"type": "test.event", "ts": 1000 + i, "session_id": "s1", "data": {}} for i in range(10)]
        summary = stats_db.ingest_events(events)
        anomalies = detector.check(summary, stats_db)
        spike_anoms = [a for a in anomalies if a["type"] == "event_rate_spike"]
        assert len(spike_anoms) == 0  # No baseline = no spike detection


class TestEmptyBatch:
    def test_no_anomalies_for_empty_batch(self, detector, stats_db):
        anomalies = detector.check({"total": 0, "by_type": {}}, stats_db)
        assert anomalies == []
