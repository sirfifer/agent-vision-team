"""Test runner wrapper — routes to the appropriate test runner per language."""

import subprocess
from typing import Optional


TEST_RUNNERS = {
    "swift": ["xcodebuild", "test"],
    "python": ["pytest", "-v", "--tb=short"],
    "rust": ["cargo", "test"],
    "typescript": ["npm", "test"],
    "javascript": ["npm", "test"],
}


def run_tests(
    scope: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Run tests using the appropriate test runner."""
    if language is None:
        # Default to python for this project
        language = "python"

    if language not in TEST_RUNNERS:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failures": [],
            "error": f"Unsupported language: {language}",
        }

    test_cmd = TEST_RUNNERS[language].copy()

    # Add scope if specified
    if scope and scope != "all":
        test_cmd.append(scope)

    try:
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes for tests
        )

        # Parse output based on language
        passed = 0
        failed = 0
        skipped = 0
        failures = []

        if language == "python":
            # Parse pytest output
            for line in result.stdout.split("\n"):
                if " passed" in line:
                    # Example: "8 passed in 0.10s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed" and i > 0:
                            try:
                                passed = int(parts[i - 1])
                            except ValueError:
                                pass
                        elif part == "failed" and i > 0:
                            try:
                                failed = int(parts[i - 1])
                            except ValueError:
                                pass
                        elif part == "skipped" and i > 0:
                            try:
                                skipped = int(parts[i - 1])
                            except ValueError:
                                pass

                # Capture FAILED test names
                if "FAILED" in line:
                    failures.append(line.strip())

        elif language in ["typescript", "javascript"]:
            # Parse npm test output (varies by test runner)
            # This is a simplified parser
            output_lower = result.stdout.lower()
            if "pass" in output_lower:
                # Try to extract numbers
                lines = result.stdout.split("\n")
                for line in lines:
                    if "passed" in line.lower() or "pass" in line.lower():
                        parts = line.split()
                        for part in parts:
                            if part.isdigit():
                                passed = int(part)
                                break

        return {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "failures": failures,
        }

    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failures": [],
            "error": "Tests timed out after 5 minutes",
        }
    except FileNotFoundError:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failures": [],
            "error": f"Test runner '{test_cmd[0]}' not found. Install it to run tests.",
        }
