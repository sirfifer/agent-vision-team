"""Coverage checker — wraps language-specific coverage tools."""

from typing import Optional


def check_coverage(
    language: Optional[str] = None,
) -> dict:
    """Check test coverage using the appropriate coverage tool."""
    # TODO: Run coverage tool (e.g., pytest --cov, xcrun llvm-cov)
    # TODO: Parse output into structured result
    return {
        "percentage": 0.0,
        "target": 80.0,
        "met": False,
        "uncovered_files": [],
    }
