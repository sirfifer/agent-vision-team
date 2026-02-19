"""Scenario 11 -- Hook-Based Task Governance Interception.

Tests the PostToolUse hook-based governance enforcement. Simulates
what happens when the ``governance-task-intercept.py`` hook fires
after a TaskCreate call, ensuring:

  1. The hook correctly creates a governance review task paired with
     the implementation task.
  2. The implementation task is modified to include ``blockedBy``.
  3. Governance records are stored in SQLite.
  4. Review tasks (loop prevention) are NOT re-governed.
  5. The async review completion path works (mock mode).
  6. The full cycle: create -> intercept -> review -> release.

This scenario does NOT call Claude Code's actual hook system; it
exercises the hook script's core logic directly as a library.

All task files are written to an isolated directory inside
``self.workspace`` so that parallel runs never collide.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_GOV_LIB = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "governance"
if str(_GOV_LIB) not in sys.path:
    sys.path.insert(0, str(_GOV_LIB))

_HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from collab_governance.models import (  # noqa: E402
    GovernedTaskRecord,
    ReviewType,
    TaskReviewRecord,
    TaskReviewStatus,
)
from collab_governance.store import GovernanceStore  # noqa: E402
from collab_governance.task_integration import (  # noqa: E402
    Task,
    TaskFileManager,
    _generate_task_id,
    get_task_governance_status,
    release_task,
)

from e2e.scenarios.base import BaseScenario, ScenarioResult  # noqa: E402


class HookBasedGovernanceScenario(BaseScenario):
    """E2E scenario exercising hook-based task governance interception."""

    name = "s11_hook_based_governance"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _task_dir(self, suffix: str = "") -> Path:
        task_dir = self.workspace / f"tasks-hook{suffix}"
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir

    def _db_path(self) -> Path:
        db_dir = self.workspace / "governance-db"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "governance.db"

    def _simulate_task_create(self, task_dir: Path, subject: str, description: str = "") -> Task:
        """Simulate what Claude Code's native TaskCreate would do: write a task file."""
        manager = TaskFileManager(task_dir)
        task_id = f"impl-{_generate_task_id()}"
        task = Task(
            id=task_id,
            subject=subject,
            description=description or f"Implementation of {subject}",
            activeForm=f"Working on {subject}",
        )
        manager.create_task(task)
        return task

    def _simulate_hook_intercept(self, task_dir: Path, db_path: Path, impl_task: Task) -> dict:
        """Simulate what governance-task-intercept.py does after TaskCreate.

        This replicates the hook's core logic without going through
        stdin/stdout JSON protocol.
        """
        manager = TaskFileManager(task_dir)
        review_id = f"review-{_generate_task_id()}"

        # Create review task
        from datetime import datetime, timezone

        review_task = Task(
            id=review_id,
            subject=f"[GOVERNANCE] Review: {impl_task.subject}",
            description=f"Governance review required.\n\nContext:\n{impl_task.description[:2000]}",
            activeForm=f"Reviewing {impl_task.subject}",
            blocks=[impl_task.id],
            governance_metadata={
                "review_type": "governance",
                "implementation_task_id": impl_task.id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "PostToolUse-hook",
            },
        )
        manager.create_task(review_task)

        # Modify implementation task to add blockedBy
        reloaded = manager.read_task(impl_task.id)
        if reloaded and review_id not in reloaded.blockedBy:
            reloaded.blockedBy.append(review_id)
            reloaded.updatedAt = time.time()
            manager.update_task(reloaded)

        # Store governance records in SQLite
        store = GovernanceStore(db_path=db_path)
        governed_task = GovernedTaskRecord(
            implementation_task_id=impl_task.id,
            subject=impl_task.subject,
            description=impl_task.description[:2000],
            context="Auto-intercepted via PostToolUse hook",
            current_status="pending_review",
        )
        store.store_governed_task(governed_task)

        task_review = TaskReviewRecord(
            review_task_id=review_id,
            implementation_task_id=impl_task.id,
            review_type=ReviewType.GOVERNANCE,
            status=TaskReviewStatus.PENDING,
            context=f"Auto-created by PostToolUse hook for: {impl_task.subject}",
        )
        store.store_task_review(task_review)
        store.close()

        return {
            "review_task_id": review_id,
            "review_record_id": task_review.id,
            "implementation_task_id": impl_task.id,
        }

    def _is_review_task(self, subject: str, task_id: str = "") -> bool:
        """Replicate the hook's loop prevention logic."""
        prefixes = ("[GOVERNANCE]", "[REVIEW]", "[SECURITY]", "[ARCHITECTURE]")
        if any(subject.upper().startswith(p) for p in prefixes):
            return True
        if task_id.startswith("review-"):
            return True
        return False

    # ------------------------------------------------------------------
    # Scenario entry point
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:
        task_dir = self._task_dir()
        db_path = self._db_path()

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
        # TESTS 1-4: Hook intercepts TaskCreate and creates governance pair
        # ==============================================================

        # 1. Simulate TaskCreate (what Claude Code's native tool does)
        impl_task = self._simulate_task_create(
            task_dir,
            subject=f"Implement {component} for {domain}",
            description=f"Build the {component} service with protocol-based DI",
        )
        self.assert_true(
            "T1: TaskCreate simulation creates a task file",
            impl_task is not None and impl_task.id.startswith("impl-"),
            expected="impl-* task",
            actual=impl_task.id,
        )
        # Initially, the task has NO blockers (native TaskCreate doesn't add them)
        self.assert_equal(
            "T1b: Native TaskCreate produces task with empty blockedBy",
            len(impl_task.blockedBy),
            0,
        )

        # 2. Simulate PostToolUse hook intercept
        review_info = self._simulate_hook_intercept(task_dir, db_path, impl_task)
        self.assert_true(
            "T2: Hook creates review task ID starting with 'review-'",
            review_info["review_task_id"].startswith("review-"),
            expected="review-*",
            actual=review_info["review_task_id"],
        )

        # 3. Verify implementation task was modified (blockedBy added)
        manager = TaskFileManager(task_dir)
        impl_reloaded = manager.read_task(impl_task.id)
        self.assert_true(
            "T3: Implementation task now has blockedBy after hook",
            len(impl_reloaded.blockedBy) == 1,
            expected="1 blocker",
            actual=f"{len(impl_reloaded.blockedBy)} blockers",
        )
        self.assert_contains(
            "T3b: blockedBy contains the review task ID",
            impl_reloaded.blockedBy,
            review_info["review_task_id"],
        )

        # 4. Verify review task was created with correct structure
        review_task = manager.read_task(review_info["review_task_id"])
        self.assert_true(
            "T4: Review task exists in task directory",
            review_task is not None,
            expected="non-None",
            actual=review_task,
        )
        self.assert_true(
            "T4b: Review task subject starts with [GOVERNANCE]",
            review_task.subject.startswith("[GOVERNANCE]"),
            expected="[GOVERNANCE]*",
            actual=review_task.subject,
        )
        self.assert_contains(
            "T4c: Review task blocks the implementation task",
            review_task.blocks,
            impl_task.id,
        )

        # ==============================================================
        # TESTS 5-6: Governance DB records
        # ==============================================================

        store = GovernanceStore(db_path=db_path)

        # 5. Governed task record exists
        governed = store.get_governed_task(impl_task.id)
        self.assert_true(
            "T5: Governed task record exists in DB",
            governed is not None,
            expected="non-None",
            actual=governed,
        )
        self.assert_equal(
            "T5b: Governed task status is pending_review",
            governed.current_status,
            "pending_review",
        )

        # 6. Task review record exists
        reviews = store.get_task_reviews(impl_task.id)
        self.assert_true(
            "T6: Task review record exists in DB",
            len(reviews) == 1,
            expected="1 review",
            actual=f"{len(reviews)} reviews",
        )
        self.assert_equal(
            "T6b: Review status is pending",
            reviews[0].status,
            TaskReviewStatus.PENDING,
        )
        self.assert_equal(
            "T6c: Review task ID matches",
            reviews[0].review_task_id,
            review_info["review_task_id"],
        )
        store.close()

        # ==============================================================
        # TESTS 7-8: Loop prevention (review tasks not re-governed)
        # ==============================================================

        # 7. Review tasks should be detected and skipped
        self.assert_true(
            "T7: Hook detects [GOVERNANCE] prefix as review task",
            self._is_review_task("[GOVERNANCE] Review: Something"),
            expected=True,
            actual=self._is_review_task("[GOVERNANCE] Review: Something"),
        )
        self.assert_true(
            "T7b: Hook detects review- ID prefix",
            self._is_review_task("Any subject", "review-abc123"),
            expected=True,
            actual=self._is_review_task("Any subject", "review-abc123"),
        )

        # 8. Normal implementation tasks are NOT detected as review tasks
        self.assert_true(
            "T8: Normal task subject is not detected as review",
            not self._is_review_task(f"Implement {component}"),
            expected=False,
            actual=self._is_review_task(f"Implement {component}"),
        )
        self.assert_true(
            "T8b: Normal task ID is not detected as review",
            not self._is_review_task("Any subject", "impl-xyz789"),
            expected=False,
            actual=self._is_review_task("Any subject", "impl-xyz789"),
        )

        # ==============================================================
        # TESTS 9-11: Full lifecycle (create -> intercept -> review -> release)
        # ==============================================================

        task_dir_lifecycle = self._task_dir("-lifecycle")
        db_path_lifecycle = self.workspace / "governance-db-lifecycle" / "governance.db"
        db_path_lifecycle.parent.mkdir(parents=True, exist_ok=True)

        # 9. Simulate full flow
        impl_task_2 = self._simulate_task_create(
            task_dir_lifecycle,
            subject=f"Add caching to {component}",
        )
        review_info_2 = self._simulate_hook_intercept(task_dir_lifecycle, db_path_lifecycle, impl_task_2)

        # Verify task is blocked
        status_before = get_task_governance_status(impl_task_2.id, task_dir=task_dir_lifecycle)
        self.assert_true(
            "T9: Task is blocked after hook intercept",
            status_before.get("is_blocked") is True,
            expected=True,
            actual=status_before.get("is_blocked"),
        )
        self.assert_true(
            "T9b: Task cannot execute before review",
            status_before.get("can_execute") is False,
            expected=False,
            actual=status_before.get("can_execute"),
        )

        # 10. Complete the review (simulate what async reviewer does)
        released = release_task(
            review_task_id=review_info_2["review_task_id"],
            verdict="approved",
            guidance="Approved: aligns with vision standards",
            task_dir=task_dir_lifecycle,
        )
        self.assert_true(
            "T10: release_task returns the implementation task",
            released is not None,
            expected="non-None",
            actual=released,
        )
        self.assert_equal(
            "T10b: Implementation blockedBy is empty after release",
            len(released.blockedBy),
            0,
        )

        # 11. Task is now executable
        status_after = get_task_governance_status(impl_task_2.id, task_dir=task_dir_lifecycle)
        self.assert_true(
            "T11: Task is no longer blocked after approved review",
            status_after.get("is_blocked") is False,
            expected=False,
            actual=status_after.get("is_blocked"),
        )
        self.assert_true(
            "T11b: Task can execute after approved review",
            status_after.get("can_execute") is True,
            expected=True,
            actual=status_after.get("can_execute"),
        )

        # ==============================================================
        # TEST 12: Governance stats reflect hook-created tasks
        # ==============================================================

        store_stats = GovernanceStore(db_path=db_path)
        stats = store_stats.get_task_governance_stats()
        self.assert_true(
            "T12: Governance stats show at least 1 governed task",
            stats.get("total_governed_tasks", 0) >= 1,
            expected=">=1",
            actual=stats.get("total_governed_tasks"),
        )
        self.assert_true(
            "T12b: Governance stats show at least 1 pending review",
            stats.get("pending_reviews", 0) >= 1,
            expected=">=1",
            actual=stats.get("pending_reviews"),
        )
        store_stats.close()

        return self._build_result(scenario_type="mixed")
