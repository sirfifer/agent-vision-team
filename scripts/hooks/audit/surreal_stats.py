"""SurrealStatsAccumulator: SurrealDB-backed rolling aggregate statistics for audit events.

Drop-in replacement for StatsAccumulator that uses the shared AVT SurrealDB
instance. Tables `audit_event`, `event_count`, `session_summary`,
`metric_window`, and `anomaly` are defined in the shared schema (avt_db.schema).

The emitter (emitter.py) stays as JSONL for the TAP guarantee (<5ms).
Only the statistics accumulator layer changes.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Resolve the shared avt_db package
# ---------------------------------------------------------------------------
_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
_SHARED_DIR = str(Path(_PROJECT_DIR) / "shared")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)


class SurrealStatsAccumulator:
    """SurrealDB-backed statistics accumulator for audit events.

    Same interface as StatsAccumulator (SQLite version). All methods are
    synchronous since hook scripts run synchronously.
    """

    def __init__(self, db_path: str = ".avt/avt.db") -> None:
        from surrealdb import Surreal
        from avt_db.schema import apply_schema_sync

        full_path = Path(_PROJECT_DIR) / db_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = Surreal(f"surrealkv://{full_path}")
        self._db.connect()
        self._db.use("avt", "main")
        apply_schema_sync(self._db)

    # ------------------------------------------------------------------
    # Event ingestion
    # ------------------------------------------------------------------

    def ingest_events(self, events: list[dict]) -> dict:
        """Ingest a batch of events, updating counts and session summaries.

        Returns a summary dict with counts for use by anomaly detection.
        """
        if not events:
            return {"total": 0, "by_type": {}}

        by_type: dict[str, int] = {}
        sessions_seen: dict[str, list[dict]] = {}

        for event in events:
            etype = event.get("type", "unknown")
            by_type[etype] = by_type.get(etype, 0) + 1

            sid = event.get("session_id", "")
            if sid:
                sessions_seen.setdefault(sid, []).append(event)

        # Update hourly buckets using UPSERT
        now = time.time()
        bucket = time.strftime("%Y-%m-%dT%H", time.gmtime(now))
        for etype, count in by_type.items():
            # Check if record exists, then upsert
            existing = self._db.query(
                "SELECT count FROM event_count "
                "WHERE bucket = $b AND event_type = $t",
                {"b": bucket, "t": etype},
            )
            if existing and len(existing) > 0:
                old_count = existing[0].get("count", 0)
                self._db.query(
                    "UPDATE event_count SET count = $new_count "
                    "WHERE bucket = $b AND event_type = $t",
                    {"new_count": old_count + count, "b": bucket, "t": etype},
                )
            else:
                self._db.query(
                    "CREATE event_count SET "
                    "bucket = $b, event_type = $t, count = $c",
                    {"b": bucket, "t": etype, "c": count},
                )

        # Update session summaries
        for sid, session_events in sessions_seen.items():
            timestamps = [e.get("ts", 0) for e in session_events]
            min_ts = min(timestamps) if timestamps else 0
            max_ts = max(timestamps) if timestamps else 0

            approvals = sum(
                1
                for e in session_events
                if e.get("data", {}).get("verdict") == "approved"
                or (e.get("data", {}).get("allowed") is True)
            )
            blocks = sum(
                1
                for e in session_events
                if e.get("data", {}).get("verdict") == "blocked"
                or e.get("data", {}).get("status") == "blocked"
            )
            gate_blocks = sum(
                1
                for e in session_events
                if e.get("type", "").endswith("_attempted")
                and e.get("data", {}).get("allowed") is False
            )
            gate_allows = sum(
                1
                for e in session_events
                if e.get("type", "").endswith("_attempted")
                and e.get("data", {}).get("allowed") is True
            )
            skips = sum(1 for e in session_events if "skipped" in e.get("type", ""))
            tasks = sum(
                1
                for e in session_events
                if e.get("type") == "governance.task_pair_created"
            )

            # Check if session summary exists
            existing = self._db.query(
                "SELECT * FROM session_summary WHERE session_id = $sid",
                {"sid": sid},
            )
            if existing and len(existing) > 0:
                row = existing[0]
                self._db.query(
                    "UPDATE session_summary SET "
                    "first_event_ts = $first_ts, "
                    "last_event_ts = $last_ts, "
                    "total_events = total_events + $n, "
                    "approval_count = approval_count + $approvals, "
                    "block_count = block_count + $blocks, "
                    "gate_block_count = gate_block_count + $gate_blocks, "
                    "gate_allow_count = gate_allow_count + $gate_allows, "
                    "skip_count = skip_count + $skips, "
                    "task_count = task_count + $tasks "
                    "WHERE session_id = $sid",
                    {
                        "first_ts": min(row.get("first_event_ts", min_ts), min_ts),
                        "last_ts": max(row.get("last_event_ts", max_ts), max_ts),
                        "n": len(session_events),
                        "approvals": approvals,
                        "blocks": blocks,
                        "gate_blocks": gate_blocks,
                        "gate_allows": gate_allows,
                        "skips": skips,
                        "tasks": tasks,
                        "sid": sid,
                    },
                )
            else:
                self._db.query(
                    "CREATE session_summary SET "
                    "session_id = $sid, "
                    "first_event_ts = $first_ts, "
                    "last_event_ts = $last_ts, "
                    "total_events = $n, "
                    "approval_count = $approvals, "
                    "block_count = $blocks, "
                    "gate_block_count = $gate_blocks, "
                    "gate_allow_count = $gate_allows, "
                    "skip_count = $skips, "
                    "task_count = $tasks",
                    {
                        "sid": sid,
                        "first_ts": min_ts,
                        "last_ts": max_ts,
                        "n": len(session_events),
                        "approvals": approvals,
                        "blocks": blocks,
                        "gate_blocks": gate_blocks,
                        "gate_allows": gate_allows,
                        "skips": skips,
                        "tasks": tasks,
                    },
                )

        return {
            "total": len(events),
            "by_type": by_type,
            "sessions_touched": list(sessions_seen.keys()),
        }

    # ------------------------------------------------------------------
    # Metric windows
    # ------------------------------------------------------------------

    def update_metric_window(
        self,
        metric_name: str,
        value: float,
        sample_count: int = 1,
    ) -> None:
        """Record a metric window value for baseline tracking."""
        now = time.time()
        window_start = now - (now % 3600)
        window_end = window_start + 3600

        existing = self._db.query(
            "SELECT value, sample_count FROM metric_window "
            "WHERE metric_name = $mn AND window_start = $ws",
            {"mn": metric_name, "ws": window_start},
        )
        if existing and len(existing) > 0:
            old = existing[0]
            old_val = old.get("value", 0)
            old_cnt = old.get("sample_count", 0)
            new_cnt = old_cnt + sample_count
            new_val = (old_val * old_cnt + value * sample_count) / new_cnt if new_cnt > 0 else value
            self._db.query(
                "UPDATE metric_window SET "
                "value = $v, sample_count = $sc "
                "WHERE metric_name = $mn AND window_start = $ws",
                {"v": new_val, "sc": new_cnt, "mn": metric_name, "ws": window_start},
            )
        else:
            self._db.query(
                "CREATE metric_window SET "
                "metric_name = $mn, "
                "window_start = $ws, "
                "window_end = $we, "
                "value = $v, "
                "sample_count = $sc",
                {
                    "mn": metric_name,
                    "ws": window_start,
                    "we": window_end,
                    "v": value,
                    "sc": sample_count,
                },
            )

    # ------------------------------------------------------------------
    # Anomaly recording
    # ------------------------------------------------------------------

    def record_anomaly(
        self,
        anomaly_id: str,
        anomaly_type: str,
        severity: str,
        description: str,
        metric_values: "dict | None" = None,
        context: "dict | None" = None,
    ) -> None:
        """Record a detected anomaly."""
        now = time.time()
        # Use UPSERT-style: delete then create for idempotency
        self._db.query(
            "DELETE type::thing('anomaly', $aid)",
            {"aid": anomaly_id},
        )
        self._db.query(
            "CREATE type::thing('anomaly', $aid) SET "
            "detected_at = $ts, "
            "anomaly_type = $atype, "
            "severity = $sev, "
            "description = $desc, "
            "metric_values = $mv, "
            "context = $ctx, "
            "escalated = false",
            {
                "aid": anomaly_id,
                "ts": now,
                "atype": anomaly_type,
                "sev": severity,
                "desc": description,
                "mv": metric_values,
                "ctx": context,
            },
        )

    def mark_anomaly_escalated(self, anomaly_id: str) -> None:
        """Mark an anomaly as escalated (sent to LLM analysis)."""
        self._db.query(
            "UPDATE type::thing('anomaly', $aid) SET escalated = true",
            {"aid": anomaly_id},
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_recent_event_rate(self, hours: int = 1) -> dict:
        """Get event counts for the last N hours, grouped by type."""
        cutoff_ts = time.time() - (hours * 3600)
        cutoff_bucket = time.strftime("%Y-%m-%dT%H", time.gmtime(cutoff_ts))
        results = self._db.query(
            "SELECT event_type, math::sum(count) AS total "
            "FROM event_count "
            "WHERE bucket >= $cb "
            "GROUP BY event_type",
            {"cb": cutoff_bucket},
        )
        return {
            row["event_type"]: row["total"]
            for row in (results or [])
        }

    def get_baseline_rate(self, metric_name: str, window_hours: int = 24) -> Optional[float]:
        """Get the average rate for a metric over a time window."""
        cutoff = time.time() - (window_hours * 3600)
        results = self._db.query(
            "SELECT math::mean(value) AS avg_val, count() AS cnt "
            "FROM metric_window "
            "WHERE metric_name = $mn AND window_start >= $cutoff "
            "GROUP ALL",
            {"mn": metric_name, "cutoff": cutoff},
        )
        if results and len(results) > 0:
            row = results[0]
            if row.get("cnt", 0) > 0:
                return row.get("avg_val")
        return None

    def get_session_summary(self, session_id: str) -> Optional[dict]:
        """Get the summary for a specific session."""
        results = self._db.query(
            "SELECT * FROM session_summary WHERE session_id = $sid",
            {"sid": session_id},
        )
        if results and len(results) > 0:
            row = results[0]
            # Return a dict matching the SQLite version's column names
            return {
                "session_id": row.get("session_id"),
                "first_event_ts": row.get("first_event_ts"),
                "last_event_ts": row.get("last_event_ts"),
                "total_events": row.get("total_events", 0),
                "approval_count": row.get("approval_count", 0),
                "block_count": row.get("block_count", 0),
                "gate_block_count": row.get("gate_block_count", 0),
                "gate_allow_count": row.get("gate_allow_count", 0),
                "skip_count": row.get("skip_count", 0),
                "task_count": row.get("task_count", 0),
            }
        return None

    def get_recent_anomalies(self, hours: int = 24) -> list[dict]:
        """Get anomalies detected in the last N hours."""
        cutoff = time.time() - (hours * 3600)
        results = self._db.query(
            "SELECT * FROM anomaly "
            "WHERE detected_at >= $cutoff "
            "ORDER BY detected_at DESC",
            {"cutoff": cutoff},
        )
        return [_normalize_anomaly(row) for row in (results or [])]

    def get_unescalated_anomalies(self) -> list[dict]:
        """Get anomalies that haven't been escalated yet."""
        results = self._db.query(
            "SELECT * FROM anomaly "
            "WHERE escalated = false "
            "ORDER BY detected_at DESC"
        )
        return [_normalize_anomaly(row) for row in (results or [])]

    # ------------------------------------------------------------------
    # Pruning
    # ------------------------------------------------------------------

    def prune_old_data(self, max_age_days: int = 30) -> int:
        """Remove data older than max_age_days. Returns rows deleted."""
        cutoff_ts = time.time() - (max_age_days * 86400)
        cutoff_bucket = time.strftime("%Y-%m-%dT%H", time.gmtime(cutoff_ts))

        deleted = 0

        # Count before delete for event_count
        before = self._db.query(
            "SELECT count() AS cnt FROM event_count WHERE bucket < $cb GROUP ALL",
            {"cb": cutoff_bucket},
        )
        if before and len(before) > 0:
            deleted += before[0].get("cnt", 0)
        self._db.query(
            "DELETE event_count WHERE bucket < $cb",
            {"cb": cutoff_bucket},
        )

        # metric_window
        before = self._db.query(
            "SELECT count() AS cnt FROM metric_window WHERE window_end < $ct GROUP ALL",
            {"ct": cutoff_ts},
        )
        if before and len(before) > 0:
            deleted += before[0].get("cnt", 0)
        self._db.query(
            "DELETE metric_window WHERE window_end < $ct",
            {"ct": cutoff_ts},
        )

        # anomaly
        before = self._db.query(
            "SELECT count() AS cnt FROM anomaly WHERE detected_at < $ct GROUP ALL",
            {"ct": cutoff_ts},
        )
        if before and len(before) > 0:
            deleted += before[0].get("cnt", 0)
        self._db.query(
            "DELETE anomaly WHERE detected_at < $ct",
            {"ct": cutoff_ts},
        )

        return deleted

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        try:
            self._db.close()
        except Exception:
            pass


def _normalize_anomaly(row: dict) -> dict:
    """Normalize a SurrealDB anomaly row to match the SQLite dict format."""
    raw_id = row.get("id", "")
    short_id = raw_id.split(":", 1)[1] if isinstance(raw_id, str) and ":" in raw_id else str(raw_id)

    return {
        "id": short_id,
        "detected_at": row.get("detected_at"),
        "anomaly_type": row.get("anomaly_type"),
        "severity": row.get("severity"),
        "description": row.get("description"),
        "metric_values": row.get("metric_values"),
        "context": row.get("context"),
        "escalated": 1 if row.get("escalated") else 0,
    }
