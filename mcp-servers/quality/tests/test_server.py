"""Basic tests for the Quality server."""

import tempfile
from pathlib import Path

from collab_quality.tools.coverage import check_coverage
from collab_quality.tools.formatting import auto_format
from collab_quality.tools.linting import run_lint
from collab_quality.tools.testing import run_tests
from collab_quality.trust_engine import TrustEngine


def test_auto_format_nonexistent_file():
    """Test formatting with nonexistent file."""
    result = auto_format(files=["nonexistent.py"], language="python")
    assert "formatted" in result
    assert "unchanged" in result
    # Nonexistent files should be in unchanged
    assert "nonexistent.py" in result["unchanged"]


def test_run_lint_nonexistent_file():
    """Test linting with nonexistent file."""
    result = run_lint(files=["nonexistent.py"], language="python")
    assert "findings" in result
    assert "total" in result
    # Should handle gracefully (may have error or 0 findings)


def test_run_tests_structure():
    """Test run_tests returns expected structure."""
    # Don't actually run pytest (would cause recursion)
    # Just test with unsupported language to check structure
    result = run_tests(scope="all", language="unsupported")
    assert "passed" in result
    assert "failed" in result
    assert "skipped" in result
    assert "failures" in result
    assert "error" in result


def test_check_coverage_structure():
    """Test coverage check returns expected structure."""
    # Use unsupported language to avoid actually running coverage
    result = check_coverage(language="unsupported")
    assert "percentage" in result
    assert "target" in result
    assert "met" in result
    assert "error" in result
    assert result["target"] == 80.0


def test_check_all_gates():
    """Test quality gates aggregation - skipped to avoid pytest recursion."""
    # Skip this test as it calls run_tests/coverage which would cause recursion
    # The gate structure is tested via the MCP server integration
    pass


def test_trust_engine_default():
    """Test trust engine default decision."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test-trust.db")
        engine = TrustEngine(db_path=db_path)
        decision = engine.get_trust_decision("finding-123")
        assert decision["decision"] == "BLOCK"


def test_trust_engine_dismissal():
    """Test trust engine dismissal recording."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test-trust.db")
        engine = TrustEngine(db_path=db_path)

        # Dismissal without justification fails
        result = engine.record_dismissal("finding-123", "", "human")
        assert not result

        # Dismissal with justification succeeds
        result = engine.record_dismissal(
            "finding-123",
            "False positive: rule doesn't apply to test files",
            "human",
        )
        assert result

        history = engine.get_dismissal_history("finding-123")
        assert len(history) == 1
        assert history[0]["dismissed_by"] == "human"


def test_trust_engine_finding_recording():
    """Test recording findings in trust engine."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test-trust.db")
        engine = TrustEngine(db_path=db_path)

        # Record a finding
        result = engine.record_finding(
            finding_id="test-001",
            tool="ruff",
            severity="error",
            component="test_module",
            description="Test finding",
        )
        assert result

        # Recording same finding again should fail
        result = engine.record_finding(
            finding_id="test-001",
            tool="ruff",
            severity="error",
            component="test_module",
            description="Test finding",
        )
        assert not result

        # Get all findings
        findings = engine.get_all_findings()
        assert len(findings) == 1
        assert findings[0]["id"] == "test-001"
        assert findings[0]["status"] == "open"


def test_language_detection():
    """Test language detection from file extensions."""
    from collab_quality.tools.formatting import detect_language

    assert detect_language("test.py") == "python"
    assert detect_language("test.ts") == "typescript"
    assert detect_language("test.swift") == "swift"
    assert detect_language("test.rs") == "rust"
    assert detect_language("test.unknown") is None
