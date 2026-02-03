"""SQLite persistence for governance decisions and reviews."""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from .models import (
    Alternative,
    Decision,
    DecisionCategory,
    Confidence,
    Finding,
    ReviewVerdict,
    Verdict,
)


DEFAULT_DB_PATH = Path(".avt/governance.db")


class GovernanceStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                agent TEXT NOT NULL,
                category TEXT NOT NULL,
                summary TEXT NOT NULL,
                detail TEXT,
                components_affected TEXT,
                alternatives TEXT,
                confidence TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                decision_id TEXT REFERENCES decisions(id),
                plan_id TEXT,
                verdict TEXT NOT NULL,
                findings TEXT,
                guidance TEXT,
                standards_verified TEXT,
                reviewer TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_decisions_task
                ON decisions(task_id);
            CREATE INDEX IF NOT EXISTS idx_reviews_decision
                ON reviews(decision_id);
            CREATE INDEX IF NOT EXISTS idx_reviews_plan
                ON reviews(plan_id);
            """
        )
        conn.commit()

    def next_sequence(self, task_id: str) -> int:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT MAX(sequence) as max_seq FROM decisions WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return (row["max_seq"] or 0) + 1

    def store_decision(self, decision: Decision) -> Decision:
        if decision.sequence == 0:
            decision.sequence = self.next_sequence(decision.task_id)
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO decisions
               (id, task_id, sequence, agent, category, summary, detail,
                components_affected, alternatives, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                decision.id,
                decision.task_id,
                decision.sequence,
                decision.agent,
                decision.category.value,
                decision.summary,
                decision.detail,
                json.dumps(decision.components_affected),
                json.dumps([a.model_dump() for a in decision.alternatives_considered]),
                decision.confidence.value,
                decision.created_at,
            ),
        )
        conn.commit()
        return decision

    def store_review(self, review: ReviewVerdict) -> ReviewVerdict:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO reviews
               (id, decision_id, plan_id, verdict, findings, guidance,
                standards_verified, reviewer, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                review.id,
                review.decision_id,
                review.plan_id,
                review.verdict.value,
                json.dumps([f.model_dump() for f in review.findings]),
                review.guidance,
                json.dumps(review.standards_verified),
                review.reviewer,
                review.created_at,
            ),
        )
        conn.commit()
        return review

    def get_decisions_for_task(self, task_id: str) -> list[Decision]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM decisions WHERE task_id = ? ORDER BY sequence",
            (task_id,),
        ).fetchall()
        return [self._row_to_decision(r) for r in rows]

    def get_review_for_decision(self, decision_id: str) -> Optional[ReviewVerdict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM reviews WHERE decision_id = ? ORDER BY created_at DESC LIMIT 1",
            (decision_id,),
        ).fetchone()
        return self._row_to_review(row) if row else None

    def get_reviews_for_task(self, task_id: str) -> list[ReviewVerdict]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT r.* FROM reviews r
               JOIN decisions d ON r.decision_id = d.id
               WHERE d.task_id = ?
               ORDER BY r.created_at""",
            (task_id,),
        ).fetchall()
        return [self._row_to_review(r) for r in rows]

    def get_all_decisions(
        self,
        task_id: Optional[str] = None,
        agent: Optional[str] = None,
        verdict: Optional[str] = None,
    ) -> list[dict]:
        conn = self._get_conn()
        query = """
            SELECT d.*, r.verdict as review_verdict, r.guidance as review_guidance
            FROM decisions d
            LEFT JOIN reviews r ON r.decision_id = d.id
            WHERE 1=1
        """
        params: list = []
        if task_id:
            query += " AND d.task_id = ?"
            params.append(task_id)
        if agent:
            query += " AND d.agent = ?"
            params.append(agent)
        if verdict:
            query += " AND r.verdict = ?"
            params.append(verdict)
        query += " ORDER BY d.created_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [
            {
                "id": r["id"],
                "task_id": r["task_id"],
                "sequence": r["sequence"],
                "agent": r["agent"],
                "category": r["category"],
                "summary": r["summary"],
                "confidence": r["confidence"],
                "verdict": r["review_verdict"],
                "guidance": r["review_guidance"] or "",
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def get_status(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM decisions").fetchone()["c"]
        approved = conn.execute(
            "SELECT COUNT(*) as c FROM reviews WHERE verdict = 'approved'"
        ).fetchone()["c"]
        blocked = conn.execute(
            "SELECT COUNT(*) as c FROM reviews WHERE verdict = 'blocked'"
        ).fetchone()["c"]
        needs_human = conn.execute(
            "SELECT COUNT(*) as c FROM reviews WHERE verdict = 'needs_human_review'"
        ).fetchone()["c"]

        recent = conn.execute(
            """SELECT d.summary, d.agent, d.category, r.verdict
               FROM decisions d
               LEFT JOIN reviews r ON r.decision_id = d.id
               ORDER BY d.created_at DESC LIMIT 5"""
        ).fetchall()

        return {
            "total_decisions": total,
            "approved": approved,
            "blocked": blocked,
            "needs_human_review": needs_human,
            "pending": total - approved - blocked - needs_human,
            "recent_activity": [
                {
                    "summary": r["summary"],
                    "agent": r["agent"],
                    "category": r["category"],
                    "verdict": r["verdict"],
                }
                for r in recent
            ],
        }

    def has_plan_review(self, task_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as c FROM reviews WHERE plan_id = ?",
            (task_id,),
        ).fetchone()
        return row["c"] > 0

    def has_unresolved_blocks(self, task_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute(
            """SELECT COUNT(*) as c FROM reviews r
               JOIN decisions d ON r.decision_id = d.id
               WHERE d.task_id = ? AND r.verdict = 'blocked'""",
            (task_id,),
        ).fetchone()
        return row["c"] > 0

    def _row_to_decision(self, row: sqlite3.Row) -> Decision:
        alts_raw = json.loads(row["alternatives"] or "[]")
        return Decision(
            id=row["id"],
            task_id=row["task_id"],
            sequence=row["sequence"],
            agent=row["agent"],
            category=DecisionCategory(row["category"]),
            summary=row["summary"],
            detail=row["detail"] or "",
            components_affected=json.loads(row["components_affected"] or "[]"),
            alternatives_considered=[Alternative(**a) for a in alts_raw],
            confidence=Confidence(row["confidence"]),
            created_at=row["created_at"],
        )

    def _row_to_review(self, row: sqlite3.Row) -> ReviewVerdict:
        findings_raw = json.loads(row["findings"] or "[]")
        return ReviewVerdict(
            id=row["id"],
            decision_id=row["decision_id"],
            plan_id=row["plan_id"],
            verdict=Verdict(row["verdict"]),
            findings=[Finding(**f) for f in findings_raw],
            guidance=row["guidance"] or "",
            standards_verified=json.loads(row["standards_verified"] or "[]"),
            reviewer=row["reviewer"],
            created_at=row["created_at"],
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
