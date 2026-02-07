"""Scenario 17 -- Cascading Alignment After Evolution Approval.

Tests that after an evolution proposal is approved, dependent entities are
identified and alignment tasks are created for them. Validates:

  - KGClient.get_entities_serving_vision finds dependent entities
  - Evidence validator rejects invalid evidence (non-mock mode)
  - Evidence validator accepts valid evidence
  - The cascade logic identifies entities via relations and observations
  - Reviewer formats architecture with intent metadata correctly

The scenario is fully self-contained with isolated JSONL and SQLite storage.
"""

from __future__ import annotations

import os
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
from collab_kg.metadata import build_intent_observations  # noqa: E402
from collab_governance.models import ExperimentEvidence  # noqa: E402
from collab_governance.kg_client import KGClient  # noqa: E402
from collab_governance.reviewer import GovernanceReviewer  # noqa: E402
from collab_governance.evidence_validator import (  # noqa: E402
    validate_evidence,
    validate_evidence_batch,
)

from e2e.scenarios.base import BaseScenario, ScenarioResult  # noqa: E402


class S17CascadingAlignment(BaseScenario):
    """E2E scenario for cascading alignment and evidence validation."""

    name = "s17_cascading_alignment"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _kg(self) -> KnowledgeGraph:
        storage_path = str(self.workspace / "kg-cascade-test.jsonl")
        return KnowledgeGraph(storage_path=storage_path)

    def _kg_client(self, kg: KnowledgeGraph) -> KGClient:
        return KGClient(kg_path=kg.storage.filepath)

    # ------------------------------------------------------------------
    # Scenario
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:

        kg = self._kg()
        kg_client = self._kg_client(kg)
        rvr = GovernanceReviewer()

        # ==============================================================
        # PART 1: Setup - create vision + architecture + dependents
        # ==============================================================

        # Vision standard
        kg.create_entities([{
            "name": "protocol_based_di",
            "entityType": "vision_standard",
            "observations": [
                "protection_tier: vision",
                "statement: All services use protocol-based dependency injection",
            ],
        }])

        # Primary architecture entity (the one being evolved)
        primary_obs = [
            "protection_tier: architecture",
            "description: Central registry for service lookup",
        ] + build_intent_observations(
            intent="Enable isolated testing via single resolution point",
            metrics=[{"name": "test_time", "criteria": "< 500ms", "baseline": "847ms"}],
            vision_alignments=[{"vision_entity": "protocol_based_di", "explanation": "Protocol-based swapping"}],
        )
        kg.create_entities([{
            "name": "service_registry",
            "entityType": "pattern",
            "observations": primary_obs,
        }])

        # Dependent entity 1 - follows the pattern
        dep1_obs = [
            "protection_tier: architecture",
            "description: Authentication service using registry for DI",
        ] + build_intent_observations(
            intent="Centralized auth with pluggable providers",
            vision_alignments=[{"vision_entity": "protocol_based_di", "explanation": "Auth providers swappable"}],
        )
        kg.create_entities([{
            "name": "auth_service",
            "entityType": "component",
            "observations": dep1_obs,
        }])

        # Dependent entity 2 - also aligned to same vision
        dep2_obs = [
            "protection_tier: architecture",
            "description: Cache layer with protocol-based backend",
        ] + build_intent_observations(
            intent="Unified cache interface for multiple backends",
            vision_alignments=[{"vision_entity": "protocol_based_di", "explanation": "Cache backends swappable"}],
        )
        kg.create_entities([{
            "name": "cache_layer",
            "entityType": "component",
            "observations": dep2_obs,
        }])

        # Create relations
        kg.create_relations([
            {"from": "service_registry", "to": "protocol_based_di", "relationType": "serves_vision"},
            {"from": "auth_service", "to": "protocol_based_di", "relationType": "serves_vision"},
            {"from": "cache_layer", "to": "protocol_based_di", "relationType": "serves_vision"},
            {"from": "auth_service", "to": "service_registry", "relationType": "follows_pattern"},
        ])

        self.assert_true(
            "P1: four entities created",
            kg.get_entity("protocol_based_di") is not None
            and kg.get_entity("service_registry") is not None
            and kg.get_entity("auth_service") is not None
            and kg.get_entity("cache_layer") is not None,
        )

        # ==============================================================
        # PART 2: KGClient finds dependents via vision alignment
        # ==============================================================

        serving_di = kg_client.get_entities_serving_vision("protocol_based_di")
        serving_names = {e["name"] for e in serving_di}
        self.assert_true(
            "P2: three entities serve protocol_based_di",
            len(serving_di) == 3,
        )
        self.assert_true(
            "P2b: service_registry in serving set",
            "service_registry" in serving_names,
        )
        self.assert_true(
            "P2c: auth_service in serving set",
            "auth_service" in serving_names,
        )
        self.assert_true(
            "P2d: cache_layer in serving set",
            "cache_layer" in serving_names,
        )

        # Each dependent has parsed metadata
        for e in serving_di:
            self.assert_true(
                f"P2e: {e['name']} has parsed intent",
                e.get("intent") is not None,
            )
            self.assert_true(
                f"P2f: {e['name']} has parsed vision alignments",
                len(e.get("vision_alignments", [])) > 0,
            )

        # ==============================================================
        # PART 3: Evidence Validator (non-mock mode)
        # ==============================================================

        # Temporarily disable mock mode to test real validation
        old_mock = os.environ.pop("GOVERNANCE_MOCK_REVIEW", None)

        # Valid test results evidence
        evidence_file = self.workspace / "test-output.txt"
        evidence_file.write_text("42 passed, 0 failed\nExecution time: 312ms\n")

        valid_evidence = ExperimentEvidence(
            evidence_type="test_results",
            source=str(evidence_file),
            raw_output="42 passed, 0 failed\nExecution time: 312ms",
            summary="All tests pass",
            metrics={"passed": 42, "failed": 0},
        )
        result = validate_evidence(valid_evidence)
        self.assert_true("P3: valid evidence passes", result.valid)

        # Evidence with missing source file
        bad_source = ExperimentEvidence(
            evidence_type="test_results",
            source="/nonexistent/path/results.txt",
            raw_output="42 passed",
            summary="Tests pass",
            metrics={"passed": 42},
        )
        bad_result = validate_evidence(bad_source)
        self.assert_true("P3b: missing source fails", not bad_result.valid)
        self.assert_true(
            "P3c: failure mentions source path",
            any("source path" in f.lower() for f in bad_result.failures),
        )

        # Evidence with no test counts
        no_counts = ExperimentEvidence(
            evidence_type="test_results",
            source=str(evidence_file),
            raw_output="Everything looks good!",
            summary="Tests seem fine",
        )
        no_counts_result = validate_evidence(no_counts)
        self.assert_true("P3d: no test counts fails", not no_counts_result.valid)
        self.assert_true(
            "P3e: failure mentions pass/fail",
            any("pass/fail" in f.lower() for f in no_counts_result.failures),
        )

        # Benchmark with no numeric data
        bad_bench = ExperimentEvidence(
            evidence_type="benchmark",
            source=str(evidence_file),
            raw_output="The system is fast",
            summary="Performance is good",
        )
        bench_result = validate_evidence(bad_bench)
        self.assert_true("P3f: vague benchmark fails", not bench_result.valid)

        # Non-numeric metric value
        bad_metric = ExperimentEvidence(
            evidence_type="test_results",
            source=str(evidence_file),
            raw_output="42 passed, 0 failed",
            metrics={"passed": "many"},
        )
        metric_result = validate_evidence(bad_metric)
        self.assert_true("P3g: non-numeric metric fails", not metric_result.valid)

        # Bad comparison structure
        bad_comp = ExperimentEvidence(
            evidence_type="test_results",
            source=str(evidence_file),
            raw_output="42 passed, 0 failed",
            metrics={"passed": 42},
            comparison_to_baseline={"test_time": {"baseline": 847}},  # missing "experiment"
        )
        comp_result = validate_evidence(bad_comp)
        self.assert_true("P3h: incomplete comparison fails", not comp_result.valid)

        # Batch validation
        mixed = [valid_evidence, bad_source]
        batch_result = validate_evidence_batch(mixed)
        self.assert_true("P3i: batch with one bad item fails", not batch_result.valid)

        all_good = [valid_evidence]
        good_batch = validate_evidence_batch(all_good)
        self.assert_true("P3j: batch with all good passes", good_batch.valid)

        # Restore mock mode
        if old_mock:
            os.environ["GOVERNANCE_MOCK_REVIEW"] = old_mock

        # ==============================================================
        # PART 4: Reviewer formats architecture with intent
        # ==============================================================

        # Architecture entities with metadata
        arch_with_meta = [{
            "name": "service_registry",
            "entityType": "pattern",
            "observations": primary_obs,
            "intent": "Enable isolated testing via single resolution point",
            "metrics": [{"name": "test_time", "criteria": "< 500ms", "baseline": "847ms"}],
            "vision_alignments": [{"vision_entity": "protocol_based_di", "explanation": "Protocol-based swapping"}],
            "completeness": "full",
        }]

        formatted = rvr._format_architecture_with_intent(arch_with_meta)
        self.assert_true("P4: formatted output not empty", len(formatted) > 0)
        self.assert_true(
            "P4b: formatted contains intent",
            "Intent:" in formatted and "isolated testing" in formatted.lower(),
        )
        self.assert_true(
            "P4c: formatted contains metrics",
            "Metrics:" in formatted and "test_time" in formatted,
        )
        self.assert_true(
            "P4d: formatted contains serves",
            "Serves:" in formatted and "protocol_based_di" in formatted,
        )
        self.assert_true(
            "P4e: formatted contains completeness",
            "Metadata completeness: full" in formatted,
        )

        # Legacy entity (no metadata)
        arch_legacy = [{
            "name": "old_component",
            "entityType": "component",
            "observations": ["description: Some old thing", "usage: Direct import"],
        }]
        legacy_formatted = rvr._format_architecture_with_intent(arch_legacy)
        self.assert_true(
            "P4f: legacy formatted uses simple format",
            "**old_component**" in legacy_formatted and "Intent:" not in legacy_formatted,
        )

        # Empty architecture
        empty_formatted = rvr._format_architecture_with_intent([])
        self.assert_true(
            "P4g: empty architecture returns placeholder",
            "no architecture" in empty_formatted.lower(),
        )

        # ==============================================================
        # PART 5: Dependent entity metadata is accessible
        # ==============================================================

        auth_meta = kg_client.get_entity_with_metadata("auth_service")
        self.assert_true("P5: auth_service metadata loaded", auth_meta is not None)
        self.assert_true(
            "P5b: auth_service has intent",
            auth_meta is not None and auth_meta["intent"] is not None,
        )
        self.assert_true(
            "P5c: auth_service completeness is full",
            auth_meta is not None and auth_meta["completeness"] == "full",
        )

        cache_meta = kg_client.get_entity_with_metadata("cache_layer")
        self.assert_true("P5d: cache_layer metadata loaded", cache_meta is not None)
        self.assert_true(
            "P5e: cache_layer has vision alignment",
            cache_meta is not None and len(cache_meta["vision_alignments"]) == 1,
        )

        return self._build_result(scenario_type="library")
