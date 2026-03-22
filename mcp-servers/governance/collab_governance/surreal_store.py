"""SurrealDB persistence for governance decisions and reviews.

Drop-in replacement for GovernanceStore (SQLite) selectable via feature flag.
Uses surrealdb sync SDK with surrealkv:// embedded mode.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from surrealdb import Surreal

from .models import (
    Alternative,
    Confidence,
    Decision,
    DecisionCategory,
    Finding,
    GovernedTaskRecord,
    HolisticReviewRecord,
    ReviewType,
    ReviewVerdict,
    TaskReviewRecord,
    TaskReviewStatus,
    UsageRecord,
    Verdict,
)

DEFAULT_DB_PATH = Path(".avt/avt.db")
_NAMESPACE = "avt"
_DATABASE = "main"


class SurrealGovernanceStore:
    """SurrealDB-backed governance store with the same public interface as GovernanceStore."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional[Surreal] = None
        self._init_db()

    def _get_db(self) -> Surreal:
        if self._db is None:
            self._db = Surreal(f"surrealkv://{self.db_path}")
            self._db.use(_NAMESPACE, _DATABASE)
        return self._db

    def _init_db(self) -> None:
        """Initialize schema (tables and indexes). Idempotent."""
        db = self._get_db()
        db.query("""
            DEFINE TABLE IF NOT EXISTS decision SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS task_id ON decision TYPE string;
            DEFINE FIELD IF NOT EXISTS sequence ON decision TYPE int;
            DEFINE FIELD IF NOT EXISTS agent ON decision TYPE string;
            DEFINE FIELD IF NOT EXISTS category ON decision TYPE string;
            DEFINE FIELD IF NOT EXISTS summary ON decision TYPE string;
            DEFINE FIELD IF NOT EXISTS detail ON decision TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS intent ON decision TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS expected_outcome ON decision TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS vision_references ON decision TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS components_affected ON decision TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS alternatives ON decision TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS confidence ON decision TYPE string DEFAULT 'high';
            DEFINE FIELD IF NOT EXISTS created_at ON decision TYPE string;
            DEFINE INDEX IF NOT EXISTS idx_decision_task ON decision FIELDS task_id;

            DEFINE TABLE IF NOT EXISTS review SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS decision_id ON review TYPE option<string>;
            DEFINE FIELD IF NOT EXISTS plan_id ON review TYPE option<string>;
            DEFINE FIELD IF NOT EXISTS verdict ON review TYPE string;
            DEFINE FIELD IF NOT EXISTS findings ON review TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS guidance ON review TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS strengths_summary ON review TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS standards_verified ON review TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS reviewer ON review TYPE string DEFAULT 'governance-reviewer';
            DEFINE FIELD IF NOT EXISTS created_at ON review TYPE string;
            DEFINE INDEX IF NOT EXISTS idx_review_decision ON review FIELDS decision_id;
            DEFINE INDEX IF NOT EXISTS idx_review_plan ON review FIELDS plan_id;

            DEFINE TABLE IF NOT EXISTS governed_task SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS implementation_task_id ON governed_task TYPE string;
            DEFINE FIELD IF NOT EXISTS subject ON governed_task TYPE string;
            DEFINE FIELD IF NOT EXISTS description ON governed_task TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS context ON governed_task TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS current_status ON governed_task TYPE string DEFAULT 'pending_review';
            DEFINE FIELD IF NOT EXISTS session_id ON governed_task TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS created_at ON governed_task TYPE string;
            DEFINE FIELD IF NOT EXISTS released_at ON governed_task TYPE option<string>;
            DEFINE INDEX IF NOT EXISTS idx_governed_task_impl ON governed_task FIELDS implementation_task_id UNIQUE;

            DEFINE TABLE IF NOT EXISTS task_review SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS review_task_id ON task_review TYPE string;
            DEFINE FIELD IF NOT EXISTS implementation_task_id ON task_review TYPE string;
            DEFINE FIELD IF NOT EXISTS review_type ON task_review TYPE string DEFAULT 'governance';
            DEFINE FIELD IF NOT EXISTS status ON task_review TYPE string DEFAULT 'pending';
            DEFINE FIELD IF NOT EXISTS context ON task_review TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS verdict ON task_review TYPE option<string>;
            DEFINE FIELD IF NOT EXISTS guidance ON task_review TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS findings ON task_review TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS standards_verified ON task_review TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS reviewer ON task_review TYPE string DEFAULT 'governance-reviewer';
            DEFINE FIELD IF NOT EXISTS created_at ON task_review TYPE string;
            DEFINE FIELD IF NOT EXISTS completed_at ON task_review TYPE option<string>;
            DEFINE INDEX IF NOT EXISTS idx_task_review_impl ON task_review FIELDS implementation_task_id;
            DEFINE INDEX IF NOT EXISTS idx_task_review_review ON task_review FIELDS review_task_id;

            DEFINE TABLE IF NOT EXISTS holistic_review SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS session_id ON holistic_review TYPE string;
            DEFINE FIELD IF NOT EXISTS task_ids ON holistic_review TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS task_subjects ON holistic_review TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS collective_intent ON holistic_review TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS verdict ON holistic_review TYPE option<string>;
            DEFINE FIELD IF NOT EXISTS findings ON holistic_review TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS guidance ON holistic_review TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS strengths_summary ON holistic_review TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS standards_verified ON holistic_review TYPE array DEFAULT [];
            DEFINE FIELD IF NOT EXISTS reviewer ON holistic_review TYPE string DEFAULT 'governance-reviewer';
            DEFINE FIELD IF NOT EXISTS created_at ON holistic_review TYPE string;
            DEFINE INDEX IF NOT EXISTS idx_holistic_review_session ON holistic_review FIELDS session_id;

            DEFINE TABLE IF NOT EXISTS token_usage SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS timestamp ON token_usage TYPE string;
            DEFINE FIELD IF NOT EXISTS session_id ON token_usage TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS agent ON token_usage TYPE string;
            DEFINE FIELD IF NOT EXISTS operation ON token_usage TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS model ON token_usage TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS input_tokens ON token_usage TYPE int DEFAULT 0;
            DEFINE FIELD IF NOT EXISTS output_tokens ON token_usage TYPE int DEFAULT 0;
            DEFINE FIELD IF NOT EXISTS cache_read_tokens ON token_usage TYPE int DEFAULT 0;
            DEFINE FIELD IF NOT EXISTS cache_creation_tokens ON token_usage TYPE int DEFAULT 0;
            DEFINE FIELD IF NOT EXISTS duration_ms ON token_usage TYPE int DEFAULT 0;
            DEFINE FIELD IF NOT EXISTS related_id ON token_usage TYPE string DEFAULT '';
            DEFINE FIELD IF NOT EXISTS prompt_bytes ON token_usage TYPE int DEFAULT 0;
            DEFINE INDEX IF NOT EXISTS idx_token_usage_timestamp ON token_usage FIELDS timestamp;
            DEFINE INDEX IF NOT EXISTS idx_token_usage_session ON token_usage FIELDS session_id;
            DEFINE INDEX IF NOT EXISTS idx_token_usage_agent ON token_usage FIELDS agent;
        """)

    # =========================================================================
    # Decision Methods
    # =========================================================================

    def next_sequence(self, task_id: str) -> int:
        db = self._get_db()
        result = db.query(
            "SELECT sequence FROM decision WHERE task_id = $tid ORDER BY sequence DESC LIMIT 1",
            {"tid": task_id},
        )
        rows = _extract_rows(result)
        if rows and rows[0].get("sequence") is not None:
            return rows[0]["sequence"] + 1
        return 1

    def store_decision(self, decision: Decision) -> Decision:
        if decision.sequence == 0:
            decision.sequence = self.next_sequence(decision.task_id)
        db = self._get_db()
        db.query(
            """CREATE type::thing('decision', $id) SET
                task_id = $task_id,
                sequence = $sequence,
                agent = $agent,
                category = $category,
                summary = $summary,
                detail = $detail,
                intent = $intent,
                expected_outcome = $expected_outcome,
                vision_references = $vision_references,
                components_affected = $components_affected,
                alternatives = $alternatives,
                confidence = $confidence,
                created_at = $created_at
            """,
            {
                "id": decision.id,
                "task_id": decision.task_id,
                "sequence": decision.sequence,
                "agent": decision.agent,
                "category": decision.category.value,
                "summary": decision.summary,
                "detail": decision.detail,
                "intent": decision.intent,
                "expected_outcome": decision.expected_outcome,
                "vision_references": decision.vision_references,
                "components_affected": decision.components_affected,
                "alternatives": [a.model_dump() for a in decision.alternatives_considered],
                "confidence": decision.confidence.value,
                "created_at": decision.created_at,
            },
        )
        return decision

    def store_review(self, review: ReviewVerdict) -> ReviewVerdict:
        db = self._get_db()
        db.query(
            """CREATE type::thing('review', $id) SET
                decision_id = $decision_id,
                plan_id = $plan_id,
                verdict = $verdict,
                findings = $findings,
                guidance = $guidance,
                strengths_summary = $strengths_summary,
                standards_verified = $standards_verified,
                reviewer = $reviewer,
                created_at = $created_at
            """,
            {
                "id": review.id,
                "decision_id": review.decision_id,
                "plan_id": review.plan_id,
                "verdict": review.verdict.value,
                "findings": [f.model_dump() for f in review.findings],
                "guidance": review.guidance,
                "strengths_summary": review.strengths_summary,
                "standards_verified": review.standards_verified,
                "reviewer": review.reviewer,
                "created_at": review.created_at,
            },
        )
        return review

    def get_decisions_for_task(self, task_id: str) -> list[Decision]:
        db = self._get_db()
        result = db.query(
            "SELECT * FROM decision WHERE task_id = $tid ORDER BY sequence ASC",
            {"tid": task_id},
        )
        return [self._row_to_decision(r) for r in _extract_rows(result)]

    def get_review_for_decision(self, decision_id: str) -> Optional[ReviewVerdict]:
        db = self._get_db()
        result = db.query(
            "SELECT * FROM review WHERE decision_id = $did ORDER BY created_at DESC LIMIT 1",
            {"did": decision_id},
        )
        rows = _extract_rows(result)
        return self._row_to_review(rows[0]) if rows else None

    def get_reviews_for_task(self, task_id: str) -> list[ReviewVerdict]:
        db = self._get_db()
        # Two-step: get decision IDs for the task, then fetch their reviews
        dec_result = db.query(
            "SELECT id FROM decision WHERE task_id = $tid",
            {"tid": task_id},
        )
        dec_ids = [_record_id_str(r.get("id")) for r in _extract_rows(dec_result)]
        if not dec_ids:
            return []
        rev_result = db.query(
            "SELECT * FROM review WHERE decision_id IN $ids ORDER BY created_at ASC",
            {"ids": dec_ids},
        )
        return [self._row_to_review(r) for r in _extract_rows(rev_result)]

    def get_all_decisions(
        self,
        task_id: Optional[str] = None,
        agent: Optional[str] = None,
        verdict: Optional[str] = None,
    ) -> list[dict]:
        db = self._get_db()
        conditions = []
        params: dict = {}
        if task_id:
            conditions.append("task_id = $task_id")
            params["task_id"] = task_id
        if agent:
            conditions.append("agent = $agent")
            params["agent"] = agent

        where = " AND ".join(conditions) if conditions else "true"
        result = db.query(
            f"SELECT * FROM decision WHERE {where} ORDER BY created_at DESC",
            params,
        )
        decisions_rows = _extract_rows(result)

        results = []
        for r in decisions_rows:
            did = _record_id_str(r.get("id"))
            # Fetch associated review
            rev_result = db.query(
                "SELECT verdict, guidance FROM review WHERE decision_id = $did LIMIT 1",
                {"did": did},
            )
            rev_rows = _extract_rows(rev_result)
            review_verdict = rev_rows[0].get("verdict") if rev_rows else None
            review_guidance = rev_rows[0].get("guidance", "") if rev_rows else ""

            if verdict and review_verdict != verdict:
                continue

            results.append({
                "id": did,
                "task_id": r.get("task_id", ""),
                "sequence": r.get("sequence", 0),
                "agent": r.get("agent", ""),
                "category": r.get("category", ""),
                "summary": r.get("summary", ""),
                "confidence": r.get("confidence", ""),
                "verdict": review_verdict,
                "guidance": review_guidance,
                "created_at": r.get("created_at", ""),
                "intent": r.get("intent", ""),
                "expected_outcome": r.get("expected_outcome", ""),
            })
        return results

    def get_status(self) -> dict:
        db = self._get_db()
        total_r = db.query("SELECT count() AS c FROM decision GROUP ALL")
        total = _scalar(total_r, "c", 0)

        approved_r = db.query("SELECT count() AS c FROM review WHERE verdict = 'approved' GROUP ALL")
        approved = _scalar(approved_r, "c", 0)

        blocked_r = db.query("SELECT count() AS c FROM review WHERE verdict = 'blocked' GROUP ALL")
        blocked = _scalar(blocked_r, "c", 0)

        needs_human_r = db.query("SELECT count() AS c FROM review WHERE verdict = 'needs_human_review' GROUP ALL")
        needs_human = _scalar(needs_human_r, "c", 0)

        recent_r = db.query(
            "SELECT id, summary, agent, category, created_at FROM decision ORDER BY created_at DESC LIMIT 5"
        )
        recent_rows = _extract_rows(recent_r)

        recent_activity = []
        for r in recent_rows:
            did = _record_id_str(r.get("id"))
            rev = db.query(
                "SELECT verdict FROM review WHERE decision_id = $did LIMIT 1",
                {"did": did},
            )
            rev_rows = _extract_rows(rev)
            recent_activity.append({
                "summary": r.get("summary", ""),
                "agent": r.get("agent", ""),
                "category": r.get("category", ""),
                "verdict": rev_rows[0].get("verdict") if rev_rows else None,
            })

        return {
            "total_decisions": total,
            "approved": approved,
            "blocked": blocked,
            "needs_human_review": needs_human,
            "pending": total - approved - blocked - needs_human,
            "recent_activity": recent_activity,
        }

    def has_plan_review(self, task_id: str) -> bool:
        db = self._get_db()
        result = db.query(
            "SELECT count() AS c FROM review WHERE plan_id = $pid GROUP ALL",
            {"pid": task_id},
        )
        return _scalar(result, "c", 0) > 0

    def has_unresolved_blocks(self, task_id: str) -> bool:
        db = self._get_db()
        # Get decision IDs for the task
        dec_result = db.query(
            "SELECT id FROM decision WHERE task_id = $tid",
            {"tid": task_id},
        )
        dec_ids = [_record_id_str(r.get("id")) for r in _extract_rows(dec_result)]
        if not dec_ids:
            return False
        result = db.query(
            "SELECT count() AS c FROM review WHERE decision_id IN $ids AND verdict = 'blocked' GROUP ALL",
            {"ids": dec_ids},
        )
        return _scalar(result, "c", 0) > 0

    # =========================================================================
    # Task Governance Methods
    # =========================================================================

    def store_governed_task(self, task: GovernedTaskRecord) -> GovernedTaskRecord:
        db = self._get_db()
        db.query(
            """CREATE type::thing('governed_task', $id) SET
                implementation_task_id = $impl_id,
                subject = $subject,
                description = $description,
                context = $context,
                current_status = $status,
                session_id = $session_id,
                created_at = $created_at,
                released_at = $released_at
            """,
            {
                "id": task.id,
                "impl_id": task.implementation_task_id,
                "subject": task.subject,
                "description": task.description,
                "context": task.context,
                "status": task.current_status,
                "session_id": task.session_id,
                "created_at": task.created_at,
                "released_at": task.released_at,
            },
        )
        return task

    def store_task_review(self, review: TaskReviewRecord) -> TaskReviewRecord:
        db = self._get_db()
        db.query(
            """CREATE type::thing('task_review', $id) SET
                review_task_id = $review_task_id,
                implementation_task_id = $impl_id,
                review_type = $review_type,
                status = $status,
                context = $context,
                verdict = $verdict,
                guidance = $guidance,
                findings = $findings,
                standards_verified = $standards_verified,
                reviewer = $reviewer,
                created_at = $created_at,
                completed_at = $completed_at
            """,
            {
                "id": review.id,
                "review_task_id": review.review_task_id,
                "impl_id": review.implementation_task_id,
                "review_type": review.review_type.value,
                "status": review.status.value,
                "context": review.context,
                "verdict": review.verdict.value if review.verdict else None,
                "guidance": review.guidance,
                "findings": [f.model_dump() for f in review.findings],
                "standards_verified": review.standards_verified,
                "reviewer": review.reviewer,
                "created_at": review.created_at,
                "completed_at": review.completed_at,
            },
        )
        return review

    def update_task_review(self, review: TaskReviewRecord) -> TaskReviewRecord:
        db = self._get_db()
        db.query(
            """UPDATE type::thing('task_review', $id) SET
                status = $status,
                verdict = $verdict,
                guidance = $guidance,
                findings = $findings,
                standards_verified = $standards_verified,
                completed_at = $completed_at
            """,
            {
                "id": review.id,
                "status": review.status.value,
                "verdict": review.verdict.value if review.verdict else None,
                "guidance": review.guidance,
                "findings": [f.model_dump() for f in review.findings],
                "standards_verified": review.standards_verified,
                "completed_at": review.completed_at,
            },
        )
        return review

    def update_governed_task_status(
        self, implementation_task_id: str, status: str, released_at: Optional[str] = None
    ) -> None:
        db = self._get_db()
        db.query(
            """UPDATE governed_task SET
                current_status = $status,
                released_at = $released_at
               WHERE implementation_task_id = $impl_id
            """,
            {
                "impl_id": implementation_task_id,
                "status": status,
                "released_at": released_at,
            },
        )

    def get_governed_task(self, implementation_task_id: str) -> Optional[GovernedTaskRecord]:
        db = self._get_db()
        result = db.query(
            "SELECT * FROM governed_task WHERE implementation_task_id = $impl_id LIMIT 1",
            {"impl_id": implementation_task_id},
        )
        rows = _extract_rows(result)
        if not rows:
            return None
        return self._row_to_governed_task(rows[0])

    def get_task_reviews(self, implementation_task_id: str) -> list[TaskReviewRecord]:
        db = self._get_db()
        result = db.query(
            "SELECT * FROM task_review WHERE implementation_task_id = $impl_id ORDER BY created_at ASC",
            {"impl_id": implementation_task_id},
        )
        return [self._row_to_task_review(r) for r in _extract_rows(result)]

    def get_task_review_by_review_task_id(self, review_task_id: str) -> Optional[TaskReviewRecord]:
        db = self._get_db()
        result = db.query(
            "SELECT * FROM task_review WHERE review_task_id = $rtid LIMIT 1",
            {"rtid": review_task_id},
        )
        rows = _extract_rows(result)
        if not rows:
            return None
        return self._row_to_task_review(rows[0])

    def get_pending_task_reviews(self) -> list[TaskReviewRecord]:
        db = self._get_db()
        result = db.query(
            "SELECT * FROM task_review WHERE status = 'pending' ORDER BY created_at ASC"
        )
        return [self._row_to_task_review(r) for r in _extract_rows(result)]

    def get_all_governed_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        db = self._get_db()
        params: dict = {"lim": limit}
        if status:
            query = "SELECT * FROM governed_task WHERE current_status = $status ORDER BY created_at DESC LIMIT $lim"
            params["status"] = status
        else:
            query = "SELECT * FROM governed_task ORDER BY created_at DESC LIMIT $lim"

        result = db.query(query, params)
        rows = _extract_rows(result)

        output = []
        for row in rows:
            impl_id = row.get("implementation_task_id", "")
            # Fetch reviews for this task
            rev_result = db.query(
                "SELECT * FROM task_review WHERE implementation_task_id = $impl_id ORDER BY created_at ASC",
                {"impl_id": impl_id},
            )
            review_list = []
            for r in _extract_rows(rev_result):
                review_list.append({
                    "id": _record_id_str(r.get("id")),
                    "review_task_id": r.get("review_task_id", ""),
                    "review_type": r.get("review_type", "governance"),
                    "status": r.get("status", "pending"),
                    "verdict": r.get("verdict"),
                    "guidance": r.get("guidance", ""),
                    "findings": r.get("findings", []),
                    "created_at": r.get("created_at", ""),
                    "completed_at": r.get("completed_at"),
                })
            output.append({
                "id": _record_id_str(row.get("id")),
                "implementation_task_id": impl_id,
                "subject": row.get("subject", ""),
                "description": row.get("description", ""),
                "current_status": row.get("current_status", "pending_review"),
                "created_at": row.get("created_at", ""),
                "released_at": row.get("released_at"),
                "reviews": review_list,
            })
        return output

    def get_task_governance_stats(self) -> dict:
        db = self._get_db()
        total = _scalar(
            db.query("SELECT count() AS c FROM governed_task GROUP ALL"), "c", 0
        )
        pending = _scalar(
            db.query("SELECT count() AS c FROM governed_task WHERE current_status = 'pending_review' GROUP ALL"),
            "c", 0,
        )
        approved = _scalar(
            db.query("SELECT count() AS c FROM governed_task WHERE current_status = 'approved' GROUP ALL"),
            "c", 0,
        )
        blocked = _scalar(
            db.query("SELECT count() AS c FROM governed_task WHERE current_status = 'blocked' GROUP ALL"),
            "c", 0,
        )
        pending_reviews = _scalar(
            db.query("SELECT count() AS c FROM task_review WHERE status = 'pending' GROUP ALL"),
            "c", 0,
        )
        return {
            "total_governed_tasks": total,
            "pending_review": pending,
            "approved": approved,
            "blocked": blocked,
            "pending_reviews": pending_reviews,
        }

    # =========================================================================
    # Holistic Review Methods
    # =========================================================================

    def store_holistic_review(self, record: HolisticReviewRecord) -> HolisticReviewRecord:
        db = self._get_db()
        db.query(
            """CREATE type::thing('holistic_review', $id) SET
                session_id = $session_id,
                task_ids = $task_ids,
                task_subjects = $task_subjects,
                collective_intent = $collective_intent,
                verdict = $verdict,
                findings = $findings,
                guidance = $guidance,
                strengths_summary = $strengths_summary,
                standards_verified = $standards_verified,
                reviewer = $reviewer,
                created_at = $created_at
            """,
            {
                "id": record.id,
                "session_id": record.session_id,
                "task_ids": record.task_ids,
                "task_subjects": record.task_subjects,
                "collective_intent": record.collective_intent,
                "verdict": record.verdict.value if record.verdict else None,
                "findings": [f.model_dump() for f in record.findings],
                "guidance": record.guidance,
                "strengths_summary": record.strengths_summary,
                "standards_verified": record.standards_verified,
                "reviewer": record.reviewer,
                "created_at": record.created_at,
            },
        )
        return record

    def get_holistic_review_for_session(self, session_id: str) -> Optional[HolisticReviewRecord]:
        db = self._get_db()
        result = db.query(
            "SELECT * FROM holistic_review WHERE session_id = $sid ORDER BY created_at DESC LIMIT 1",
            {"sid": session_id},
        )
        rows = _extract_rows(result)
        if not rows:
            return None
        return self._row_to_holistic_review(rows[0])

    def get_tasks_for_session(self, session_id: str) -> list[GovernedTaskRecord]:
        db = self._get_db()
        result = db.query(
            "SELECT * FROM governed_task WHERE session_id = $sid ORDER BY created_at ASC",
            {"sid": session_id},
        )
        return [self._row_to_governed_task(r) for r in _extract_rows(result)]

    def get_latest_task_timestamp_for_session(self, session_id: str) -> Optional[str]:
        db = self._get_db()
        result = db.query(
            "SELECT math::max(created_at) AS latest FROM governed_task WHERE session_id = $sid",
            {"sid": session_id},
        )
        rows = _extract_rows(result)
        if rows and rows[0].get("latest"):
            return rows[0]["latest"]
        return None

    # =========================================================================
    # Token Usage Tracking Methods
    # =========================================================================

    def store_usage(self, record: UsageRecord) -> UsageRecord:
        db = self._get_db()
        db.query(
            """CREATE type::thing('token_usage', $id) SET
                timestamp = $timestamp,
                session_id = $session_id,
                agent = $agent,
                operation = $operation,
                model = $model,
                input_tokens = $input_tokens,
                output_tokens = $output_tokens,
                cache_read_tokens = $cache_read_tokens,
                cache_creation_tokens = $cache_creation_tokens,
                duration_ms = $duration_ms,
                related_id = $related_id,
                prompt_bytes = $prompt_bytes
            """,
            {
                "id": record.id,
                "timestamp": record.timestamp,
                "session_id": record.session_id,
                "agent": record.agent,
                "operation": record.operation,
                "model": record.model,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "cache_read_tokens": record.cache_read_tokens,
                "cache_creation_tokens": record.cache_creation_tokens,
                "duration_ms": record.duration_ms,
                "related_id": record.related_id,
                "prompt_bytes": record.prompt_bytes,
            },
        )
        return record

    def get_usage_summary(
        self,
        period: str = "day",
        session_id: Optional[str] = None,
    ) -> dict:
        db = self._get_db()
        where, params = self._usage_period_filter(period, session_id)
        result = db.query(
            f"""SELECT
                count() AS call_count,
                math::sum(input_tokens) AS total_input,
                math::sum(output_tokens) AS total_output,
                math::sum(cache_read_tokens) AS total_cache_reads,
                math::sum(cache_creation_tokens) AS total_cache_creation,
                math::sum(duration_ms) AS total_duration_ms,
                math::sum(prompt_bytes) AS total_prompt_bytes
            FROM token_usage WHERE {where} GROUP ALL""",
            params,
        )
        rows = _extract_rows(result)
        if rows:
            r = rows[0]
            total_in = r.get("total_input") or 0
            total_out = r.get("total_output") or 0
            return {
                "period": period,
                "call_count": r.get("call_count") or 0,
                "total_input_tokens": total_in,
                "total_output_tokens": total_out,
                "total_tokens": total_in + total_out,
                "total_cache_reads": r.get("total_cache_reads") or 0,
                "total_cache_creation": r.get("total_cache_creation") or 0,
                "total_duration_ms": r.get("total_duration_ms") or 0,
                "total_prompt_bytes": r.get("total_prompt_bytes") or 0,
            }
        return {
            "period": period,
            "call_count": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cache_reads": 0,
            "total_cache_creation": 0,
            "total_duration_ms": 0,
            "total_prompt_bytes": 0,
        }

    def get_usage_by_agent(
        self,
        period: str = "day",
        session_id: Optional[str] = None,
    ) -> list[dict]:
        db = self._get_db()
        where, params = self._usage_period_filter(period, session_id)
        result = db.query(
            f"""SELECT
                agent,
                count() AS call_count,
                math::sum(input_tokens) AS total_input,
                math::sum(output_tokens) AS total_output,
                math::sum(duration_ms) AS total_duration_ms
            FROM token_usage WHERE {where}
            GROUP BY agent""",
            params,
        )
        output = []
        for r in _extract_rows(result):
            total_in = r.get("total_input") or 0
            total_out = r.get("total_output") or 0
            output.append({
                "agent": r.get("agent", ""),
                "call_count": r.get("call_count") or 0,
                "input_tokens": total_in,
                "output_tokens": total_out,
                "total_tokens": total_in + total_out,
                "duration_ms": r.get("total_duration_ms") or 0,
            })
        # Sort in Python (SurrealDB embedded doesn't support ORDER BY on expressions)
        output.sort(key=lambda x: x["total_tokens"], reverse=True)
        return output

    def get_usage_by_operation(
        self,
        period: str = "day",
        session_id: Optional[str] = None,
    ) -> list[dict]:
        db = self._get_db()
        where, params = self._usage_period_filter(period, session_id)
        result = db.query(
            f"""SELECT
                operation,
                count() AS call_count,
                math::sum(input_tokens) AS total_input,
                math::sum(output_tokens) AS total_output,
                math::mean(prompt_bytes) AS avg_prompt_bytes,
                math::sum(duration_ms) AS total_duration_ms
            FROM token_usage WHERE {where}
            GROUP BY operation""",
            params,
        )
        output = []
        for r in _extract_rows(result):
            total_in = r.get("total_input") or 0
            total_out = r.get("total_output") or 0
            output.append({
                "operation": r.get("operation", ""),
                "call_count": r.get("call_count") or 0,
                "input_tokens": total_in,
                "output_tokens": total_out,
                "total_tokens": total_in + total_out,
                "avg_prompt_bytes": int(r.get("avg_prompt_bytes") or 0),
                "duration_ms": r.get("total_duration_ms") or 0,
            })
        # Sort in Python (SurrealDB embedded doesn't support ORDER BY on expressions)
        output.sort(key=lambda x: x["total_tokens"], reverse=True)
        return output

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _usage_period_filter(self, period: str, session_id: Optional[str] = None) -> tuple[str, dict]:
        """Build WHERE clause fragment and params for usage queries."""
        if period == "session" and session_id:
            return "session_id = $session_id", {"session_id": session_id}

        now = datetime.now(timezone.utc)
        if period == "week":
            cutoff = (now - timedelta(days=7)).isoformat()
        else:  # day
            cutoff = (now - timedelta(days=1)).isoformat()

        params: dict = {"cutoff": cutoff}
        clause = "timestamp >= $cutoff"
        if session_id:
            clause += " AND session_id = $session_id"
            params["session_id"] = session_id
        return clause, params

    def _row_to_decision(self, row: dict) -> Decision:
        alts_raw = row.get("alternatives") or []
        return Decision(
            id=_record_id_str(row.get("id")),
            task_id=row.get("task_id", ""),
            sequence=row.get("sequence", 0),
            agent=row.get("agent", ""),
            category=DecisionCategory(row.get("category", "pattern_choice")),
            summary=row.get("summary", ""),
            detail=row.get("detail", ""),
            intent=row.get("intent", ""),
            expected_outcome=row.get("expected_outcome", ""),
            vision_references=row.get("vision_references") or [],
            components_affected=row.get("components_affected") or [],
            alternatives_considered=[Alternative(**a) for a in alts_raw],
            confidence=Confidence(row.get("confidence", "high")),
            created_at=row.get("created_at", ""),
        )

    def _row_to_review(self, row: dict) -> ReviewVerdict:
        findings_raw = row.get("findings") or []
        return ReviewVerdict(
            id=_record_id_str(row.get("id")),
            decision_id=row.get("decision_id"),
            plan_id=row.get("plan_id"),
            verdict=Verdict(row.get("verdict", "approved")),
            findings=[Finding(**f) for f in findings_raw],
            guidance=row.get("guidance", ""),
            strengths_summary=row.get("strengths_summary", ""),
            standards_verified=row.get("standards_verified") or [],
            reviewer=row.get("reviewer", "governance-reviewer"),
            created_at=row.get("created_at", ""),
        )

    def _row_to_governed_task(self, row: dict) -> GovernedTaskRecord:
        return GovernedTaskRecord(
            id=_record_id_str(row.get("id")),
            implementation_task_id=row.get("implementation_task_id", ""),
            subject=row.get("subject", ""),
            description=row.get("description", ""),
            context=row.get("context", ""),
            current_status=row.get("current_status", "pending_review"),
            session_id=row.get("session_id", ""),
            created_at=row.get("created_at", ""),
            released_at=row.get("released_at"),
        )

    def _row_to_task_review(self, row: dict) -> TaskReviewRecord:
        findings_raw = row.get("findings") or []
        verdict_val = row.get("verdict")
        return TaskReviewRecord(
            id=_record_id_str(row.get("id")),
            review_task_id=row.get("review_task_id", ""),
            implementation_task_id=row.get("implementation_task_id", ""),
            review_type=ReviewType(row.get("review_type", "governance")),
            status=TaskReviewStatus(row.get("status", "pending")),
            context=row.get("context", ""),
            verdict=Verdict(verdict_val) if verdict_val else None,
            guidance=row.get("guidance", ""),
            findings=[Finding(**f) for f in findings_raw],
            standards_verified=row.get("standards_verified") or [],
            reviewer=row.get("reviewer", "governance-reviewer"),
            created_at=row.get("created_at", ""),
            completed_at=row.get("completed_at"),
        )

    def _row_to_holistic_review(self, row: dict) -> HolisticReviewRecord:
        findings_raw = row.get("findings") or []
        verdict_val = row.get("verdict")
        return HolisticReviewRecord(
            id=_record_id_str(row.get("id")),
            session_id=row.get("session_id", ""),
            task_ids=row.get("task_ids") or [],
            task_subjects=row.get("task_subjects") or [],
            collective_intent=row.get("collective_intent", ""),
            verdict=Verdict(verdict_val) if verdict_val else None,
            findings=[Finding(**f) for f in findings_raw],
            guidance=row.get("guidance", ""),
            strengths_summary=row.get("strengths_summary", ""),
            standards_verified=row.get("standards_verified") or [],
            reviewer=row.get("reviewer", "governance-reviewer"),
            created_at=row.get("created_at", ""),
        )

    def close(self) -> None:
        if self._db is not None:
            self._db = None


# =============================================================================
# Module-level Helpers
# =============================================================================


def _extract_rows(result) -> list[dict]:
    """Extract row dicts from SurrealDB query result.

    The SurrealDB Python SDK returns results in varying formats depending
    on version:
      - List of dicts directly
      - List of {"result": [...], "status": "OK"} wrapper objects
      - Single dict with "result" key
    This helper normalises all of them to a flat list of row dicts.
    """
    if result is None:
        return []
    # If result is already a list of plain dicts (no "result" key), return as-is
    if isinstance(result, list):
        if not result:
            return []
        first = result[0]
        # Wrapped format: [{"result": [...], "status": "OK"}, ...]
        if isinstance(first, dict) and "result" in first:
            inner = first["result"]
            return inner if isinstance(inner, list) else []
        # Flat list of row dicts
        if isinstance(first, dict):
            return result
    if isinstance(result, dict):
        inner = result.get("result", [])
        return inner if isinstance(inner, list) else []
    return []


def _record_id_str(value) -> str:
    """Convert a SurrealDB record ID to a plain string.

    The SDK v1.0.x returns RecordID objects with table_name and record_id
    attributes, or sometimes 'table:id' strings. We extract just the ID
    portion so it matches what the caller originally provided (and what
    the SQLite store returns).

    SurrealDB wraps non-standard identifiers in angle brackets (e.g.
    ``⟨smoke-d1⟩``), which must be stripped.
    """
    if value is None:
        return ""
    # RecordID object (surrealdb SDK v1.0.x)
    if hasattr(value, "record_id"):
        return _strip_brackets(str(value.record_id))
    if hasattr(value, "key"):
        return _strip_brackets(str(value.key))
    s = str(value)
    if ":" in s:
        return _strip_brackets(s.split(":", 1)[1])
    return _strip_brackets(s)


def _strip_brackets(s: str) -> str:
    """Remove SurrealDB angle-bracket quoting from identifiers.

    SurrealDB uses ``\u27e8`` and ``\u27e9`` (mathematical angle brackets)
    to quote identifiers containing special characters like hyphens.
    """
    if s.startswith("\u27e8") and s.endswith("\u27e9"):
        return s[1:-1]
    # Also handle regular angle brackets just in case
    if s.startswith("<") and s.endswith(">"):
        return s[1:-1]
    return s


def _scalar(result, key: str, default=0):
    """Extract a single scalar value from a SurrealDB aggregate query result."""
    rows = _extract_rows(result)
    if rows:
        val = rows[0].get(key)
        return val if val is not None else default
    return default
