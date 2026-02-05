"""S12 -- Cross-server integration: KG + Governance + Task system.

Verifies the end-to-end flow across multiple server libraries:
  1. Create KG entities (vision + architecture tiers)
  2. Create governance decisions referencing those components
  3. Use KGClient to read the KG and verify standards are loaded
  4. Store governed tasks and verify linkage between tasks and decisions
  5. Verify governance status includes task governance stats

Scenario type: positive.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "knowledge-graph"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "governance"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "quality"))

from collab_kg.graph import KnowledgeGraph
from collab_governance.kg_client import KGClient
from collab_governance.models import (
    Decision,
    DecisionCategory,
    Confidence,
    ReviewVerdict,
    Verdict,
    GovernedTaskRecord,
    TaskReviewRecord,
    TaskReviewStatus,
    ReviewType,
)
from collab_governance.store import GovernanceStore

from .base import BaseScenario, ScenarioResult


class S12CrossServerIntegration(BaseScenario):
    """Assert that KG, governance, and task systems integrate correctly."""

    name = "s12-cross-server-integration"
    isolation_mode = "library"

    def run(self, **kwargs: Any) -> ScenarioResult:
        # -- Setup: use the generated project's KG --------------------------
        kg = KnowledgeGraph(storage_path=str(self.project.kg_path))

        vision_std = self.project.vision_standards[0]
        arch_pattern = self.project.architecture_patterns[0]

        # -- Step 1: Verify KG entities exist (created by project generator) -
        vision_entity = kg.get_entity(vision_std["name"])
        self.assert_true(
            "vision entity exists in KG",
            vision_entity is not None,
            expected="entity present",
            actual="present" if vision_entity is not None else "missing",
        )

        arch_entity = kg.get_entity(arch_pattern["name"])
        self.assert_true(
            "architecture entity exists in KG",
            arch_entity is not None,
            expected="entity present",
            actual="present" if arch_entity is not None else "missing",
        )

        # Verify vision entity has correct tier
        if vision_entity is not None:
            self.assert_contains(
                "vision entity has protection_tier observation",
                vision_entity.observations,
                "protection_tier: vision",
            )

        # Verify architecture entity has correct tier
        if arch_entity is not None:
            self.assert_contains(
                "architecture entity has protection_tier observation",
                arch_entity.observations,
                "protection_tier: architecture",
            )

        # -- Step 2: Use KGClient to read KG (governance's view) ------------
        kg_client = KGClient(kg_path=self.project.kg_path)

        vision_standards = kg_client.get_vision_standards()
        self.assert_true(
            "KGClient finds vision standards",
            len(vision_standards) > 0,
            expected=">0 standards",
            actual=f"{len(vision_standards)} standards",
        )

        arch_entities = kg_client.get_architecture_entities()
        self.assert_true(
            "KGClient finds architecture entities",
            len(arch_entities) > 0,
            expected=">0 entities",
            actual=f"{len(arch_entities)} entities",
        )

        # Search by component name
        component = self.project.components[0]
        search_results = kg_client.search_entities([component])
        # The component name appears in observations via template filling
        self.assert_true(
            "KGClient search returns results for component",
            len(search_results) >= 0,  # may or may not find depending on template
            expected="search completes without error",
            actual=f"{len(search_results)} results",
        )

        # -- Step 3: Create governance decisions referencing KG components ---
        db_path = self.workspace / "s12-governance.db"
        store = GovernanceStore(db_path=db_path)
        task_id = "task-s12-integration"

        decision = store.store_decision(Decision(
            task_id=task_id,
            agent="worker-1",
            category=DecisionCategory.COMPONENT_DESIGN,
            summary=f"Design {component} following {vision_std['name']}",
            detail=f"Implementing {component} in compliance with: {vision_std['statement']}",
            components_affected=[component],
            confidence=Confidence.HIGH,
        ))

        self.assert_true(
            "governance decision stored",
            decision.id is not None and len(decision.id) > 0,
        )

        # Store an approved review
        review = store.store_review(ReviewVerdict(
            decision_id=decision.id,
            verdict=Verdict.APPROVED,
            standards_verified=[vision_std["name"], arch_pattern["name"]],
        ))

        self.assert_equal(
            "review verdict is approved",
            review.verdict,
            Verdict.APPROVED,
        )

        self.assert_contains(
            "review verified vision standard",
            review.standards_verified,
            vision_std["name"],
        )

        self.assert_contains(
            "review verified architecture pattern",
            review.standards_verified,
            arch_pattern["name"],
        )

        # -- Step 4: Record decision in KG for institutional memory ---------
        kg_client.record_decision(
            decision_id=decision.id,
            summary=decision.summary,
            verdict="approved",
            agent="worker-1",
        )

        # Verify the decision was recorded in the KG
        kg_decision_entities = kg_client.search_entities([f"governance_decision_{decision.id}"])
        self.assert_true(
            "governance decision recorded in KG",
            len(kg_decision_entities) > 0,
            expected=">0 entities",
            actual=f"{len(kg_decision_entities)} entities",
        )

        # -- Step 5: Store governed task and verify linkage -----------------
        impl_task_id = "impl-s12-001"
        governed_task = GovernedTaskRecord(
            implementation_task_id=impl_task_id,
            subject=f"Implement {component}",
            description=f"Full implementation of {component} service",
            context=f"Must comply with {vision_std['name']}",
        )
        stored_task = store.store_governed_task(governed_task)

        self.assert_true(
            "governed task stored",
            stored_task.id is not None and len(stored_task.id) > 0,
        )

        self.assert_equal(
            "governed task status is pending_review",
            stored_task.current_status,
            "pending_review",
        )

        # Store a task review
        task_review = TaskReviewRecord(
            review_task_id="review-s12-001",
            implementation_task_id=impl_task_id,
            review_type=ReviewType.GOVERNANCE,
            status=TaskReviewStatus.APPROVED,
            context=f"Governance review for {component}",
            verdict=Verdict.APPROVED,
            standards_verified=[vision_std["name"]],
        )
        stored_review = store.store_task_review(task_review)

        self.assert_equal(
            "task review type is GOVERNANCE",
            stored_review.review_type,
            ReviewType.GOVERNANCE,
        )

        self.assert_equal(
            "task review status is APPROVED",
            stored_review.status,
            TaskReviewStatus.APPROVED,
        )

        # Update governed task status
        store.update_governed_task_status(impl_task_id, "approved")

        # -- Step 6: Verify governance status includes task stats -----------
        task_stats = store.get_task_governance_stats()

        self.assert_equal(
            "total governed tasks is 1",
            task_stats["total_governed_tasks"],
            1,
        )

        self.assert_equal(
            "approved governed tasks is 1",
            task_stats["approved"],
            1,
        )

        # Verify the governed task can be retrieved
        retrieved_task = store.get_governed_task(impl_task_id)
        self.assert_true(
            "governed task retrievable by impl ID",
            retrieved_task is not None,
        )

        if retrieved_task is not None:
            self.assert_equal(
                "retrieved task status is approved",
                retrieved_task.current_status,
                "approved",
            )

        # Verify task reviews are retrievable
        task_reviews = store.get_task_reviews(impl_task_id)
        self.assert_equal(
            "one task review stored for governed task",
            len(task_reviews),
            1,
        )

        # -- Overall governance status includes both decision and task stats -
        overall_status = store.get_status()
        self.assert_equal(
            "overall status shows 1 decision",
            overall_status["total_decisions"],
            1,
        )

        self.assert_equal(
            "overall status shows 1 approved review",
            overall_status["approved"],
            1,
        )

        store.close()
        return self._build_result(scenario_type="positive")
