"""Formatter wrapper — routes to the appropriate formatter per language."""

from typing import Optional


FORMATTERS = {
    "swift": "swiftformat",
    "python": "ruff format",
    "rust": "rustfmt",
    "typescript": "prettier --write",
}


def auto_format(
    files: Optional[list[str]] = None,
    language: Optional[str] = None,
) -> dict:
    """Format files using the appropriate formatter."""
    # TODO: Detect language from file extensions if not specified
    # TODO: Run the formatter subprocess
    # TODO: Return list of formatted and unchanged files
    return {"formatted": [], "unchanged": files or []}
