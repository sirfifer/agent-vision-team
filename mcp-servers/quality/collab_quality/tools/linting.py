"""Linter wrapper — routes to the appropriate linter per language."""

import json
import subprocess
from pathlib import Path
from typing import Optional

LINTERS = {
    "swift": ["swiftlint", "lint", "--reporter", "json"],
    "python": ["ruff", "check", "--output-format=json"],
    "rust": ["cargo", "clippy", "--message-format=json"],
    "typescript": ["eslint", "--format=json"],
    "javascript": ["eslint", "--format=json"],
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


def run_lint(
    files: Optional[list[str]] = None,
    language: Optional[str] = None,
) -> dict:
    """Run linting using the appropriate linter."""
    if files is None or len(files) == 0:
        return {"findings": [], "auto_fixable": 0, "total": 0, "error": "No files specified"}

    # Detect language if not specified
    if language is None and len(files) > 0:
        language = detect_language(files[0])

    if language is None or language not in LINTERS:
        return {
            "findings": [],
            "auto_fixable": 0,
            "total": 0,
            "error": f"Unsupported or undetected language: {language}",
        }

    linter_cmd = LINTERS[language]

    try:
        # Run linter
        result = subprocess.run(
            linter_cmd + files,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Parse JSON output (most linters support JSON)
        findings = []
        auto_fixable = 0

        if result.stdout:
            try:
                if language == "python":
                    # Ruff JSON format
                    lint_results = json.loads(result.stdout)
                    for item in lint_results:
                        finding = {
                            "file": item.get("filename"),
                            "line": item.get("location", {}).get("row"),
                            "column": item.get("location", {}).get("column"),
                            "severity": item.get("code"),
                            "message": item.get("message"),
                            "rule": item.get("code"),
                        }
                        findings.append(finding)
                        if item.get("fix"):
                            auto_fixable += 1

                elif language in ["typescript", "javascript"]:
                    # ESLint JSON format
                    lint_results = json.loads(result.stdout)
                    for file_result in lint_results:
                        for msg in file_result.get("messages", []):
                            finding = {
                                "file": file_result.get("filePath"),
                                "line": msg.get("line"),
                                "column": msg.get("column"),
                                "severity": msg.get("severity"),  # 1 = warning, 2 = error
                                "message": msg.get("message"),
                                "rule": msg.get("ruleId"),
                            }
                            findings.append(finding)
                            if msg.get("fix"):
                                auto_fixable += 1

                elif language == "swift":
                    # SwiftLint JSON format
                    lint_results = json.loads(result.stdout)
                    for item in lint_results:
                        finding = {
                            "file": item.get("file"),
                            "line": item.get("line"),
                            "column": item.get("character"),
                            "severity": item.get("severity"),
                            "message": item.get("reason"),
                            "rule": item.get("rule_id"),
                        }
                        findings.append(finding)

            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "findings": [],
                    "auto_fixable": 0,
                    "total": 0,
                    "error": "Failed to parse linter output",
                    "raw_output": result.stdout[:500],  # First 500 chars
                }

        return {
            "findings": findings,
            "auto_fixable": auto_fixable,
            "total": len(findings),
        }

    except subprocess.TimeoutExpired:
        return {
            "findings": [],
            "auto_fixable": 0,
            "total": 0,
            "error": "Linter timed out after 60 seconds",
        }
    except FileNotFoundError:
        return {
            "findings": [],
            "auto_fixable": 0,
            "total": 0,
            "error": f"Linter '{linter_cmd[0]}' not found. Install it to use linting.",
        }
