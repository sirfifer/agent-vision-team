"""Scenario 01 — Knowledge Graph Tier Protection.

Tests CRUD operations across all three protection tiers and verifies that
the tier enforcement rules hold:

  - Vision tier: immutable by agents, only humans can modify/delete.
  - Architecture tier: agents require change_approved=True to modify;
    agents cannot delete.
  - Quality tier: any agent can read, write, and delete freely.

The scenario is fully self-contained: it creates an isolated JSONL storage
file inside `self.workspace` so that parallel runs never collide.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — import the KG library directly from the mono-repo
# ---------------------------------------------------------------------------
_KG_LIB = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "knowledge-graph"
if str(_KG_LIB) not in sys.path:
    sys.path.insert(0, str(_KG_LIB))

from collab_kg.graph import KnowledgeGraph  # noqa: E402

from e2e.scenarios.base import BaseScenario, ScenarioResult  # noqa: E402


class KGTierProtectionScenario(BaseScenario):
    """E2E scenario exercising Knowledge Graph tier protection enforcement."""

    name = "s01_kg_tier_protection"
    isolation_mode = "library"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _kg(self) -> KnowledgeGraph:
        """Return a KnowledgeGraph backed by an isolated file in the workspace."""
        storage_path = str(self.workspace / "kg-tier-test.jsonl")
        return KnowledgeGraph(storage_path=storage_path)

    def _seed_entities(self, kg: KnowledgeGraph) -> None:
        """Seed the graph with one entity at each tier using project data."""
        # Use project-generated vision standards and architecture patterns
        # when available, otherwise fall back to sensible defaults.
        vision_obs = "protection_tier: vision"
        arch_obs = "protection_tier: architecture"
        quality_obs = "protection_tier: quality"

        project = self.project
        vision_detail = (
            project.vision_standards[0]["statement"]
            if hasattr(project, "vision_standards") and project.vision_standards
            else "All services use protocol-based DI"
        )
        arch_detail = (
            project.architecture_patterns[0]["description"]
            if hasattr(project, "architecture_patterns") and project.architecture_patterns
            else "ServiceRegistry pattern"
        )
        component = project.components[0] if hasattr(project, "components") and project.components else "AuthService"

        kg.create_entities(
            [
                {
                    "name": "VisionStandard_DI",
                    "entityType": "vision_standard",
                    "observations": [vision_obs, vision_detail],
                },
                {
                    "name": "ArchPattern_ServiceRegistry",
                    "entityType": "pattern",
                    "observations": [arch_obs, arch_detail],
                },
                {
                    "name": f"QualityNote_{component}",
                    "entityType": "component",
                    "observations": [quality_obs, f"{component} needs error handling review"],
                },
            ]
        )

    # ------------------------------------------------------------------
    # Scenario entry point
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:
        kg = self._kg()
        self._seed_entities(kg)

        component = (
            self.project.components[0]
            if hasattr(self.project, "components") and self.project.components
            else "AuthService"
        )

        # ==============================================================
        # POSITIVE CASES
        # ==============================================================

        # 1. Create entities at all three tiers — succeeds
        entity_count_before = len(kg.search_nodes(""))
        # We already seeded 3 entities; verify they exist.
        self.assert_true(
            "P1: Create entities at all three tiers succeeds",
            entity_count_before >= 3,
            expected=">=3 entities",
            actual=entity_count_before,
        )

        # 2. Agent writes to quality-tier entity — succeeds
        added, err = kg.add_observations(
            f"QualityNote_{component}",
            ["Agent added quality note"],
            caller_role="agent",
            change_approved=False,
        )
        self.assert_true(
            "P2: Agent writes to quality-tier entity succeeds",
            added > 0 and err is None,
            expected="observation added, no error",
            actual=f"added={added}, err={err}",
        )

        # 3. Agent writes to architecture-tier WITH approval — succeeds
        added, err = kg.add_observations(
            "ArchPattern_ServiceRegistry",
            ["Agent note: verified in code review"],
            caller_role="agent",
            change_approved=True,
        )
        self.assert_true(
            "P3: Agent writes to arch-tier WITH approval succeeds",
            added > 0 and err is None,
            expected="observation added, no error",
            actual=f"added={added}, err={err}",
        )

        # 4. Search finds created entities
        results = kg.search_nodes("ServiceRegistry")
        found_names = [r.name for r in results]
        self.assert_contains(
            "P4: Search finds architecture entity",
            found_names,
            "ArchPattern_ServiceRegistry",
        )

        # 5. get_entities_by_tier returns correct results
        vision_entities = kg.get_entities_by_tier("vision")
        vision_names = [e.name for e in vision_entities]
        self.assert_contains(
            "P5: get_entities_by_tier('vision') returns vision entity",
            vision_names,
            "VisionStandard_DI",
        )
        arch_entities = kg.get_entities_by_tier("architecture")
        arch_names = [e.name for e in arch_entities]
        self.assert_contains(
            "P5b: get_entities_by_tier('architecture') returns arch entity",
            arch_names,
            "ArchPattern_ServiceRegistry",
        )

        # 6. Human can modify vision entities
        added, err = kg.add_observations(
            "VisionStandard_DI",
            ["Human updated vision standard"],
            caller_role="human",
            change_approved=False,
        )
        self.assert_true(
            "P6: Human can modify vision entities",
            added > 0 and err is None,
            expected="observation added, no error",
            actual=f"added={added}, err={err}",
        )

        # ==============================================================
        # NEGATIVE CASES
        # ==============================================================

        # 7. Agent cannot write to vision-tier entity
        added, err = kg.add_observations(
            "VisionStandard_DI",
            ["Agent tries to modify vision"],
            caller_role="agent",
            change_approved=False,
        )
        self.assert_true(
            "N7: Agent cannot write to vision-tier entity",
            added == 0 and err is not None,
            expected="blocked (added=0, error message)",
            actual=f"added={added}, err={err}",
        )
        if err:
            self.assert_contains(
                "N7b: Error message mentions 'immutable' or 'Vision'",
                err,
                "Vision",
            )

        # 8. Agent cannot write to architecture-tier WITHOUT approval
        added, err = kg.add_observations(
            "ArchPattern_ServiceRegistry",
            ["Agent tries unapproved arch write"],
            caller_role="agent",
            change_approved=False,
        )
        self.assert_true(
            "N8: Agent cannot write to arch-tier WITHOUT approval",
            added == 0 and err is not None,
            expected="blocked (added=0, error message)",
            actual=f"added={added}, err={err}",
        )
        if err:
            self.assert_contains(
                "N8b: Error message mentions 'Architecture' or 'approved'",
                err,
                "Architecture",
            )

        # 9. Agent cannot delete vision-tier entity
        deleted, err = kg.delete_entity(
            "VisionStandard_DI",
            caller_role="agent",
        )
        self.assert_true(
            "N9: Agent cannot delete vision-tier entity",
            deleted is False and err is not None,
            expected="blocked (deleted=False, error message)",
            actual=f"deleted={deleted}, err={err}",
        )

        # 10. Agent cannot delete architecture-tier entity
        deleted, err = kg.delete_entity(
            "ArchPattern_ServiceRegistry",
            caller_role="agent",
        )
        self.assert_true(
            "N10: Agent cannot delete arch-tier entity",
            deleted is False and err is not None,
            expected="blocked (deleted=False, error message)",
            actual=f"deleted={deleted}, err={err}",
        )

        return self._build_result(scenario_type="mixed")
