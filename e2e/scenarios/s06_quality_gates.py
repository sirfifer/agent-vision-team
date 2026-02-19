"""S06 -- Governance status counts and decision-review flow.

Tests the GovernanceStore's get_status() method by storing a mix of decisions
and reviews with different verdicts, then verifying the aggregate counts
returned are correct.

Scenario type: positive.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "knowledge-graph"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "governance"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "quality"))

from collab_governance.models import (
    Confidence,
    Decision,
    DecisionCategory,
    ReviewVerdict,
    Verdict,
)
from collab_governance.store import GovernanceStore

from .base import BaseScenario, ScenarioResult


class S06QualityGates(BaseScenario):
    """Assert that governance status returns correct counts for verdicts."""

    name = "s06-quality-gates"
    isolation_mode = "library"

    def run(self, **kwargs: Any) -> ScenarioResult:
        db_path = self.workspace / "s06-governance.db"
        store = GovernanceStore(db_path=db_path)

        # -- Initial state: everything is zero --------------------------------
        initial_status = store.get_status()

        self.assert_equal(
            "initial total_decisions is 0",
            initial_status["total_decisions"],
            0,
        )
        self.assert_equal(
            "initial approved is 0",
            initial_status["approved"],
            0,
        )
        self.assert_equal(
            "initial blocked is 0",
            initial_status["blocked"],
            0,
        )

        # -- Store 3 decisions with different review verdicts -----------------

        # Decision 1: approved
        d1 = store.store_decision(
            Decision(
                task_id="task-s06-1",
                agent="worker-1",
                category=DecisionCategory.PATTERN_CHOICE,
                summary="Use repository pattern for data access",
                confidence=Confidence.HIGH,
            )
        )
        store.store_review(
            ReviewVerdict(
                decision_id=d1.id,
                verdict=Verdict.APPROVED,
                standards_verified=["vision-std-1"],
            )
        )

        # Decision 2: blocked
        d2 = store.store_decision(
            Decision(
                task_id="task-s06-2",
                agent="worker-2",
                category=DecisionCategory.COMPONENT_DESIGN,
                summary="Use singleton for config manager",
                confidence=Confidence.MEDIUM,
            )
        )
        store.store_review(
            ReviewVerdict(
                decision_id=d2.id,
                verdict=Verdict.BLOCKED,
                guidance="Singletons violate vision standard: no singletons in production code",
            )
        )

        # Decision 3: needs_human_review
        d3 = store.store_decision(
            Decision(
                task_id="task-s06-3",
                agent="worker-3",
                category=DecisionCategory.DEVIATION,
                summary="Deviate from event-driven to synchronous RPC",
                confidence=Confidence.LOW,
            )
        )
        store.store_review(
            ReviewVerdict(
                decision_id=d3.id,
                verdict=Verdict.NEEDS_HUMAN_REVIEW,
                guidance="Deviation requires human assessment of trade-offs",
            )
        )

        # Decision 4: no review yet (pending)
        store.store_decision(
            Decision(
                task_id="task-s06-4",
                agent="worker-1",
                category=DecisionCategory.API_DESIGN,
                summary="Add pagination to list endpoints",
                confidence=Confidence.HIGH,
            )
        )

        # -- Verify status counts -------------------------------------------
        status = store.get_status()

        self.assert_equal(
            "total_decisions is 4",
            status["total_decisions"],
            4,
        )

        self.assert_equal(
            "approved count is 1",
            status["approved"],
            1,
        )

        self.assert_equal(
            "blocked count is 1",
            status["blocked"],
            1,
        )

        self.assert_equal(
            "needs_human_review count is 1",
            status["needs_human_review"],
            1,
        )

        self.assert_equal(
            "pending count is 1 (4 total - 1 approved - 1 blocked - 1 needs_human)",
            status["pending"],
            1,
        )

        # -- Verify recent activity contains our decisions -------------------
        self.assert_true(
            "recent_activity is populated",
            len(status["recent_activity"]) > 0,
            expected="non-empty list",
            actual=f"{len(status['recent_activity'])} items",
        )

        # -- Verify individual decision retrieval ----------------------------
        d1_review = store.get_review_for_decision(d1.id)
        self.assert_true(
            "review exists for decision 1",
            d1_review is not None,
        )

        if d1_review is not None:
            self.assert_equal(
                "decision 1 verdict is approved",
                d1_review.verdict,
                Verdict.APPROVED,
            )

        d2_review = store.get_review_for_decision(d2.id)
        self.assert_true(
            "review exists for decision 2",
            d2_review is not None,
        )

        if d2_review is not None:
            self.assert_equal(
                "decision 2 verdict is blocked",
                d2_review.verdict,
                Verdict.BLOCKED,
            )

        store.close()
        return self._build_result(scenario_type="positive")
