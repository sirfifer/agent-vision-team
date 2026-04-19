"""Smoke tests for SurrealGovernanceStore.

Instantiates the store against a temporary SurrealKV database and exercises
every public method to verify basic correctness and parity with the SQLite
GovernanceStore.

Run:
    cd mcp-servers/governance
    uv run pytest tests/test_surreal_governance_store.py -v
"""

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Guard: skip all tests if surrealdb or pydantic are not installed
pytest.importorskip("surrealdb", reason="surrealdb SDK not installed")
pytest.importorskip("pydantic", reason="pydantic not installed")

from collab_governance.models import (
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

from collab_governance.surreal_store import SurrealGovernanceStore  # noqa: E402


@pytest.fixture()
def store(tmp_path: Path):
    """Create a SurrealGovernanceStore backed by a temporary directory."""
    db_path = tmp_path / "test.db"
    s = SurrealGovernanceStore(db_path=db_path)
    yield s
    s.close()
    # Clean up the SurrealKV data directory
    if db_path.exists():
        shutil.rmtree(db_path, ignore_errors=True)


# ---- Decision + Review round-trip ----


def test_store_and_retrieve_decision(store: SurrealGovernanceStore):
    d = Decision(
        id="dec-001",
        task_id="task-1",
        agent="worker-1",
        category=DecisionCategory.PATTERN_CHOICE,
        summary="Use factory pattern",
        detail="Factories over constructors for flexibility.",
        intent="Improve testability",
        expected_outcome="All services use DI",
        vision_references=["protocol-di"],
        components_affected=["ServiceRegistry"],
        confidence=Confidence.HIGH,
    )
    result = store.store_decision(d)
    assert result.sequence == 1

    decisions = store.get_decisions_for_task("task-1")
    assert len(decisions) == 1
    assert decisions[0].id == "dec-001"
    assert decisions[0].summary == "Use factory pattern"
    assert decisions[0].intent == "Improve testability"
    assert decisions[0].vision_references == ["protocol-di"]
    assert decisions[0].components_affected == ["ServiceRegistry"]


def test_sequence_auto_increment(store: SurrealGovernanceStore):
    for i in range(3):
        d = Decision(
            id=f"dec-{i}",
            task_id="task-seq",
            agent="w",
            category=DecisionCategory.API_DESIGN,
            summary=f"Decision {i}",
        )
        store.store_decision(d)

    decisions = store.get_decisions_for_task("task-seq")
    seqs = [d.sequence for d in decisions]
    assert seqs == [1, 2, 3]


def test_store_and_retrieve_review(store: SurrealGovernanceStore):
    # Pre-requisite: a decision
    d = Decision(
        id="dec-r",
        task_id="task-r",
        agent="w",
        category=DecisionCategory.COMPONENT_DESIGN,
        summary="Design widget",
    )
    store.store_decision(d)

    review = ReviewVerdict(
        id="rev-001",
        decision_id="dec-r",
        verdict=Verdict.APPROVED,
        findings=[
            Finding(
                tier="quality",
                severity="minor",
                description="Looks good",
                suggestion="None",
                strengths=["Clean design"],
                salvage_guidance="",
            )
        ],
        guidance="Proceed.",
        strengths_summary="Solid approach.",
        standards_verified=["di-standard"],
        reviewer="governance-reviewer",
    )
    store.store_review(review)

    fetched = store.get_review_for_decision("dec-r")
    assert fetched is not None
    assert fetched.verdict == Verdict.APPROVED
    assert fetched.strengths_summary == "Solid approach."
    assert len(fetched.findings) == 1
    assert fetched.findings[0].strengths == ["Clean design"]


def test_get_reviews_for_task(store: SurrealGovernanceStore):
    d = Decision(
        id="dec-t",
        task_id="task-t",
        agent="w",
        category=DecisionCategory.PATTERN_CHOICE,
        summary="Choose pattern",
    )
    store.store_decision(d)
    r = ReviewVerdict(
        id="rev-t",
        decision_id="dec-t",
        verdict=Verdict.BLOCKED,
        guidance="Needs rework.",
    )
    store.store_review(r)

    reviews = store.get_reviews_for_task("task-t")
    assert len(reviews) == 1
    assert reviews[0].verdict == Verdict.BLOCKED


# ---- get_all_decisions with filters ----


def test_get_all_decisions_filters(store: SurrealGovernanceStore):
    d1 = Decision(
        id="fa-1", task_id="t1", agent="alice",
        category=DecisionCategory.API_DESIGN, summary="API v1",
    )
    d2 = Decision(
        id="fa-2", task_id="t2", agent="bob",
        category=DecisionCategory.DEVIATION, summary="Deviate",
    )
    store.store_decision(d1)
    store.store_decision(d2)

    r1 = ReviewVerdict(id="fr-1", decision_id="fa-1", verdict=Verdict.APPROVED)
    r2 = ReviewVerdict(id="fr-2", decision_id="fa-2", verdict=Verdict.BLOCKED)
    store.store_review(r1)
    store.store_review(r2)

    # Filter by agent
    by_agent = store.get_all_decisions(agent="alice")
    assert len(by_agent) == 1
    assert by_agent[0]["agent"] == "alice"

    # Filter by verdict
    by_verdict = store.get_all_decisions(verdict="blocked")
    assert len(by_verdict) == 1
    assert by_verdict[0]["verdict"] == "blocked"


# ---- get_status ----


def test_get_status(store: SurrealGovernanceStore):
    d = Decision(
        id="st-1", task_id="ts", agent="w",
        category=DecisionCategory.PATTERN_CHOICE, summary="Status test",
    )
    store.store_decision(d)
    r = ReviewVerdict(id="sr-1", decision_id="st-1", verdict=Verdict.APPROVED)
    store.store_review(r)

    status = store.get_status()
    assert status["total_decisions"] == 1
    assert status["approved"] == 1
    assert status["blocked"] == 0
    assert len(status["recent_activity"]) == 1


# ---- has_plan_review / has_unresolved_blocks ----


def test_has_plan_review(store: SurrealGovernanceStore):
    assert store.has_plan_review("nonexistent") is False
    r = ReviewVerdict(id="pr-1", plan_id="plan-1", verdict=Verdict.APPROVED)
    store.store_review(r)
    assert store.has_plan_review("plan-1") is True


def test_has_unresolved_blocks(store: SurrealGovernanceStore):
    d = Decision(
        id="ub-1", task_id="t-ub", agent="w",
        category=DecisionCategory.SCOPE_CHANGE, summary="Block test",
    )
    store.store_decision(d)
    assert store.has_unresolved_blocks("t-ub") is False

    r = ReviewVerdict(id="ubr-1", decision_id="ub-1", verdict=Verdict.BLOCKED)
    store.store_review(r)
    assert store.has_unresolved_blocks("t-ub") is True


# ---- Governed Task lifecycle ----


def test_governed_task_lifecycle(store: SurrealGovernanceStore):
    task = GovernedTaskRecord(
        id="gt-1",
        implementation_task_id="impl-1",
        subject="Build widget",
        description="A widget that does things.",
        context="Context here",
        session_id="sess-abc",
    )
    store.store_governed_task(task)

    fetched = store.get_governed_task("impl-1")
    assert fetched is not None
    assert fetched.subject == "Build widget"
    assert fetched.session_id == "sess-abc"
    assert fetched.current_status == "pending_review"

    # Update status
    now = datetime.now(timezone.utc).isoformat()
    store.update_governed_task_status("impl-1", "approved", now)
    updated = store.get_governed_task("impl-1")
    assert updated is not None
    assert updated.current_status == "approved"
    assert updated.released_at == now


def test_get_tasks_for_session(store: SurrealGovernanceStore):
    for i in range(3):
        t = GovernedTaskRecord(
            id=f"gts-{i}",
            implementation_task_id=f"impl-s-{i}",
            subject=f"Task {i}",
            session_id="sess-xyz",
        )
        store.store_governed_task(t)
    # Add one from different session
    t_other = GovernedTaskRecord(
        id="gts-other",
        implementation_task_id="impl-s-other",
        subject="Other session task",
        session_id="sess-other",
    )
    store.store_governed_task(t_other)

    tasks = store.get_tasks_for_session("sess-xyz")
    assert len(tasks) == 3


# ---- Task Review ----


def test_task_review_crud(store: SurrealGovernanceStore):
    task = GovernedTaskRecord(
        id="gt-tr", implementation_task_id="impl-tr", subject="Review me",
    )
    store.store_governed_task(task)

    tr = TaskReviewRecord(
        id="tr-1",
        review_task_id="rtask-1",
        implementation_task_id="impl-tr",
        review_type=ReviewType.GOVERNANCE,
        status=TaskReviewStatus.PENDING,
        context="Check this task.",
    )
    store.store_task_review(tr)

    # Retrieve by impl ID
    reviews = store.get_task_reviews("impl-tr")
    assert len(reviews) == 1
    assert reviews[0].status == TaskReviewStatus.PENDING

    # Retrieve by review task ID
    by_rtid = store.get_task_review_by_review_task_id("rtask-1")
    assert by_rtid is not None
    assert by_rtid.id == "tr-1"

    # Pending reviews
    pending = store.get_pending_task_reviews()
    assert len(pending) == 1

    # Update
    tr.status = TaskReviewStatus.APPROVED
    tr.verdict = Verdict.APPROVED
    tr.guidance = "Ship it."
    tr.completed_at = datetime.now(timezone.utc).isoformat()
    store.update_task_review(tr)

    updated = store.get_task_reviews("impl-tr")
    assert updated[0].status == TaskReviewStatus.APPROVED
    assert updated[0].guidance == "Ship it."

    # No longer pending
    assert len(store.get_pending_task_reviews()) == 0


# ---- get_all_governed_tasks ----


def test_get_all_governed_tasks(store: SurrealGovernanceStore):
    for i in range(3):
        t = GovernedTaskRecord(
            id=f"gat-{i}",
            implementation_task_id=f"impl-gat-{i}",
            subject=f"Governed {i}",
        )
        store.store_governed_task(t)

    all_tasks = store.get_all_governed_tasks()
    assert len(all_tasks) == 3

    # With limit
    limited = store.get_all_governed_tasks(limit=2)
    assert len(limited) == 2


def test_task_governance_stats(store: SurrealGovernanceStore):
    t = GovernedTaskRecord(
        id="tgs-1", implementation_task_id="impl-tgs",
        subject="Stats test", current_status="approved",
    )
    store.store_governed_task(t)
    stats = store.get_task_governance_stats()
    assert stats["total_governed_tasks"] == 1
    assert stats["approved"] == 1


# ---- Holistic Review ----


def test_holistic_review(store: SurrealGovernanceStore):
    hr = HolisticReviewRecord(
        id="hr-1",
        session_id="sess-hol",
        task_ids=["t1", "t2"],
        task_subjects=["Build X", "Build Y"],
        collective_intent="Build a system",
        verdict=Verdict.APPROVED,
        findings=[],
        guidance="All good.",
        strengths_summary="Well scoped.",
        standards_verified=["di-standard"],
    )
    store.store_holistic_review(hr)

    fetched = store.get_holistic_review_for_session("sess-hol")
    assert fetched is not None
    assert fetched.verdict == Verdict.APPROVED
    assert fetched.task_ids == ["t1", "t2"]
    assert fetched.strengths_summary == "Well scoped."

    # Non-existent session
    assert store.get_holistic_review_for_session("nonexistent") is None


# ---- Token Usage ----


def test_usage_store_and_summary(store: SurrealGovernanceStore):
    now = datetime.now(timezone.utc).isoformat()
    for i in range(3):
        u = UsageRecord(
            id=f"u-{i}",
            timestamp=now,
            session_id="sess-u",
            agent="governance-reviewer",
            operation="review_decision",
            model="sonnet",
            input_tokens=1000,
            output_tokens=200,
            cache_read_tokens=50,
            cache_creation_tokens=10,
            duration_ms=500,
            related_id=f"dec-{i}",
            prompt_bytes=2000,
        )
        store.store_usage(u)

    summary = store.get_usage_summary(period="day")
    assert summary["call_count"] == 3
    assert summary["total_input_tokens"] == 3000
    assert summary["total_output_tokens"] == 600
    assert summary["total_tokens"] == 3600

    # By session
    sess_summary = store.get_usage_summary(period="session", session_id="sess-u")
    assert sess_summary["call_count"] == 3


def test_usage_by_agent(store: SurrealGovernanceStore):
    now = datetime.now(timezone.utc).isoformat()
    for agent in ["alice", "bob", "alice"]:
        u = UsageRecord(
            id=f"ua-{agent}-{now}",
            timestamp=now,
            agent=agent,
            operation="review_decision",
            input_tokens=100,
            output_tokens=50,
        )
        store.store_usage(u)

    by_agent = store.get_usage_by_agent(period="day")
    agents = {r["agent"] for r in by_agent}
    assert "alice" in agents
    assert "bob" in agents


def test_usage_by_operation(store: SurrealGovernanceStore):
    now = datetime.now(timezone.utc).isoformat()
    for op in ["review_decision", "review_plan", "review_decision"]:
        u = UsageRecord(
            id=f"uo-{op}-{now}",
            timestamp=now,
            agent="reviewer",
            operation=op,
            input_tokens=500,
            output_tokens=100,
            prompt_bytes=1500,
        )
        store.store_usage(u)

    by_op = store.get_usage_by_operation(period="day")
    ops = {r["operation"] for r in by_op}
    assert "review_decision" in ops
    assert "review_plan" in ops


# ---- close is safe to call multiple times ----


def test_close_idempotent(store: SurrealGovernanceStore):
    store.close()
    store.close()  # should not raise
