"""Scenario 18 -- Extended Coverage for Evolution Workflow.

Tests untested paths and edge cases identified during coverage audit:

  - Architecture promotion: decision lookup, metadata building, entity checks
  - Cascade alignment: dependent entity discovery via search_entities
  - Evidence validator edge cases: timestamps, formats, boundaries
  - Error paths: invalid state transitions, missing entities, status filters
  - Intent-aware decision review: prompt formatting with/without metadata

The scenario is fully self-contained with isolated JSONL and SQLite storage.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_KG_LIB = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "knowledge-graph"
_GOV_LIB = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "governance"
for _p in (_KG_LIB, _GOV_LIB):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from collab_kg.graph import KnowledgeGraph  # noqa: E402
from collab_kg.metadata import build_intent_observations  # noqa: E402
from collab_governance.models import (  # noqa: E402
    Decision,
    DecisionCategory,
    Confidence,
    EvolutionProposal,
    EvolutionStatus,
    ExperimentEvidence,
    ReviewVerdict,
    Verdict,
)
from collab_governance.store import GovernanceStore  # noqa: E402
from collab_governance.reviewer import GovernanceReviewer  # noqa: E402
from collab_governance.kg_client import KGClient  # noqa: E402
from collab_governance.evidence_validator import (  # noqa: E402
    validate_evidence,
)

from e2e.scenarios.base import BaseScenario, ScenarioResult  # noqa: E402


class S18ExtendedCoverage(BaseScenario):
    """E2E scenario for extended coverage of evolution workflow gaps."""

    name = "s18_extended_coverage"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _kg(self) -> KnowledgeGraph:
        storage_path = str(self.workspace / "kg-extended-test.jsonl")
        return KnowledgeGraph(storage_path=storage_path)

    def _store(self) -> GovernanceStore:
        db_path = self.workspace / "governance-extended-test.db"
        return GovernanceStore(db_path=db_path)

    def _kg_client(self, kg: KnowledgeGraph) -> KGClient:
        return KGClient(kg_path=kg.storage.filepath)

    # ------------------------------------------------------------------
    # Scenario
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:

        kg = self._kg()
        kg_client = self._kg_client(kg)
        gov_store = self._store()
        rvr = GovernanceReviewer()

        # ==============================================================
        # PART 1: Architecture Promotion Logic
        # ==============================================================

        # Store a decision and approve it (promotion requires approved decision)
        decision = Decision(
            task_id="task-promo-test",
            agent="worker-1",
            category=DecisionCategory.PATTERN_CHOICE,
            summary="Use event sourcing for audit trail",
            detail="Event sourcing provides complete audit trail",
            components_affected=["audit_service"],
            confidence=Confidence.HIGH,
        )
        decision = gov_store.store_decision(decision)

        review = ReviewVerdict(
            decision_id=decision.id,
            verdict=Verdict.APPROVED,
            guidance="Approved. Good pattern choice.",
            standards_verified=["audit_trail_standard"],
        )
        gov_store.store_review(review)

        # Verify decision is retrievable as approved
        approved_decisions = gov_store.get_all_decisions(verdict="approved")
        found = any(d.get("id") == decision.id for d in approved_decisions)
        self.assert_true("P1: approved decision retrievable", found)

        # Build intent observations for promotion
        promo_obs = build_intent_observations(
            intent="Maintain complete audit trail for compliance",
            metrics=[{"name": "event_replay_time", "criteria": "< 2s", "baseline": "N/A"}],
            vision_alignments=[{"vision_entity": "audit_compliance", "explanation": "Full event history"}],
        )
        self.assert_true("P1b: promotion observations not empty", len(promo_obs) > 0)
        self.assert_true(
            "P1c: observations contain intent prefix",
            any(o.startswith("intent: ") for o in promo_obs),
        )
        self.assert_true(
            "P1d: observations contain metric prefix",
            any(o.startswith("outcome_metric: ") for o in promo_obs),
        )
        self.assert_true(
            "P1e: observations contain vision alignment prefix",
            any(o.startswith("vision_alignment: ") for o in promo_obs),
        )
        self.assert_true(
            "P1f: observations contain completeness",
            any(o.startswith("metadata_completeness: ") for o in promo_obs),
        )

        # Entity existence check: nonexistent returns None
        missing = kg_client.get_entity_with_metadata("event_sourcing_pattern")
        self.assert_true("P1g: nonexistent entity returns None", missing is None)

        # Create entity to test "already exists" path
        kg.create_entities([{
            "name": "event_sourcing_pattern",
            "entityType": "pattern",
            "observations": promo_obs,
        }])
        existing = kg_client.get_entity_with_metadata("event_sourcing_pattern")
        self.assert_true("P1h: existing entity is found", existing is not None)

        # ==============================================================
        # PART 2: Cascade Discovery Logic (dependent entity finding)
        # ==============================================================

        # Create vision standard
        kg.create_entities([{
            "name": "event_driven_arch",
            "entityType": "vision_standard",
            "observations": [
                "protection_tier: vision",
                "statement: All state changes communicated via events",
            ],
        }])

        # Create architecture entities serving the vision
        for dep_name in ("order_service", "inventory_service", "notification_service"):
            dep_obs = [
                "protection_tier: architecture",
                f"description: {dep_name.replace('_', ' ').title()}",
            ] + build_intent_observations(
                intent=f"Handle {dep_name.split('_')[0]} domain via events",
                vision_alignments=[{"vision_entity": "event_driven_arch", "explanation": "Event-based communication"}],
            )
            # Add cross-reference to event_bus in order_service for cascade discovery
            if dep_name == "order_service":
                dep_obs.append("depends_on: event_bus for order lifecycle events")
            kg.create_entities([{
                "name": dep_name,
                "entityType": "component",
                "observations": dep_obs,
            }])
            kg.create_relations([{
                "from": dep_name,
                "to": "event_driven_arch",
                "relationType": "serves_vision",
            }])

        # Create event_bus pattern (the entity being evolved)
        evo_obs = [
            "protection_tier: architecture",
            "description: Central event bus for inter-service communication",
        ] + build_intent_observations(
            intent="Decouple services via async event passing",
            vision_alignments=[{"vision_entity": "event_driven_arch", "explanation": "Core event infrastructure"}],
        )
        kg.create_entities([{
            "name": "event_bus",
            "entityType": "pattern",
            "observations": evo_obs,
        }])
        kg.create_relations([{
            "from": "event_bus",
            "to": "event_driven_arch",
            "relationType": "serves_vision",
        }])

        # Test cascade discovery pattern (mirrors _create_cascade_alignment_tasks logic)
        # Step 1: get_entities_serving_vision finds entities aligned to the target
        serving = kg_client.get_entities_serving_vision("event_driven_arch")
        self.assert_true(
            "P2: four entities serve event_driven_arch",
            len(serving) == 4,  # order, inventory, notification, event_bus
        )

        # Step 2: search_entities finds entities mentioning target by name/observation
        related = kg_client.search_entities(["event_bus"])
        related_names = {e.get("name") for e in related}
        self.assert_true(
            "P2b: search finds event_bus entity",
            "event_bus" in related_names,
        )
        self.assert_true(
            "P2c: search finds order_service via observation",
            "order_service" in related_names,
        )

        # Step 3: Compute cascade union (minus target)
        cascade_target = "event_bus"
        dependents = {e.get("name") for e in serving}
        for r in related:
            name = r.get("name", "")
            if name and name != cascade_target:
                dependents.add(name)
        dependents.discard(cascade_target)  # exclude self if present

        self.assert_true(
            "P2d: cascade dependents include order_service",
            "order_service" in dependents,
        )
        self.assert_true(
            "P2e: cascade dependents include inventory_service",
            "inventory_service" in dependents,
        )
        self.assert_true(
            "P2f: cascade does NOT include the target itself",
            cascade_target not in dependents,
        )

        # ==============================================================
        # PART 3: Evidence Validator Timestamp Edge Cases
        # ==============================================================

        # Disable mock mode for real validation
        old_mock = os.environ.pop("GOVERNANCE_MOCK_REVIEW", None)

        evidence_file = self.workspace / "test-output-ts.txt"
        evidence_file.write_text("42 passed, 0 failed\nExecution time: 312ms\n")

        # 3a: Invalid timestamp format
        bad_ts = ExperimentEvidence(
            evidence_type="test_results",
            source=str(evidence_file),
            raw_output="42 passed, 0 failed",
            summary="Tests pass",
            metrics={"passed": 42, "failed": 0},
            timestamp="not-a-valid-timestamp",
        )
        r_bad_ts = validate_evidence(bad_ts)
        self.assert_true("P3a: invalid timestamp fails", not r_bad_ts.valid)
        self.assert_true(
            "P3b: failure mentions timestamp",
            any("timestamp" in f.lower() for f in r_bad_ts.failures),
        )

        # 3c: Timestamp before experiment start
        experiment_start = "2026-02-06T00:00:00+00:00"
        before_start = ExperimentEvidence(
            evidence_type="test_results",
            source=str(evidence_file),
            raw_output="42 passed, 0 failed",
            summary="Tests pass",
            metrics={"passed": 42, "failed": 0},
            timestamp="2026-02-05T00:00:00+00:00",
        )
        r_before = validate_evidence(before_start, experiment_start=experiment_start)
        self.assert_true("P3c: before-start timestamp fails", not r_before.valid)
        self.assert_true(
            "P3d: failure mentions 'before experiment'",
            any("before experiment" in f.lower() for f in r_before.failures),
        )

        # 3e: Far-future timestamp (>30 days)
        future_ts = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
        far_future = ExperimentEvidence(
            evidence_type="test_results",
            source=str(evidence_file),
            raw_output="42 passed, 0 failed",
            summary="Tests pass",
            metrics={"passed": 42, "failed": 0},
            timestamp=future_ts,
        )
        r_future = validate_evidence(far_future)
        self.assert_true("P3e: far-future timestamp fails", not r_future.valid)
        self.assert_true(
            "P3f: failure mentions 'future'",
            any("future" in f.lower() for f in r_future.failures),
        )

        # 3g: Valid timestamp within window
        valid_ts = datetime.now(timezone.utc).isoformat()
        valid_within = ExperimentEvidence(
            evidence_type="test_results",
            source=str(evidence_file),
            raw_output="42 passed, 0 failed",
            summary="Tests pass",
            metrics={"passed": 42, "failed": 0},
            timestamp=valid_ts,
        )
        r_valid_ts = validate_evidence(valid_within, experiment_start="2026-01-01T00:00:00+00:00")
        self.assert_true("P3g: valid timestamp passes", r_valid_ts.valid)

        # 3h: Benchmark with numeric measurements in raw output (should pass)
        bench_with_numbers = ExperimentEvidence(
            evidence_type="benchmark",
            source=str(evidence_file),
            raw_output="Throughput: 1500 ops/sec, Latency: 2.3ms p99",
            summary="Performance benchmark results",
        )
        r_bench = validate_evidence(bench_with_numbers)
        self.assert_true("P3h: benchmark with numeric output passes", r_bench.valid)

        # Restore mock mode
        if old_mock:
            os.environ["GOVERNANCE_MOCK_REVIEW"] = old_mock

        # ==============================================================
        # PART 4: Error Paths - Evolution Lifecycle
        # ==============================================================

        # 4a: Get nonexistent proposal
        missing_proposal = gov_store.get_evolution_proposal("nonexistent-id")
        self.assert_true("P4a: nonexistent proposal returns None", missing_proposal is None)

        # 4b: Create and reject a proposal, verify state persistence
        proposal = EvolutionProposal(
            target_entity="event_bus",
            original_intent="Decouple services",
            proposed_change="Replace with gRPC streaming",
            rationale="Lower latency",
            validation_criteria=["Latency < 1ms"],
            proposing_agent="worker-1",
        )
        proposal = gov_store.store_evolution_proposal(proposal)
        proposal.status = EvolutionStatus.REJECTED
        proposal.review_verdict = "rejected"
        gov_store.update_evolution_proposal(proposal)

        retrieved_rejected = gov_store.get_evolution_proposal(proposal.id)
        self.assert_true(
            "P4b: rejected proposal status persisted",
            retrieved_rejected is not None and retrieved_rejected.status == EvolutionStatus.REJECTED,
        )

        # Verify rejected status blocks evidence (as checked in submit_experiment_evidence)
        self.assert_true(
            "P4c: rejected status not in evidence-accepting states",
            retrieved_rejected.status not in (EvolutionStatus.EXPERIMENTING, EvolutionStatus.PROPOSED),
        )

        # 4d: Create approved proposal, verify it also blocks evidence
        proposal2 = EvolutionProposal(
            target_entity="event_bus",
            original_intent="Decouple services",
            proposed_change="Switch to message queue",
            rationale="Better durability",
            validation_criteria=["No message loss"],
            proposing_agent="worker-2",
        )
        proposal2 = gov_store.store_evolution_proposal(proposal2)
        proposal2.status = EvolutionStatus.APPROVED
        gov_store.update_evolution_proposal(proposal2)

        retrieved_approved = gov_store.get_evolution_proposal(proposal2.id)
        self.assert_true(
            "P4d: approved status not in evidence-accepting states",
            retrieved_approved.status not in (EvolutionStatus.EXPERIMENTING, EvolutionStatus.PROPOSED),
        )

        # 4e: needs_more_evidence state persistence
        proposal3 = EvolutionProposal(
            target_entity="event_bus",
            original_intent="Decouple services",
            proposed_change="Add circuit breaker",
            rationale="Fault tolerance",
            validation_criteria=["99.9% uptime"],
            proposing_agent="worker-3",
        )
        proposal3 = gov_store.store_evolution_proposal(proposal3)
        proposal3.status = EvolutionStatus.NEEDS_MORE_EVIDENCE
        gov_store.update_evolution_proposal(proposal3)

        retrieved_nme = gov_store.get_evolution_proposal(proposal3.id)
        self.assert_true(
            "P4e: needs_more_evidence status persisted",
            retrieved_nme is not None and retrieved_nme.status == EvolutionStatus.NEEDS_MORE_EVIDENCE,
        )

        # 4f: Query by entity finds all 3 proposals
        entity_proposals = gov_store.get_evolution_proposals_for_entity("event_bus")
        self.assert_true(
            "P4f: three proposals for event_bus",
            len(entity_proposals) == 3,
        )

        # 4g: Status filter queries
        rejected_list = gov_store.get_all_evolution_proposals(status="rejected")
        self.assert_true("P4g: one rejected proposal", len(rejected_list) == 1)

        approved_list = gov_store.get_all_evolution_proposals(status="approved")
        self.assert_true("P4h: one approved proposal", len(approved_list) == 1)

        nme_list = gov_store.get_all_evolution_proposals(status="needs_more_evidence")
        self.assert_true("P4i: one needs_more_evidence proposal", len(nme_list) == 1)

        # 4j: Active experiments (experimenting/validated only)
        active = gov_store.get_active_experiments()
        self.assert_true(
            "P4j: no active experiments (none in experimenting/validated)",
            len(active) == 0,
        )

        # ==============================================================
        # PART 5: Intent-Aware Decision Review Prompt Formatting
        # ==============================================================

        # Architecture entities WITH parsed metadata
        arch_with_meta = [{
            "name": "event_bus",
            "entityType": "pattern",
            "observations": evo_obs,
            "intent": "Decouple services via async event passing",
            "metrics": [{"name": "event_latency", "criteria": "< 5ms", "baseline": "12ms"}],
            "vision_alignments": [{"vision_entity": "event_driven_arch", "explanation": "Core event infrastructure"}],
            "completeness": "full",
        }]

        # Architecture entities WITHOUT metadata (legacy)
        arch_no_meta = [{
            "name": "old_logger",
            "entityType": "component",
            "observations": ["description: Legacy logging system", "usage: Direct import"],
        }]

        # Test rich format with metadata
        rich_formatted = rvr._format_architecture_with_intent(arch_with_meta)
        self.assert_true("P5: rich format contains Intent", "Intent:" in rich_formatted)
        self.assert_true(
            "P5b: rich format contains Metrics",
            "Metrics:" in rich_formatted and "event_latency" in rich_formatted,
        )
        self.assert_true(
            "P5c: rich format contains Serves",
            "Serves:" in rich_formatted and "event_driven_arch" in rich_formatted,
        )
        self.assert_true(
            "P5d: rich format contains completeness",
            "Metadata completeness: full" in rich_formatted,
        )

        # Test legacy format (no metadata)
        legacy_formatted = rvr._format_architecture_with_intent(arch_no_meta)
        self.assert_true(
            "P5e: legacy format uses simple style",
            "**old_logger**" in legacy_formatted and "Intent:" not in legacy_formatted,
        )

        # Test _build_decision_prompt WITH metadata entities
        test_decision = Decision(
            task_id="task-test",
            agent="worker-1",
            category=DecisionCategory.PATTERN_CHOICE,
            summary="Use WebSocket for real-time updates",
            components_affected=["event_bus"],
            confidence=Confidence.HIGH,
        )
        prompt_with_meta = rvr._build_decision_prompt(test_decision, [], arch_with_meta)
        self.assert_true(
            "P5f: prompt has intent instructions when metadata present",
            "Intent-aware evaluation" in prompt_with_meta,
        )
        self.assert_true(
            "P5g: prompt contains entity intent",
            "Intent:" in prompt_with_meta and "Decouple services" in prompt_with_meta,
        )

        # Test _build_decision_prompt WITHOUT metadata entities
        prompt_no_meta = rvr._build_decision_prompt(test_decision, [], arch_no_meta)
        self.assert_true(
            "P5h: prompt has NO intent instructions without metadata",
            "Intent-aware evaluation" not in prompt_no_meta,
        )

        # Test evolution proposal review prompt
        test_proposal = EvolutionProposal(
            target_entity="event_bus",
            original_intent="Decouple services",
            proposed_change="Replace with message queue",
            rationale="Better durability and ordering guarantees",
            experiment_plan="Run parallel implementation with A/B test",
            validation_criteria=["No message loss", "Latency < 5ms"],
            proposing_agent="worker-1",
        )
        target_meta = {
            "intent": "Decouple services via async event passing",
            "metrics": [{"name": "event_latency", "criteria": "< 5ms", "baseline": "12ms"}],
            "vision_alignments": [{"vision_entity": "event_driven_arch", "explanation": "Core event infrastructure"}],
        }
        evo_prompt = rvr._build_evolution_prompt(test_proposal, target_meta, [])
        self.assert_true(
            "P5i: evolution prompt contains target intent",
            "Decouple services" in evo_prompt,
        )
        self.assert_true(
            "P5j: evolution prompt contains validation criteria",
            "No message loss" in evo_prompt and "Latency < 5ms" in evo_prompt,
        )
        self.assert_true(
            "P5k: evolution prompt contains intent preservation instruction",
            "Intent preservation" in evo_prompt,
        )

        return self._build_result(scenario_type="library")
