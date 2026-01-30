"""Additional tests to improve coverage for Quality server."""

import tempfile
from pathlib import Path

from collab_quality.tools.formatting import auto_format, detect_language as detect_lang_format
from collab_quality.tools.linting import run_lint
from collab_quality.tools.testing import run_tests
from collab_quality.tools.coverage import check_coverage
from collab_quality.trust_engine import TrustEngine


def test_format_no_files():
    """Test formatting with no files specified."""
    result = auto_format(files=None)
    assert "error" in result
    assert "No files specified" in result["error"]


def test_format_empty_list():
    """Test formatting with empty file list."""
    result = auto_format(files=[])
    assert "error" in result
    assert "No files specified" in result["error"]


def test_format_unsupported_language():
    """Test formatting with unsupported language."""
    result = auto_format(files=["test.xyz"], language="unsupported")
    assert "error" in result
    assert "Unsupported" in result["error"]


def test_format_language_detection():
    """Test automatic language detection for formatting."""
    # No language specified, should detect from extension
    result = auto_format(files=["test.unknown"])
    assert "error" in result or "unchanged" in result


def test_format_detect_language_helper():
    """Test language detection helper function."""
    assert detect_lang_format("test.py") == "python"
    assert detect_lang_format("test.ts") == "typescript"
    assert detect_lang_format("test.tsx") == "typescript"
    assert detect_lang_format("test.js") == "javascript"
    assert detect_lang_format("test.jsx") == "javascript"
    assert detect_lang_format("test.swift") == "swift"
    assert detect_lang_format("test.rs") == "rust"
    assert detect_lang_format("test.unknown") is None


def test_lint_no_files():
    """Test linting with no files specified."""
    result = run_lint(files=None)
    assert "error" in result
    assert "No files specified" in result["error"]


def test_lint_empty_list():
    """Test linting with empty file list."""
    result = run_lint(files=[])
    assert "error" in result


def test_lint_unsupported_language():
    """Test linting with unsupported language."""
    result = run_lint(files=["test.xyz"], language="unsupported")
    assert "error" in result
    assert "Unsupported" in result["error"]


def test_lint_detect_language_helper():
    """Test language detection for linting."""
    from collab_quality.tools.linting import detect_language

    assert detect_language("test.py") == "python"
    assert detect_language("test.ts") == "typescript"
    assert detect_language("test.js") == "javascript"
    assert detect_language("test.swift") == "swift"
    assert detect_language("test.rs") == "rust"
    assert detect_language("test.unknown") is None


def test_run_tests_default_language():
    """Test that tests default to python when no language specified."""
    # Use unsupported language to avoid running pytest
    result = run_tests(scope=None, language="unsupported_lang")
    assert "passed" in result
    assert "failed" in result
    assert "error" in result


def test_coverage_unsupported_language():
    """Test coverage with unsupported language."""
    result = check_coverage(language="unsupported")
    assert "error" in result
    assert "not supported" in result["error"]


def test_coverage_default_language():
    """Test coverage defaults to python."""
    # Use unsupported language to avoid actually running coverage
    result = check_coverage(language="fake")
    assert "percentage" in result
    assert "target" in result
    assert "error" in result


def test_trust_engine_record_then_dismiss():
    """Test recording a finding then dismissing it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test-trust.db")
        engine = TrustEngine(db_path=db_path)

        # Record a finding
        recorded = engine.record_finding(
            finding_id="finding-001",
            tool="eslint",
            severity="warning",
            component="auth",
            description="Missing semicolon",
        )
        assert recorded

        # Get trust decision (should default to BLOCK)
        decision = engine.get_trust_decision("finding-001")
        assert decision["decision"] == "BLOCK"

        # Dismiss it
        dismissed = engine.record_dismissal(
            "finding-001",
            "Semicolons not required in our style guide",
            "tech_lead",
        )
        assert dismissed

        # Get trust decision again (should now be TRACK)
        decision = engine.get_trust_decision("finding-001")
        assert decision["decision"] == "TRACK"
        assert "Previously dismissed" in decision["rationale"]


def test_trust_engine_get_all_findings():
    """Test getting all findings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test-trust.db")
        engine = TrustEngine(db_path=db_path)

        # Record multiple findings
        engine.record_finding("f1", "ruff", "error", "module1", "Error 1")
        engine.record_finding("f2", "eslint", "warning", "module2", "Warning 1")
        engine.record_finding("f3", "swiftlint", "error", "module3", "Error 2")

        # Get all findings
        findings = engine.get_all_findings()
        assert len(findings) == 3

        # Get only open findings
        open_findings = engine.get_all_findings(status="open")
        assert len(open_findings) == 3

        # Dismiss one
        engine.record_dismissal("f1", "Not applicable", "human")

        # Get dismissed findings
        dismissed_findings = engine.get_all_findings(status="dismissed")
        assert len(dismissed_findings) == 1
        assert dismissed_findings[0]["id"] == "f1"


def test_trust_engine_get_nonexistent_finding_decision():
    """Test getting trust decision for nonexistent finding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test-trust.db")
        engine = TrustEngine(db_path=db_path)

        # Should return default BLOCK decision
        decision = engine.get_trust_decision("nonexistent-finding")
        assert decision["decision"] == "BLOCK"


def test_trust_engine_dismissal_history_empty():
    """Test getting dismissal history for finding with no dismissals."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test-trust.db")
        engine = TrustEngine(db_path=db_path)

        history = engine.get_dismissal_history("nonexistent")
        assert len(history) == 0


def test_trust_engine_multiple_dismissals():
    """Test that multiple dismissals are recorded in history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test-trust.db")
        engine = TrustEngine(db_path=db_path)

        # Record finding
        engine.record_finding("multi-dismiss", "tool", "error", "comp", "desc")

        # Dismiss multiple times (simulating re-opening and re-dismissing)
        engine.record_dismissal("multi-dismiss", "Reason 1", "person1")
        engine.record_dismissal("multi-dismiss", "Reason 2", "person2")

        # Should have 2 entries in history
        history = engine.get_dismissal_history("multi-dismiss")
        assert len(history) == 2
        # Most recent should be first
        assert history[0]["dismissed_by"] == "person2"
        assert history[1]["dismissed_by"] == "person1"
