#!/usr/bin/env python3
"""Escalation chain runner: entry point for the tiered LLM escalation.

Spawned by _audit-process.py when warning+ anomalies are detected.
Runs independently as a detached subprocess. Each tier spawns the next
only if warranted. If any tier crashes, prior tier outputs are preserved.

The chain: Haiku triage -> Sonnet analysis -> Opus deep dive

Usage: _audit-escalate.py

Reads anomalies from .avt/audit/.pending-anomalies.json
Writes tier outputs to .avt/audit/{triage,analysis,deep-analysis}.json

Environment:
    CLAUDE_PROJECT_DIR: Project root directory
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
AUDIT_DIR = Path(PROJECT_DIR) / ".avt" / "audit"
PENDING_ANOMALIES_PATH = AUDIT_DIR / ".pending-anomalies.json"
EVENTS_PATH = AUDIT_DIR / "events.jsonl"
LOG_PATH = AUDIT_DIR / "audit.log"
STATS_DB_PATH = AUDIT_DIR / "statistics.db"

# Add hooks dir to path for audit module imports
HOOKS_DIR = Path(PROJECT_DIR) / "scripts" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))


def _log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] [audit-escalate] {msg}\n")
    except Exception:
        pass


def _load_anomalies() -> list[dict]:
    """Load pending anomalies from the temp file written by the processor."""
    if not PENDING_ANOMALIES_PATH.exists():
        return []
    try:
        data = json.loads(PENDING_ANOMALIES_PATH.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _load_recent_events(max_events: int = 200) -> list[dict]:
    """Load the most recent events from events.jsonl."""
    if not EVENTS_PATH.exists():
        return []
    try:
        with open(EVENTS_PATH) as f:
            lines = f.readlines()
        recent = lines[-max_events:] if len(lines) > max_events else lines
        events = []
        for line in recent:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return events
    except OSError:
        return []


def _load_current_settings() -> dict:
    """Load current project settings for context."""
    config_path = Path(PROJECT_DIR) / ".avt" / "project-config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text()).get("settings", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _load_session_summaries() -> list[dict]:
    """Load recent session summaries from statistics.db."""
    try:
        from audit.stats import StatsAccumulator

        stats = StatsAccumulator(db_path=STATS_DB_PATH)
        conn = stats._get_conn()
        rows = conn.execute(
            """SELECT * FROM session_summaries
               ORDER BY last_event_ts DESC LIMIT 10"""
        ).fetchall()
        stats.close()
        return [dict(row) for row in rows]
    except Exception:
        return []


def main() -> int:
    start = time.time()
    _log("Escalation chain started")

    # Load inputs
    anomalies = _load_anomalies()
    if not anomalies:
        _log("No pending anomalies; exiting")
        return 0

    _log(f"Processing {len(anomalies)} anomalies")

    # Load config for model selection
    try:
        from audit.config import load_audit_config

        cfg = load_audit_config()
        models = cfg.get("models", {})
    except Exception:
        models = {}

    # Load directives
    try:
        from audit.prompts import load_directives

        directives = load_directives()
    except Exception:
        directives = []

    # Load existing recommendations
    try:
        from audit.recommendations import RecommendationManager

        rec_mgr = RecommendationManager()
        existing_recs = rec_mgr.get_active()
    except Exception:
        rec_mgr = None
        existing_recs = []

    # Load recent stats summary
    try:
        from audit.stats import StatsAccumulator

        stats = StatsAccumulator(db_path=STATS_DB_PATH)
        recent_stats = stats.get_recent_event_rate(hours=24)
        stats.close()
    except Exception:
        recent_stats = {}

    # ===== TIER 1: Haiku triage =====
    try:
        from audit.escalation import run_tier1_haiku

        haiku_result = run_tier1_haiku(
            anomalies=anomalies,
            directives=directives,
            recent_stats=recent_stats,
            recent_recommendations=existing_recs,
            model=models.get("triage", "haiku"),
        )
    except Exception as e:
        _log(f"Tier 1 error: {e}")
        haiku_result = None

    if not haiku_result:
        _log("Tier 1 failed; stopping escalation")
        return 0

    # Apply Haiku's recommendations
    if rec_mgr and haiku_result.get("recommendations"):
        for rec_data in haiku_result["recommendations"]:
            anomaly_type = rec_data.get("anomaly_type", "unknown")
            rec_mgr.update_from_escalation(
                anomaly_type=anomaly_type,
                suggestion=rec_data.get("suggestion", ""),
                analysis=haiku_result.get("analysis", ""),
                tier="haiku",
            )

    verdict = haiku_result.get("verdict", "known_pattern")
    escalate = haiku_result.get("escalate", False)
    _log(f"Tier 1 verdict: {verdict}, escalate: {escalate}")

    if not escalate:
        elapsed = time.time() - start
        _log(f"Escalation complete at Tier 1 ({elapsed:.1f}s)")
        _cleanup()
        return 0

    # ===== TIER 2: Sonnet analysis =====
    event_window = _load_recent_events(max_events=200)
    current_settings = _load_current_settings()

    try:
        from audit.escalation import run_tier2_sonnet

        sonnet_result = run_tier2_sonnet(
            haiku_triage=haiku_result,
            anomalies=anomalies,
            directives=directives,
            event_window=event_window,
            current_settings=current_settings,
            existing_recommendations=existing_recs,
            model=models.get("analysis", "sonnet"),
        )
    except Exception as e:
        _log(f"Tier 2 error: {e}")
        sonnet_result = None

    if not sonnet_result:
        _log("Tier 2 failed; stopping escalation")
        _cleanup()
        return 0

    # Apply Sonnet's recommendations
    if rec_mgr and sonnet_result.get("recommendations"):
        for rec_data in sonnet_result["recommendations"]:
            anomaly_type = rec_data.get("anomaly_type", "unknown")
            rec_mgr.update_from_escalation(
                anomaly_type=anomaly_type,
                suggestion=rec_data.get("suggestion", ""),
                analysis=sonnet_result.get("analysis", ""),
                tier="sonnet",
            )

    escalate_to_opus = sonnet_result.get("escalate_to_opus", False)
    _log(f"Tier 2 complete, escalate to Opus: {escalate_to_opus}")

    if not escalate_to_opus:
        elapsed = time.time() - start
        _log(f"Escalation complete at Tier 2 ({elapsed:.1f}s)")
        _cleanup()
        return 0

    # ===== TIER 3: Opus deep dive =====
    session_summaries = _load_session_summaries()

    try:
        from audit.escalation import run_tier3_opus

        opus_result = run_tier3_opus(
            sonnet_analysis=sonnet_result,
            anomalies=anomalies,
            directives=directives,
            event_window=event_window,
            current_settings=current_settings,
            existing_recommendations=existing_recs,
            session_summaries=session_summaries,
            model=models.get("deep_dive", "opus"),
        )
    except Exception as e:
        _log(f"Tier 3 error: {e}")
        opus_result = None

    if opus_result:
        # Apply Opus's recommendations
        if rec_mgr and opus_result.get("recommendations"):
            for rec_data in opus_result["recommendations"]:
                anomaly_type = rec_data.get("anomaly_type", "systemic")
                rec_mgr.update_from_escalation(
                    anomaly_type=anomaly_type,
                    suggestion=rec_data.get("suggestion", ""),
                    analysis=opus_result.get("deep_analysis", ""),
                    tier="opus",
                )
        _log("Tier 3 complete")
    else:
        _log("Tier 3 failed")

    elapsed = time.time() - start
    _log(f"Full escalation chain complete ({elapsed:.1f}s)")
    _cleanup()
    return 0


def _cleanup() -> None:
    """Clean up temp files."""
    try:
        PENDING_ANOMALIES_PATH.unlink(missing_ok=True)
    except OSError:
        pass


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        _log(f"ERROR: {e}")
        _cleanup()
        sys.exit(0)  # Never fail loudly; background process
