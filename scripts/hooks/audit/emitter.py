"""Fire-and-forget audit event emission. TAP guarantee: never raises.

The audit emitter appends structured events to an append-only JSONL file.
It follows the Network TAP principle: if it fails, the calling hook is
completely unaffected. No exceptions propagate. No delays introduced.

Usage from hooks:
    from audit.emitter import emit_audit_event
    emit_audit_event("governance.task_pair_created", {
        "impl_task_id": impl_id,
        "review_task_id": review_id,
    }, source="hook:governance-task-intercept", session_id=session_id)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from uuid import uuid4

_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
_AUDIT_DIR = Path(_PROJECT_DIR) / ".avt" / "audit"
_EVENTS_PATH = _AUDIT_DIR / "events.jsonl"
_SETTLE_TS_PATH = _AUDIT_DIR / ".last-event-ts"


def emit_audit_event(
    event_type: str,
    data: dict,
    source: str = "",
    session_id: str = "",
    agent: str = "",
) -> None:
    """Append one structured event to events.jsonl. Fire-and-forget.

    Args:
        event_type: Dotted event type (e.g., "governance.task_pair_created")
        data: Event-specific payload (must be JSON-serializable)
        source: Origin of this event (e.g., "hook:governance-task-intercept")
        session_id: Claude session ID (from hook input or env)
        agent: Agent role that triggered this event (e.g., "worker-001")

    This function NEVER raises. All exceptions are silently swallowed.
    This is the TAP guarantee: audit emission must never fail the calling hook.
    """
    try:
        ts = time.time()
        event = {
            "id": f"evt-{uuid4().hex[:8]}",
            "ts": ts,
            "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
            "session_id": session_id or os.environ.get("CLAUDE_SESSION_ID", ""),
            "agent": agent,
            "source": source,
            "type": event_type,
            "data": data,
        }
        _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with open(_EVENTS_PATH, "a") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")
        # Update settle timestamp (used by _audit-settle-check.py)
        _SETTLE_TS_PATH.write_text(str(ts))
    except Exception:
        pass  # TAP guarantee: never fail the calling hook
