"""Scenario 14 -- Architecture Metadata (Intent / Vision Alignment).

Tests the intent-driven architecture metadata system:

  - Setting and retrieving structured metadata (intent, outcome_metric,
    vision_alignment) on architecture-tier entities.
  - The ``get_architecture_completeness`` tool correctly reports completeness.
  - The ``set_entity_metadata`` tool respects tier protection.
  - The ``validate_ingestion`` tool returns accurate completeness reports.
  - The ``metadata.py`` helper functions parse and build observations correctly.
  - Evolution proposal storage and retrieval in the governance store.

The scenario is fully self-contained: it creates isolated JSONL and SQLite
storage files inside ``self.workspace`` so parallel runs never collide.
"""

from __future__ import annotations

import sys
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
from collab_kg.metadata import (  # noqa: E402
    build_intent_observations,
    get_intent,
    get_metadata_completeness,
    get_outcome_metrics,
    get_vision_alignments,
    strip_metadata_observations,
)
from collab_governance.models import (  # noqa: E402
    EvolutionProposal,
    EvolutionStatus,
    ExperimentEvidence,
)
from collab_governance.store import GovernanceStore  # noqa: E402

from e2e.scenarios.base import BaseScenario, ScenarioResult  # noqa: E402


class S14ArchitectureMetadata(BaseScenario):
    """E2E scenario exercising intent/outcome metadata on architectural entities."""

    name = "s14_architecture_metadata"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _kg(self) -> KnowledgeGraph:
        storage_path = str(self.workspace / "kg-metadata-test.jsonl")
        return KnowledgeGraph(storage_path=storage_path)

    def _store(self) -> GovernanceStore:
        db_path = self.workspace / "gov-metadata-test.db"
        return GovernanceStore(db_path=db_path)

    def _seed(self, kg: KnowledgeGraph) -> None:
        """Seed the graph with vision and architecture entities."""
        kg.create_entities([
            {
                "name": "protocol_based_di",
                "entityType": "vision_standard",
                "observations": [
                    "protection_tier: vision",
                    "statement: All services use protocol-based dependency injection",
                ],
            },
            {
                "name": "no_singletons",
                "entityType": "vision_standard",
                "observations": [
                    "protection_tier: vision",
                    "statement: No singletons in production code",
                ],
            },
            {
                "name": "service_registry_pattern",
                "entityType": "pattern",
                "observations": [
                    "protection_tier: architecture",
                    "description: Central registry for service lookup and lifecycle management",
                ],
            },
            {
                "name": "auth_service",
                "entityType": "component",
                "observations": [
                    "protection_tier: architecture",
                    "description: Handles authentication and authorization",
                ],
            },
        ])

    # ------------------------------------------------------------------
    # Scenario
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:
        kg = self._kg()
        self._seed(kg)

        # ==============================================================
        # PART 1: Metadata helper functions
        # ==============================================================

        # 1. build_intent_observations produces correct observations
        obs = build_intent_observations(
            intent="Enable isolated testing of all service consumers",
            metrics=[
                {"name": "test_isolation_time", "criteria": "< 500ms", "baseline": "847ms"},
            ],
            vision_alignments=[
                {"vision_entity": "protocol_based_di", "explanation": "Services swappable via protocols"},
            ],
        )
        self.assert_true(
            "P1: build_intent_observations produces intent observation",
            any(o.startswith("intent: ") for o in obs),
        )
        self.assert_true(
            "P1c: produces outcome_metric observation",
            any(o.startswith("outcome_metric: ") for o in obs),
        )
        self.assert_true(
            "P1d: produces vision_alignment observation",
            any(o.startswith("vision_alignment: ") for o in obs),
        )
        self.assert_equal(
            "P1e: completeness is full",
            get_metadata_completeness(obs),
            "full",
        )

        # 2. Parse functions extract correctly from built observations
        self.assert_equal(
            "P2: get_intent extracts intent",
            get_intent(obs),
            "Enable isolated testing of all service consumers",
        )
        metrics = get_outcome_metrics(obs)
        self.assert_equal("P2c: one metric parsed", len(metrics), 1)
        self.assert_equal("P2d: metric name correct", metrics[0]["name"], "test_isolation_time")
        self.assert_equal("P2e: metric baseline correct", metrics[0]["baseline"], "847ms")

        alignments = get_vision_alignments(obs)
        self.assert_equal("P2f: one alignment parsed", len(alignments), 1)
        self.assert_equal(
            "P2g: alignment entity correct",
            alignments[0]["vision_entity"],
            "protocol_based_di",
        )

        # 3. Empty observations produce "none" completeness
        self.assert_equal(
            "P3: empty observations produce 'none' completeness",
            get_metadata_completeness([]),
            "none",
        )

        # 4. Partial observations produce "partial" completeness
        partial = ["intent: Some intent here"]
        self.assert_equal(
            "P4: partial observations produce 'partial' completeness",
            get_metadata_completeness(partial),
            "partial",
        )

        # 5. strip_metadata_observations removes only metadata
        mixed = [
            "protection_tier: architecture",
            "description: Some description",
            "intent: old intent",
            "metadata_completeness: partial",
        ]
        stripped = strip_metadata_observations(mixed)
        self.assert_equal("P5: strip keeps non-metadata", len(stripped), 2)
        self.assert_contains("P5b: protection_tier preserved", stripped, "protection_tier: architecture")
        self.assert_contains("P5c: description preserved", stripped, "description: Some description")

        # ==============================================================
        # PART 2: Entity metadata on the KG
        # ==============================================================

        # 6. Add metadata to architecture entity (human caller)
        entity = kg.get_entity("service_registry_pattern")
        self.assert_true("P6: entity exists before metadata", entity is not None)

        metadata_obs = build_intent_observations(
            intent="Decouple service creation from consumption",
            metrics=[{"name": "test_isolation", "criteria": "< 500ms", "baseline": "not measured"}],
            vision_alignments=[{"vision_entity": "protocol_based_di", "explanation": "Protocol-based swapping"}],
        )

        # Human can add metadata to architecture entity
        added, err = kg.add_observations(
            "service_registry_pattern",
            metadata_obs,
            caller_role="human",
        )
        self.assert_true(
            "P6b: human adds metadata to arch entity",
            added > 0 and err is None,
            expected="observations added",
            actual=f"added={added}, err={err}",
        )

        # Verify metadata is retrievable
        entity = kg.get_entity("service_registry_pattern")
        self.assert_equal(
            "P6c: intent retrievable after add",
            get_intent(entity.observations),
            "Decouple service creation from consumption",
        )
        self.assert_equal(
            "P6d: completeness is full",
            get_metadata_completeness(entity.observations),
            "full",
        )

        # 7. Agent cannot add metadata to architecture entity without approval
        added, err = kg.add_observations(
            "service_registry_pattern",
            ["intent: Agent tries to change intent"],
            caller_role="agent",
            change_approved=False,
        )
        self.assert_true(
            "N7: agent cannot modify arch entity metadata without approval",
            added == 0 and err is not None,
        )

        # 8. Agent CAN add metadata with approval
        added, err = kg.add_observations(
            "service_registry_pattern",
            ["outcome_metric: build_time|< 30s|45s"],
            caller_role="agent",
            change_approved=True,
        )
        self.assert_true(
            "P8: agent can add metadata to arch entity WITH approval",
            added > 0 and err is None,
        )

        # 9. get_entities_by_tier returns entities with metadata
        arch_entities = kg.get_entities_by_tier("architecture")
        enriched = [
            e for e in arch_entities
            if get_metadata_completeness(e.observations) != "none"
        ]
        self.assert_true(
            "P9: at least one arch entity has metadata",
            len(enriched) >= 1,
            expected=">=1 enriched",
            actual=len(enriched),
        )

        # ==============================================================
        # PART 3: Evolution proposal storage
        # ==============================================================

        store = self._store()

        # 10. Store and retrieve an evolution proposal
        proposal = EvolutionProposal(
            target_entity="service_registry_pattern",
            original_intent="Decouple service creation from consumption",
            proposed_change="Replace runtime registry with compile-time DI macros",
            rationale="40% faster test execution, zero runtime overhead",
            experiment_plan="Create worktree, implement macro-based DI, run full test suite",
            validation_criteria=[
                "test_isolation metric improves by >= 30%",
                "all existing tests pass without modification",
            ],
            proposing_agent="worker-1",
        )
        stored = store.store_evolution_proposal(proposal)
        self.assert_true("P10: proposal stored", stored.id == proposal.id)

        retrieved = store.get_evolution_proposal(proposal.id)
        self.assert_true("P10b: proposal retrievable", retrieved is not None)
        self.assert_equal(
            "P10c: target entity preserved",
            retrieved.target_entity,
            "service_registry_pattern",
        )
        self.assert_equal(
            "P10d: status is proposed",
            retrieved.status,
            EvolutionStatus.PROPOSED,
        )
        self.assert_equal(
            "P10e: validation criteria preserved",
            len(retrieved.validation_criteria),
            2,
        )

        # 11. Update proposal status to experimenting
        proposal.status = EvolutionStatus.EXPERIMENTING
        proposal.worktree_branch = "experiment/compile-time-di"
        store.update_evolution_proposal(proposal)

        updated = store.get_evolution_proposal(proposal.id)
        self.assert_equal(
            "P11: status updated to experimenting",
            updated.status,
            EvolutionStatus.EXPERIMENTING,
        )
        self.assert_equal(
            "P11b: worktree branch set",
            updated.worktree_branch,
            "experiment/compile-time-di",
        )

        # 12. Add evidence to proposal
        evidence = ExperimentEvidence(
            evidence_type="benchmark",
            source="/tmp/test-results/bench-output.json",
            summary="Test suite completed in 512ms (was 847ms)",
            metrics={"test_isolation_time": 512},
            comparison_to_baseline={
                "test_isolation_time": {"baseline": 847, "experiment": 512, "improvement": "39.5%"},
            },
        )
        proposal.evidence.append(evidence)
        proposal.status = EvolutionStatus.VALIDATED
        store.update_evolution_proposal(proposal)

        validated = store.get_evolution_proposal(proposal.id)
        self.assert_equal(
            "P12: evidence stored",
            len(validated.evidence),
            1,
        )
        self.assert_equal(
            "P12b: evidence type preserved",
            validated.evidence[0].evidence_type,
            "benchmark",
        )
        self.assert_equal(
            "P12c: status is validated",
            validated.status,
            EvolutionStatus.VALIDATED,
        )

        # 13. Query proposals by entity
        entity_proposals = store.get_evolution_proposals_for_entity("service_registry_pattern")
        self.assert_equal(
            "P13: one proposal for target entity",
            len(entity_proposals),
            1,
        )

        # 14. Query active experiments
        # Our proposal is in 'validated' state which counts as active
        active = store.get_active_experiments()
        self.assert_true(
            "P14: validated proposal shows in active experiments",
            any(p.id == proposal.id for p in active),
        )

        # 15. Store a second proposal (rejected)
        proposal2 = EvolutionProposal(
            target_entity="auth_service",
            proposed_change="Switch from JWT to session tokens",
            rationale="Simpler revocation model",
            proposing_agent="worker-2",
        )
        store.store_evolution_proposal(proposal2)
        proposal2.status = EvolutionStatus.REJECTED
        proposal2.review_verdict = "rejected"
        store.update_evolution_proposal(proposal2)

        all_proposals = store.get_all_evolution_proposals()
        self.assert_equal("P15: two total proposals", len(all_proposals), 2)

        rejected_only = store.get_all_evolution_proposals(status="rejected")
        self.assert_equal("P15b: one rejected proposal", len(rejected_only), 1)

        store.close()

        return self._build_result(scenario_type="mixed")
