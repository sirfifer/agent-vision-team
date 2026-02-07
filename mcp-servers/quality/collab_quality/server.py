"""Quality MCP server."""

from typing import Optional

from fastmcp import FastMCP

from .tools.formatting import auto_format as _auto_format
from .tools.linting import run_lint as _run_lint
from .tools.testing import run_tests as _run_tests
from .tools.coverage import check_coverage as _check_coverage
from .gates import check_all_gates as _check_all_gates
from .trust_engine import TrustEngine

mcp = FastMCP("Collab Intelligence Quality")

trust_engine = TrustEngine()


@mcp.tool()
def auto_format(
    files: Optional[list[str]] = None,
    language: Optional[str] = None,
) -> dict:
    """Auto-format files using the appropriate formatter for the language."""
    return _auto_format(files, language)


@mcp.tool()
def run_lint(
    files: Optional[list[str]] = None,
    language: Optional[str] = None,
) -> dict:
    """Run linting on files using the appropriate linter."""
    return _run_lint(files, language)


@mcp.tool()
def run_tests(
    scope: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Run tests using the appropriate test runner."""
    return _run_tests(scope, language)


@mcp.tool()
def check_coverage(language: Optional[str] = None) -> dict:
    """Check test coverage."""
    return _check_coverage(language)


@mcp.tool()
def check_all_gates() -> dict:
    """Run all quality gates and return aggregated results."""
    results = _check_all_gates()
    return results.model_dump()


@mcp.tool()
def validate() -> dict:
    """Comprehensive validation — all gates plus summary."""
    results = _check_all_gates()
    gate_names = ["build", "lint", "tests", "coverage", "findings"]
    failed = [
        name for name in gate_names
        if not getattr(results, name).passed
    ]

    if results.all_passed:
        summary = "All quality gates passed."
    else:
        summary = f"Failed gates: {', '.join(failed)}"

    return {
        "gates": results.model_dump(),
        "summary": summary,
        "all_passed": results.all_passed,
    }


@mcp.tool()
def get_trust_decision(finding_id: str) -> dict:
    """Get trust classification for a finding."""
    return trust_engine.get_trust_decision(finding_id)


@mcp.tool()
def record_dismissal(
    finding_id: str,
    justification: str,
    dismissed_by: str,
) -> dict:
    """Record a finding dismissal with required justification."""
    recorded = trust_engine.record_dismissal(finding_id, justification, dismissed_by)
    return {"recorded": recorded}


@mcp.tool()
def get_all_findings(status: Optional[str] = None) -> dict:
    """Get all findings, optionally filtered by status ('open' or 'dismissed').

    Returns findings from the trust engine database with their current
    status and metadata. Use this to populate dashboard finding panels.

    Args:
        status: Optional filter - 'open' or 'dismissed'. Omit for all findings.

    Returns:
        {findings: [{id, tool, severity, component, description, created_at, status}]}
    """
    findings = trust_engine.get_all_findings(status=status)
    return {"findings": findings}


@mcp.tool()
def get_dismissal_history(finding_id: str) -> dict:
    """Get the dismissal audit trail for a finding.

    Returns all dismissal records for a finding, ordered by most recent first.
    Every dismissal includes who dismissed it and their justification.

    Args:
        finding_id: The finding ID to get history for.

    Returns:
        {history: [{dismissed_by, justification, dismissed_at}]}
    """
    history = trust_engine.get_dismissal_history(finding_id)
    return {"history": history}


if __name__ == "__main__":
    mcp.run(transport="sse", port=3102)
