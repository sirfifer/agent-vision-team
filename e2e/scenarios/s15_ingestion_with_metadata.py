"""Scenario 15 -- Architecture Ingestion with Intent Metadata.

Tests that the document ingestion pipeline correctly extracts structured
intent, metrics, and vision alignment sections from architecture documents
and produces KG entities with correct metadata observations and completeness
tracking.

The scenario is fully self-contained: it creates temporary markdown files
and an isolated JSONL storage file inside ``self.workspace``.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_KG_LIB = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "knowledge-graph"
if str(_KG_LIB) not in sys.path:
    sys.path.insert(0, str(_KG_LIB))

from collab_kg.graph import KnowledgeGraph  # noqa: E402
from collab_kg.ingestion import ingest_folder, parse_document  # noqa: E402
from collab_kg.metadata import (  # noqa: E402
    get_intent,
    get_metadata_completeness,
    get_outcome_metrics,
    get_vision_alignments,
)

from e2e.scenarios.base import BaseScenario, ScenarioResult  # noqa: E402


class S15IngestionWithMetadata(BaseScenario):
    """E2E scenario exercising ingestion of architecture docs with structured metadata."""

    name = "s15_ingestion_with_metadata"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _kg(self) -> KnowledgeGraph:
        storage_path = str(self.workspace / "kg-ingestion-metadata-test.jsonl")
        return KnowledgeGraph(storage_path=storage_path)

    def _write_doc(self, name: str, content: str) -> Path:
        """Write a markdown document to the docs folder."""
        docs_dir = self.workspace / "docs" / "architecture"
        docs_dir.mkdir(parents=True, exist_ok=True)
        doc_path = docs_dir / f"{name}.md"
        doc_path.write_text(textwrap.dedent(content), encoding="utf-8")
        return doc_path

    # ------------------------------------------------------------------
    # Scenario
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:
        kg = self._kg()

        # ==============================================================
        # PART 1: parse_document extracts intent/metrics/vision
        # ==============================================================

        full_doc_path = self._write_doc("service-registry", """\
            # Service Registry Pattern

            ## Type

            pattern

            ## Description

            Central registry for service lookup and lifecycle management.
            All services register at startup and are resolved through the registry.

            ## Intent

            Enable any component to be tested in isolation without real dependencies
            by providing a single point of service resolution that can be swapped for stubs.

            ## Metrics

            - test_isolation_time|< 500ms per test|847ms average
            - stub_coverage|100% of services have stub implementations|72%

            ## Vision Alignment

            - protocol_based_di|Services are swappable via protocol-based interfaces
            - no_singletons|Registry instance is injected, never accessed globally

            ## Usage

            Register services at app startup. Resolve via the registry protocol.
        """)

        entity = parse_document(full_doc_path, "architecture")
        self.assert_true(
            "P1: parse_document returns entity for full architecture doc",
            entity is not None,
        )

        obs = entity["observations"]

        # Intent extraction
        intent = get_intent(obs)
        self.assert_true(
            "P1b: intent extracted from document",
            intent is not None,
        )
        self.assert_true(
            "P1c: intent contains 'isolation'",
            intent is not None and "isolation" in intent.lower(),
        )

        # Metrics extraction
        metrics = get_outcome_metrics(obs)
        self.assert_true(
            "P1f: two metrics extracted",
            len(metrics) == 2,
        )
        self.assert_true(
            "P1g: first metric is test_isolation_time",
            len(metrics) >= 1 and metrics[0]["name"] == "test_isolation_time",
        )
        self.assert_true(
            "P1h: first metric has baseline 847ms average",
            len(metrics) >= 1 and "847ms" in metrics[0]["baseline"],
        )

        # Vision alignment extraction
        alignments = get_vision_alignments(obs)
        self.assert_true(
            "P1i: two vision alignments extracted",
            len(alignments) == 2,
        )
        self.assert_true(
            "P1j: first alignment references protocol_based_di",
            len(alignments) >= 1 and alignments[0]["vision_entity"] == "protocol_based_di",
        )

        # Metadata completeness
        completeness = get_metadata_completeness(obs)
        self.assert_true(
            "P1k: full doc has 'full' metadata completeness",
            completeness == "full",
        )
        self.assert_true(
            "P1l: metadata_completeness observation present",
            any(o == "metadata_completeness: full" for o in obs),
        )

        # ==============================================================
        # PART 2: Partial metadata (no vision alignment)
        # ==============================================================

        partial_doc_path = self._write_doc("cache-strategy", """\
            # Cache Strategy

            ## Type

            pattern

            ## Description

            Application-level caching strategy for frequently accessed data.

            ## Intent

            Reduce database load and improve response times for read-heavy endpoints.

            ## Usage

            Use the cache decorator on repository methods.
        """)

        partial_entity = parse_document(partial_doc_path, "architecture")
        self.assert_true(
            "P2: parse_document returns entity for partial doc",
            partial_entity is not None,
        )

        partial_obs = partial_entity["observations"]
        self.assert_true(
            "P2b: intent extracted from partial doc",
            get_intent(partial_obs) is not None,
        )
        self.assert_true(
            "P2d: no vision alignments in partial doc",
            len(get_vision_alignments(partial_obs)) == 0,
        )
        self.assert_true(
            "P2e: partial doc has 'partial' completeness",
            get_metadata_completeness(partial_obs) == "partial",
        )

        # ==============================================================
        # PART 3: No metadata (legacy-style doc)
        # ==============================================================

        legacy_doc_path = self._write_doc("logging-standard", """\
            # Logging Standard

            ## Type

            standard

            ## Description

            All services must use structured JSON logging via the shared logger.

            ## Rationale

            Consistent log formatting enables centralized log aggregation.

            ## Usage

            Import the shared logger and use structured fields.
        """)

        legacy_entity = parse_document(legacy_doc_path, "architecture")
        self.assert_true(
            "P3: parse_document returns entity for legacy doc",
            legacy_entity is not None,
        )

        legacy_obs = legacy_entity["observations"]
        self.assert_true(
            "P3b: no intent in legacy doc",
            get_intent(legacy_obs) is None,
        )
        self.assert_true(
            "P3d: legacy doc has 'none' completeness",
            get_metadata_completeness(legacy_obs) == "none",
        )

        # ==============================================================
        # PART 4: Folder ingestion with mixed metadata levels
        # ==============================================================

        docs_dir = str(self.workspace / "docs" / "architecture")
        result = ingest_folder(kg, docs_dir, "architecture")

        self.assert_true(
            "P4: ingest_folder ingests 3 documents",
            result["ingested"] == 3,
        )
        self.assert_true(
            "P4b: no ingestion errors",
            len(result["errors"]) == 0,
        )
        self.assert_true(
            "P4c: 3 entity names returned",
            len(result["entities"]) == 3,
        )

        # Verify entities in KG
        sr = kg.get_entity("service_registry_pattern")
        self.assert_true(
            "P4d: service_registry_pattern entity exists in KG",
            sr is not None,
        )
        self.assert_true(
            "P4e: KG entity has intent observation",
            sr is not None and any(o.startswith("intent: ") for o in sr.observations),
        )
        self.assert_true(
            "P4g: KG entity has outcome_metric observations",
            sr is not None and sum(1 for o in sr.observations if o.startswith("outcome_metric: ")) == 2,
        )
        self.assert_true(
            "P4h: KG entity has vision_alignment observations",
            sr is not None and sum(1 for o in sr.observations if o.startswith("vision_alignment: ")) == 2,
        )
        self.assert_true(
            "P4i: KG entity has metadata_completeness: full",
            sr is not None and "metadata_completeness: full" in sr.observations,
        )

        # Verify partial entity in KG
        cs = kg.get_entity("cache_strategy")
        self.assert_true(
            "P4j: cache_strategy entity exists in KG",
            cs is not None,
        )
        self.assert_true(
            "P4k: cache_strategy has partial completeness",
            cs is not None and "metadata_completeness: partial" in cs.observations,
        )

        # Verify legacy entity in KG
        ls = kg.get_entity("logging_standard")
        self.assert_true(
            "P4l: logging_standard entity exists in KG",
            ls is not None,
        )
        self.assert_true(
            "P4m: logging_standard has none completeness",
            ls is not None and "metadata_completeness: none" in ls.observations,
        )

        # ==============================================================
        # PART 5: Vision doc ingestion (no metadata fields expected)
        # ==============================================================

        vision_dir = self.workspace / "docs" / "vision"
        vision_dir.mkdir(parents=True, exist_ok=True)
        (vision_dir / "di-standard.md").write_text(textwrap.dedent("""\
            # Protocol-Based DI

            ## Statement

            All services use protocol-based dependency injection.

            ## Rationale

            Enables testability and loose coupling across all components.
        """), encoding="utf-8")

        vision_result = ingest_folder(kg, str(vision_dir), "vision")
        self.assert_true(
            "P5: vision doc ingested",
            vision_result["ingested"] == 1,
        )

        vi = kg.get_entity("protocol_based_di")
        self.assert_true(
            "P5b: vision entity exists",
            vi is not None,
        )
        self.assert_true(
            "P5c: vision entity has no metadata_completeness (not architecture)",
            vi is not None and not any(o.startswith("metadata_completeness:") for o in vi.observations),
        )

        # ==============================================================
        # PART 6: Re-ingestion preserves updated metadata structure
        # ==============================================================

        # Update the service-registry doc (add a third metric)
        self._write_doc("service-registry", """\
            # Service Registry Pattern

            ## Type

            pattern

            ## Description

            Central registry for service lookup and lifecycle management.

            ## Intent

            Enable any component to be tested in isolation without real dependencies.

            ## Metrics

            - test_isolation_time|< 500ms per test|847ms average
            - stub_coverage|100% of services have stub implementations|72%
            - registry_init_time|< 100ms startup|not measured

            ## Vision Alignment

            - protocol_based_di|Services are swappable via protocol-based interfaces

            ## Usage

            Register services at app startup.
        """)

        # Re-ingest
        result2 = ingest_folder(kg, docs_dir, "architecture")
        self.assert_true(
            "P6: re-ingestion succeeds",
            result2["ingested"] == 3,
        )

        sr2 = kg.get_entity("service_registry_pattern")
        self.assert_true(
            "P6b: re-ingested entity has 3 metrics",
            sr2 is not None and sum(1 for o in sr2.observations if o.startswith("outcome_metric: ")) == 3,
        )
        self.assert_true(
            "P6c: re-ingested entity now has 1 vision alignment (was 2)",
            sr2 is not None and sum(1 for o in sr2.observations if o.startswith("vision_alignment: ")) == 1,
        )
        self.assert_true(
            "P6d: re-ingested entity still full completeness",
            sr2 is not None and "metadata_completeness: full" in sr2.observations,
        )

        return self._build_result(scenario_type="library")
