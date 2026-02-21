"""Anomaly detection: pure-Python threshold checks on audit statistics.

No LLM calls. Compares current metrics against configured thresholds
and rolling baselines. Returns anomaly records for further processing.
"""

from __future__ import annotations

from uuid import uuid4


class AnomalyDetector:
    """Threshold-based anomaly detector for audit event batches."""

    def __init__(self, thresholds: "dict | None" = None) -> None:
        self.thresholds = thresholds or {}

    def check(self, batch_summary: dict, stats: "object") -> list[dict]:
        """Run all anomaly checks against the current batch.

        Args:
            batch_summary: Output of StatsAccumulator.ingest_events()
            stats: StatsAccumulator instance for baseline queries

        Returns:
            List of anomaly dicts with id, type, severity, description, metric_values
        """
        anomalies: list[dict] = []

        anomalies.extend(self._check_block_rate(batch_summary, stats))
        anomalies.extend(self._check_gate_block_rate(batch_summary, stats))
        anomalies.extend(self._check_event_rate_spike(batch_summary, stats))
        anomalies.extend(self._check_idle_blocks(batch_summary))
        anomalies.extend(self._check_reinforcement_skips(batch_summary))

        return anomalies

    def _check_block_rate(self, batch_summary: dict, stats: "object") -> list[dict]:
        """Detect high governance block rates per session."""
        anomalies = []
        threshold = self.thresholds.get("governance_block_rate", 0.5)

        for sid in batch_summary.get("sessions_touched", []):
            summary = stats.get_session_summary(sid)
            if not summary or summary["task_count"] < 2:
                continue
            total_decisions = summary["approval_count"] + summary["block_count"]
            if total_decisions == 0:
                continue
            block_rate = summary["block_count"] / total_decisions
            if block_rate > threshold:
                anomalies.append(
                    {
                        "id": f"anom-{uuid4().hex[:8]}",
                        "type": "high_block_rate",
                        "severity": "warning",
                        "description": (
                            f"Session {sid[:8]} has {block_rate:.0%} block rate "
                            f"({summary['block_count']}/{total_decisions} decisions blocked)"
                        ),
                        "metric_values": {
                            "session_id": sid,
                            "block_rate": block_rate,
                            "block_count": summary["block_count"],
                            "total_decisions": total_decisions,
                        },
                    }
                )
        return anomalies

    def _check_gate_block_rate(self, batch_summary: dict, stats: "object") -> list[dict]:
        """Detect high gate block rates (completion/idle blocks)."""
        anomalies = []
        for sid in batch_summary.get("sessions_touched", []):
            summary = stats.get_session_summary(sid)
            if not summary:
                continue
            total_gates = summary["gate_block_count"] + summary["gate_allow_count"]
            if total_gates < 3:
                continue
            gate_block_rate = summary["gate_block_count"] / total_gates
            if gate_block_rate > 0.5:
                anomalies.append(
                    {
                        "id": f"anom-{uuid4().hex[:8]}",
                        "type": "high_gate_block_rate",
                        "severity": "warning",
                        "description": (
                            f"Session {sid[:8]} has {gate_block_rate:.0%} gate block rate "
                            f"({summary['gate_block_count']}/{total_gates} gates blocked)"
                        ),
                        "metric_values": {
                            "session_id": sid,
                            "gate_block_rate": gate_block_rate,
                            "gate_block_count": summary["gate_block_count"],
                            "total_gates": total_gates,
                        },
                    }
                )
        return anomalies

    def _check_event_rate_spike(self, batch_summary: dict, stats: "object") -> list[dict]:
        """Detect event rate spikes vs baseline."""
        anomalies = []
        spike_multiplier = self.thresholds.get("event_rate_spike_multiplier", 3.0)
        total = batch_summary.get("total", 0)
        if total == 0:
            return anomalies

        baseline = stats.get_baseline_rate("events_per_hour", window_hours=24)
        if baseline and baseline > 0 and total > baseline * spike_multiplier:
            anomalies.append(
                {
                    "id": f"anom-{uuid4().hex[:8]}",
                    "type": "event_rate_spike",
                    "severity": "info",
                    "description": (
                        f"Event rate spike: {total} events in batch "
                        f"vs {baseline:.1f} baseline ({total / baseline:.1f}x)"
                    ),
                    "metric_values": {
                        "current_rate": total,
                        "baseline": baseline,
                        "multiplier": total / baseline,
                    },
                }
            )
        return anomalies

    def _check_idle_blocks(self, batch_summary: dict) -> list[dict]:
        """Detect repeated idle blocks in a batch."""
        anomalies = []
        threshold = self.thresholds.get("idle_block_count", 3)
        idle_blocks = batch_summary.get("by_type", {}).get("agent.idle_blocked", 0)
        if idle_blocks >= threshold:
            anomalies.append(
                {
                    "id": f"anom-{uuid4().hex[:8]}",
                    "type": "repeated_idle_blocks",
                    "severity": "warning",
                    "description": (f"{idle_blocks} idle blocks in this batch (threshold: {threshold})"),
                    "metric_values": {
                        "idle_blocks": idle_blocks,
                        "threshold": threshold,
                    },
                }
            )
        return anomalies

    def _check_reinforcement_skips(self, batch_summary: dict) -> list[dict]:
        """Detect high context reinforcement skip rates."""
        anomalies = []
        threshold = self.thresholds.get("reinforcement_skip_rate", 0.7)
        by_type = batch_summary.get("by_type", {})
        skips = by_type.get("context.reinforcement_skipped", 0)
        injections = by_type.get("context.reinforcement_injected", 0)
        total = skips + injections
        if total < 3:
            return anomalies
        skip_rate = skips / total
        if skip_rate > threshold:
            anomalies.append(
                {
                    "id": f"anom-{uuid4().hex[:8]}",
                    "type": "high_reinforcement_skip_rate",
                    "severity": "warning",
                    "description": (f"Context reinforcement skip rate: {skip_rate:.0%} ({skips}/{total})"),
                    "metric_values": {
                        "skip_rate": skip_rate,
                        "skips": skips,
                        "injections": injections,
                    },
                }
            )
        return anomalies
