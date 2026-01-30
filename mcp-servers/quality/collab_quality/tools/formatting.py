"""Formatter wrapper — routes to the appropriate formatter per language."""

import subprocess
from pathlib import Path
from typing import Optional


FORMATTERS = {
    "swift": ["swiftformat"],
    "python": ["ruff", "format"],
    "rust": ["rustfmt"],
    "typescript": ["prettier", "--write"],
    "javascript": ["prettier", "--write"],
}


def detect_language(filepath: str) -> Optional[str]:
    """Detect language from file extension."""
    ext = Path(filepath).suffix.lower()
    language_map = {
        ".swift": "swift",
        ".py": "python",
        ".rs": "rust",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
    }
    return language_map.get(ext)


def auto_format(
    files: Optional[list[str]] = None,
    language: Optional[str] = None,
) -> dict:
    """Format files using the appropriate formatter."""
    if files is None or len(files) == 0:
        # No files specified - would need git to find changed files
        return {"formatted": [], "unchanged": [], "error": "No files specified"}

    # Detect language if not specified
    if language is None and len(files) > 0:
        language = detect_language(files[0])

    if language is None or language not in FORMATTERS:
        return {
            "formatted": [],
            "unchanged": files,
            "error": f"Unsupported or undetected language: {language}",
        }

    formatter_cmd = FORMATTERS[language]
    formatted = []
    unchanged = []

    for filepath in files:
        # Check if file exists
        if not Path(filepath).exists():
            unchanged.append(filepath)
            continue

        try:
            # Run formatter
            result = subprocess.run(
                formatter_cmd + [filepath],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                formatted.append(filepath)
            else:
                # Formatter failed or file already formatted
                unchanged.append(filepath)

        except subprocess.TimeoutExpired:
            unchanged.append(filepath)
        except FileNotFoundError:
            # Formatter not installed
            return {
                "formatted": [],
                "unchanged": files,
                "error": f"Formatter '{formatter_cmd[0]}' not found. Install it to use formatting.",
            }

    return {"formatted": formatted, "unchanged": unchanged}
