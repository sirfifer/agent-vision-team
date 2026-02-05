"""S08 -- Multi-blocker task lifecycle.

Creates a governed task pair with one initial blocker, adds two more review
blockers, then releases them one at a time and verifies the task remains
blocked until all blockers are released.

Scenario type: positive.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "knowledge-graph"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "governance"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "quality"))

from collab_governance.task_integration import (
    create_governed_task_pair,
    add_additional_review,
    release_task,
    get_task_governance_status,
)

from .base import BaseScenario, ScenarioResult


class S08MultiBlockerTask(BaseScenario):
    """Assert that tasks with multiple blockers stay blocked until all are released."""

    name = "s08-multi-blocker-task"
    isolation_mode = "library"

    def run(self, **kwargs: Any) -> ScenarioResult:
        task_dir = self.workspace / "s08-tasks"
        task_dir.mkdir(parents=True, exist_ok=True)

        component = self.project.components[0]

        # -- Step 1: Create governed task pair (1 blocker) -------------------
        review_task, impl_task = create_governed_task_pair(
            subject=f"Implement {component} service",
            description=f"Build the {component} with DI support",
            context=f"Must follow {self.project.domain_name} vision standards",
            review_type="governance",
            task_dir=task_dir,
        )

        self.assert_true(
            "review task created",
            review_task is not None and review_task.id is not None,
        )

        self.assert_true(
            "implementation task created",
            impl_task is not None and impl_task.id is not None,
        )

        # Verify initial state: 1 blocker
        status_1 = get_task_governance_status(impl_task.id, task_dir=task_dir)
        self.assert_true(
            "task is blocked after creation",
            status_1.get("is_blocked", False),
        )

        self.assert_equal(
            "task has 1 blocker initially",
            len(status_1.get("blockers", [])),
            1,
        )

        self.assert_true(
            "task cannot execute with blocker",
            not status_1.get("can_execute", True),
            expected=False,
            actual=status_1.get("can_execute"),
        )

        # -- Step 2: Add 2nd blocker (security review) ----------------------
        review_2 = add_additional_review(
            task_id=impl_task.id,
            review_type="security",
            context=f"Security review for {component}",
            task_dir=task_dir,
        )

        self.assert_true(
            "second review task created",
            review_2 is not None,
        )

        status_2 = get_task_governance_status(impl_task.id, task_dir=task_dir)
        self.assert_equal(
            "task has 2 blockers after security review added",
            len(status_2.get("blockers", [])),
            2,
        )

        # -- Step 3: Add 3rd blocker (architecture review) ------------------
        review_3 = add_additional_review(
            task_id=impl_task.id,
            review_type="architecture",
            context=f"Architecture review for {component}",
            task_dir=task_dir,
        )

        self.assert_true(
            "third review task created",
            review_3 is not None,
        )

        status_3 = get_task_governance_status(impl_task.id, task_dir=task_dir)
        self.assert_equal(
            "task has 3 blockers total",
            len(status_3.get("blockers", [])),
            3,
        )

        self.assert_true(
            "task is still blocked with 3 blockers",
            status_3.get("is_blocked", False),
        )

        # -- Step 4: Release 1st blocker -> still blocked (2 remaining) -----
        release_task(
            review_task_id=review_task.id,
            verdict="approved",
            guidance="Governance review passed",
            task_dir=task_dir,
        )

        status_after_1 = get_task_governance_status(impl_task.id, task_dir=task_dir)
        self.assert_true(
            "task still blocked after releasing 1st blocker",
            status_after_1.get("is_blocked", False),
        )

        self.assert_equal(
            "2 blockers remaining after 1st release",
            len(status_after_1.get("blockers", [])),
            2,
        )

        self.assert_true(
            "task cannot execute with 2 blockers",
            not status_after_1.get("can_execute", True),
            expected=False,
            actual=status_after_1.get("can_execute"),
        )

        # -- Step 5: Release 2nd blocker -> still blocked (1 remaining) -----
        release_task(
            review_task_id=review_2.id,
            verdict="approved",
            guidance="Security review passed",
            task_dir=task_dir,
        )

        status_after_2 = get_task_governance_status(impl_task.id, task_dir=task_dir)
        self.assert_true(
            "task still blocked after releasing 2nd blocker",
            status_after_2.get("is_blocked", False),
        )

        self.assert_equal(
            "1 blocker remaining after 2nd release",
            len(status_after_2.get("blockers", [])),
            1,
        )

        # -- Step 6: Release 3rd blocker -> fully released ------------------
        release_task(
            review_task_id=review_3.id,
            verdict="approved",
            guidance="Architecture review passed",
            task_dir=task_dir,
        )

        status_final = get_task_governance_status(impl_task.id, task_dir=task_dir)
        self.assert_true(
            "task is unblocked after all blockers released",
            not status_final.get("is_blocked", True),
            expected=False,
            actual=status_final.get("is_blocked"),
        )

        self.assert_equal(
            "0 blockers remaining after all releases",
            len(status_final.get("blockers", [])),
            0,
        )

        self.assert_true(
            "task can now execute",
            status_final.get("can_execute", False),
        )

        return self._build_result(scenario_type="positive")
