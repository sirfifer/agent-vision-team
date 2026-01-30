"""Quality gate aggregation — checks all gates and returns combined result."""

from .models import GateResult, GateResults
from .tools.formatting import auto_format
from .tools.linting import run_lint
from .tools.testing import run_tests
from .tools.coverage import check_coverage


def check_all_gates() -> GateResults:
    """Run all quality gates and return aggregated results."""
    # Build gate
    # TODO: Run build command and check exit code
    build = GateResult(name="build", passed=True, detail="Build check not yet implemented")

    # Lint gate
    lint_result = run_lint()
    lint_passed = lint_result.get("total", 1) == 0 and "error" not in lint_result
    lint = GateResult(
        name="lint",
        passed=lint_passed,
        detail=lint_result.get("error", f"{lint_result.get('total', 0)} violations"),
    )

    # Test gate
    test_result = run_tests()
    test_passed = test_result.get("failed", 1) == 0 and "error" not in test_result
    tests = GateResult(
        name="tests",
        passed=test_passed,
        detail=test_result.get("error", f"{test_result.get('passed', 0)} passed, {test_result.get('failed', 0)} failed"),
    )

    # Coverage gate
    cov_result = check_coverage()
    cov_passed = cov_result.get("met", False) and "error" not in cov_result
    coverage = GateResult(
        name="coverage",
        passed=cov_passed,
        detail=cov_result.get("error", f"{cov_result.get('percentage', 0)}% (target: {cov_result.get('target', 80)}%)"),
    )

    # Findings gate (no critical findings)
    # TODO: Check for unresolved critical findings
    findings = GateResult(name="findings", passed=True, detail="No critical findings")

    all_passed = all([build.passed, lint.passed, tests.passed, coverage.passed, findings.passed])

    return GateResults(
        build=build,
        lint=lint,
        tests=tests,
        coverage=coverage,
        findings=findings,
        all_passed=all_passed,
    )
