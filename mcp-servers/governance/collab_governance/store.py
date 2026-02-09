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
    GovernedTaskRecord,
    HolisticReviewRecord,
    ReviewType,
    ReviewVerdict,
    TaskReviewRecord,
    TaskReviewStatus,
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

            -- Task governance tables
            CREATE TABLE IF NOT EXISTS governed_tasks (
                id TEXT PRIMARY KEY,
                implementation_task_id TEXT UNIQUE NOT NULL,
                subject TEXT NOT NULL,
                description TEXT,
                context TEXT,
                current_status TEXT NOT NULL DEFAULT 'pending_review',
                created_at TEXT NOT NULL,
                released_at TEXT
            );

            CREATE TABLE IF NOT EXISTS task_reviews (
                id TEXT PRIMARY KEY,
                review_task_id TEXT NOT NULL,
                implementation_task_id TEXT NOT NULL REFERENCES governed_tasks(implementation_task_id),
                review_type TEXT NOT NULL DEFAULT 'governance',
                status TEXT NOT NULL DEFAULT 'pending',
                context TEXT,
                verdict TEXT,
                guidance TEXT,
                findings TEXT,
                standards_verified TEXT,
                reviewer TEXT NOT NULL DEFAULT 'governance-reviewer',
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_governed_tasks_impl
                ON governed_tasks(implementation_task_id);
            CREATE INDEX IF NOT EXISTS idx_task_reviews_impl
                ON task_reviews(implementation_task_id);
            CREATE INDEX IF NOT EXISTS idx_task_reviews_review
                ON task_reviews(review_task_id);

            -- Holistic review table
            CREATE TABLE IF NOT EXISTS holistic_reviews (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                task_ids TEXT NOT NULL,
                task_subjects TEXT NOT NULL,
                collective_intent TEXT,
                verdict TEXT,
                findings TEXT,
                guidance TEXT,
                standards_verified TEXT,
                reviewer TEXT NOT NULL DEFAULT 'governance-reviewer',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_holistic_reviews_session
                ON holistic_reviews(session_id);
            """
        )
        conn.commit()

        # Idempotent migration: add session_id column to governed_tasks
        try:
            conn.execute("ALTER TABLE governed_tasks ADD COLUMN session_id TEXT DEFAULT ''")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Idempotent migration: add strengths_summary column for PIN feedback
        for table in ("reviews", "holistic_reviews"):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN strengths_summary TEXT DEFAULT ''")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists

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
                strengths_summary, standards_verified, reviewer, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                review.id,
                review.decision_id,
                review.plan_id,
                review.verdict.value,
                json.dumps([f.model_dump() for f in review.findings]),
                review.guidance,
                review.strengths_summary,
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
        # strengths_summary may not exist in older DBs before migration runs
        try:
            strengths_summary = row["strengths_summary"] or ""
        except (IndexError, KeyError):
            strengths_summary = ""
        return ReviewVerdict(
            id=row["id"],
            decision_id=row["decision_id"],
            plan_id=row["plan_id"],
            verdict=Verdict(row["verdict"]),
            findings=[Finding(**f) for f in findings_raw],
            guidance=row["guidance"] or "",
            strengths_summary=strengths_summary,
            standards_verified=json.loads(row["standards_verified"] or "[]"),
            reviewer=row["reviewer"],
            created_at=row["created_at"],
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # =========================================================================
    # Task Governance Methods
    # =========================================================================

    def store_governed_task(self, task: GovernedTaskRecord) -> GovernedTaskRecord:
        """Store a governed task record."""
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO governed_tasks
               (id, implementation_task_id, subject, description, context,
                current_status, created_at, released_at, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.id,
                task.implementation_task_id,
                task.subject,
                task.description,
                task.context,
                task.current_status,
                task.created_at,
                task.released_at,
                task.session_id,
            ),
        )
        conn.commit()
        return task

    def store_task_review(self, review: TaskReviewRecord) -> TaskReviewRecord:
        """Store a task review record."""
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO task_reviews
               (id, review_task_id, implementation_task_id, review_type, status,
                context, verdict, guidance, findings, standards_verified,
                reviewer, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                review.id,
                review.review_task_id,
                review.implementation_task_id,
                review.review_type.value,
                review.status.value,
                review.context,
                review.verdict.value if review.verdict else None,
                review.guidance,
                json.dumps([f.model_dump() for f in review.findings]),
                json.dumps(review.standards_verified),
                review.reviewer,
                review.created_at,
                review.completed_at,
            ),
        )
        conn.commit()
        return review

    def update_task_review(self, review: TaskReviewRecord) -> TaskReviewRecord:
        """Update a task review record."""
        conn = self._get_conn()
        conn.execute(
            """UPDATE task_reviews SET
               status = ?, verdict = ?, guidance = ?, findings = ?,
               standards_verified = ?, completed_at = ?
               WHERE id = ?""",
            (
                review.status.value,
                review.verdict.value if review.verdict else None,
                review.guidance,
                json.dumps([f.model_dump() for f in review.findings]),
                json.dumps(review.standards_verified),
                review.completed_at,
                review.id,
            ),
        )
        conn.commit()
        return review

    def update_governed_task_status(
        self, implementation_task_id: str, status: str, released_at: Optional[str] = None
    ) -> None:
        """Update the status of a governed task."""
        conn = self._get_conn()
        conn.execute(
            """UPDATE governed_tasks SET current_status = ?, released_at = ?
               WHERE implementation_task_id = ?""",
            (status, released_at, implementation_task_id),
        )
        conn.commit()

    def get_governed_task(self, implementation_task_id: str) -> Optional[GovernedTaskRecord]:
        """Get a governed task by implementation task ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM governed_tasks WHERE implementation_task_id = ?",
            (implementation_task_id,),
        ).fetchone()
        if not row:
            return None
        return GovernedTaskRecord(
            id=row["id"],
            implementation_task_id=row["implementation_task_id"],
            subject=row["subject"],
            description=row["description"] or "",
            context=row["context"] or "",
            current_status=row["current_status"],
            session_id=row["session_id"] or "",
            created_at=row["created_at"],
            released_at=row["released_at"],
        )

    def get_task_reviews(self, implementation_task_id: str) -> list[TaskReviewRecord]:
        """Get all reviews for a governed task."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM task_reviews WHERE implementation_task_id = ? ORDER BY created_at",
            (implementation_task_id,),
        ).fetchall()
        return [self._row_to_task_review(r) for r in rows]

    def get_task_review_by_review_task_id(self, review_task_id: str) -> Optional[TaskReviewRecord]:
        """Get a task review by its review task ID (Claude Code task ID)."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM task_reviews WHERE review_task_id = ?",
            (review_task_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_task_review(row)

    def get_pending_task_reviews(self) -> list[TaskReviewRecord]:
        """Get all pending task reviews."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM task_reviews WHERE status = 'pending' ORDER BY created_at",
        ).fetchall()
        return [self._row_to_task_review(r) for r in rows]

    def get_all_governed_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get all governed tasks with their review details."""
        conn = self._get_conn()
        query = "SELECT * FROM governed_tasks WHERE 1=1"
        params: list = []
        if status:
            query += " AND current_status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            impl_id = row["implementation_task_id"]
            reviews = conn.execute(
                "SELECT * FROM task_reviews WHERE implementation_task_id = ? ORDER BY created_at",
                (impl_id,),
            ).fetchall()
            review_list = []
            for r in reviews:
                findings_raw = json.loads(r["findings"] or "[]")
                review_list.append({
                    "id": r["id"],
                    "review_task_id": r["review_task_id"],
                    "review_type": r["review_type"],
                    "status": r["status"],
                    "verdict": r["verdict"],
                    "guidance": r["guidance"] or "",
                    "findings": findings_raw,
                    "created_at": r["created_at"],
                    "completed_at": r["completed_at"],
                })
            result.append({
                "id": row["id"],
                "implementation_task_id": impl_id,
                "subject": row["subject"],
                "description": row["description"] or "",
                "current_status": row["current_status"],
                "created_at": row["created_at"],
                "released_at": row["released_at"],
                "reviews": review_list,
            })
        return result

    def get_task_governance_stats(self) -> dict:
        """Get statistics about task governance."""
        conn = self._get_conn()
        total_tasks = conn.execute(
            "SELECT COUNT(*) as c FROM governed_tasks"
        ).fetchone()["c"]
        pending = conn.execute(
            "SELECT COUNT(*) as c FROM governed_tasks WHERE current_status = 'pending_review'"
        ).fetchone()["c"]
        approved = conn.execute(
            "SELECT COUNT(*) as c FROM governed_tasks WHERE current_status = 'approved'"
        ).fetchone()["c"]
        blocked = conn.execute(
            "SELECT COUNT(*) as c FROM governed_tasks WHERE current_status = 'blocked'"
        ).fetchone()["c"]

        pending_reviews = conn.execute(
            "SELECT COUNT(*) as c FROM task_reviews WHERE status = 'pending'"
        ).fetchone()["c"]

        return {
            "total_governed_tasks": total_tasks,
            "pending_review": pending,
            "approved": approved,
            "blocked": blocked,
            "pending_reviews": pending_reviews,
        }

    # =========================================================================
    # Holistic Review Methods
    # =========================================================================

    def store_holistic_review(self, record: HolisticReviewRecord) -> HolisticReviewRecord:
        """Store a holistic review record."""
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO holistic_reviews
               (id, session_id, task_ids, task_subjects, collective_intent,
                verdict, findings, guidance, strengths_summary,
                standards_verified, reviewer, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id,
                record.session_id,
                json.dumps(record.task_ids),
                json.dumps(record.task_subjects),
                record.collective_intent,
                record.verdict.value if record.verdict else None,
                json.dumps([f.model_dump() for f in record.findings]),
                record.guidance,
                record.strengths_summary,
                json.dumps(record.standards_verified),
                record.reviewer,
                record.created_at,
            ),
        )
        conn.commit()
        return record

    def get_holistic_review_for_session(self, session_id: str) -> Optional[HolisticReviewRecord]:
        """Get the holistic review for a session, if one exists."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM holistic_reviews WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_holistic_review(row)

    def get_tasks_for_session(self, session_id: str) -> list[GovernedTaskRecord]:
        """Get all governed tasks for a session."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM governed_tasks WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        return [
            GovernedTaskRecord(
                id=r["id"],
                implementation_task_id=r["implementation_task_id"],
                subject=r["subject"],
                description=r["description"] or "",
                context=r["context"] or "",
                current_status=r["current_status"],
                session_id=r["session_id"] or "",
                created_at=r["created_at"],
                released_at=r["released_at"],
            )
            for r in rows
        ]

    def get_latest_task_timestamp_for_session(self, session_id: str) -> Optional[str]:
        """Get the created_at of the most recently created task in a session."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT MAX(created_at) as latest FROM governed_tasks WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return row["latest"] if row and row["latest"] else None

    def _row_to_holistic_review(self, row: sqlite3.Row) -> HolisticReviewRecord:
        """Convert a database row to a HolisticReviewRecord."""
        findings_raw = json.loads(row["findings"] or "[]")
        verdict = Verdict(row["verdict"]) if row["verdict"] else None
        try:
            strengths_summary = row["strengths_summary"] or ""
        except (IndexError, KeyError):
            strengths_summary = ""
        return HolisticReviewRecord(
            id=row["id"],
            session_id=row["session_id"],
            task_ids=json.loads(row["task_ids"] or "[]"),
            task_subjects=json.loads(row["task_subjects"] or "[]"),
            collective_intent=row["collective_intent"] or "",
            verdict=verdict,
            findings=[Finding(**f) for f in findings_raw],
            guidance=row["guidance"] or "",
            strengths_summary=strengths_summary,
            standards_verified=json.loads(row["standards_verified"] or "[]"),
            reviewer=row["reviewer"],
            created_at=row["created_at"],
        )

    def _row_to_task_review(self, row: sqlite3.Row) -> TaskReviewRecord:
        """Convert a database row to a TaskReviewRecord."""
        findings_raw = json.loads(row["findings"] or "[]")
        verdict = Verdict(row["verdict"]) if row["verdict"] else None
        return TaskReviewRecord(
            id=row["id"],
            review_task_id=row["review_task_id"],
            implementation_task_id=row["implementation_task_id"],
            review_type=ReviewType(row["review_type"]),
            status=TaskReviewStatus(row["status"]),
            context=row["context"] or "",
            verdict=verdict,
            guidance=row["guidance"] or "",
            findings=[Finding(**f) for f in findings_raw],
            standards_verified=json.loads(row["standards_verified"] or "[]"),
            reviewer=row["reviewer"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )
