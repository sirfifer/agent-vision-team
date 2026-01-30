"""Basic tests for the Quality server."""

from collab_quality.tools.formatting import auto_format
from collab_quality.tools.linting import run_lint
from collab_quality.tools.testing import run_tests
from collab_quality.tools.coverage import check_coverage
from collab_quality.gates import check_all_gates
from collab_quality.trust_engine import TrustEngine


def test_auto_format_stub():
    result = auto_format(files=["test.py"], language="python")
    assert "formatted" in result
    assert "unchanged" in result


def test_run_lint_stub():
    result = run_lint(files=["test.py"], language="python")
    assert "findings" in result
    assert "total" in result
    assert result["total"] == 0


def test_run_tests_stub():
    result = run_tests(scope="all", language="python")
    assert "passed" in result
    assert "failed" in result
    assert result["failed"] == 0


def test_check_coverage_stub():
    result = check_coverage(language="python")
    assert "percentage" in result
    assert "target" in result
    assert "met" in result


def test_check_all_gates():
    results = check_all_gates()
    assert results.build.passed
    assert hasattr(results, "all_passed")


def test_trust_engine_default():
    engine = TrustEngine()
    decision = engine.get_trust_decision("finding-123")
    assert decision["decision"] == "BLOCK"


def test_trust_engine_dismissal():
    engine = TrustEngine()

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
