"""S09 -- Scope change and deviation detection.

Verifies that SCOPE_CHANGE and DEVIATION decisions are stored with the correct
category and can be flagged as needing human review via the verdict system.

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


class S09ScopeChangeDetection(BaseScenario):
    """Assert that scope changes and deviations are correctly categorised and flaggable."""

    name = "s09-scope-change-detection"
    isolation_mode = "library"

    def run(self, **kwargs: Any) -> ScenarioResult:
        db_path = self.workspace / "s09-governance.db"
        store = GovernanceStore(db_path=db_path)
        task_id = "task-s09-scope"

        component = self.project.components[0]

        # -- Store a SCOPE_CHANGE decision ----------------------------------
        scope_decision = Decision(
            task_id=task_id,
            agent="worker-1",
            category=DecisionCategory.SCOPE_CHANGE,
            summary=f"Adding caching layer to {component} beyond original scope",
            detail=(
                "The task brief specified only the core CRUD operations, but "
                "performance profiling shows a caching layer is essential. "
                "This extends the scope of the implementation."
            ),
            components_affected=[component],
            confidence=Confidence.HIGH,
        )
        stored_scope = store.store_decision(scope_decision)

        self.assert_equal(
            "scope change stored with correct category",
            stored_scope.category,
            DecisionCategory.SCOPE_CHANGE,
        )

        self.assert_equal(
            "scope change category value is 'scope_change'",
            stored_scope.category.value,
            "scope_change",
        )

        # -- Verify it can be retrieved by task -----------------------------
        decisions = store.get_decisions_for_task(task_id)
        self.assert_equal(
            "one decision in task after scope change",
            len(decisions),
            1,
        )

        self.assert_equal(
            "retrieved decision is SCOPE_CHANGE",
            decisions[0].category,
            DecisionCategory.SCOPE_CHANGE,
        )

        # -- Flag SCOPE_CHANGE as needs_human_review via review verdict -----
        scope_review = ReviewVerdict(
            decision_id=stored_scope.id,
            verdict=Verdict.NEEDS_HUMAN_REVIEW,
            guidance="Scope changes require human assessment of resource impact",
        )
        stored_review = store.store_review(scope_review)

        self.assert_equal(
            "scope change review verdict is needs_human_review",
            stored_review.verdict,
            Verdict.NEEDS_HUMAN_REVIEW,
        )

        # -- Store a DEVIATION decision -------------------------------------
        deviation_decision = Decision(
            task_id=task_id,
            agent="worker-2",
            category=DecisionCategory.DEVIATION,
            summary=f"Using REST instead of gRPC for {component} internal API",
            detail=(
                "The architecture pattern recommends gRPC for inter-service "
                "communication, but the team lacks gRPC expertise and the "
                "latency requirements are met by REST."
            ),
            components_affected=[component],
            confidence=Confidence.MEDIUM,
        )
        stored_deviation = store.store_decision(deviation_decision)

        self.assert_equal(
            "deviation stored with correct category",
            stored_deviation.category,
            DecisionCategory.DEVIATION,
        )

        self.assert_equal(
            "deviation category value is 'deviation'",
            stored_deviation.category.value,
            "deviation",
        )

        # -- Flag DEVIATION as needs_human_review ---------------------------
        deviation_review = ReviewVerdict(
            decision_id=stored_deviation.id,
            verdict=Verdict.NEEDS_HUMAN_REVIEW,
            guidance="Architecture deviations require human sign-off",
        )
        store.store_review(deviation_review)

        # -- Verify governance status reflects both human review flags -------
        status = store.get_status()

        self.assert_equal(
            "total decisions is 2",
            status["total_decisions"],
            2,
        )

        self.assert_equal(
            "needs_human_review count is 2",
            status["needs_human_review"],
            2,
        )

        self.assert_equal(
            "approved count is 0",
            status["approved"],
            0,
        )

        self.assert_equal(
            "blocked count is 0",
            status["blocked"],
            0,
        )

        # -- Verify get_all_decisions with verdict filter -------------------
        human_review_decisions = store.get_all_decisions(verdict="needs_human_review")
        self.assert_equal(
            "two decisions with needs_human_review verdict",
            len(human_review_decisions),
            2,
        )

        # Verify categories in filtered results
        categories = {d["category"] for d in human_review_decisions}
        self.assert_contains(
            "filtered results include scope_change",
            categories,
            "scope_change",
        )

        self.assert_contains(
            "filtered results include deviation",
            categories,
            "deviation",
        )

        store.close()
        return self._build_result(scenario_type="positive")
