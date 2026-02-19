"""S05 -- Architecture deviation and scope change governance decisions.

Verifies that governance decisions with DEVIATION and SCOPE_CHANGE categories
are stored correctly in the GovernanceStore and can be retrieved.

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
)
from collab_governance.store import GovernanceStore

from .base import BaseScenario, ScenarioResult


class S05ArchitectureDeviation(BaseScenario):
    """Assert that architecture deviations and scope changes are stored correctly."""

    name = "s05-architecture-deviation"
    isolation_mode = "library"

    def run(self, **kwargs: Any) -> ScenarioResult:
        arch_pattern = self.project.architecture_patterns[0]
        task_id = "task-s05-arch-dev"

        # -- Setup: create a fresh governance store --------------------------
        db_path = self.workspace / "s05-governance.db"
        store = GovernanceStore(db_path=db_path)

        # -- Store a DEVIATION decision referencing the architecture pattern --
        deviation = Decision(
            task_id=task_id,
            agent="worker-1",
            category=DecisionCategory.DEVIATION,
            summary=f"Deviating from {arch_pattern['name']}: using direct calls instead",
            detail=(
                f"The architecture pattern '{arch_pattern['description']}' "
                "recommends async event channels, but for this specific case "
                "a synchronous direct call is more appropriate due to latency "
                "requirements."
            ),
            components_affected=[self.project.components[0]],
            confidence=Confidence.MEDIUM,
        )
        stored_deviation = store.store_decision(deviation)

        self.assert_true(
            "deviation decision stored successfully",
            stored_deviation.id is not None and len(stored_deviation.id) > 0,
            expected="non-empty ID",
            actual=stored_deviation.id,
        )

        self.assert_equal(
            "deviation category is DEVIATION",
            stored_deviation.category,
            DecisionCategory.DEVIATION,
        )

        self.assert_equal(
            "deviation sequence is 1",
            stored_deviation.sequence,
            1,
        )

        # -- Retrieve and verify the deviation decision ----------------------
        decisions = store.get_decisions_for_task(task_id)
        self.assert_equal(
            "one decision stored for task",
            len(decisions),
            1,
        )

        self.assert_equal(
            "retrieved decision category is DEVIATION",
            decisions[0].category,
            DecisionCategory.DEVIATION,
        )

        self.assert_contains(
            "deviation summary references pattern name",
            decisions[0].summary,
            arch_pattern["name"],
        )

        # -- Store a SCOPE_CHANGE decision -----------------------------------
        scope_change = Decision(
            task_id=task_id,
            agent="worker-1",
            category=DecisionCategory.SCOPE_CHANGE,
            summary="Adding monitoring endpoints outside original scope",
            detail=(
                "The task brief only covered the core service implementation, "
                "but adding health and metrics endpoints is necessary for "
                "production readiness."
            ),
            components_affected=[self.project.components[0]],
            confidence=Confidence.HIGH,
        )
        stored_scope = store.store_decision(scope_change)

        self.assert_true(
            "scope change decision stored successfully",
            stored_scope.id is not None and len(stored_scope.id) > 0,
            expected="non-empty ID",
            actual=stored_scope.id,
        )

        self.assert_equal(
            "scope change category is SCOPE_CHANGE",
            stored_scope.category,
            DecisionCategory.SCOPE_CHANGE,
        )

        self.assert_equal(
            "scope change sequence is 2",
            stored_scope.sequence,
            2,
        )

        # -- Verify both decisions are present for the task ------------------
        all_decisions = store.get_decisions_for_task(task_id)
        self.assert_equal(
            "two decisions stored for task",
            len(all_decisions),
            2,
        )

        categories = [d.category for d in all_decisions]
        self.assert_contains(
            "DEVIATION category present in decisions",
            categories,
            DecisionCategory.DEVIATION,
        )

        self.assert_contains(
            "SCOPE_CHANGE category present in decisions",
            categories,
            DecisionCategory.SCOPE_CHANGE,
        )

        store.close()
        return self._build_result(scenario_type="positive")
