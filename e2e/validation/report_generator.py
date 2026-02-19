"""Report generator for E2E test results.

Produces three output forms:
1. A JSON report (machine-parseable) written to disk.
2. A console summary printed to stdout with pass/fail counts per scenario.
3. Detailed output for any failed assertions.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from e2e.scenarios.base import ScenarioResult

# ------------------------------------------------------------------
# ANSI helpers (gracefully degrade when output is not a terminal)
# ------------------------------------------------------------------


class _Colors:
    """ANSI color codes, disabled when output is not a TTY."""

    def __init__(self, stream: TextIO):
        use_color = hasattr(stream, "isatty") and stream.isatty()
        self.GREEN = "\033[32m" if use_color else ""
        self.RED = "\033[31m" if use_color else ""
        self.YELLOW = "\033[33m" if use_color else ""
        self.CYAN = "\033[36m" if use_color else ""
        self.BOLD = "\033[1m" if use_color else ""
        self.DIM = "\033[2m" if use_color else ""
        self.RESET = "\033[0m" if use_color else ""


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


class ReportGenerator:
    """Generates reports from a collection of ``ScenarioResult`` objects."""

    def __init__(self, results: list[ScenarioResult], suite_name: str = "E2E Suite"):
        self.results = results
        self.suite_name = suite_name
        self._timestamp = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # 1. JSON report
    # ------------------------------------------------------------------

    def write_json(self, path: Path | str) -> Path:
        """Write a machine-parseable JSON report to *path*.

        Args:
            path: File path for the JSON output. Parent directories are
                  created automatically.

        Returns:
            The resolved ``Path`` that was written.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        report = self._build_report_dict()
        path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        return path

    def to_json(self) -> str:
        """Return the JSON report as a string (no file I/O)."""
        return json.dumps(self._build_report_dict(), indent=2, default=str)

    # ------------------------------------------------------------------
    # 2. Console summary
    # ------------------------------------------------------------------

    def print_summary(self, stream: TextIO | None = None) -> None:
        """Print a human-readable summary to *stream* (default: stdout).

        Includes:
        - Per-scenario pass/fail counts and duration.
        - Suite-level totals.
        - Details of any failed assertions.
        """
        out = stream or sys.stdout
        c = _Colors(out)

        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_scenarios = len(self.results)
        scenarios_passed = sum(1 for r in self.results if r.success)
        scenarios_failed = total_scenarios - scenarios_passed

        # ---- Header ----
        out.write(f"\n{c.BOLD}{'=' * 70}{c.RESET}\n")
        out.write(f"{c.BOLD}  {self.suite_name}{c.RESET}\n")
        out.write(f"{c.DIM}  {self._timestamp}{c.RESET}\n")
        out.write(f"{c.BOLD}{'=' * 70}{c.RESET}\n\n")

        # ---- Per-scenario rows ----
        for result in self.results:
            status_icon = f"{c.GREEN}PASS{c.RESET}" if result.success else f"{c.RED}FAIL{c.RESET}"
            duration_str = f"{result.duration_ms:>8.1f}ms"
            counts = f"{result.passed} passed, {result.failed} failed"
            type_tag = f"{c.DIM}[{result.scenario_type}]{c.RESET}"

            out.write(f"  {status_icon}  {result.name:<40s} {counts:<22s} {duration_str}  {type_tag}\n")

        # ---- Totals ----
        out.write(f"\n{c.BOLD}{'-' * 70}{c.RESET}\n")
        suite_color = c.GREEN if scenarios_failed == 0 else c.RED
        out.write(
            f"  {c.BOLD}Scenarios:{c.RESET}  "
            f"{c.GREEN}{scenarios_passed} passed{c.RESET}, "
            f"{c.RED}{scenarios_failed} failed{c.RESET}, "
            f"{total_scenarios} total\n"
        )
        out.write(
            f"  {c.BOLD}Assertions:{c.RESET} "
            f"{c.GREEN}{total_passed} passed{c.RESET}, "
            f"{c.RED}{total_failed} failed{c.RESET}, "
            f"{total_passed + total_failed} total\n"
        )
        total_duration = sum(r.duration_ms for r in self.results)
        out.write(f"  {c.BOLD}Duration:{c.RESET}   {total_duration:.1f}ms\n")
        out.write(
            f"  {c.BOLD}Result:{c.RESET}     "
            f"{suite_color}{c.BOLD}{'ALL PASSED' if scenarios_failed == 0 else 'FAILURES DETECTED'}{c.RESET}\n"
        )
        out.write(f"{c.BOLD}{'=' * 70}{c.RESET}\n")

        # ---- Failure details ----
        failures = [r for r in self.results if not r.success]
        if failures:
            out.write(f"\n{c.RED}{c.BOLD}  FAILURE DETAILS{c.RESET}\n")
            out.write(f"{c.BOLD}{'-' * 70}{c.RESET}\n")
            for result in failures:
                self._print_failure_detail(result, out, c)
            out.write("\n")

    # ------------------------------------------------------------------
    # 3. Failure details (also used by print_summary)
    # ------------------------------------------------------------------

    def get_failure_details(self) -> list[dict[str, Any]]:
        """Return structured details for every failed assertion across all scenarios.

        Each entry includes the scenario name, assertion name, expected/actual
        values, and error message.
        """
        details: list[dict[str, Any]] = []
        for result in self.results:
            if result.error:
                details.append(
                    {
                        "scenario": result.name,
                        "assertion": "execution",
                        "expected": "no error",
                        "actual": result.error,
                        "error": result.error,
                    }
                )
            for assertion in result.assertions:
                if not assertion.passed:
                    details.append(
                        {
                            "scenario": result.name,
                            "assertion": assertion.name,
                            "expected": assertion.expected,
                            "actual": assertion.actual,
                            "error": assertion.error,
                        }
                    )
        return details

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_report_dict(self) -> dict[str, Any]:
        """Assemble the full report dictionary."""
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)

        return {
            "suite": self.suite_name,
            "timestamp": self._timestamp,
            "summary": {
                "scenarios_total": len(self.results),
                "scenarios_passed": sum(1 for r in self.results if r.success),
                "scenarios_failed": sum(1 for r in self.results if not r.success),
                "assertions_passed": total_passed,
                "assertions_failed": total_failed,
                "assertions_total": total_passed + total_failed,
                "total_duration_ms": round(sum(r.duration_ms for r in self.results), 2),
                "success": all(r.success for r in self.results),
            },
            "scenarios": [r.to_dict() for r in self.results],
            "failures": self.get_failure_details(),
        }

    def _print_failure_detail(
        self,
        result: ScenarioResult,
        out: TextIO,
        c: _Colors,
    ) -> None:
        """Print detailed information about a single failed scenario."""
        out.write(f"\n  {c.RED}{c.BOLD}Scenario: {result.name}{c.RESET}\n")

        if result.error:
            out.write(f"    {c.RED}Scenario error:{c.RESET} {result.error}\n")

        failed_assertions = [a for a in result.assertions if not a.passed]
        for assertion in failed_assertions:
            out.write(f"\n    {c.YELLOW}Assertion:{c.RESET} {assertion.name}\n")
            out.write(f"      Expected: {assertion.expected!r}\n")
            out.write(f"      Actual:   {assertion.actual!r}\n")
            if assertion.error:
                # Indent multiline errors (e.g. tracebacks)
                error_lines = assertion.error.strip().split("\n")
                out.write(f"      Error:    {error_lines[0]}\n")
                for line in error_lines[1:]:
                    out.write(f"                {line}\n")


# ------------------------------------------------------------------
# Convenience function
# ------------------------------------------------------------------


def generate_report(
    results: list[ScenarioResult],
    *,
    suite_name: str = "E2E Suite",
    json_path: Path | str | None = None,
    print_to_console: bool = True,
    stream: TextIO | None = None,
) -> dict[str, Any]:
    """One-call convenience: generate all report outputs at once.

    Args:
        results: List of completed ``ScenarioResult`` objects.
        suite_name: Name for the test suite header.
        json_path: If provided, write a JSON report to this path.
        print_to_console: If ``True``, print the console summary.
        stream: Output stream for the console summary (default: stdout).

    Returns:
        The report dictionary (same structure as the JSON file).
    """
    gen = ReportGenerator(results, suite_name=suite_name)

    if json_path is not None:
        gen.write_json(json_path)

    if print_to_console:
        gen.print_summary(stream=stream)

    return gen._build_report_dict()


def print_summary(
    results: list[ScenarioResult],
    *,
    suite_name: str = "E2E Suite",
    report_path: Path | str | None = None,
    stream: TextIO | None = None,
) -> None:
    """Module-level convenience wrapper for ``ReportGenerator.print_summary``.

    Also prints the report file path when *report_path* is provided.

    Args:
        results: List of completed ``ScenarioResult`` objects.
        suite_name: Name for the test suite header.
        report_path: Path to the JSON report file (printed for reference).
        stream: Output stream (default: stdout).
    """
    out = stream or sys.stdout
    gen = ReportGenerator(results, suite_name=suite_name)
    gen.print_summary(stream=out)

    if report_path is not None:
        out.write(f"  Report written to: {report_path}\n\n")
