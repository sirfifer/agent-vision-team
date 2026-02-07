"""File service for reading session state, task briefs, and agent definitions."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import config


class FileService:
    """Handles miscellaneous file I/O for the Gateway."""

    def __init__(self, project_dir: Path | None = None) -> None:
        self.project_dir = project_dir or config.project_dir
        self.avt_root = self.project_dir / ".avt"

    def read_session_state(self) -> dict:
        """Read session state from .avt/session-state.md."""
        state_path = self.avt_root / "session-state.md"
        if not state_path.exists():
            return {"phase": "inactive"}

        content = state_path.read_text()
        phase = "inactive"
        checkpoint = None
        worktrees: list[str] = []

        for line in content.splitlines():
            if line.startswith("## Phase:"):
                phase = line.split(":", 1)[1].strip().lower()
            elif line.startswith("## Checkpoint:"):
                checkpoint = line.split(":", 1)[1].strip()
            elif line.startswith("- worktree:"):
                worktrees.append(line.split(":", 1)[1].strip())

        result: dict = {"phase": phase}
        if checkpoint:
            result["lastCheckpoint"] = checkpoint
        if worktrees:
            result["activeWorktrees"] = worktrees
        return result

    def count_tasks(self) -> dict:
        """Count active and total task briefs."""
        briefs_dir = self.avt_root / "task-briefs"
        if not briefs_dir.exists():
            return {"active": 0, "total": 0}

        total = 0
        active = 0
        for f in briefs_dir.iterdir():
            if f.suffix == ".md":
                total += 1
                content = f.read_text()
                if "status: active" in content.lower() or "## Status: Active" in content:
                    active += 1
        return {"active": active, "total": total}

    def detect_agents(self) -> list[dict]:
        """Detect configured agents from .claude/agents/ directory."""
        agents_dir = self.project_dir / ".claude" / "agents"
        if not agents_dir.exists():
            return []

        agents = []
        for f in sorted(agents_dir.iterdir()):
            if f.suffix == ".md":
                name = f.stem
                role = name  # role matches filename by convention
                agents.append({
                    "id": name,
                    "name": name.replace("-", " ").title(),
                    "role": role,
                    "status": "idle",
                })
        return agents

    def read_hook_governance_status(self) -> dict | None:
        """Read hook governance status from .avt/governance.db if available."""
        db_path = self.avt_root / "governance.db"
        if not db_path.exists():
            return None

        # Use sqlite3 to query the hook interception table
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check if the table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='governed_tasks'")
            if not cursor.fetchone():
                conn.close()
                return None

            cursor.execute("SELECT COUNT(*) FROM governed_tasks")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT created_at, subject FROM governed_tasks ORDER BY created_at DESC LIMIT 5")
            recent = [{"timestamp": row[0], "subject": row[1]} for row in cursor.fetchall()]

            last_at = recent[0]["timestamp"] if recent else None
            conn.close()

            return {
                "totalInterceptions": total,
                "lastInterceptionAt": last_at,
                "recentInterceptions": recent,
            }
        except Exception:
            return None
