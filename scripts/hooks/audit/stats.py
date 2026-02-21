"""StatsAccumulator: SQLite-backed rolling aggregate statistics for audit events.

Maintains hourly/daily/weekly event counts, per-session summaries, metric
windows, and anomaly records. All writes are batched UPSERTs for efficiency.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path


class StatsAccumulator:
    """SQLite-backed statistics accumulator for audit events."""

    def __init__(self, db_path: "Path | str") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: "sqlite3.Connection | None" = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            -- Hourly event count buckets
            CREATE TABLE IF NOT EXISTS event_counts (
                bucket TEXT NOT NULL,
                event_type TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (bucket, event_type)
            );

            -- Per-session summaries
            CREATE TABLE IF NOT EXISTS session_summaries (
                session_id TEXT PRIMARY KEY,
                first_event_ts REAL,
                last_event_ts REAL,
                total_events INTEGER NOT NULL DEFAULT 0,
                approval_count INTEGER NOT NULL DEFAULT 0,
                block_count INTEGER NOT NULL DEFAULT 0,
                gate_block_count INTEGER NOT NULL DEFAULT 0,
                gate_allow_count INTEGER NOT NULL DEFAULT 0,
                skip_count INTEGER NOT NULL DEFAULT 0,
                task_count INTEGER NOT NULL DEFAULT 0
            );

            -- Rolling metric windows for baseline comparisons
            CREATE TABLE IF NOT EXISTS metric_windows (
                metric_name TEXT NOT NULL,
                window_start REAL NOT NULL,
                window_end REAL NOT NULL,
                value REAL NOT NULL,
                sample_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (metric_name, window_start)
            );

            -- Detected anomaly records
            CREATE TABLE IF NOT EXISTS anomalies (
                id TEXT PRIMARY KEY,
                detected_at REAL NOT NULL,
                anomaly_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'warning',
                description TEXT NOT NULL,
                metric_values TEXT,
                context TEXT,
                escalated INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_event_counts_bucket
                ON event_counts(bucket);
            CREATE INDEX IF NOT EXISTS idx_anomalies_type
                ON anomalies(anomaly_type);
            CREATE INDEX IF NOT EXISTS idx_anomalies_detected
                ON anomalies(detected_at);
        """)
        conn.commit()

    def ingest_events(self, events: list[dict]) -> dict:
        """Ingest a batch of events, updating counts and session summaries.

        Returns a summary dict with counts for use by anomaly detection.
        """
        if not events:
            return {"total": 0, "by_type": {}}

        conn = self._get_conn()
        by_type: dict[str, int] = {}
        sessions_seen: dict[str, list[dict]] = {}

        for event in events:
            etype = event.get("type", "unknown")
            by_type[etype] = by_type.get(etype, 0) + 1

            sid = event.get("session_id", "")
            if sid:
                sessions_seen.setdefault(sid, []).append(event)

        # Update hourly buckets
        now = time.time()
        bucket = time.strftime("%Y-%m-%dT%H", time.gmtime(now))
        for etype, count in by_type.items():
            conn.execute(
                """INSERT INTO event_counts (bucket, event_type, count)
                   VALUES (?, ?, ?)
                   ON CONFLICT(bucket, event_type)
                   DO UPDATE SET count = count + excluded.count""",
                (bucket, etype, count),
            )

        # Update session summaries
        for sid, session_events in sessions_seen.items():
            timestamps = [e.get("ts", 0) for e in session_events]
            min_ts = min(timestamps) if timestamps else 0
            max_ts = max(timestamps) if timestamps else 0

            approvals = sum(
                1
                for e in session_events
                if e.get("data", {}).get("verdict") == "approved" or (e.get("data", {}).get("allowed") is True)
            )
            blocks = sum(
                1
                for e in session_events
                if e.get("data", {}).get("verdict") == "blocked" or e.get("data", {}).get("status") == "blocked"
            )
            gate_blocks = sum(
                1
                for e in session_events
                if e.get("type", "").endswith("_attempted") and e.get("data", {}).get("allowed") is False
            )
            gate_allows = sum(
                1
                for e in session_events
                if e.get("type", "").endswith("_attempted") and e.get("data", {}).get("allowed") is True
            )
            skips = sum(1 for e in session_events if "skipped" in e.get("type", ""))
            tasks = sum(1 for e in session_events if e.get("type") == "governance.task_pair_created")

            conn.execute(
                """INSERT INTO session_summaries
                   (session_id, first_event_ts, last_event_ts, total_events,
                    approval_count, block_count, gate_block_count,
                    gate_allow_count, skip_count, task_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET
                    first_event_ts = MIN(first_event_ts, excluded.first_event_ts),
                    last_event_ts = MAX(last_event_ts, excluded.last_event_ts),
                    total_events = total_events + excluded.total_events,
                    approval_count = approval_count + excluded.approval_count,
                    block_count = block_count + excluded.block_count,
                    gate_block_count = gate_block_count + excluded.gate_block_count,
                    gate_allow_count = gate_allow_count + excluded.gate_allow_count,
                    skip_count = skip_count + excluded.skip_count,
                    task_count = task_count + excluded.task_count""",
                (sid, min_ts, max_ts, len(session_events), approvals, blocks, gate_blocks, gate_allows, skips, tasks),
            )

        conn.commit()

        return {
            "total": len(events),
            "by_type": by_type,
            "sessions_touched": list(sessions_seen.keys()),
        }

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
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO anomalies
               (id, detected_at, anomaly_type, severity, description,
                metric_values, context)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                anomaly_id,
                time.time(),
                anomaly_type,
                severity,
                description,
                json.dumps(metric_values) if metric_values else None,
                json.dumps(context) if context else None,
            ),
        )
        conn.commit()

    def get_recent_event_rate(self, hours: int = 1) -> dict:
        """Get event counts for the last N hours, grouped by type."""
        conn = self._get_conn()
        cutoff_ts = time.time() - (hours * 3600)
        cutoff_bucket = time.strftime("%Y-%m-%dT%H", time.gmtime(cutoff_ts))
        rows = conn.execute(
            """SELECT event_type, SUM(count) as total
               FROM event_counts
               WHERE bucket >= ?
               GROUP BY event_type""",
            (cutoff_bucket,),
        ).fetchall()
        return {row["event_type"]: row["total"] for row in rows}

    def get_baseline_rate(self, metric_name: str, window_hours: int = 24) -> "float | None":
        """Get the average rate for a metric over a time window."""
        conn = self._get_conn()
        cutoff = time.time() - (window_hours * 3600)
        row = conn.execute(
            """SELECT AVG(value) as avg_val, COUNT(*) as cnt
               FROM metric_windows
               WHERE metric_name = ? AND window_start >= ?""",
            (metric_name, cutoff),
        ).fetchone()
        if row and row["cnt"] > 0:
            return row["avg_val"]
        return None

    def update_metric_window(
        self,
        metric_name: str,
        value: float,
        sample_count: int = 1,
    ) -> None:
        """Record a metric window value for baseline tracking."""
        now = time.time()
        # Use hourly windows
        window_start = now - (now % 3600)
        window_end = window_start + 3600

        conn = self._get_conn()
        conn.execute(
            """INSERT INTO metric_windows
               (metric_name, window_start, window_end, value, sample_count)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(metric_name, window_start)
               DO UPDATE SET
                value = (value * sample_count + excluded.value * excluded.sample_count)
                        / (sample_count + excluded.sample_count),
                sample_count = sample_count + excluded.sample_count""",
            (metric_name, window_start, window_end, value, sample_count),
        )
        conn.commit()

    def get_session_summary(self, session_id: str) -> "dict | None":
        """Get the summary for a specific session."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM session_summaries WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_recent_anomalies(self, hours: int = 24) -> list[dict]:
        """Get anomalies detected in the last N hours."""
        conn = self._get_conn()
        cutoff = time.time() - (hours * 3600)
        rows = conn.execute(
            """SELECT * FROM anomalies
               WHERE detected_at >= ?
               ORDER BY detected_at DESC""",
            (cutoff,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_unescalated_anomalies(self) -> list[dict]:
        """Get anomalies that haven't been escalated yet."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM anomalies
               WHERE escalated = 0
               ORDER BY detected_at DESC""",
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_anomaly_escalated(self, anomaly_id: str) -> None:
        """Mark an anomaly as escalated (sent to LLM analysis)."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE anomalies SET escalated = 1 WHERE id = ?",
            (anomaly_id,),
        )
        conn.commit()

    def prune_old_data(self, max_age_days: int = 30) -> int:
        """Remove data older than max_age_days. Returns rows deleted."""
        conn = self._get_conn()
        cutoff_ts = time.time() - (max_age_days * 86400)
        cutoff_bucket = time.strftime("%Y-%m-%dT%H", time.gmtime(cutoff_ts))

        deleted = 0
        cur = conn.execute("DELETE FROM event_counts WHERE bucket < ?", (cutoff_bucket,))
        deleted += cur.rowcount

        cur = conn.execute("DELETE FROM metric_windows WHERE window_end < ?", (cutoff_ts,))
        deleted += cur.rowcount

        cur = conn.execute("DELETE FROM anomalies WHERE detected_at < ?", (cutoff_ts,))
        deleted += cur.rowcount

        conn.commit()
        return deleted

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
