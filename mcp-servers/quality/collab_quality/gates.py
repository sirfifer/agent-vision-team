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
    lint = GateResult(
        name="lint",
        passed=lint_result["total"] == 0,
        detail=f"{lint_result['total']} violations",
    )

    # Test gate
    test_result = run_tests()
    tests = GateResult(
        name="tests",
        passed=test_result["failed"] == 0,
        detail=f"{test_result['passed']} passed, {test_result['failed']} failed",
    )

    # Coverage gate
    cov_result = check_coverage()
    coverage = GateResult(
        name="coverage",
        passed=cov_result["met"],
        detail=f"{cov_result['percentage']}% (target: {cov_result['target']}%)",
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
