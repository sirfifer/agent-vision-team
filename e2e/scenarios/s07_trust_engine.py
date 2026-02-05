"""S07 -- Trust engine finding lifecycle.

Tests the TrustEngine from the quality server: recording findings,
dismissing them with justification, verifying trust decisions change,
and checking dismissal audit trail.

Scenario type: positive.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "knowledge-graph"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "governance"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "quality"))

from collab_quality.trust_engine import TrustEngine
from collab_quality.models import TrustDecision

from .base import BaseScenario, ScenarioResult


class S07TrustEngine(BaseScenario):
    """Assert that the trust engine tracks findings and dismissals correctly."""

    name = "s07-trust-engine"
    isolation_mode = "library"

    def run(self, **kwargs: Any) -> ScenarioResult:
        db_path = self.workspace / "s07-trust-engine.db"
        engine = TrustEngine(db_path=str(db_path))

        component = self.project.components[0]

        # -- Record a new finding -------------------------------------------
        finding_id = "LINT-S07-001"
        recorded = engine.record_finding(
            finding_id=finding_id,
            tool="ruff",
            severity="warning",
            component=component,
            description=f"Unused import in {component}",
        )

        self.assert_true(
            "finding recorded successfully",
            recorded,
        )

        # -- Default trust decision is BLOCK --------------------------------
        decision = engine.get_trust_decision(finding_id)

        self.assert_equal(
            "default trust decision is BLOCK",
            decision["decision"],
            TrustDecision.BLOCK.value,
        )

        # -- Duplicate recording is rejected --------------------------------
        duplicate = engine.record_finding(
            finding_id=finding_id,
            tool="ruff",
            severity="warning",
            component=component,
            description="Duplicate record attempt",
        )

        self.assert_true(
            "duplicate finding recording returns False",
            not duplicate,
            expected=False,
            actual=duplicate,
        )

        # -- Dismissal without justification is rejected --------------------
        empty_dismiss = engine.record_dismissal(
            finding_id=finding_id,
            justification="   ",
            dismissed_by="tech_lead",
        )

        self.assert_true(
            "empty justification dismissal rejected",
            not empty_dismiss,
            expected=False,
            actual=empty_dismiss,
        )

        # -- Dismiss with valid justification -------------------------------
        dismissed = engine.record_dismissal(
            finding_id=finding_id,
            justification="Import is used by plugin loader at runtime",
            dismissed_by="tech_lead",
        )

        self.assert_true(
            "dismissal with justification succeeds",
            dismissed,
        )

        # -- Trust decision changes to TRACK after dismissal ----------------
        post_dismiss_decision = engine.get_trust_decision(finding_id)

        self.assert_equal(
            "trust decision after dismissal is TRACK",
            post_dismiss_decision["decision"],
            TrustDecision.TRACK.value,
        )

        self.assert_contains(
            "rationale mentions the dismisser",
            post_dismiss_decision["rationale"],
            "tech_lead",
        )

        # -- Dismissal audit trail ------------------------------------------
        history = engine.get_dismissal_history(finding_id)

        self.assert_equal(
            "one dismissal in history",
            len(history),
            1,
        )

        self.assert_equal(
            "dismissal history records correct dismisser",
            history[0]["dismissed_by"],
            "tech_lead",
        )

        self.assert_contains(
            "dismissal history records justification",
            history[0]["justification"],
            "plugin loader",
        )

        # -- Record a second finding and verify all-findings query ----------
        finding_id_2 = "LINT-S07-002"
        engine.record_finding(
            finding_id=finding_id_2,
            tool="eslint",
            severity="error",
            component=component,
            description="Missing return type annotation",
        )

        all_findings = engine.get_all_findings()
        self.assert_equal(
            "two total findings recorded",
            len(all_findings),
            2,
        )

        open_findings = engine.get_all_findings(status="open")
        self.assert_equal(
            "one open finding (second one)",
            len(open_findings),
            1,
        )

        dismissed_findings = engine.get_all_findings(status="dismissed")
        self.assert_equal(
            "one dismissed finding (first one)",
            len(dismissed_findings),
            1,
        )

        return self._build_result(scenario_type="positive")
