"""Scenario 13 -- Hook Pipeline at Scale.

Stress-tests the governance hook interception pipeline to verify that
100% of tasks are correctly intercepted, blocked, reviewed, and released.

Phases:

  1. **Rapid-fire creation**: Create 50 tasks in sequence, intercept each.
     Verify every single one has a review pair, blockedBy, and DB records.
  2. **Concurrent creation**: Create 20 tasks in parallel threads.
     Verify no race conditions; all 20 get correct governance pairs.
  3. **Full pipeline release**: Release ALL tasks via mock review.
     Verify 100% get unblocked and governance stats are accurate.
  4. **Performance metrics**: Report timing for interception throughput.

This scenario exercises the hook's core logic as a library (same as s11),
but at higher volume and with concurrency to surface race conditions or
data corruption that would only appear at scale.
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RAPID_FIRE_COUNT = 50
CONCURRENT_COUNT = 20
CONCURRENT_WORKERS = 8


class HookPipelineAtScaleScenario(BaseScenario):
    """E2E scenario: governance hook pipeline at scale."""

    name = "s13_hook_pipeline_at_scale"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _task_dir(self, suffix: str = "") -> Path:
        task_dir = self.workspace / f"tasks-scale{suffix}"
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir

    def _db_path(self, suffix: str = "") -> Path:
        db_dir = self.workspace / f"governance-db-scale{suffix}"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "governance.db"

    def _create_task(self, task_dir: Path, index: int) -> Task:
        """Create a single implementation task (simulates native TaskCreate)."""
        manager = TaskFileManager(task_dir)
        task_id = f"impl-{_generate_task_id()}"
        task = Task(
            id=task_id,
            subject=f"Scale task {index:03d}: implement feature #{index}",
            description=f"Implementation of feature #{index} for scale testing",
            activeForm=f"Working on feature #{index}",
        )
        manager.create_task(task)
        return task

    def _intercept_task(self, task_dir: Path, db_path: Path, impl_task: Task) -> dict:
        """Simulate hook interception: create review pair + DB records."""
        manager = TaskFileManager(task_dir)
        review_id = f"review-{_generate_task_id()}"

        # Create review task
        review_task = Task(
            id=review_id,
            subject=f"[GOVERNANCE] Review: {impl_task.subject}",
            description=(f"Governance review required.\n\nContext:\n{impl_task.description[:2000]}"),
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
            context="Auto-intercepted via PostToolUse hook (scale test)",
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
            "implementation_task_id": impl_task.id,
        }

    def _create_and_intercept(self, task_dir: Path, db_path: Path, index: int) -> dict:
        """Combined: create a task and immediately intercept it.

        Returns dict with review_task_id, implementation_task_id.
        Used for both sequential and concurrent tests.
        """
        impl_task = self._create_task(task_dir, index)
        return self._intercept_task(task_dir, db_path, impl_task)

    # ------------------------------------------------------------------
    # Scenario entry point
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:
        # ==============================================================
        # PHASE 1: Rapid-fire sequential creation (50 tasks)
        # ==============================================================

        task_dir = self._task_dir("-rapid")
        db_path = self._db_path("-rapid")

        t0 = time.monotonic()
        pairs: list[dict] = []
        for i in range(RAPID_FIRE_COUNT):
            pair = self._create_and_intercept(task_dir, db_path, i)
            pairs.append(pair)
        rapid_elapsed = time.monotonic() - t0

        # -- Verify 100% interception --

        manager = TaskFileManager(task_dir)
        all_tasks = manager.list_tasks()
        impl_tasks = [t for t in all_tasks if t.id.startswith("impl-")]
        review_tasks = [t for t in all_tasks if t.id.startswith("review-")]

        self.assert_equal(
            f"P1-T1: Created exactly {RAPID_FIRE_COUNT} implementation tasks",
            len(impl_tasks),
            RAPID_FIRE_COUNT,
        )
        self.assert_equal(
            f"P1-T2: Created exactly {RAPID_FIRE_COUNT} review tasks",
            len(review_tasks),
            RAPID_FIRE_COUNT,
        )

        # Every impl task has exactly 1 blocker
        blocked_count = 0
        for t in impl_tasks:
            if len(t.blockedBy) == 1 and t.blockedBy[0].startswith("review-"):
                blocked_count += 1
        self.assert_equal(
            "P1-T3: 100% of impl tasks have exactly 1 review blocker",
            blocked_count,
            RAPID_FIRE_COUNT,
        )

        # Every review task has exactly 1 blocks entry
        blocking_count = 0
        for t in review_tasks:
            if len(t.blocks) == 1 and t.blocks[0].startswith("impl-"):
                blocking_count += 1
        self.assert_equal(
            "P1-T4: 100% of review tasks block exactly 1 impl task",
            blocking_count,
            RAPID_FIRE_COUNT,
        )

        # Every impl task is blocked (cannot execute)
        unblocked_tasks = manager.get_pending_unblocked_tasks()
        # Only review tasks should be "unblocked" (they have no blockedBy)
        unblocked_impl = [t for t in unblocked_tasks if t.id.startswith("impl-")]
        self.assert_equal(
            "P1-T5: Zero impl tasks are available for execution (all blocked)",
            len(unblocked_impl),
            0,
        )

        # DB has correct record counts
        store = GovernanceStore(db_path=db_path)
        stats = store.get_task_governance_stats()
        self.assert_equal(
            f"P1-T6: DB has {RAPID_FIRE_COUNT} governed task records",
            stats.get("total_governed_tasks", 0),
            RAPID_FIRE_COUNT,
        )
        self.assert_equal(
            f"P1-T7: DB has {RAPID_FIRE_COUNT} pending review records",
            stats.get("pending_reviews", 0),
            RAPID_FIRE_COUNT,
        )
        store.close()

        # Performance: report average time per intercept
        avg_ms = (rapid_elapsed / RAPID_FIRE_COUNT) * 1000
        self.assert_true(
            f"P1-T8: Avg intercept time < 100ms (got {avg_ms:.1f}ms)",
            avg_ms < 100,
            expected="<100ms",
            actual=f"{avg_ms:.1f}ms",
        )

        # ==============================================================
        # PHASE 2: Concurrent creation (20 tasks in parallel threads)
        # ==============================================================

        task_dir_conc = self._task_dir("-concurrent")
        db_path_conc = self._db_path("-concurrent")

        t1 = time.monotonic()
        concurrent_pairs: list[dict] = []
        errors: list[str] = []

        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as pool:
            futures = {
                pool.submit(self._create_and_intercept, task_dir_conc, db_path_conc, i): i
                for i in range(CONCURRENT_COUNT)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    pair = future.result()
                    concurrent_pairs.append(pair)
                except Exception as e:
                    errors.append(f"Task {idx}: {e}")

        conc_elapsed = time.monotonic() - t1

        self.assert_equal(
            "P2-T1: Zero errors during concurrent creation",
            len(errors),
            0,
        )
        self.assert_equal(
            f"P2-T2: All {CONCURRENT_COUNT} concurrent pairs created",
            len(concurrent_pairs),
            CONCURRENT_COUNT,
        )

        # Verify all concurrent tasks are correctly governed
        manager_conc = TaskFileManager(task_dir_conc)
        conc_all = manager_conc.list_tasks()
        conc_impl = [t for t in conc_all if t.id.startswith("impl-")]
        conc_review = [t for t in conc_all if t.id.startswith("review-")]

        self.assert_equal(
            f"P2-T3: {CONCURRENT_COUNT} concurrent impl tasks exist",
            len(conc_impl),
            CONCURRENT_COUNT,
        )
        self.assert_equal(
            f"P2-T4: {CONCURRENT_COUNT} concurrent review tasks exist",
            len(conc_review),
            CONCURRENT_COUNT,
        )

        # Every concurrent impl task has exactly 1 blocker
        conc_blocked = sum(1 for t in conc_impl if len(t.blockedBy) == 1 and t.blockedBy[0].startswith("review-"))
        self.assert_equal(
            "P2-T5: 100% of concurrent impl tasks have 1 review blocker",
            conc_blocked,
            CONCURRENT_COUNT,
        )

        # No duplicate review IDs (each task gets a unique review)
        conc_review_ids = [t.id for t in conc_review]
        self.assert_equal(
            "P2-T6: All concurrent review IDs are unique (no duplicates)",
            len(conc_review_ids),
            len(set(conc_review_ids)),
        )

        # DB records match concurrent count
        store_conc = GovernanceStore(db_path=db_path_conc)
        stats_conc = store_conc.get_task_governance_stats()
        self.assert_equal(
            f"P2-T7: Concurrent DB has {CONCURRENT_COUNT} governed tasks",
            stats_conc.get("total_governed_tasks", 0),
            CONCURRENT_COUNT,
        )
        store_conc.close()

        conc_avg_ms = (conc_elapsed / CONCURRENT_COUNT) * 1000
        self.assert_true(
            f"P2-T8: Concurrent avg time < 200ms (got {conc_avg_ms:.1f}ms)",
            conc_avg_ms < 200,
            expected="<200ms",
            actual=f"{conc_avg_ms:.1f}ms",
        )

        # ==============================================================
        # PHASE 3: Full pipeline release (approve all rapid-fire tasks)
        # ==============================================================

        released_count = 0
        release_errors: list[str] = []

        t2 = time.monotonic()
        for pair in pairs:
            try:
                released = release_task(
                    review_task_id=pair["review_task_id"],
                    verdict="approved",
                    guidance="Auto-approved in scale test",
                    task_dir=task_dir,
                )
                if released and len(released.blockedBy) == 0:
                    released_count += 1
                else:
                    release_errors.append(
                        f"{pair['implementation_task_id']}: blockedBy={released.blockedBy if released else 'None'}"
                    )
            except Exception as e:
                release_errors.append(f"{pair['implementation_task_id']}: {e}")
        release_elapsed = time.monotonic() - t2

        self.assert_equal(
            f"P3-T1: 100% of {RAPID_FIRE_COUNT} tasks released successfully",
            released_count,
            RAPID_FIRE_COUNT,
        )
        self.assert_equal(
            "P3-T2: Zero errors during bulk release",
            len(release_errors),
            0,
        )

        # All impl tasks should now be executable
        post_release = manager.get_pending_unblocked_tasks()
        post_release_impl = [t for t in post_release if t.id.startswith("impl-")]
        self.assert_equal(
            f"P3-T3: All {RAPID_FIRE_COUNT} impl tasks now executable",
            len(post_release_impl),
            RAPID_FIRE_COUNT,
        )

        # Verify each task individually via get_task_governance_status
        can_execute_count = 0
        for pair in pairs:
            status = get_task_governance_status(pair["implementation_task_id"], task_dir=task_dir)
            if status.get("can_execute") is True:
                can_execute_count += 1

        self.assert_equal(
            "P3-T4: 100% report can_execute=True after release",
            can_execute_count,
            RAPID_FIRE_COUNT,
        )

        release_avg_ms = (release_elapsed / RAPID_FIRE_COUNT) * 1000
        self.assert_true(
            f"P3-T5: Avg release time < 50ms (got {release_avg_ms:.1f}ms)",
            release_avg_ms < 50,
            expected="<50ms",
            actual=f"{release_avg_ms:.1f}ms",
        )

        # ==============================================================
        # PHASE 4: Cross-pair integrity (no task references a wrong pair)
        # ==============================================================

        # Verify every impl task's blockedBy was exactly the correct review
        # (before release they had 1 blocker; after release they have 0)
        # We already verified this, but let's also check that review tasks
        # have the correct `blocks` pointing to the right impl
        integrity_ok = 0
        for pair in pairs:
            review = manager.read_task(pair["review_task_id"])
            if review and pair["implementation_task_id"] in review.blocks:
                integrity_ok += 1

        self.assert_equal(
            "P4-T1: 100% of review tasks point to correct impl task",
            integrity_ok,
            RAPID_FIRE_COUNT,
        )

        # No orphaned review tasks (every review blocks an existing impl)
        review_all = [t for t in manager.list_tasks() if t.id.startswith("review-")]
        orphaned = 0
        for rt in review_all:
            for blocked_id in rt.blocks:
                impl = manager.read_task(blocked_id)
                if not impl:
                    orphaned += 1
        self.assert_equal(
            "P4-T2: Zero orphaned review tasks (all point to existing impl)",
            orphaned,
            0,
        )

        # ==============================================================
        # Summary stats (informational, not pass/fail)
        # ==============================================================

        total_tasks_created = RAPID_FIRE_COUNT + CONCURRENT_COUNT
        total_pairs = total_tasks_created  # each gets a review
        total_files = total_tasks_created * 2  # impl + review per task

        self.assert_true(
            (
                f"SUMMARY: Created {total_tasks_created} tasks, "
                f"{total_pairs} governance pairs, "
                f"{total_files} task files. "
                f"Rapid: {rapid_elapsed:.2f}s ({avg_ms:.1f}ms/task). "
                f"Concurrent: {conc_elapsed:.2f}s ({conc_avg_ms:.1f}ms/task). "
                f"Release: {release_elapsed:.2f}s ({release_avg_ms:.1f}ms/task)."
            ),
            True,
            expected="summary",
            actual="logged",
        )

        return self._build_result(scenario_type="mixed")
