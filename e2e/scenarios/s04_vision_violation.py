"""S04 -- Vision tier violation enforcement.

Verifies that vision-tier entities in the Knowledge Graph are immutable
by agents and can only be modified by human callers.

Scenario type: negative (agent write blocked) + positive (human write allowed).
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "knowledge-graph"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "governance"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "quality"))

from collab_kg.graph import KnowledgeGraph

from .base import BaseScenario, ScenarioResult


class S04VisionViolation(BaseScenario):
    """Assert that agents cannot modify vision-tier KG entities."""

    name = "s04-vision-violation"
    isolation_mode = "library"

    def run(self, **kwargs: Any) -> ScenarioResult:
        # -- Setup: create a KG seeded with a vision standard ----------------
        vision_std = self.project.vision_standards[0]
        kg = KnowledgeGraph(storage_path=str(self.project.kg_path))

        # Verify the vision entity was loaded from the generated KG
        entity = kg.get_entity(vision_std["name"])
        self.assert_true(
            "vision entity exists in KG",
            entity is not None,
            expected="entity present",
            actual="present" if entity is not None else "missing",
        )

        # -- Negative test: agent attempts to add observation to vision entity
        added, error = kg.add_observations(
            entity_name=vision_std["name"],
            observations=["Agent-injected conflicting observation"],
            caller_role="agent",
            change_approved=False,
        )

        self.assert_equal(
            "agent observation count is 0 (blocked)",
            added,
            0,
        )

        self.assert_true(
            "error message returned for agent write",
            error is not None,
            expected="error message present",
            actual="present" if error is not None else "missing",
        )

        self.assert_contains(
            "error mentions vision or immutable",
            (error or "").lower(),
            "vision",
        )

        # -- Negative test: agent attempts to delete observations from vision entity
        deleted, del_error = kg.delete_observations(
            entity_name=vision_std["name"],
            observations=[vision_std["statement"]],
            caller_role="agent",
            change_approved=False,
        )

        self.assert_equal(
            "agent deletion count is 0 (blocked)",
            deleted,
            0,
        )

        self.assert_true(
            "error message returned for agent delete",
            del_error is not None,
            expected="error message present",
            actual="present" if del_error is not None else "missing",
        )

        # -- Positive control: human CAN modify the vision entity -----------
        added_human, human_error = kg.add_observations(
            entity_name=vision_std["name"],
            observations=["Human-approved clarification"],
            caller_role="human",
            change_approved=False,
        )

        self.assert_equal(
            "human observation count is 1 (allowed)",
            added_human,
            1,
        )

        self.assert_true(
            "no error for human write",
            human_error is None,
            expected="no error",
            actual=human_error,
        )

        # -- Verify the entity now has the human observation -----------------
        updated_entity = kg.get_entity(vision_std["name"])
        self.assert_true(
            "entity still exists after human modification",
            updated_entity is not None,
        )

        if updated_entity is not None:
            self.assert_contains(
                "human observation present in entity",
                updated_entity.observations,
                "Human-approved clarification",
            )

        return self._build_result(scenario_type="mixed")
