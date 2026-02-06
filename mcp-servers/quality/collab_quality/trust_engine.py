"""Tool Trust Engine — classifies findings and tracks dismissals."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import TrustDecision, DismissalRecord


class TrustEngine:
    def __init__(self, db_path: str = ".avt/trust-engine.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with trust engine schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Findings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                tool TEXT NOT NULL,
                severity TEXT NOT NULL,
                component TEXT,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                dismissed_by TEXT,
                dismissal_justification TEXT,
                dismissed_at TEXT
            )
        """)

        # Dismissal history table (separate for audit trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dismissal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finding_id TEXT NOT NULL,
                dismissed_by TEXT NOT NULL,
                justification TEXT NOT NULL,
                dismissed_at TEXT NOT NULL,
                FOREIGN KEY (finding_id) REFERENCES findings(id)
            )
        """)

        conn.commit()
        conn.close()

    def get_trust_decision(self, finding_id: str) -> dict:
        """Determine trust classification for a finding."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if this finding has been dismissed before
        cursor.execute("""
            SELECT status, dismissed_by, dismissal_justification
            FROM findings
            WHERE id = ?
        """, (finding_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            status, dismissed_by, justification = result
            if status == "dismissed":
                return {
                    "decision": TrustDecision.TRACK.value,
                    "rationale": f"Previously dismissed by {dismissed_by}: {justification}",
                }

        # Default: all findings are trusted (BLOCK)
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO findings (id, tool, severity, component, description, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, 'open')
            """, (finding_id, tool, severity, component, description, datetime.utcnow().isoformat()))

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Finding already exists
            return False
        finally:
            conn.close()

    def record_dismissal(
        self,
        finding_id: str,
        justification: str,
        dismissed_by: str,
    ) -> bool:
        """Record a finding dismissal with required justification."""
        if not justification.strip():
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        dismissed_at = datetime.utcnow().isoformat()

        try:
            # Update finding status
            cursor.execute("""
                UPDATE findings
                SET status = 'dismissed',
                    dismissed_by = ?,
                    dismissal_justification = ?,
                    dismissed_at = ?
                WHERE id = ?
            """, (dismissed_by, justification, dismissed_at, finding_id))

            # Add to dismissal history
            cursor.execute("""
                INSERT INTO dismissal_history (finding_id, dismissed_by, justification, dismissed_at)
                VALUES (?, ?, ?, ?)
            """, (finding_id, dismissed_by, justification, dismissed_at))

            conn.commit()
            return True
        finally:
            conn.close()

    def get_dismissal_history(self, finding_id: str) -> list[dict]:
        """Get dismissal history for a finding."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT dismissed_by, justification, dismissed_at
            FROM dismissal_history
            WHERE finding_id = ?
            ORDER BY dismissed_at DESC
        """, (finding_id,))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "dismissed_by": row[0],
                "justification": row[1],
                "dismissed_at": row[2],
            }
            for row in results
        ]

    def get_unresolved_findings(self, min_severity: str = "high") -> list[dict]:
        """Get unresolved findings at or above a severity threshold.

        Severity hierarchy: critical > high > medium > low > info.
        Returns findings with status 'open' at or above min_severity.
        """
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        threshold = severity_order.get(min_severity.lower(), 1)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, tool, severity, component, description, created_at, status
            FROM findings
            WHERE status = 'open'
            ORDER BY created_at DESC
        """)

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "tool": row[1],
                "severity": row[2],
                "component": row[3],
                "description": row[4],
                "created_at": row[5],
                "status": row[6],
            }
            for row in results
            if severity_order.get(row[2].lower(), 4) <= threshold
        ]

    def get_all_findings(self, status: Optional[str] = None) -> list[dict]:
        """Get all findings, optionally filtered by status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT id, tool, severity, component, description, created_at, status
                FROM findings
                WHERE status = ?
                ORDER BY created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT id, tool, severity, component, description, created_at, status
                FROM findings
                ORDER BY created_at DESC
            """)

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "tool": row[1],
                "severity": row[2],
                "component": row[3],
                "description": row[4],
                "created_at": row[5],
                "status": row[6],
            }
            for row in results
        ]
