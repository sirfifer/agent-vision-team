"""Base scenario framework for E2E testing.

Provides the foundational classes for defining test scenarios with
structured assertions, timing, and result collection.
"""

import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class AssertionResult:
    """Result of a single assertion within a scenario."""

    name: str
    passed: bool
    expected: Any
    actual: Any
    error: Optional[str] = None

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        msg = f"[{status}] {self.name}"
        if not self.passed:
            msg += f" (expected={self.expected!r}, actual={self.actual!r})"
            if self.error:
                msg += f" -- {self.error}"
        return msg


@dataclass
class ScenarioResult:
    """Aggregate result of running a complete scenario."""

    name: str
    passed: int
    failed: int
    assertions: list[AssertionResult]
    duration_ms: float
    scenario_type: str  # "positive", "negative", "mixed"
    error: Optional[str] = None

    @property
    def total(self) -> int:
        return self.passed + self.failed

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.error is None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary for JSON reporting."""
        return {
            "name": self.name,
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 2),
            "scenario_type": self.scenario_type,
            "error": self.error,
            "assertions": [
                {
                    "name": a.name,
                    "passed": a.passed,
                    "expected": _safe_serialize(a.expected),
                    "actual": _safe_serialize(a.actual),
                    "error": a.error,
                }
                for a in self.assertions
            ],
        }

    def __str__(self) -> str:
        status = "PASSED" if self.success else "FAILED"
        lines = [f"Scenario: {self.name} [{status}] ({self.duration_ms:.1f}ms)"]
        lines.append(f"  Assertions: {self.passed} passed, {self.failed} failed, {self.total} total")
        if self.error:
            lines.append(f"  Error: {self.error}")
        for a in self.assertions:
            if not a.passed:
                lines.append(f"    {a}")
        return "\n".join(lines)


def _safe_serialize(value: Any) -> Any:
    """Convert a value to something JSON-safe."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_serialize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe_serialize(v) for k, v in value.items()}
    if isinstance(value, set):
        return sorted(_safe_serialize(v) for v in value)
    if isinstance(value, Path):
        return str(value)
    return repr(value)


class BaseScenario:
    """Base class for all E2E test scenarios.

    Subclasses must override ``run()`` and should set ``name``
    and ``isolation_mode`` as class attributes.

    Attributes:
        name: Human-readable scenario identifier.
        isolation_mode: How the scenario interacts with the system under test.
            ``"library"`` imports and calls Python APIs directly.
            ``"http"`` communicates over HTTP with running MCP servers.
    """

    name: str = "unnamed"
    isolation_mode: str = "library"  # "library" or "http"

    def __init__(self, project: Any, workspace: Path):
        """
        Args:
            project: Project-level configuration / fixture (e.g. paths, config).
            workspace: Temporary directory for scenario isolation.
        """
        self.project = project
        self.workspace = workspace
        self._assertions: list[AssertionResult] = []

    # ------------------------------------------------------------------
    # Assertion helpers
    # ------------------------------------------------------------------

    def assert_true(
        self,
        name: str,
        condition: bool,
        expected: Any = True,
        actual: Any = None,
    ) -> AssertionResult:
        """Record a boolean assertion.

        Args:
            name: Descriptive label for the assertion.
            condition: The boolean to evaluate.
            expected: What was expected (for reporting).
            actual: What was observed (for reporting). Defaults to *condition*.
        """
        if actual is None:
            actual = condition
        result = AssertionResult(
            name=name,
            passed=bool(condition),
            expected=expected,
            actual=actual,
            error=None if condition else f"Condition was {actual!r}, expected {expected!r}",
        )
        self._assertions.append(result)
        return result

    def assert_equal(self, name: str, actual: Any, expected: Any) -> AssertionResult:
        """Record an equality assertion.

        Args:
            name: Descriptive label.
            actual: The value produced by the system under test.
            expected: The value that was expected.
        """
        passed = actual == expected
        result = AssertionResult(
            name=name,
            passed=passed,
            expected=expected,
            actual=actual,
            error=None if passed else f"Expected {expected!r}, got {actual!r}",
        )
        self._assertions.append(result)
        return result

    def assert_contains(self, name: str, haystack: Any, needle: Any) -> AssertionResult:
        """Record a containment assertion.

        Works with strings (substring check), lists/tuples (membership),
        dicts (key presence), and sets.

        Args:
            name: Descriptive label.
            haystack: The container to search within.
            needle: The element to look for.
        """
        try:
            if isinstance(haystack, dict):
                passed = needle in haystack
            elif isinstance(haystack, (str, list, tuple, set, frozenset)):
                passed = needle in haystack
            else:
                # Fall back to generic __contains__
                passed = needle in haystack
        except TypeError:
            passed = False

        result = AssertionResult(
            name=name,
            passed=passed,
            expected=f"contains {needle!r}",
            actual=haystack if isinstance(haystack, str) and len(str(haystack)) < 200 else type(haystack).__name__,
            error=None if passed else f"{needle!r} not found in {type(haystack).__name__}",
        )
        self._assertions.append(result)
        return result

    def assert_error(self, name: str, result: dict) -> AssertionResult:
        """Assert that *result* contains an error indicator.

        Checks for common error representations:
        - ``"error"`` key present and truthy
        - ``"success"`` key present and falsy
        - ``"status"`` key equal to ``"error"``

        Args:
            name: Descriptive label.
            result: Dictionary returned by the system under test.
        """
        has_error = bool(result.get("error")) or result.get("success") is False or result.get("status") == "error"
        assertion = AssertionResult(
            name=name,
            passed=has_error,
            expected="error present",
            actual=self._summarize_result(result),
            error=None if has_error else "Expected an error but result appears successful",
        )
        self._assertions.append(assertion)
        return assertion

    def assert_no_error(self, name: str, result: dict) -> AssertionResult:
        """Assert that *result* does NOT contain an error.

        Inverse of ``assert_error``.

        Args:
            name: Descriptive label.
            result: Dictionary returned by the system under test.
        """
        has_error = bool(result.get("error")) or result.get("success") is False or result.get("status") == "error"
        assertion = AssertionResult(
            name=name,
            passed=not has_error,
            expected="no error",
            actual=self._summarize_result(result),
            error=None
            if not has_error
            else f"Unexpected error: {result.get('error', result.get('status', 'unknown'))}",
        )
        self._assertions.append(assertion)
        return assertion

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ScenarioResult:
        """Execute the scenario logic.  Override in subclasses.

        Must call assertion helpers and return ``self._build_result(...)``.
        """
        raise NotImplementedError(f"{type(self).__name__} must implement run()")

    def execute(self, **kwargs: Any) -> ScenarioResult:
        """Public entry point.  Wraps ``run()`` with timing and error handling.

        Returns a ``ScenarioResult`` regardless of whether ``run()`` raises.
        """
        start = time.time()
        try:
            result = self.run(**kwargs)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            duration = (time.time() - start) * 1000
            tb = traceback.format_exc()
            return ScenarioResult(
                name=self.name,
                passed=0,
                failed=1,
                assertions=[
                    AssertionResult(
                        name="execution",
                        passed=False,
                        expected="no error",
                        actual=str(e),
                        error=tb,
                    )
                ],
                duration_ms=duration,
                scenario_type="mixed",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_result(self, scenario_type: str = "mixed") -> ScenarioResult:
        """Build a ``ScenarioResult`` from the assertions collected so far.

        Args:
            scenario_type: One of ``"positive"``, ``"negative"``, or ``"mixed"``.
        """
        passed = sum(1 for a in self._assertions if a.passed)
        failed = len(self._assertions) - passed
        return ScenarioResult(
            name=self.name,
            passed=passed,
            failed=failed,
            assertions=list(self._assertions),
            duration_ms=0,  # filled in by execute()
            scenario_type=scenario_type,
        )

    @staticmethod
    def _summarize_result(result: dict) -> str:
        """Create a short human-readable summary of a result dict."""
        parts: list[str] = []
        for key in ("status", "success", "error", "verdict"):
            if key in result:
                parts.append(f"{key}={result[key]!r}")
        if not parts:
            keys = list(result.keys())[:5]
            parts.append(f"keys={keys}")
        return ", ".join(parts)
