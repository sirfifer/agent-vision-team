#!/usr/bin/env python3
"""Background settle checker: detects end of task creation, triggers holistic review.

Spawned by governance-task-intercept.py after each TaskCreate.
Waits SETTLE_SECONDS, then checks if any newer tasks were created.
If not, this was the last task, so it triggers the holistic review.
If yes, exits silently (a newer checker handles it).

Usage: _holistic-settle-check.py <session_id> <my_timestamp> [transcript_path]

Environment:
    CLAUDE_PROJECT_DIR: Project root directory
    GOVERNANCE_MOCK_REVIEW: If set, auto-approves holistic review (E2E tests)
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SETTLE_SECONDS = 3  # Wait this long for more tasks before triggering review
MIN_TASKS_FOR_REVIEW = 2  # Single tasks skip holistic review

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
GOVERNANCE_DIR = Path(PROJECT_DIR) / "mcp-servers" / "governance"
DB_PATH = Path(PROJECT_DIR) / ".avt" / "governance.db"
# FLAG_PATH is set dynamically in main() using the session_id argument.
# Session-scoped flag files (.holistic-review-pending-{session_id}) allow
# multiple concurrent Agent Teams teammates to have independent reviews.
FLAG_PATH: Path = Path(PROJECT_DIR) / ".avt" / ".holistic-review-pending-unknown"
LOG_PATH = Path(PROJECT_DIR) / ".avt" / "hook-holistic.log"

sys.path.insert(0, str(GOVERNANCE_DIR))

# Audit: fire-and-forget event emission
_HOOKS_DIR = Path(PROJECT_DIR) / "scripts" / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))
try:
    from audit.emitter import emit_audit_event

    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False


def _log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] [settle] {msg}\n")
    except Exception:
        pass


def _extract_transcript_context(transcript_path: str) -> str:
    """Extract agent's recent reasoning from transcript JSONL."""
    if not transcript_path or not Path(transcript_path).exists():
        return "(transcript not available)"
    try:
        with open(transcript_path) as f:
            lines = f.readlines()
        recent = lines[-50:] if len(lines) > 50 else lines
        excerpts = []
        for line in recent:
            try:
                entry = json.loads(line)
                if entry.get("role") == "assistant":
                    content = entry.get("content", "")
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                excerpts.append(block["text"][:500])
                    elif isinstance(content, str):
                        excerpts.append(content[:500])
            except json.JSONDecodeError:
                continue
        return "\n---\n".join(excerpts[-5:])
    except Exception:
        return "(could not read transcript)"


def _load_standards() -> tuple[list[dict], list[dict]]:
    """Load vision/architecture standards from KG JSONL."""
    kg_path = Path(PROJECT_DIR) / ".claude" / "collab" / "knowledge-graph.jsonl"
    vision: list[dict] = []
    architecture: list[dict] = []
    if not kg_path.exists():
        return vision, architecture
    try:
        with open(kg_path) as f:
            for line in f:
                try:
                    entity = json.loads(line)
                    tier = entity.get("protectionTier", "")
                    if tier == "vision":
                        vision.append(entity)
                    elif tier == "architecture":
                        architecture.append(entity)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return vision, architecture


def _queue_individual_review(
    review_task_id: str,
    impl_task_id: str,
    subject: str,
    session_id: str = "",
    transcript_path: str = "",
) -> None:
    """Start the individual review for a single task (existing mechanism)."""
    review_script = Path(PROJECT_DIR) / "scripts" / "hooks" / "_run-governance-review.sh"
    if not review_script.exists():
        _log(f"Individual review script not found; skipping review for {impl_task_id}")
        return
    try:
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = PROJECT_DIR
        subprocess.Popen(
            [str(review_script), review_task_id, impl_task_id, subject, session_id, transcript_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        _log(f"Individual review queued: review={review_task_id} impl={impl_task_id}")
    except Exception as e:
        _log(f"WARNING: Failed to queue individual review: {e}")


def _spawn_context_update(session_id: str, transcript_path: str, source: str) -> None:
    """Spawn background context update to capture milestones/discoveries."""
    update_script = Path(PROJECT_DIR) / "scripts" / "hooks" / "_update-session-context.py"
    if not update_script.exists():
        return
    try:
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = PROJECT_DIR
        subprocess.Popen(
            ["python3", str(update_script), session_id, transcript_path, source],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        _log(f"Context update spawned: session={session_id} source={source}")
    except Exception as e:
        _log(f"WARNING: Failed to spawn context update: {e}")


def _remove_flag() -> None:
    """Remove the holistic review flag file, unblocking work tools."""
    try:
        FLAG_PATH.unlink()
        _log("Flag file removed. Work tools unblocked.")
    except FileNotFoundError:
        pass


def _update_flag(status: str, guidance: str = "", findings: list = None, strengths_summary: str = "") -> None:
    """Update the flag file with a new status and optional details."""
    data: dict = {"status": status, "guidance": guidance, "strengths_summary": strengths_summary}
    if findings:
        data["findings"] = findings
    try:
        FLAG_PATH.write_text(json.dumps(data))
        _log(f"Flag file updated: status={status}")
    except Exception as e:
        _log(f"WARNING: Failed to update flag file: {e}")


def main() -> None:
    global FLAG_PATH

    if len(sys.argv) < 3:
        print("Usage: _holistic-settle-check.py <session_id> <my_timestamp> [transcript_path]")
        sys.exit(1)

    session_id = sys.argv[1]
    my_timestamp = float(sys.argv[2])
    transcript_path = sys.argv[3] if len(sys.argv) > 3 else ""

    # Set session-scoped flag path
    FLAG_PATH = Path(PROJECT_DIR) / ".avt" / f".holistic-review-pending-{session_id}"

    _log(f"Settle checker started: session={session_id} ts={my_timestamp}")

    # Wait for settle period
    time.sleep(SETTLE_SECONDS)

    from collab_governance.store import GovernanceStore

    store = GovernanceStore(db_path=DB_PATH)

    # Check if any newer tasks were created in this session
    tasks = store.get_tasks_for_session(session_id)
    if not tasks:
        _log("No tasks found for session; exiting")
        store.close()
        return

    newest_ts = max(datetime.fromisoformat(t.created_at).timestamp() for t in tasks)

    if newest_ts > my_timestamp + 0.5:  # 0.5s tolerance
        _log(f"Newer tasks exist (newest={newest_ts:.2f} vs mine={my_timestamp:.2f}); deferring")
        store.close()
        return

    _log(f"I'm the latest checker. {len(tasks)} tasks to review holistically.")

    # Race condition guard: check if holistic review already ran
    existing = store.get_holistic_review_for_session(session_id)
    if existing:
        _log(f"Holistic review already exists: verdict={existing.verdict}")
        # If the existing review was approved, clean up any re-created flag file
        # (subagent tasks can re-create the flag after the main batch was approved)
        from collab_governance.models import Verdict

        if existing.verdict == Verdict.APPROVED:
            _remove_flag()
            _log("Cleaned up re-created flag file (session already approved).")
        store.close()
        return

    # Single task: skip holistic review, go straight to individual review
    if len(tasks) < MIN_TASKS_FOR_REVIEW:
        _log(f"Only {len(tasks)} task(s); skipping holistic review, starting individual review")
        if _HAS_AUDIT:
            emit_audit_event(
                "governance.holistic_review_skipped",
                {
                    "session_id": session_id,
                    "reason": "below_min_tasks",
                    "task_count": len(tasks),
                },
                source="hook:holistic-settle-check",
                session_id=session_id,
            )
        _remove_flag()
        for task in tasks:
            # Find the review_task_id from task_reviews table
            reviews = store.get_task_reviews(task.implementation_task_id)
            if reviews:
                _queue_individual_review(
                    reviews[0].review_task_id,
                    task.implementation_task_id,
                    task.subject,
                    session_id=session_id,
                    transcript_path=transcript_path,
                )
        store.close()
        return

    # Run holistic review
    _log(f"Running holistic review for {len(tasks)} tasks...")

    # Check for mock mode (E2E tests)
    if os.environ.get("GOVERNANCE_MOCK_REVIEW"):
        _log("Mock mode: auto-approving holistic review")
        from collab_governance.models import HolisticReviewRecord, Verdict

        record = HolisticReviewRecord(
            session_id=session_id,
            task_ids=[t.implementation_task_id for t in tasks],
            task_subjects=[t.subject for t in tasks],
            collective_intent="Mock holistic review: auto-approved",
            verdict=Verdict.APPROVED,
            findings=[],
            guidance="Mock review: auto-approved for E2E testing.",
            standards_verified=["mock"],
        )
        store.store_holistic_review(record)
        _remove_flag()

        # Start individual reviews
        for task in tasks:
            reviews = store.get_task_reviews(task.implementation_task_id)
            if reviews:
                _queue_individual_review(
                    reviews[0].review_task_id,
                    task.implementation_task_id,
                    task.subject,
                    session_id=session_id,
                    transcript_path=transcript_path,
                )

        store.close()
        _log("Mock holistic review completed. Individual reviews queued.")
        return

    # Real holistic review via GovernanceReviewer
    transcript_excerpt = _extract_transcript_context(transcript_path)
    vision_standards, architecture = _load_standards()

    from collab_governance.reviewer import GovernanceReviewer

    reviewer = GovernanceReviewer()

    tasks_for_review = [
        {
            "subject": t.subject,
            "description": t.description,
            "impl_id": t.implementation_task_id,
        }
        for t in tasks
    ]

    verdict = reviewer.review_task_group(
        tasks=tasks_for_review,
        transcript_excerpt=transcript_excerpt,
        vision_standards=vision_standards,
        architecture=architecture,
    )

    # Store holistic review record
    from collab_governance.models import HolisticReviewRecord, Verdict

    record = HolisticReviewRecord(
        session_id=session_id,
        task_ids=[t.implementation_task_id for t in tasks],
        task_subjects=[t.subject for t in tasks],
        collective_intent=verdict.guidance[:500],
        verdict=verdict.verdict,
        findings=verdict.findings,
        guidance=verdict.guidance,
        strengths_summary=verdict.strengths_summary,
        standards_verified=verdict.standards_verified,
    )
    store.store_holistic_review(record)

    _log(f"Holistic review complete: verdict={verdict.verdict.value}")

    # Audit: emit holistic review completion
    if _HAS_AUDIT:
        emit_audit_event(
            "governance.holistic_review_completed",
            {
                "session_id": session_id,
                "verdict": verdict.verdict.value,
                "task_count": len(tasks),
                "findings_count": len(verdict.findings),
                "standards_verified": verdict.standards_verified,
            },
            source="hook:holistic-settle-check",
            session_id=session_id,
        )

    # Spawn context update to capture milestones/discoveries from transcript
    _spawn_context_update(session_id, transcript_path, "holistic_review")

    if verdict.verdict == Verdict.APPROVED:
        _remove_flag()
        # Start individual reviews
        for task in tasks:
            reviews = store.get_task_reviews(task.implementation_task_id)
            if reviews:
                _queue_individual_review(
                    reviews[0].review_task_id,
                    task.implementation_task_id,
                    task.subject,
                    session_id=session_id,
                    transcript_path=transcript_path,
                )
        _log("Individual reviews queued after holistic approval.")

    elif verdict.verdict == Verdict.BLOCKED:
        _update_flag(
            "blocked",
            guidance=verdict.guidance,
            findings=[f.model_dump() for f in verdict.findings],
            strengths_summary=verdict.strengths_summary,
        )
        _log("Work tools remain blocked (holistic review: blocked).")

    else:  # needs_human_review
        _update_flag("needs_human_review", guidance=verdict.guidance)
        _log("Work tools remain blocked (holistic review: needs_human_review).")

    store.close()


if __name__ == "__main__":
    main()
