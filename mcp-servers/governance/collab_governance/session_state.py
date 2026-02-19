"""Session state generation from governance data.

Generates `.avt/session-state.md` by querying the governance store
for current task counts, recent activity, and system status.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .store import GovernanceStore


def generate_session_state(
    gov_store: GovernanceStore,
    output_path: Path,
    extra_notes: Optional[list[str]] = None,
) -> dict:
    """Generate session-state.md from governance database.

    Queries the governance store for:
    - Task governance stats (pending, approved, blocked)
    - Decision/review counts
    - Recent activity

    Args:
        gov_store: GovernanceStore instance to query.
        output_path: Path to write the session-state.md file.
        extra_notes: Optional additional notes to append.

    Returns:
        {"path": str, "tasks": int, "decisions": int}
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Gather data
    task_stats = gov_store.get_task_governance_stats()
    decision_status = gov_store.get_status()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Session State",
        "",
        f"**Last Updated**: {now}",
        "**Phase**: Active development",
        f"**Active Tasks**: {task_stats.get('pending_review', 0)}",
        "",
        "## System Status",
        "",
        "| Component | Status | Notes |",
        "|-----------|--------|-------|",
        "| Knowledge Graph Server | Ready | Persistence active |",
        "| Quality Server | Ready | Trust engine active |",
        f"| Governance Server | Ready | {task_stats.get('total_governed_tasks', 0)} governed tasks |",
        "",
        "## Task Governance",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total governed tasks | {task_stats.get('total_governed_tasks', 0)} |",
        f"| Pending review | {task_stats.get('pending_review', 0)} |",
        f"| Approved | {task_stats.get('approved', 0)} |",
        f"| Blocked | {task_stats.get('blocked', 0)} |",
        f"| Pending reviews | {task_stats.get('pending_reviews', 0)} |",
        "",
        "## Decision History",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total decisions | {decision_status.get('total_decisions', 0)} |",
        f"| Approved | {decision_status.get('approved', 0)} |",
        f"| Blocked | {decision_status.get('blocked', 0)} |",
        f"| Needs human review | {decision_status.get('needs_human_review', 0)} |",
        f"| Pending | {decision_status.get('pending', 0)} |",
        "",
    ]

    # Recent activity
    recent = decision_status.get("recent_activity", [])
    if recent:
        lines.extend(
            [
                "## Recent Activity",
                "",
            ]
        )
        for item in recent:
            verdict = item.get("verdict", "pending")
            lines.append(
                f"- [{item.get('category', '?')}] {item.get('summary', '?')} by {item.get('agent', '?')} -- {verdict}"
            )
        lines.append("")

    # Extra notes
    if extra_notes:
        lines.extend(
            [
                "## Notes",
                "",
            ]
        )
        for note in extra_notes:
            lines.append(f"- {note}")
        lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "path": str(output_path),
        "tasks": task_stats.get("total_governed_tasks", 0),
        "decisions": decision_status.get("total_decisions", 0),
    }
