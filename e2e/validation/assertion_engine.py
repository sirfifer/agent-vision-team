"""Domain-agnostic assertion helpers for governance system behavior.

These static methods return ``(passed: bool, message: str)`` tuples
so callers can integrate the results into any reporting framework
(including ``BaseScenario.assert_true``).
"""

from __future__ import annotations

from typing import Any


class AssertionEngine:
    """Deterministic assertions for governance system behavior.

    Every method returns a ``(bool, str)`` tuple:
    - ``True, "..."``  -- assertion passed, message describes what was verified.
    - ``False, "..."`` -- assertion failed, message explains what went wrong.
    """

    # ------------------------------------------------------------------
    # Tier protection
    # ------------------------------------------------------------------

    @staticmethod
    def assert_tier_protected(result: dict, tier: str) -> tuple[bool, str]:
        """Assert that a tier-protected write was blocked.

        A protected write should result in an error whose message or code
        references the tier that was violated.

        Args:
            result: The response dict from the attempted write operation.
            tier: The protection tier that should have blocked the write
                  (e.g. ``"vision"``, ``"architecture"``).
        """
        # Check for error indicators
        has_error = (
            bool(result.get("error"))
            or result.get("success") is False
            or result.get("status") == "error"
            or result.get("blocked") is True
        )

        if not has_error:
            return (
                False,
                f"Expected tier-protected write to be blocked (tier={tier!r}), "
                f"but the operation appeared to succeed: {_summarize(result)}",
            )

        # Verify the error references the expected tier
        error_text = _extract_error_text(result).lower()
        tier_lower = tier.lower()

        tier_referenced = (
            tier_lower in error_text
            or "tier" in error_text
            or "protected" in error_text
            or "permission" in error_text
            or "unauthorized" in error_text
        )

        if not tier_referenced:
            return (
                False,
                f"Write was blocked, but the error does not reference tier {tier!r}. "
                f"Error text: {error_text[:200]}",
            )

        return (
            True,
            f"Tier-protected write correctly blocked for tier={tier!r}",
        )

    # ------------------------------------------------------------------
    # Governance verdicts
    # ------------------------------------------------------------------

    @staticmethod
    def assert_verdict(result: dict, expected_verdict: str) -> tuple[bool, str]:
        """Assert that a governance verdict matches the expected value.

        Checks the ``verdict`` key (case-insensitive).  Also accepts
        ``decision.verdict`` for nested response shapes.

        Args:
            result: Response from a governance submission.
            expected_verdict: The expected verdict string
                (e.g. ``"approved"``, ``"blocked"``, ``"needs_human_review"``).
        """
        actual = _extract_verdict(result)

        if actual is None:
            return (
                False,
                f"No verdict found in result. Expected {expected_verdict!r}. "
                f"Keys present: {list(result.keys())}",
            )

        if actual.lower() == expected_verdict.lower():
            return True, f"Verdict matches: {actual!r}"

        return (
            False,
            f"Verdict mismatch: expected {expected_verdict!r}, got {actual!r}",
        )

    # ------------------------------------------------------------------
    # Task blocking
    # ------------------------------------------------------------------

    @staticmethod
    def assert_task_blocked(status: dict) -> tuple[bool, str]:
        """Assert that a task is blocked and cannot execute.

        Checks common indicators: ``blocked=True``, ``status="blocked"``,
        ``can_execute=False``, or a non-empty ``blockers`` list.

        Args:
            status: Task status dictionary.
        """
        is_blocked = (
            status.get("blocked") is True
            or status.get("status") == "blocked"
            or status.get("can_execute") is False
            or bool(status.get("blockers"))
        )

        if is_blocked:
            blockers = status.get("blockers", [])
            reason = status.get("reason", status.get("error", ""))
            detail = f"blockers={blockers}" if blockers else f"reason={reason!r}"
            return True, f"Task is correctly blocked ({detail})"

        return (
            False,
            f"Expected task to be blocked, but it appears unblocked: {_summarize(status)}",
        )

    @staticmethod
    def assert_task_released(status: dict) -> tuple[bool, str]:
        """Assert that a task is unblocked and available for execution.

        Inverse of ``assert_task_blocked``.

        Args:
            status: Task status dictionary.
        """
        is_blocked = (
            status.get("blocked") is True
            or status.get("status") == "blocked"
            or status.get("can_execute") is False
            or bool(status.get("blockers"))
        )

        if not is_blocked:
            return True, "Task is correctly released and available"

        blockers = status.get("blockers", [])
        reason = status.get("reason", status.get("error", ""))
        detail = f"blockers={blockers}" if blockers else f"reason={reason!r}"
        return (
            False,
            f"Expected task to be released, but it is still blocked ({detail})",
        )

    # ------------------------------------------------------------------
    # Review findings
    # ------------------------------------------------------------------

    @staticmethod
    def assert_has_findings(result: dict) -> tuple[bool, str]:
        """Assert that a review result contains at least one finding.

        Checks ``findings`` (list), ``finding_count`` (int > 0), and
        ``issues`` (list) as common response shapes.

        Args:
            result: Review result dictionary.
        """
        findings = result.get("findings", result.get("issues", []))
        finding_count = result.get("finding_count", len(findings) if isinstance(findings, list) else 0)

        if isinstance(findings, list) and len(findings) > 0:
            return True, f"Review has {len(findings)} finding(s)"

        if finding_count > 0:
            return True, f"Review has {finding_count} finding(s)"

        return (
            False,
            f"Expected findings but none were present. Keys: {list(result.keys())}",
        )

    @staticmethod
    def assert_no_findings(result: dict) -> tuple[bool, str]:
        """Assert that a review result contains no findings.

        Inverse of ``assert_has_findings``.

        Args:
            result: Review result dictionary.
        """
        findings = result.get("findings", result.get("issues", []))
        finding_count = result.get("finding_count", len(findings) if isinstance(findings, list) else 0)

        if (isinstance(findings, list) and len(findings) == 0) or finding_count == 0:
            return True, "Review has no findings as expected"

        count = len(findings) if isinstance(findings, list) else finding_count
        return (
            False,
            f"Expected no findings but found {count}",
        )

    @staticmethod
    def assert_finding_severity(result: dict, min_severity: str) -> tuple[bool, str]:
        """Assert that at least one finding meets the minimum severity.

        Severity hierarchy (low to high): info < warning < error < critical.

        Args:
            result: Review result dictionary containing ``findings``.
            min_severity: Minimum severity to look for.
        """
        severity_order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
        min_level = severity_order.get(min_severity.lower(), -1)

        if min_level < 0:
            return False, f"Unknown severity level: {min_severity!r}"

        findings = result.get("findings", result.get("issues", []))
        if not isinstance(findings, list):
            return False, "No findings list found in result"

        for finding in findings:
            sev = finding.get("severity", finding.get("level", "")).lower()
            if severity_order.get(sev, -1) >= min_level:
                return True, f"Found finding with severity {sev!r} (>= {min_severity!r})"

        severities = [f.get("severity", f.get("level", "unknown")) for f in findings]
        return (
            False,
            f"No finding meets minimum severity {min_severity!r}. Found: {severities}",
        )

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def assert_key_present(result: dict, key: str) -> tuple[bool, str]:
        """Assert that a key is present in the result dictionary."""
        if key in result:
            return True, f"Key {key!r} is present"
        return False, f"Key {key!r} not found. Available keys: {list(result.keys())}"

    @staticmethod
    def assert_key_value(result: dict, key: str, expected: Any) -> tuple[bool, str]:
        """Assert that a key has the expected value."""
        if key not in result:
            return False, f"Key {key!r} not found. Available keys: {list(result.keys())}"
        actual = result[key]
        if actual == expected:
            return True, f"Key {key!r} has expected value {expected!r}"
        return False, f"Key {key!r}: expected {expected!r}, got {actual!r}"

    @staticmethod
    def assert_count(result: dict, key: str, expected_count: int) -> tuple[bool, str]:
        """Assert that a list-valued key has the expected number of items."""
        value = result.get(key)
        if value is None:
            return False, f"Key {key!r} not found in result"
        if not isinstance(value, (list, tuple)):
            return False, f"Key {key!r} is not a list (type={type(value).__name__})"
        actual_count = len(value)
        if actual_count == expected_count:
            return True, f"Key {key!r} has {expected_count} items as expected"
        return False, f"Key {key!r}: expected {expected_count} items, got {actual_count}"


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _extract_error_text(result: dict) -> str:
    """Pull an error description from various possible result shapes."""
    if isinstance(result.get("error"), str):
        return result["error"]
    if isinstance(result.get("error"), dict):
        return result["error"].get("message", str(result["error"]))
    if isinstance(result.get("message"), str):
        return result["message"]
    if isinstance(result.get("detail"), str):
        return result["detail"]
    return str(result)


def _extract_verdict(result: dict) -> str | None:
    """Extract the verdict string from various response shapes."""
    if "verdict" in result:
        return str(result["verdict"])
    # Nested under decision / review
    for wrapper_key in ("decision", "review", "result"):
        nested = result.get(wrapper_key)
        if isinstance(nested, dict) and "verdict" in nested:
            return str(nested["verdict"])
    return None


def _summarize(d: dict) -> str:
    """Short summary of a dict for error messages."""
    parts: list[str] = []
    for key in ("status", "success", "error", "verdict", "blocked"):
        if key in d:
            parts.append(f"{key}={d[key]!r}")
    if not parts:
        keys = list(d.keys())[:6]
        parts.append(f"keys={keys}")
    return ", ".join(parts)
