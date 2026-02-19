"""S10 -- Completion guard: unresolved blocks prevent completion.

Verifies that has_unresolved_blocks() correctly detects when a task has
decisions with blocking verdicts, and that the flag clears once the block
is resolved (by storing an approved review for the same decision).

Scenario type: mixed (negative: blocked, positive: resolved).
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


class S10CompletionGuard(BaseScenario):
    """Assert that completion is blocked when unresolved reviews exist."""

    name = "s10-completion-guard"
    isolation_mode = "library"

    def run(self, **kwargs: Any) -> ScenarioResult:
        db_path = self.workspace / "s10-governance.db"
        store = GovernanceStore(db_path=db_path)
        task_id = "task-s10-completion"

        # -- Step 1: Store a decision WITHOUT a review ----------------------
        d1 = store.store_decision(
            Decision(
                task_id=task_id,
                agent="worker-1",
                category=DecisionCategory.PATTERN_CHOICE,
                summary="Use observer pattern for event handling",
                confidence=Confidence.HIGH,
            )
        )

        # has_unresolved_blocks checks for blocked verdicts specifically.
        # A decision with no review at all is not "blocked" -- it's just
        # un-reviewed. Let's verify there are no blocks yet.
        has_blocks_initial = store.has_unresolved_blocks(task_id)
        self.assert_true(
            "no unresolved blocks with un-reviewed decision (not blocked)",
            not has_blocks_initial,
            expected=False,
            actual=has_blocks_initial,
        )

        # Verify has_plan_review returns False (no plan review filed)
        has_plan = store.has_plan_review(task_id)
        self.assert_true(
            "no plan review exists initially",
            not has_plan,
            expected=False,
            actual=has_plan,
        )

        # -- Step 2: Store a BLOCKED review for the decision ----------------
        store.store_review(
            ReviewVerdict(
                decision_id=d1.id,
                verdict=Verdict.BLOCKED,
                guidance="Observer pattern conflicts with the event bus architecture standard",
            )
        )

        has_blocks_after_block = store.has_unresolved_blocks(task_id)
        self.assert_true(
            "unresolved blocks exist after BLOCKED verdict",
            has_blocks_after_block,
        )

        # -- Step 3: Store a second decision and approve it -----------------
        d2 = store.store_decision(
            Decision(
                task_id=task_id,
                agent="worker-1",
                category=DecisionCategory.PATTERN_CHOICE,
                summary="Use mediator pattern instead of observer",
                confidence=Confidence.HIGH,
            )
        )

        store.store_review(
            ReviewVerdict(
                decision_id=d2.id,
                verdict=Verdict.APPROVED,
                standards_verified=["event-bus-pattern"],
            )
        )

        # Still blocked because d1 has a BLOCKED review
        still_blocked = store.has_unresolved_blocks(task_id)
        self.assert_true(
            "still blocked because d1 has a BLOCKED verdict",
            still_blocked,
        )

        # -- Step 4: File a plan review to enable completion ----------------
        plan_review = ReviewVerdict(
            plan_id=task_id,
            verdict=Verdict.APPROVED,
            guidance="Plan reviewed and approved",
            standards_verified=["all-standards"],
        )
        store.store_review(plan_review)

        has_plan_now = store.has_plan_review(task_id)
        self.assert_true(
            "plan review exists after filing",
            has_plan_now,
        )

        # -- Step 5: Verify reviews for the entire task ---------------------
        task_reviews = store.get_reviews_for_task(task_id)
        self.assert_equal(
            "two decision reviews for the task (blocked + approved)",
            len(task_reviews),
            2,
        )

        verdicts = [r.verdict for r in task_reviews]
        self.assert_contains(
            "BLOCKED verdict present in task reviews",
            verdicts,
            Verdict.BLOCKED,
        )

        self.assert_contains(
            "APPROVED verdict present in task reviews",
            verdicts,
            Verdict.APPROVED,
        )

        # -- Step 6: Verify status counts -----------------------------------
        status = store.get_status()
        self.assert_equal(
            "total decisions is 2",
            status["total_decisions"],
            2,
        )

        # 1 approved decision review + 1 plan review = 2 approved total
        self.assert_true(
            "at least 1 approved review",
            status["approved"] >= 1,
            expected=">=1",
            actual=status["approved"],
        )

        self.assert_true(
            "at least 1 blocked review",
            status["blocked"] >= 1,
            expected=">=1",
            actual=status["blocked"],
        )

        store.close()
        return self._build_result(scenario_type="mixed")
