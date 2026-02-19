"""Scenario 03 — Governed Task Lifecycle.

Tests the governed task system end-to-end using ``task_integration``
directly.  Validates the full lifecycle:

  1. Create a governed task pair (review + implementation).
  2. Implementation is born blocked by the review.
  3. Releasing the review (approved) unblocks the implementation.
  4. Multi-blocker flows: additional reviews can stack, and only
     full release of ALL blockers makes the task executable.
  5. A blocked verdict keeps the task blocked.

All task files are written to an isolated directory inside
``self.workspace`` so that parallel runs never collide and the real
``~/.claude/tasks/`` directory is never touched.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — import the Governance library directly from the mono-repo
# ---------------------------------------------------------------------------
_GOV_LIB = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "governance"
if str(_GOV_LIB) not in sys.path:
    sys.path.insert(0, str(_GOV_LIB))

from collab_governance.task_integration import (  # noqa: E402
    TaskFileManager,
    add_additional_review,
    create_governed_task_pair,
    get_task_governance_status,
    release_task,
)

from e2e.scenarios.base import BaseScenario, ScenarioResult  # noqa: E402


class GovernedTaskLifecycleScenario(BaseScenario):
    """E2E scenario exercising the governed task lifecycle."""

    name = "s03_governed_task_lifecycle"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _task_dir(self) -> Path:
        """Return an isolated task directory inside the workspace."""
        task_dir = self.workspace / "tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir

    # ------------------------------------------------------------------
    # Scenario entry point
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:
        task_dir = self._task_dir()

        # Derive domain-specific names from the project fixture
        component = (
            self.project.components[0]
            if hasattr(self.project, "components") and self.project.components
            else "AuthService"
        )
        domain = (
            self.project.domain_name
            if hasattr(self.project, "domain_name") and self.project.domain_name
            else "TestDomain"
        )

        # ==============================================================
        # TESTS 1-6: Basic governed task pair lifecycle
        # ==============================================================

        # 1. Create governed task pair — review + implementation created
        review_task, impl_task = create_governed_task_pair(
            subject=f"Implement {component} for {domain}",
            description=f"Build the {component} service with protocol-based DI",
            context=f"Part of the {domain} initiative, must follow vision standards",
            review_type="governance",
            task_dir=task_dir,
        )

        self.assert_true(
            "T1: Create governed task pair returns two tasks",
            review_task is not None and impl_task is not None,
            expected="two non-None tasks",
            actual=f"review={review_task is not None}, impl={impl_task is not None}",
        )
        self.assert_true(
            "T1b: Review task ID starts with 'review-'",
            review_task.id.startswith("review-"),
            expected="review-*",
            actual=review_task.id,
        )
        self.assert_true(
            "T1c: Implementation task ID starts with 'impl-'",
            impl_task.id.startswith("impl-"),
            expected="impl-*",
            actual=impl_task.id,
        )

        # 2. Implementation task is blocked (blockedBy contains review id)
        self.assert_contains(
            "T2: Implementation blockedBy contains review task ID",
            impl_task.blockedBy,
            review_task.id,
        )

        # 3. Review task blocks the implementation (blocks contains impl id)
        self.assert_contains(
            "T3: Review task blocks contains implementation task ID",
            review_task.blocks,
            impl_task.id,
        )

        # 4. Task status shows blocked
        status = get_task_governance_status(impl_task.id, task_dir=task_dir)
        self.assert_true(
            "T4: Task governance status shows is_blocked=True",
            status.get("is_blocked") is True,
            expected=True,
            actual=status.get("is_blocked"),
        )
        self.assert_true(
            "T4b: Task governance status shows can_execute=False",
            status.get("can_execute") is False,
            expected=False,
            actual=status.get("can_execute"),
        )
        self.assert_equal(
            "T4c: Task status has 1 blocker",
            len(status.get("blockers", [])),
            1,
        )

        # 5. Release task (approved) — implementation unblocks
        released_impl = release_task(
            review_task_id=review_task.id,
            verdict="approved",
            guidance="Approved: design aligns with vision standards",
            task_dir=task_dir,
        )
        self.assert_true(
            "T5: release_task returns the implementation task",
            released_impl is not None,
            expected="non-None task",
            actual=released_impl,
        )
        self.assert_true(
            "T5b: Implementation blockedBy is now empty",
            len(released_impl.blockedBy) == 0,
            expected="empty list",
            actual=released_impl.blockedBy,
        )

        # 6. Task status shows can_execute after release
        status_after = get_task_governance_status(impl_task.id, task_dir=task_dir)
        self.assert_true(
            "T6: Task governance status shows is_blocked=False after release",
            status_after.get("is_blocked") is False,
            expected=False,
            actual=status_after.get("is_blocked"),
        )
        self.assert_true(
            "T6b: Task governance status shows can_execute=True after release",
            status_after.get("can_execute") is True,
            expected=True,
            actual=status_after.get("can_execute"),
        )

        # ==============================================================
        # TESTS 7-9: Multi-blocker flow
        # ==============================================================

        # Create a fresh task pair for multi-blocker testing
        task_dir_multi = self.workspace / "tasks-multi"
        task_dir_multi.mkdir(parents=True, exist_ok=True)

        review_task_2, impl_task_2 = create_governed_task_pair(
            subject=f"Add security layer to {component}",
            description=f"Implement authorization checks in {component}",
            context=f"{domain} security requirements",
            review_type="governance",
            task_dir=task_dir_multi,
        )

        # 7. Add security review — task now has 2 blockers
        security_review = add_additional_review(
            task_id=impl_task_2.id,
            review_type="security",
            context=f"Security review for {component} authorization layer",
            task_dir=task_dir_multi,
        )
        self.assert_true(
            "T7: add_additional_review returns a review task",
            security_review is not None,
            expected="non-None task",
            actual=security_review,
        )
        self.assert_true(
            "T7b: Security review ID contains 'security'",
            "security" in security_review.id,
            expected="contains 'security'",
            actual=security_review.id,
        )

        # Re-read the implementation task to see updated blockers
        manager = TaskFileManager(task_dir_multi)
        impl_reloaded = manager.read_task(impl_task_2.id)
        self.assert_equal(
            "T7c: Implementation task now has 2 blockers",
            len(impl_reloaded.blockedBy),
            2,
        )
        self.assert_contains(
            "T7d: Blockers include original review",
            impl_reloaded.blockedBy,
            review_task_2.id,
        )
        self.assert_contains(
            "T7e: Blockers include security review",
            impl_reloaded.blockedBy,
            security_review.id,
        )

        # 8. Release first blocker — still blocked (1 remaining)
        release_task(
            review_task_id=review_task_2.id,
            verdict="approved",
            guidance="Governance review passed",
            task_dir=task_dir_multi,
        )

        status_partial = get_task_governance_status(impl_task_2.id, task_dir=task_dir_multi)
        self.assert_true(
            "T8: After releasing first blocker, task is still blocked",
            status_partial.get("is_blocked") is True,
            expected=True,
            actual=status_partial.get("is_blocked"),
        )
        self.assert_true(
            "T8b: After releasing first blocker, can_execute is False",
            status_partial.get("can_execute") is False,
            expected=False,
            actual=status_partial.get("can_execute"),
        )
        self.assert_equal(
            "T8c: Exactly 1 blocker remaining",
            len(status_partial.get("blockers", [])),
            1,
        )

        # 9. Release second blocker — fully released
        release_task(
            review_task_id=security_review.id,
            verdict="approved",
            guidance="Security review passed",
            task_dir=task_dir_multi,
        )

        status_fully_released = get_task_governance_status(impl_task_2.id, task_dir=task_dir_multi)
        self.assert_true(
            "T9: After releasing all blockers, is_blocked=False",
            status_fully_released.get("is_blocked") is False,
            expected=False,
            actual=status_fully_released.get("is_blocked"),
        )
        self.assert_true(
            "T9b: After releasing all blockers, can_execute=True",
            status_fully_released.get("can_execute") is True,
            expected=True,
            actual=status_fully_released.get("can_execute"),
        )

        # ==============================================================
        # TEST 10: Blocked verdict keeps task blocked
        # ==============================================================

        task_dir_blocked = self.workspace / "tasks-blocked"
        task_dir_blocked.mkdir(parents=True, exist_ok=True)

        review_task_3, impl_task_3 = create_governed_task_pair(
            subject=f"Refactor {component} internals",
            description=f"Internal refactoring of {component}",
            context=f"Refactoring within {domain}",
            review_type="governance",
            task_dir=task_dir_blocked,
        )

        # Release with "blocked" verdict
        blocked_result = release_task(
            review_task_id=review_task_3.id,
            verdict="blocked",
            guidance="Blocked: refactoring plan conflicts with vision standard on DI",
            task_dir=task_dir_blocked,
        )

        self.assert_true(
            "T10: Blocked verdict returns the implementation task",
            blocked_result is not None,
            expected="non-None task",
            actual=blocked_result,
        )

        # The implementation task should still have blockers (not removed on block)
        status_blocked = get_task_governance_status(impl_task_3.id, task_dir=task_dir_blocked)
        self.assert_true(
            "T10b: Blocked verdict keeps is_blocked=True",
            status_blocked.get("is_blocked") is True,
            expected=True,
            actual=status_blocked.get("is_blocked"),
        )
        self.assert_true(
            "T10c: Blocked verdict keeps can_execute=False",
            status_blocked.get("can_execute") is False,
            expected=False,
            actual=status_blocked.get("can_execute"),
        )

        # Verify the block guidance was appended to the impl task description
        manager_blocked = TaskFileManager(task_dir_blocked)
        impl_reloaded_blocked = manager_blocked.read_task(impl_task_3.id)
        self.assert_contains(
            "T10d: Block guidance appended to implementation description",
            impl_reloaded_blocked.description,
            "BLOCKED",
        )

        return self._build_result(scenario_type="mixed")
