"""SurrealDB-backed Trust Engine -- classifies findings and tracks dismissals.

Drop-in replacement for TrustEngine that uses the shared AVT SurrealDB
instance instead of a standalone SQLite file. Tables `finding` and
`dismissal_history` are defined in the shared schema (avt_db.schema).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import TrustDecision

# ---------------------------------------------------------------------------
# Resolve the shared avt_db package.  It lives at <project>/shared/avt_db
# and may not be on sys.path yet.
# ---------------------------------------------------------------------------
_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
_SHARED_DIR = str(Path(_PROJECT_DIR) / "shared")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)


class SurrealTrustEngine:
    """SurrealDB-backed trust engine with the same interface as TrustEngine."""

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
    # Public interface (mirrors TrustEngine exactly)
    # ------------------------------------------------------------------

    def get_trust_decision(self, finding_id: str) -> dict:
        """Determine trust classification for a finding."""
        result = self._db.query(
            "SELECT status, dismissed_by, dismissal_justification "
            "FROM type::thing('finding', $fid)",
            {"fid": finding_id},
        )
        if result and len(result) > 0:
            row = result[0]
            if row.get("status") == "dismissed":
                return {
                    "decision": TrustDecision.TRACK.value,
                    "rationale": (
                        f"Previously dismissed by {row.get('dismissed_by')}: "
                        f"{row.get('dismissal_justification')}"
                    ),
                }

        return {
            "decision": TrustDecision.BLOCK.value,
            "rationale": "Default: all tool findings presumed legitimate until proven otherwise.",
        }

    def record_finding(
        self,
        finding_id: str,
        tool: str,
        severity: str,
        component: Optional[str],
        description: str,
    ) -> bool:
        """Record a new finding in the database."""
        # Check if finding already exists
        existing = self._db.query(
            "SELECT id FROM type::thing('finding', $fid)",
            {"fid": finding_id},
        )
        if existing and len(existing) > 0:
            return False

        self._db.query(
            "CREATE type::thing('finding', $fid) SET "
            "tool = $tool, "
            "severity = $severity, "
            "component = $component, "
            "description = $description, "
            "created_at = $created_at, "
            "status = 'open'",
            {
                "fid": finding_id,
                "tool": tool,
                "severity": severity,
                "component": component,
                "description": description,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return True

    def record_dismissal(
        self,
        finding_id: str,
        justification: str,
        dismissed_by: str,
    ) -> bool:
        """Record a finding dismissal with required justification."""
        if not justification.strip():
            return False

        dismissed_at = datetime.now(timezone.utc).isoformat()

        # Update finding status
        self._db.query(
            "UPDATE type::thing('finding', $fid) SET "
            "status = 'dismissed', "
            "dismissed_by = $dismissed_by, "
            "dismissal_justification = $justification, "
            "dismissed_at = $dismissed_at",
            {
                "fid": finding_id,
                "dismissed_by": dismissed_by,
                "justification": justification,
                "dismissed_at": dismissed_at,
            },
        )

        # Add to dismissal history
        self._db.query(
            "CREATE dismissal_history SET "
            "finding_id = $fid, "
            "dismissed_by = $dismissed_by, "
            "justification = $justification, "
            "dismissed_at = $dismissed_at",
            {
                "fid": finding_id,
                "dismissed_by": dismissed_by,
                "justification": justification,
                "dismissed_at": dismissed_at,
            },
        )
        return True

    def get_dismissal_history(self, finding_id: str) -> list[dict]:
        """Get dismissal history for a finding."""
        results = self._db.query(
            "SELECT dismissed_by, justification, dismissed_at "
            "FROM dismissal_history "
            "WHERE finding_id = $fid "
            "ORDER BY dismissed_at DESC",
            {"fid": finding_id},
        )
        return [
            {
                "dismissed_by": row["dismissed_by"],
                "justification": row["justification"],
                "dismissed_at": row["dismissed_at"],
            }
            for row in (results or [])
        ]

    def get_unresolved_findings(self, min_severity: str = "high") -> list[dict]:
        """Get unresolved findings at or above a severity threshold.

        Severity hierarchy: critical > high > medium > low > info.
        Returns findings with status 'open' at or above min_severity.
        """
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        threshold = severity_order.get(min_severity.lower(), 1)

        results = self._db.query(
            "SELECT * FROM finding WHERE status = 'open' ORDER BY created_at DESC"
        )
        return [
            {
                "id": _extract_finding_id(row),
                "tool": row["tool"],
                "severity": row["severity"],
                "component": row.get("component"),
                "description": row["description"],
                "created_at": row["created_at"],
                "status": row["status"],
            }
            for row in (results or [])
            if severity_order.get(row.get("severity", "").lower(), 4) <= threshold
        ]

    def get_all_findings(self, status: Optional[str] = None) -> list[dict]:
        """Get all findings, optionally filtered by status."""
        if status:
            results = self._db.query(
                "SELECT * FROM finding WHERE status = $s ORDER BY created_at DESC",
                {"s": status},
            )
        else:
            results = self._db.query(
                "SELECT * FROM finding ORDER BY created_at DESC"
            )
        return [
            {
                "id": _extract_finding_id(row),
                "tool": row["tool"],
                "severity": row["severity"],
                "component": row.get("component"),
                "description": row["description"],
                "created_at": row["created_at"],
                "status": row["status"],
            }
            for row in (results or [])
        ]


def _extract_finding_id(row: dict) -> str:
    """Extract the short finding ID from a SurrealDB record.

    SurrealDB record IDs are RecordID objects (str gives 'finding:my_id').
    We want just 'my_id'.
    """
    raw_id = row.get("id", "")
    raw_str = str(raw_id)
    if ":" in raw_str:
        return raw_str.split(":", 1)[1]
    return raw_str
