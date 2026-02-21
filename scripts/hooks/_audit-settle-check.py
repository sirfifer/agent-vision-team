#!/usr/bin/env python3
"""Background audit settle checker: waits for activity to settle, then spawns processor.

Spawned by governance-task-intercept.py after audit event emission.
Waits AUDIT_SETTLE_SECONDS (5s, longer than governance's 3s so audit runs after
governance settles), then checks if any newer events arrived. If not, spawns
the audit processor.

Usage: _audit-settle-check.py <my_timestamp>

Environment:
    CLAUDE_PROJECT_DIR: Project root directory
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
AUDIT_DIR = Path(PROJECT_DIR) / ".avt" / "audit"
SETTLE_TS_PATH = AUDIT_DIR / ".last-event-ts"
LOCK_PATH = AUDIT_DIR / ".processor-lock"
LOG_PATH = AUDIT_DIR / "audit.log"

# Default settle time; overridden by config if available
DEFAULT_SETTLE_SECONDS = 5
# Lock files older than this are considered stale
LOCK_STALENESS_SECONDS = 60


def _log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] [audit-settle] {msg}\n")
    except Exception:
        pass


def _load_settle_seconds() -> int:
    """Load settle_seconds from audit config, falling back to default."""
    try:
        hooks_dir = Path(PROJECT_DIR) / "scripts" / "hooks"
        sys.path.insert(0, str(hooks_dir))
        from audit.config import load_audit_config

        cfg = load_audit_config()
        return cfg.get("settle_seconds", DEFAULT_SETTLE_SECONDS)
    except Exception:
        return DEFAULT_SETTLE_SECONDS


def _is_audit_enabled() -> bool:
    """Check if audit is enabled in config."""
    try:
        hooks_dir = Path(PROJECT_DIR) / "scripts" / "hooks"
        sys.path.insert(0, str(hooks_dir))
        from audit.config import load_audit_config

        cfg = load_audit_config()
        return cfg.get("enabled", False)
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: _audit-settle-check.py <my_timestamp>")
        return 1

    my_timestamp = float(sys.argv[1])
    _log(f"Settle checker started: ts={my_timestamp:.2f}")

    # Check if audit is enabled
    if not _is_audit_enabled():
        _log("Audit disabled; exiting")
        return 0

    # Wait for settle period
    settle_seconds = _load_settle_seconds()
    time.sleep(settle_seconds)

    # Check if newer events arrived during settle period
    try:
        if SETTLE_TS_PATH.exists():
            latest_ts = float(SETTLE_TS_PATH.read_text().strip())
            if latest_ts > my_timestamp + 0.1:  # 100ms tolerance
                _log(
                    f"Newer events exist (latest={latest_ts:.2f} vs mine={my_timestamp:.2f}); "
                    "deferring to newer checker"
                )
                return 0
        else:
            _log("No .last-event-ts found; nothing to process")
            return 0
    except (ValueError, OSError) as e:
        _log(f"Error reading settle timestamp: {e}")
        return 0

    # Check if processor is already running (lock file)
    if LOCK_PATH.exists():
        try:
            lock_age = time.time() - LOCK_PATH.stat().st_mtime
            if lock_age < LOCK_STALENESS_SECONDS:
                _log(f"Processor lock exists ({lock_age:.0f}s old, < {LOCK_STALENESS_SECONDS}s); skipping")
                return 0
            else:
                _log(f"Stale lock found ({lock_age:.0f}s old); removing and proceeding")
                LOCK_PATH.unlink(missing_ok=True)
        except OSError:
            pass

    # Spawn the audit processor as a detached subprocess
    processor_script = Path(PROJECT_DIR) / "scripts" / "hooks" / "_audit-process.py"
    if not processor_script.exists():
        _log("Processor script not found; skipping")
        return 0

    try:
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = PROJECT_DIR
        subprocess.Popen(
            ["python3", str(processor_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        _log("Audit processor spawned")
    except Exception as e:
        _log(f"Failed to spawn processor: {e}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        _log(f"ERROR: {e}")
        sys.exit(0)  # Never fail loudly; background process
