"""Linter wrapper — routes to the appropriate linter per language."""

from typing import Optional


LINTERS = {
    "swift": "swiftlint lint",
    "python": "ruff check",
    "rust": "cargo clippy",
    "typescript": "eslint",
}


def run_lint(
    files: Optional[list[str]] = None,
    language: Optional[str] = None,
) -> dict:
    """Run linting using the appropriate linter."""
    # TODO: Detect language from file extensions if not specified
    # TODO: Run the linter subprocess
    # TODO: Parse output into structured findings
    return {"findings": [], "auto_fixable": 0, "total": 0}
