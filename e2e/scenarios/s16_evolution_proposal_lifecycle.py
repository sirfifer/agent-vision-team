"""Scenario 16 -- Evolution Proposal Lifecycle.

Tests the full lifecycle of an architecture evolution proposal:

  - propose_evolution: submit a proposal, get intent-aware review
  - submit_experiment_evidence: submit validated evidence
  - present_evolution_results: compile side-by-side comparison
  - approve_evolution: human verdict, KG update

Uses mock review mode so no live claude binary is needed.
The scenario is fully self-contained with isolated JSONL and SQLite storage.
"""

from __future__ import annotations

import os
import sys
import tempfile
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
    EvolutionProposal,
    EvolutionStatus,
    ExperimentEvidence,
)
from collab_governance.store import GovernanceStore  # noqa: E402
from collab_governance.reviewer import GovernanceReviewer  # noqa: E402
from collab_governance.kg_client import KGClient  # noqa: E402
from collab_governance.evidence_validator import (  # noqa: E402
    validate_evidence,
    validate_evidence_batch,
    EvidenceValidationResult,
)

from e2e.scenarios.base import BaseScenario, ScenarioResult  # noqa: E402


class S16EvolutionProposalLifecycle(BaseScenario):
    """E2E scenario exercising the full evolution proposal lifecycle."""

    name = "s16_evolution_proposal_lifecycle"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _kg(self) -> KnowledgeGraph:
        storage_path = str(self.workspace / "kg-evolution-test.jsonl")
        return KnowledgeGraph(storage_path=storage_path)

    def _store(self) -> GovernanceStore:
        db_path = self.workspace / "governance-evolution-test.db"
        return GovernanceStore(db_path=db_path)

    def _kg_client(self, kg: KnowledgeGraph) -> KGClient:
        return KGClient(kg_path=kg.storage.filepath)

    # ------------------------------------------------------------------
    # Scenario
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:
        # Enable mock review
        os.environ["GOVERNANCE_MOCK_REVIEW"] = "1"

        kg = self._kg()
        gov_store = self._store()
        kg_client = self._kg_client(kg)
        rvr = GovernanceReviewer()

        # ==============================================================
        # PART 1: Setup - create architecture entity with full metadata
        # ==============================================================

        # Create a vision standard
        kg.create_entities([{
            "name": "protocol_based_di",
            "entityType": "vision_standard",
            "observations": [
                "protection_tier: vision",
                "statement: All services use protocol-based dependency injection",
            ],
        }])

        # Create architecture entity with full intent metadata
        obs = [
            "protection_tier: architecture",
            "description: Central registry for service lookup and lifecycle management",
        ] + build_intent_observations(
            intent="Enable any component to be tested in isolation without real dependencies",
            metrics=[
                {"name": "test_isolation_time", "criteria": "< 500ms per test", "baseline": "847ms average"},
                {"name": "stub_coverage", "criteria": "100% of services", "baseline": "72%"},
            ],
            vision_alignments=[
                {"vision_entity": "protocol_based_di", "explanation": "Services swappable via protocols"},
            ],
        )
        kg.create_entities([{
            "name": "service_registry_pattern",
            "entityType": "pattern",
            "observations": obs,
        }])

        # Add serves_vision relation
        kg.create_relations([{
            "from": "service_registry_pattern",
            "to": "protocol_based_di",
            "relationType": "serves_vision",
        }])

        sr = kg.get_entity("service_registry_pattern")
        self.assert_true("P1: entity created with metadata", sr is not None)
        self.assert_true(
            "P1b: entity has full completeness",
            sr is not None and "metadata_completeness: full" in sr.observations,
        )

        # ==============================================================
        # PART 2: Propose evolution
        # ==============================================================

        entity_data = kg_client.get_entity_with_metadata("service_registry_pattern")
        self.assert_true("P2: entity metadata loaded", entity_data is not None)
        self.assert_true(
            "P2b: parsed intent matches",
            entity_data is not None and "isolation" in (entity_data.get("intent") or "").lower(),
        )

        proposal = EvolutionProposal(
            target_entity="service_registry_pattern",
            original_intent=entity_data.get("intent", "") if entity_data else "",
            proposed_change="Replace service registry with protocol witnesses for compile-time safety",
            rationale="Protocol witnesses eliminate runtime lookup failures and enable dead code elimination",
            experiment_plan="Create parallel implementation in worktree, run existing test suite, benchmark",
            validation_criteria=[
                "All existing tests pass",
                "Test isolation time < 500ms",
                "No runtime lookup failures",
            ],
            proposing_agent="worker-1",
        )

        # Store proposal
        proposal = gov_store.store_evolution_proposal(proposal)
        self.assert_true("P2c: proposal stored", proposal.id is not None)
        self.assert_true(
            "P2d: proposal status is proposed",
            proposal.status == EvolutionStatus.PROPOSED,
        )

        # Review proposal
        vision_standards = [{"name": "protocol_based_di", "observations": ["All services use protocol-based DI"]}]
        review = rvr.review_evolution_proposal(proposal, entity_data, vision_standards)
        self.assert_true("P2e: review returns approved (mock)", review.verdict.value == "approved")

        # Update proposal based on review
        proposal.status = EvolutionStatus.EXPERIMENTING
        proposal.review_verdict = "approved_for_experimentation"
        gov_store.update_evolution_proposal(proposal)

        retrieved = gov_store.get_evolution_proposal(proposal.id)
        self.assert_true(
            "P2f: proposal updated to experimenting",
            retrieved is not None and retrieved.status == EvolutionStatus.EXPERIMENTING,
        )

        # ==============================================================
        # PART 3: Submit experiment evidence
        # ==============================================================

        # Create a temp evidence file
        evidence_file = self.workspace / "test-results.txt"
        evidence_file.write_text("Tests: 42 passed, 0 failed, 0 skipped\nTime: 312ms\n")

        evidence = ExperimentEvidence(
            evidence_type="test_results",
            source=str(evidence_file),
            raw_output="Tests: 42 passed, 0 failed, 0 skipped\nTime: 312ms",
            summary="All 42 tests pass with protocol witnesses. Average time 312ms (was 847ms).",
            metrics={"test_count": 42, "pass_count": 42, "avg_time_ms": 312},
            comparison_to_baseline={
                "test_isolation_time": {"baseline": 847, "experiment": 312, "improvement": "63%"},
            },
        )

        # Validate evidence (mock mode allows all)
        validation = validate_evidence(evidence, experiment_start=proposal.created_at)
        self.assert_true("P3: evidence validates", validation.valid)

        # Add to proposal
        proposal.evidence.append(evidence)
        gov_store.update_evolution_proposal(proposal)

        retrieved2 = gov_store.get_evolution_proposal(proposal.id)
        self.assert_true(
            "P3b: evidence persisted",
            retrieved2 is not None and len(retrieved2.evidence) == 1,
        )
        self.assert_true(
            "P3c: evidence type correct",
            retrieved2 is not None and retrieved2.evidence[0].evidence_type == "test_results",
        )

        # Add benchmark evidence
        bench_evidence = ExperimentEvidence(
            evidence_type="benchmark",
            source="",
            raw_output="Benchmark: registry_lookup 0.8ms, witness_resolve 0.1ms",
            summary="Protocol witness resolution is 8x faster than registry lookup",
            metrics={"registry_lookup_ms": 0.8, "witness_resolve_ms": 0.1},
            comparison_to_baseline={
                "lookup_time": {"baseline": 0.8, "experiment": 0.1, "improvement": "87.5%"},
            },
        )

        proposal.evidence.append(bench_evidence)
        gov_store.update_evolution_proposal(proposal)

        # Validate batch
        batch_result = validate_evidence_batch(proposal.evidence, experiment_start=proposal.created_at)
        self.assert_true("P3d: batch validates", batch_result.valid)

        # ==============================================================
        # PART 4: Present results
        # ==============================================================

        # Mark as validated
        proposal.status = EvolutionStatus.VALIDATED
        gov_store.update_evolution_proposal(proposal)

        validated_proposal = gov_store.get_evolution_proposal(proposal.id)
        self.assert_true(
            "P4: proposal is validated",
            validated_proposal is not None and validated_proposal.status == EvolutionStatus.VALIDATED,
        )
        self.assert_true(
            "P4b: has 2 evidence items",
            validated_proposal is not None and len(validated_proposal.evidence) == 2,
        )

        # ==============================================================
        # PART 5: Approve evolution
        # ==============================================================

        proposal.status = EvolutionStatus.APPROVED
        proposal.review_verdict = "approved"
        gov_store.update_evolution_proposal(proposal)

        approved = gov_store.get_evolution_proposal(proposal.id)
        self.assert_true(
            "P5: proposal approved",
            approved is not None and approved.status == EvolutionStatus.APPROVED,
        )
        self.assert_true(
            "P5b: review verdict is approved",
            approved is not None and approved.review_verdict == "approved",
        )

        # ==============================================================
        # PART 6: Query methods
        # ==============================================================

        # Get proposals for entity
        entity_proposals = gov_store.get_evolution_proposals_for_entity("service_registry_pattern")
        self.assert_true(
            "P6: one proposal for entity",
            len(entity_proposals) == 1,
        )

        # Get all proposals
        all_proposals = gov_store.get_all_evolution_proposals()
        self.assert_true("P6b: one total proposal", len(all_proposals) == 1)

        # Get by status
        approved_proposals = gov_store.get_all_evolution_proposals(status="approved")
        self.assert_true("P6c: one approved proposal", len(approved_proposals) == 1)

        rejected_proposals = gov_store.get_all_evolution_proposals(status="rejected")
        self.assert_true("P6d: zero rejected proposals", len(rejected_proposals) == 0)

        # Active experiments (should be empty since we moved past experimenting)
        active = gov_store.get_active_experiments()
        self.assert_true("P6e: no active experiments (approved)", len(active) == 0)

        # ==============================================================
        # PART 7: KGClient entity metadata helpers
        # ==============================================================

        em = kg_client.get_entity_with_metadata("service_registry_pattern")
        self.assert_true("P7: entity metadata loaded", em is not None)
        self.assert_true(
            "P7b: intent parsed",
            em is not None and em["intent"] is not None and "isolation" in em["intent"].lower(),
        )
        self.assert_true(
            "P7c: metrics parsed",
            em is not None and len(em["metrics"]) == 2,
        )
        self.assert_true(
            "P7d: vision alignments parsed",
            em is not None and len(em["vision_alignments"]) == 1,
        )
        self.assert_true(
            "P7e: completeness is full",
            em is not None and em["completeness"] == "full",
        )

        # Entities serving vision
        serving = kg_client.get_entities_serving_vision("protocol_based_di")
        self.assert_true(
            "P7f: one entity serves protocol_based_di",
            len(serving) == 1,
        )
        self.assert_true(
            "P7g: correct entity name",
            len(serving) == 1 and serving[0]["name"] == "service_registry_pattern",
        )

        # Non-existent entity
        missing = kg_client.get_entity_with_metadata("nonexistent")
        self.assert_true("P7h: missing entity returns None", missing is None)

        return self._build_result(scenario_type="library")
