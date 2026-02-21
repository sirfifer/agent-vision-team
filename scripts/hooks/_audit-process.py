#!/usr/bin/env python3
"""Audit processor: reads new events, updates statistics, checks anomalies.

Spawned by _audit-settle-check.py after activity settles.
Uses file-based locking to prevent concurrent runs.
Exits quickly (~5ms) when nothing noteworthy is found.
On anomaly detection, spawns the escalation chain as a detached subprocess.

Usage: _audit-process.py

Environment:
    CLAUDE_PROJECT_DIR: Project root directory
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
AUDIT_DIR = Path(PROJECT_DIR) / ".avt" / "audit"
EVENTS_PATH = AUDIT_DIR / "events.jsonl"
CHECKPOINT_PATH = AUDIT_DIR / "checkpoint.json"
LOCK_PATH = AUDIT_DIR / ".processor-lock"
LOG_PATH = AUDIT_DIR / "audit.log"
STATS_DB_PATH = AUDIT_DIR / "statistics.db"

# Maximum events.jsonl size before rotation (10MB)
MAX_EVENTS_SIZE = 10 * 1024 * 1024


def _log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] [audit-process] {msg}\n")
    except Exception:
        pass


def _acquire_lock() -> "int | None":
    """Acquire processor lock. Returns fd on success, None on failure."""
    try:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(LOCK_PATH), os.O_WRONLY | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.write(fd, str(os.getpid()).encode())
        return fd
    except (OSError, IOError):
        return None


def _release_lock(fd: int) -> None:
    """Release processor lock."""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def _load_checkpoint() -> dict:
    """Load the last-processed checkpoint (byte offset + event count)."""
    if not CHECKPOINT_PATH.exists():
        return {"byte_offset": 0, "event_count": 0, "last_processed_ts": 0}
    try:
        return json.loads(CHECKPOINT_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"byte_offset": 0, "event_count": 0, "last_processed_ts": 0}


def _save_checkpoint(checkpoint: dict) -> None:
    """Save checkpoint atomically."""
    tmp = CHECKPOINT_PATH.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(checkpoint))
        tmp.rename(CHECKPOINT_PATH)
    except OSError as e:
        _log(f"Error saving checkpoint: {e}")
        try:
            tmp.unlink()
        except OSError:
            pass


def _read_new_events(byte_offset: int) -> tuple[list[dict], int]:
    """Read events from events.jsonl starting at byte_offset.

    Returns (events, new_byte_offset).
    """
    if not EVENTS_PATH.exists():
        return [], byte_offset

    events = []
    try:
        with open(EVENTS_PATH, "r") as f:
            # If offset is beyond file size (e.g. after rotation), reset
            f.seek(0, 2)  # seek to end
            file_size = f.tell()
            if byte_offset > file_size:
                byte_offset = 0

            f.seek(byte_offset)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # Skip corrupt lines
            new_offset = f.tell()
    except OSError as e:
        _log(f"Error reading events: {e}")
        return [], byte_offset

    return events, new_offset


def _check_anomalies(batch_summary: dict, stats) -> list[dict]:
    """Check for anomalies using the AnomalyDetector module.

    This is a lightweight, pure-Python threshold check. No LLM calls.
    """
    if batch_summary.get("total", 0) == 0:
        return []

    try:
        hooks_dir = Path(PROJECT_DIR) / "scripts" / "hooks"
        sys.path.insert(0, str(hooks_dir))
        from audit.anomaly import AnomalyDetector
        from audit.config import load_audit_config

        cfg = load_audit_config()
        detector = AnomalyDetector(thresholds=cfg.get("thresholds", {}))
        return detector.check(batch_summary, stats)
    except Exception as e:
        _log(f"Anomaly detection error: {e}")
        return []


def _rotate_events_if_needed() -> None:
    """Rotate events.jsonl if it exceeds MAX_EVENTS_SIZE."""
    if not EVENTS_PATH.exists():
        return
    try:
        size = EVENTS_PATH.stat().st_size
        if size <= MAX_EVENTS_SIZE:
            return
        import gzip

        rotated = EVENTS_PATH.with_suffix(f".{time.strftime('%Y%m%d%H%M%S')}.jsonl.gz")
        with open(EVENTS_PATH, "rb") as f_in, gzip.open(rotated, "wb") as f_out:
            f_out.writelines(f_in)
        # Truncate the original
        EVENTS_PATH.write_text("")
        _log(f"Rotated events.jsonl to {rotated.name} ({size} bytes)")
    except Exception as e:
        _log(f"Event rotation failed: {e}")


def _spawn_escalation(anomalies: list[dict]) -> None:
    """Spawn the escalation chain as a detached subprocess."""
    escalate_script = Path(PROJECT_DIR) / "scripts" / "hooks" / "_audit-escalate.py"
    if not escalate_script.exists():
        _log("Escalation script not found; skipping")
        return

    # Write anomalies to a temp file for the escalation chain
    anomalies_path = AUDIT_DIR / ".pending-anomalies.json"
    try:
        anomalies_path.write_text(json.dumps(anomalies, indent=2))
    except OSError as e:
        _log(f"Failed to write anomalies for escalation: {e}")
        return

    try:
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = PROJECT_DIR
        subprocess.Popen(
            ["python3", str(escalate_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        _log(f"Escalation chain spawned for {len(anomalies)} anomalies")
    except Exception as e:
        _log(f"Failed to spawn escalation: {e}")


def main() -> int:
    start = time.time()
    _log("Processor started")

    # Acquire exclusive lock
    lock_fd = _acquire_lock()
    if lock_fd is None:
        _log("Could not acquire lock; another processor is running")
        return 0

    try:
        # Load checkpoint
        checkpoint = _load_checkpoint()
        byte_offset = checkpoint.get("byte_offset", 0)

        # Read new events since last checkpoint
        events, new_offset = _read_new_events(byte_offset)
        if not events:
            _log("No new events; exiting")
            return 0

        _log(f"Read {len(events)} new events (offset {byte_offset} -> {new_offset})")

        # Initialize stats accumulator
        hooks_dir = Path(PROJECT_DIR) / "scripts" / "hooks"
        sys.path.insert(0, str(hooks_dir))
        from audit.stats import StatsAccumulator

        stats = StatsAccumulator(db_path=STATS_DB_PATH)

        try:
            # Ingest events into statistics
            batch_summary = stats.ingest_events(events)
            _log(f"Ingested: {batch_summary['total']} events, {len(batch_summary['by_type'])} types")

            # Update hourly event rate metric window
            stats.update_metric_window("events_per_hour", float(len(events)))

            # Check anomaly thresholds
            anomalies = _check_anomalies(batch_summary, stats)

            if anomalies:
                _log(f"Detected {len(anomalies)} anomalies")

                # Record anomalies in stats DB and create recommendations
                try:
                    from audit.recommendations import RecommendationManager

                    rec_mgr = RecommendationManager()
                except Exception:
                    rec_mgr = None

                for anom in anomalies:
                    stats.record_anomaly(
                        anomaly_id=anom["id"],
                        anomaly_type=anom["type"],
                        severity=anom["severity"],
                        description=anom["description"],
                        metric_values=anom.get("metric_values"),
                    )
                    if rec_mgr is not None:
                        rec_mgr.create_from_anomaly(anom)

                # Check if LLM escalation is enabled
                try:
                    from audit.config import load_audit_config

                    cfg = load_audit_config()
                    if cfg.get("llm_analysis_enabled", True):
                        escalatable = [a for a in anomalies if a.get("severity") in ("warning", "critical")]
                        if escalatable:
                            _spawn_escalation(escalatable)
                except Exception:
                    pass
            else:
                _log("No anomalies detected")

            # Prune old data periodically (every ~100 batches)
            if checkpoint.get("event_count", 0) % 100 < len(events):
                try:
                    deleted = stats.prune_old_data(max_age_days=30)
                    if deleted > 0:
                        _log(f"Pruned {deleted} old records")
                except Exception:
                    pass

            # Rotate events.jsonl if too large
            _rotate_events_if_needed()

        finally:
            stats.close()

        # Save new checkpoint
        _save_checkpoint(
            {
                "byte_offset": new_offset,
                "event_count": checkpoint.get("event_count", 0) + len(events),
                "last_processed_ts": time.time(),
            }
        )

        elapsed = (time.time() - start) * 1000
        _log(f"Processor finished in {elapsed:.1f}ms ({len(events)} events, {len(anomalies)} anomalies)")

    finally:
        _release_lock(lock_fd)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        _log(f"ERROR: {e}")
        # Clean up lock on crash
        LOCK_PATH.unlink(missing_ok=True)
        sys.exit(0)  # Never fail loudly; background process
