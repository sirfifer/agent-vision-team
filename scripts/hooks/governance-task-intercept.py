#!/usr/bin/env python3
"""PostToolUse hook: intercept TaskCreate to enforce governance-gated execution.

This hook fires after every successful TaskCreate call. It:
1. Creates a governance review task that blocks the implementation task
2. Modifies the implementation task file to add blockedBy
3. Records governance state in SQLite
4. Queues an async automated review (background process)

The result: every task is "blocked from birth" regardless of whether
the agent explicitly used create_governed_task() or not.

Hook protocol:
- Reads JSON from stdin (tool_name, tool_input, tool_result)
- Writes JSON to stdout (hookSpecificOutput with additionalContext)
- Exit 0 = success (context injected into Claude's conversation)
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ── Resolve paths ──────────────────────────────────────────────────────────

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
GOVERNANCE_DIR = Path(PROJECT_DIR) / "mcp-servers" / "governance"
DB_PATH = Path(PROJECT_DIR) / ".avt" / "governance.db"

# Add governance server to Python path so we can import its modules
sys.path.insert(0, str(GOVERNANCE_DIR))

from collab_governance.task_integration import (
    Task,
    TaskFileManager,
    _generate_task_id,
    _get_task_dir,
)
from collab_governance.store import GovernanceStore
from collab_governance.models import (
    GovernedTaskRecord,
    ReviewType,
    TaskReviewRecord,
    TaskReviewStatus,
)


# ── Loop prevention ───────────────────────────────────────────────────────

REVIEW_PREFIXES = ("[GOVERNANCE]", "[REVIEW]", "[SECURITY]", "[ARCHITECTURE]")


def _is_review_task(subject: str, task_id: str = "") -> bool:
    """Detect if this is a review task (skip to prevent infinite loops)."""
    if any(subject.upper().startswith(p) for p in REVIEW_PREFIXES):
        return True
    if task_id.startswith("review-"):
        return True
    return False


# ── Extract task info from hook input ──────────────────────────────────────

def _extract_task_info(hook_input: dict) -> dict | None:
    """Extract the created task's ID and details from PostToolUse input.

    The hook receives tool_input (what the agent sent) and tool_result
    (what the tool returned). We need the task ID from tool_result
    and the subject/description from tool_input or tool_result.
    """
    tool_input = hook_input.get("tool_input", {})
    tool_result = hook_input.get("tool_result", {})

    # tool_result may be a string (JSON) or dict
    if isinstance(tool_result, str):
        try:
            tool_result = json.loads(tool_result)
        except (json.JSONDecodeError, TypeError):
            tool_result = {}

    # Try to get task ID from various possible locations in tool_result
    task_id = (
        tool_result.get("id")
        or tool_result.get("taskId")
        or tool_result.get("task_id")
        or ""
    )

    # Try to get subject/description
    subject = (
        tool_result.get("subject")
        or tool_input.get("subject")
        or tool_input.get("prompt", "")[:200]
        or ""
    )

    description = (
        tool_result.get("description")
        or tool_input.get("description")
        or ""
    )

    if not task_id and not subject:
        return None

    return {
        "task_id": task_id,
        "subject": subject,
        "description": description,
        "tool_input": tool_input,
        "tool_result": tool_result,
    }


# ── Create governance pair ─────────────────────────────────────────────────

def _create_governance_pair(task_info: dict) -> dict:
    """Create a review task and link it to the implementation task.

    Returns dict with review_task_id, review_record_id, and status info.
    """
    impl_id = task_info["task_id"]
    subject = task_info["subject"]
    description = task_info["description"]

    manager = TaskFileManager()
    review_id = f"review-{_generate_task_id()}"

    # TaskCreate's tool_result is empty; discover the actual task ID by
    # scanning the task directory for a recently created task matching
    # the subject. This is the primary path, not a fallback.
    if not impl_id:
        impl_id = _discover_task_id(manager, subject) or ""
        if impl_id:
            _log(f"Discovered implementation task ID: {impl_id}")

    # Create the review task file
    review_task = Task(
        id=review_id,
        subject=f"[GOVERNANCE] Review: {subject}",
        description=(
            f"Governance review required before execution.\n\n"
            f"Context:\n{description[:2000]}"
        ),
        activeForm=f"Reviewing {subject}",
        blocks=[impl_id] if impl_id else [],
        governance_metadata={
            "review_type": "governance",
            "implementation_task_id": impl_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "PostToolUse-hook",
        },
    )
    manager.create_task(review_task)

    # Modify the implementation task to add blockedBy
    impl_task = manager.read_task(impl_id) if impl_id else None
    if impl_task:
        if review_id not in impl_task.blockedBy:
            impl_task.blockedBy.append(review_id)
            impl_task.updatedAt = time.time()
            manager.update_task(impl_task)
    else:
        # Last resort: scan by subject match
        found_id = _try_find_and_block_task(manager, subject, review_id)
        if found_id and not impl_id:
            impl_id = found_id
            # Update the review task's blocks to point to the discovered ID
            review_task_read = manager.read_task(review_id)
            if review_task_read and impl_id not in review_task_read.blocks:
                review_task_read.blocks = [impl_id]
                manager.update_task(review_task_read)

    # Store governance records in SQLite
    # Prefix impl_id with list_id to avoid collisions across test runs
    # (sequential IDs like "1", "2" would collide without a namespace)
    list_id = os.environ.get("CLAUDE_CODE_TASK_LIST_ID", "default")
    db_impl_id = f"{list_id}/{impl_id}" if impl_id else f"unknown-{_generate_task_id()}"
    try:
        store = GovernanceStore(db_path=DB_PATH)
        governed_task = GovernedTaskRecord(
            implementation_task_id=db_impl_id,
            subject=subject,
            description=description[:2000],
            context=f"Auto-intercepted via PostToolUse hook",
            current_status="pending_review",
        )
        store.store_governed_task(governed_task)

        task_review = TaskReviewRecord(
            review_task_id=review_id,
            implementation_task_id=governed_task.implementation_task_id,
            review_type=ReviewType.GOVERNANCE,
            status=TaskReviewStatus.PENDING,
            context=f"Auto-created by PostToolUse hook for: {subject}",
        )
        store.store_task_review(task_review)
        store.close()

        review_record_id = task_review.id
    except Exception as e:
        # If DB write fails, the file-level governance still works
        review_record_id = f"db-error-{_generate_task_id()}"
        _log(f"WARNING: Failed to store governance records: {e}")

    return {
        "review_task_id": review_id,
        "review_record_id": review_record_id,
        "implementation_task_id": impl_id,
        "subject": subject,
    }


def _discover_task_id(manager: TaskFileManager, subject: str) -> str | None:
    """Find the implementation task ID by matching subject in the task directory.

    TaskCreate's tool_result is an empty string, so we discover the task ID
    by scanning existing tasks for a subject match. Since the hook fires
    immediately after TaskCreate, the file should already exist.
    """
    for task in manager.list_tasks():
        if task.subject == subject and not _is_review_task(task.subject, task.id):
            return task.id
    return None


def _try_find_and_block_task(
    manager: TaskFileManager, subject: str, review_id: str
) -> str | None:
    """Fallback: scan task directory for a recently created task matching subject.

    Returns the discovered task ID if found, or None.
    """
    for task in manager.list_tasks():
        if task.subject == subject and not task.blockedBy:
            if review_id not in task.blockedBy:
                task.blockedBy.append(review_id)
                task.updatedAt = time.time()
                manager.update_task(task)
                return task.id
    return None


# ── Async review queueing ──────────────────────────────────────────────────

def _queue_async_review(review_info: dict) -> None:
    """Spawn an async governance review in the background.

    Uses claude --print with the governance-reviewer agent to evaluate
    the task against vision standards and architecture patterns.
    The review result will update the governance DB and release the
    task blocker if approved.

    Spawns as a background process so the hook returns immediately.
    """
    review_script = Path(PROJECT_DIR) / "scripts" / "hooks" / "_run-governance-review.sh"

    if not review_script.exists():
        # If the async review script doesn't exist yet, skip.
        # The review can still be completed manually via complete_task_review().
        _log("NOTE: Async review script not found. Review must be completed manually.")
        return

    try:
        subprocess.Popen(
            [
                str(review_script),
                review_info["review_task_id"],
                review_info["implementation_task_id"],
                review_info.get("subject", ""),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent process
        )
    except Exception as e:
        _log(f"WARNING: Failed to queue async review: {e}")


# ── Logging ────────────────────────────────────────────────────────────────

LOG_PATH = Path(PROJECT_DIR) / ".avt" / "hook-governance.log"


def _log(msg: str) -> None:
    """Append a log line (best-effort, never raises)."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, IOError):
        # Can't parse input; exit silently (don't break the agent)
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    _log(f"PostToolUse fired for tool: {tool_name}")

    # Extract task information
    task_info = _extract_task_info(hook_input)
    if not task_info:
        _log("No task info extracted; skipping governance interception")
        sys.exit(0)

    # Loop prevention: don't govern review tasks
    if _is_review_task(task_info["subject"], task_info.get("task_id", "")):
        _log(f"Skipping review task: {task_info['subject']}")
        sys.exit(0)

    _log(f"Intercepting task: {task_info['subject']} (id={task_info['task_id']})")

    # Create the governance pair
    review_info = _create_governance_pair(task_info)
    _log(
        f"Governance pair created: review={review_info['review_task_id']} "
        f"impl={review_info['implementation_task_id']}"
    )

    # Queue async review
    _queue_async_review(review_info)

    # Return additionalContext to Claude
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"GOVERNANCE: Task '{task_info['subject']}' has been automatically "
                f"paired with governance review {review_info['review_task_id']}. "
                f"The task is blocked until review completes. "
                f"Review is queued for automated processing. "
                f"Use get_task_review_status('{review_info['implementation_task_id']}') "
                f"to check status."
            ),
        }
    }
    json.dump(output, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
