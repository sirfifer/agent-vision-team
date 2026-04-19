"""Smoke tests for SurrealTrustEngine.

Verifies basic CRUD operations work against an embedded SurrealDB instance.
"""

from __future__ import annotations

import os
import sys

import pytest

# Guard: skip all tests if surrealdb SDK is not installed
pytest.importorskip("surrealdb", reason="surrealdb SDK not installed")

# Ensure the shared avt_db package is importable
_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
_SHARED_DIR = os.path.join(_PROJECT_DIR, "shared")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)


@pytest.fixture()
def trust_engine(tmp_path):
    """Create a SurrealTrustEngine against a temporary DB."""
    # Point the engine at a temp directory so tests are isolated
    old_project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    os.environ["CLAUDE_PROJECT_DIR"] = str(tmp_path)

    # Patch the module-level _PROJECT_DIR before import
    import collab_quality.surreal_trust_engine as mod
    orig_project_dir = mod._PROJECT_DIR
    mod._PROJECT_DIR = str(tmp_path)

    try:
        from collab_quality.surreal_trust_engine import SurrealTrustEngine
        engine = SurrealTrustEngine(db_path=".avt/avt.db")
        yield engine
    finally:
        mod._PROJECT_DIR = orig_project_dir
        if old_project_dir is not None:
            os.environ["CLAUDE_PROJECT_DIR"] = old_project_dir
        else:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)


class TestRecordFinding:
    def test_record_new_finding(self, trust_engine):
        result = trust_engine.record_finding("f1", "ruff", "warning", "AuthService", "Unused import")
        assert result is True

    def test_duplicate_finding_returns_false(self, trust_engine):
        trust_engine.record_finding("f1", "ruff", "warning", "AuthService", "Unused import")
        result = trust_engine.record_finding("f1", "ruff", "warning", "AuthService", "Unused import")
        assert result is False

    def test_finding_with_none_component(self, trust_engine):
        result = trust_engine.record_finding("f2", "mypy", "error", None, "Type error")
        assert result is True


class TestTrustDecision:
    def test_default_decision_is_block(self, trust_engine):
        decision = trust_engine.get_trust_decision("nonexistent")
        assert decision["decision"] == "BLOCK"

    def test_dismissed_finding_returns_track(self, trust_engine):
        trust_engine.record_finding("f1", "ruff", "warning", "AuthService", "Unused import")
        trust_engine.record_dismissal("f1", "False positive", "human")
        decision = trust_engine.get_trust_decision("f1")
        assert decision["decision"] == "TRACK"
        assert "human" in decision["rationale"]


class TestDismissal:
    def test_record_dismissal(self, trust_engine):
        trust_engine.record_finding("f1", "ruff", "warning", "AuthService", "Unused import")
        result = trust_engine.record_dismissal("f1", "False positive", "human")
        assert result is True

    def test_empty_justification_rejected(self, trust_engine):
        result = trust_engine.record_dismissal("f1", "  ", "human")
        assert result is False

    def test_dismissal_history(self, trust_engine):
        trust_engine.record_finding("f1", "ruff", "warning", "AuthService", "Unused import")
        trust_engine.record_dismissal("f1", "False positive", "human")
        trust_engine.record_dismissal("f1", "Confirmed false positive", "reviewer")

        history = trust_engine.get_dismissal_history("f1")
        assert len(history) == 2
        assert history[0]["dismissed_by"] in ("human", "reviewer")


class TestGetFindings:
    def test_get_all_findings(self, trust_engine):
        trust_engine.record_finding("f1", "ruff", "warning", "Svc", "desc1")
        trust_engine.record_finding("f2", "mypy", "error", "Svc", "desc2")
        findings = trust_engine.get_all_findings()
        assert len(findings) == 2

    def test_filter_by_status(self, trust_engine):
        trust_engine.record_finding("f1", "ruff", "warning", "Svc", "desc1")
        trust_engine.record_finding("f2", "mypy", "error", "Svc", "desc2")
        trust_engine.record_dismissal("f1", "OK", "human")

        open_findings = trust_engine.get_all_findings(status="open")
        assert len(open_findings) == 1
        assert open_findings[0]["id"] == "f2"

        dismissed = trust_engine.get_all_findings(status="dismissed")
        assert len(dismissed) == 1
        assert dismissed[0]["id"] == "f1"

    def test_unresolved_findings_severity_filter(self, trust_engine):
        trust_engine.record_finding("f1", "ruff", "critical", "Svc", "Critical issue")
        trust_engine.record_finding("f2", "ruff", "high", "Svc", "High issue")
        trust_engine.record_finding("f3", "ruff", "low", "Svc", "Low issue")

        # Only critical and high
        unresolved = trust_engine.get_unresolved_findings(min_severity="high")
        ids = [f["id"] for f in unresolved]
        assert "f1" in ids
        assert "f2" in ids
        assert "f3" not in ids

        # Only critical
        unresolved = trust_engine.get_unresolved_findings(min_severity="critical")
        ids = [f["id"] for f in unresolved]
        assert "f1" in ids
        assert "f2" not in ids
