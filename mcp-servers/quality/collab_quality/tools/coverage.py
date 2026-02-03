"""Coverage checker — wraps language-specific coverage tools."""

import subprocess
from typing import Optional

from ..config import get_coverage_threshold


COVERAGE_TOOLS = {
    "python": ["pytest", "--cov", "--cov-report=term"],
    "javascript": ["npm", "run", "coverage"],
    "typescript": ["npm", "run", "coverage"],
}


def check_coverage(
    language: Optional[str] = None,
) -> dict:
    """Check test coverage using the appropriate coverage tool."""
    # Get threshold from project config (defaults to 80 if not set)
    target = get_coverage_threshold()

    if language is None:
        # Default to python for this project
        language = "python"

    if language not in COVERAGE_TOOLS:
        return {
            "percentage": 0.0,
            "target": target,
            "met": False,
            "uncovered_files": [],
            "error": f"Coverage checking not supported for {language}",
        }

    coverage_cmd = COVERAGE_TOOLS[language]

    try:
        result = subprocess.run(
            coverage_cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        percentage = 0.0
        uncovered_files = []

        if language == "python":
            # Parse pytest-cov output
            # Example: "TOTAL    123    45    63%"
            for line in result.stdout.split("\n"):
                if "TOTAL" in line:
                    parts = line.split()
                    for part in parts:
                        if "%" in part:
                            try:
                                percentage = float(part.rstrip("%"))
                            except ValueError:
                                pass

                # Look for files with low coverage (below configured threshold)
                if "%" in line and "TOTAL" not in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "%" in part:
                            try:
                                file_cov = float(part.rstrip("%"))
                                if file_cov < target and i > 0:
                                    # First part is usually the filename
                                    uncovered_files.append(parts[0])
                            except ValueError:
                                pass

        met = percentage >= target

        return {
            "percentage": percentage,
            "target": target,
            "met": met,
            "uncovered_files": uncovered_files,
        }

    except subprocess.TimeoutExpired:
        return {
            "percentage": 0.0,
            "target": target,
            "met": False,
            "uncovered_files": [],
            "error": "Coverage check timed out after 5 minutes",
        }
    except FileNotFoundError:
        return {
            "percentage": 0.0,
            "target": target,
            "met": False,
            "uncovered_files": [],
            "error": f"Coverage tool '{coverage_cmd[0]}' not found.",
        }
