"""Scenario 02 — Governance Decision Flow.

Tests the governance decision storage lifecycle by exercising the
``GovernanceStore`` directly.  We verify that decisions across multiple
categories are persisted correctly, that decision history can be queried,
and that category-specific metadata is preserved for downstream flagging.

NOTE: We test the **store layer** only, not the full review cycle (which
requires ``claude --print``).  Server-level auto-flagging of ``deviation``
and ``scope_change`` categories is validated separately at the HTTP level.

The scenario uses an isolated SQLite database inside ``self.workspace``
so that parallel runs never collide.
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

from collab_governance.models import (  # noqa: E402
    Alternative,
    Confidence,
    Decision,
    DecisionCategory,
    Finding,
    ReviewVerdict,
    Verdict,
)
from collab_governance.store import GovernanceStore  # noqa: E402

from e2e.scenarios.base import BaseScenario, ScenarioResult  # noqa: E402


class GovernanceDecisionFlowScenario(BaseScenario):
    """E2E scenario exercising governance decision storage and retrieval."""

    name = "s02_governance_decision_flow"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _store(self) -> GovernanceStore:
        """Return a GovernanceStore backed by an isolated SQLite DB."""
        db_path = self.workspace / "governance-flow-test.db"
        return GovernanceStore(db_path=db_path)

    def _make_decision(
        self,
        task_id: str,
        category: DecisionCategory,
        summary: str,
        agent: str = "worker-1",
        detail: str = "",
        components: list[str] | None = None,
        alternatives: list[Alternative] | None = None,
        confidence: Confidence = Confidence.HIGH,
    ) -> Decision:
        """Build a Decision model ready for storage."""
        return Decision(
            task_id=task_id,
            agent=agent,
            category=category,
            summary=summary,
            detail=detail,
            components_affected=components or [],
            alternatives_considered=alternatives or [],
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Scenario entry point
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:
        store = self._store()

        # Derive domain-specific names from the project fixture when available
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
        task_id = f"task-{domain.lower().replace(' ', '-')}-001"

        # ==============================================================
        # POSITIVE CASES
        # ==============================================================

        # 1. Store a pattern_choice decision — succeeds
        decision_pattern = self._make_decision(
            task_id=task_id,
            category=DecisionCategory.PATTERN_CHOICE,
            summary=f"Use ServiceRegistry pattern for {component}",
            detail=f"Chosen for {domain} to centralize dependency resolution",
            components=[component],
            alternatives=[
                Alternative(
                    option="Manual DI",
                    reason_rejected="Does not scale with number of services",
                ),
            ],
        )
        stored_pattern = store.store_decision(decision_pattern)
        self.assert_true(
            "P1: Store pattern_choice decision succeeds",
            stored_pattern.id == decision_pattern.id,
            expected=decision_pattern.id,
            actual=stored_pattern.id,
        )
        self.assert_equal(
            "P1b: Stored decision has correct category",
            stored_pattern.category,
            DecisionCategory.PATTERN_CHOICE,
        )
        self.assert_true(
            "P1c: Sequence was auto-assigned",
            stored_pattern.sequence >= 1,
            expected=">=1",
            actual=stored_pattern.sequence,
        )

        # 2. Store a component_design decision — succeeds
        decision_component = self._make_decision(
            task_id=task_id,
            category=DecisionCategory.COMPONENT_DESIGN,
            summary=f"Design {component} with protocol-based interface",
            detail="Interface exposes async methods for CRUD operations",
            components=[component, "ServiceRegistry"],
            confidence=Confidence.MEDIUM,
        )
        stored_component = store.store_decision(decision_component)
        self.assert_true(
            "P2: Store component_design decision succeeds",
            stored_component.id == decision_component.id,
            expected=decision_component.id,
            actual=stored_component.id,
        )
        self.assert_equal(
            "P2b: Stored decision has correct category",
            stored_component.category,
            DecisionCategory.COMPONENT_DESIGN,
        )
        self.assert_true(
            "P2c: Sequence incremented from previous decision",
            stored_component.sequence > stored_pattern.sequence,
            expected=f">{stored_pattern.sequence}",
            actual=stored_component.sequence,
        )

        # 3. Get decision history returns stored decisions
        decisions = store.get_decisions_for_task(task_id)
        self.assert_equal(
            "P3: Decision history returns 2 decisions for task",
            len(decisions),
            2,
        )
        decision_summaries = [d.summary for d in decisions]
        self.assert_contains(
            "P3b: History contains pattern_choice summary",
            decision_summaries,
            f"Use ServiceRegistry pattern for {component}",
        )
        self.assert_contains(
            "P3c: History contains component_design summary",
            decision_summaries,
            f"Design {component} with protocol-based interface",
        )

        # Verify get_all_decisions returns the data with optional filters
        all_decisions = store.get_all_decisions(task_id=task_id)
        self.assert_equal(
            "P3d: get_all_decisions with task filter returns 2",
            len(all_decisions),
            2,
        )

        # ==============================================================
        # NEGATIVE / EDGE CASES (categories that trigger special handling)
        # ==============================================================

        # 4. Deviation category stores correctly
        #    At the server level, deviation decisions auto-flag as
        #    needs_human_review. Here we verify the store layer preserves
        #    the category so the server can detect it.
        decision_deviation = self._make_decision(
            task_id=task_id,
            category=DecisionCategory.DEVIATION,
            summary=f"Deviate from event-bus pattern for {component} hot path",
            detail="Direct call needed for latency-sensitive path",
            components=[component],
            confidence=Confidence.LOW,
        )
        stored_deviation = store.store_decision(decision_deviation)
        self.assert_equal(
            "N4: Deviation decision stores with correct category",
            stored_deviation.category,
            DecisionCategory.DEVIATION,
        )
        self.assert_equal(
            "N4b: Deviation decision confidence preserved as LOW",
            stored_deviation.confidence,
            Confidence.LOW,
        )

        # Store a review that marks it as needs_human_review to verify
        # the store can persist that verdict
        review_deviation = ReviewVerdict(
            decision_id=stored_deviation.id,
            verdict=Verdict.NEEDS_HUMAN_REVIEW,
            findings=[
                Finding(
                    tier="architecture",
                    severity="warning",
                    description="Deviates from event-bus architecture standard",
                    suggestion="Get human approval before proceeding",
                ),
            ],
            guidance="Requires human review: deviation from established pattern",
            standards_verified=["event-bus-pattern"],
        )
        stored_review = store.store_review(review_deviation)
        self.assert_equal(
            "N4c: Review verdict stored as NEEDS_HUMAN_REVIEW",
            stored_review.verdict,
            Verdict.NEEDS_HUMAN_REVIEW,
        )

        # Verify has_unresolved_blocks detects blocked reviews
        # (needs_human_review is NOT 'blocked', so this should be False)
        has_blocks = store.has_unresolved_blocks(task_id)
        self.assert_true(
            "N4d: needs_human_review does NOT count as unresolved block",
            has_blocks is False,
            expected=False,
            actual=has_blocks,
        )

        # 5. Scope change category stores correctly
        decision_scope = self._make_decision(
            task_id=task_id,
            category=DecisionCategory.SCOPE_CHANGE,
            summary="Expand scope to include audit logging",
            detail=f"Audit logging needed for {domain} compliance requirements",
            components=[component, "AuditLogger"],
            confidence=Confidence.MEDIUM,
        )
        stored_scope = store.store_decision(decision_scope)
        self.assert_equal(
            "N5: Scope change decision stores with correct category",
            stored_scope.category,
            DecisionCategory.SCOPE_CHANGE,
        )

        # Store a blocked review for scope change
        review_scope = ReviewVerdict(
            decision_id=stored_scope.id,
            verdict=Verdict.BLOCKED,
            findings=[
                Finding(
                    tier="vision",
                    severity="critical",
                    description="Scope expansion not approved in task brief",
                    suggestion="Submit scope change proposal to orchestrator",
                ),
            ],
            guidance="Blocked: scope changes require orchestrator approval",
            standards_verified=["scope-management"],
        )
        store.store_review(review_scope)

        # Now has_unresolved_blocks should be True (a BLOCKED verdict exists)
        has_blocks = store.has_unresolved_blocks(task_id)
        self.assert_true(
            "N5b: Blocked verdict registers as unresolved block",
            has_blocks is True,
            expected=True,
            actual=has_blocks,
        )

        # Verify the full decision count
        all_for_task = store.get_decisions_for_task(task_id)
        self.assert_equal(
            "N5c: Total decisions for task is 4 (2 positive + deviation + scope_change)",
            len(all_for_task),
            4,
        )

        # Verify governance status
        status = store.get_status()
        self.assert_true(
            "N5d: Governance status total_decisions >= 4",
            status["total_decisions"] >= 4,
            expected=">=4",
            actual=status["total_decisions"],
        )
        self.assert_true(
            "N5e: Governance status blocked count >= 1",
            status["blocked"] >= 1,
            expected=">=1",
            actual=status["blocked"],
        )

        store.close()
        return self._build_result(scenario_type="mixed")
