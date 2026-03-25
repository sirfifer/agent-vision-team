"""Compatibility monitor core module.

Provides dependency manifest loading, finding classification, delta detection,
report generation, and adaptive follow-up logic for the Claude Code
compatibility monitoring system.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

# Priority definitions matching the intelligence search playbook
PRIORITY_DEFS = {
    "P0": "Critical: Confirmed conflict. System breaks on update.",
    "P1": "High: Deprecation or semantic change requiring near-term action.",
    "P2": "Strategic: New feature or opportunity to evaluate for adoption.",
    "P3": "Track: Ecosystem direction, monitor only.",
}

# Category values for findings
CATEGORIES = ("Conflict", "Opportunity", "General Intelligence")
CONFIDENCE_LEVELS = ("Confirmed", "Likely", "Rumor")
ACTIONS = ("Immediate fix", "Plan migration", "Evaluate adoption", "Monitor", "None")


def load_dependency_manifest(project_dir: str | None = None) -> dict:
    """Parse platform-deps.yaml and return structured dependency data.

    Returns:
        Dict with keys: version, claude_code_minimum, dependencies (list of dicts).
        Each dependency dict has: name, category, description, critical, used_by, etc.
    """
    root = Path(project_dir or _PROJECT_DIR)
    deps_path = root / "scripts" / "validation" / "platform-deps.yaml"

    if not deps_path.exists():
        return {"version": "unknown", "claude_code_minimum": "unknown", "dependencies": []}

    try:
        # Use PyYAML if available, fall back to basic parsing
        import yaml
        with open(deps_path) as f:
            raw = yaml.safe_load(f)
    except ImportError:
        # Minimal YAML-like parsing for the flat structure we need
        raw = _parse_deps_yaml_minimal(deps_path)

    if not raw or not isinstance(raw, dict):
        return {"version": "unknown", "claude_code_minimum": "unknown", "dependencies": []}

    deps_list = []
    raw_deps = raw.get("dependencies", {})
    if isinstance(raw_deps, dict):
        for dep_name, dep_data in raw_deps.items():
            if isinstance(dep_data, dict):
                dep_data["name"] = dep_name
                deps_list.append(dep_data)

    return {
        "version": raw.get("version", "unknown"),
        "claude_code_minimum": raw.get("claude_code_minimum", "unknown"),
        "dependencies": deps_list,
    }


def _parse_deps_yaml_minimal(path: Path) -> dict | None:
    """Minimal YAML parser for platform-deps.yaml when PyYAML is unavailable.

    Handles the specific structure of platform-deps.yaml: top-level scalars,
    a nested 'dependencies' dict with two-level nesting, and list values
    prefixed with '- '.
    """
    try:
        text = path.read_text()
        result: dict[str, Any] = {}
        dependencies: dict[str, dict[str, Any]] = {}
        in_dependencies = False
        current_dep: str | None = None
        current_key: str | None = None

        for line in text.splitlines():
            # Skip comments and blank lines
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Detect indentation level
            indent = len(line) - len(line.lstrip())

            if indent == 0:
                # Top-level key
                in_dependencies = False
                current_dep = None
                if ":" in stripped:
                    key, _, value = stripped.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key == "dependencies":
                        in_dependencies = True
                    elif value and value != "null":
                        result[key] = value

            elif in_dependencies and indent == 2 and ":" in stripped and not stripped.startswith("-"):
                # Dependency name (2-space indent under dependencies)
                dep_name, _, value = stripped.partition(":")
                dep_name = dep_name.strip()
                value = value.strip()
                if not value:
                    current_dep = dep_name
                    dependencies[current_dep] = {}
                    current_key = None

            elif in_dependencies and current_dep and indent == 4:
                if stripped.startswith("- "):
                    # List item under current_key
                    if current_key and current_key in dependencies[current_dep]:
                        item = stripped[2:].strip().strip('"').strip("'")
                        dependencies[current_dep][current_key].append(item)
                elif ":" in stripped:
                    # Key-value pair within a dependency
                    key, _, value = stripped.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if value:
                        # Parse booleans
                        if value == "true":
                            dependencies[current_dep][key] = True
                        elif value == "false":
                            dependencies[current_dep][key] = False
                        else:
                            dependencies[current_dep][key] = value
                        current_key = None
                    else:
                        # Key with no value; next indented lines are its children
                        current_key = key
                        dependencies[current_dep][key] = []

            elif in_dependencies and current_dep and indent == 6 and stripped.startswith("- "):
                # List item at 6-space indent (under a 4-space key like used_by or models)
                if current_key and current_key in dependencies[current_dep]:
                    item = stripped[2:].strip().strip('"').strip("'")
                    dependencies[current_dep][current_key].append(item)

            elif in_dependencies and current_dep and indent == 6 and ":" in stripped:
                # Nested key-value at 6-space indent (under args or similar)
                if current_key:
                    key, _, value = stripped.partition(":")
                    value = value.strip().strip('"').strip("'")
                    if isinstance(dependencies[current_dep].get(current_key), list):
                        # Convert list to dict for nested key-value
                        if not dependencies[current_dep][current_key]:
                            dependencies[current_dep][current_key] = {}
                    if isinstance(dependencies[current_dep].get(current_key), dict):
                        dependencies[current_dep][current_key][key.strip()] = value

        if dependencies:
            result["dependencies"] = dependencies

        return result
    except Exception:
        return None


def classify_finding(finding: dict) -> str:
    """Apply P0-P3 priority classification to a finding.

    Args:
        finding: Dict with keys: category, affected_component, confidence,
                 is_breaking, is_deprecation, is_opportunity

    Returns:
        Priority string: "P0", "P1", "P2", or "P3"
    """
    category = finding.get("category", "")
    confidence = finding.get("confidence", "Rumor")
    is_breaking = finding.get("is_breaking", False)
    is_deprecation = finding.get("is_deprecation", False)
    is_opportunity = finding.get("is_opportunity", False)

    # P0: Confirmed breaking change
    if is_breaking and confidence == "Confirmed":
        return "P0"

    # P1: Likely breaking, or confirmed deprecation/semantic change
    if is_breaking and confidence == "Likely":
        return "P1"
    if is_deprecation and confidence in ("Confirmed", "Likely"):
        return "P1"

    # P2: Opportunity or strategic change
    if is_opportunity and confidence in ("Confirmed", "Likely"):
        return "P2"
    if category == "Conflict" and confidence == "Rumor":
        return "P2"

    # P3: Everything else
    return "P3"


def is_known_finding(finding: dict, baseline_observations: list[str]) -> bool:
    """Check if a finding is already known from previous checks.

    Args:
        finding: Dict with at minimum a 'title' key
        baseline_observations: List of observation strings from KG

    Returns:
        True if this finding matches an existing observation
    """
    title = finding.get("title", "").lower()
    source = finding.get("source", "").lower()

    if not title:
        return False

    for obs in baseline_observations:
        obs_lower = obs.lower()
        # Match on title substring or source URL
        if title in obs_lower:
            return True
        if source and source in obs_lower:
            return True

    return False


def generate_report(
    findings: list[dict],
    manifest: dict,
    check_date: str | None = None,
) -> str:
    """Produce a change report markdown following the intelligence search template.

    Args:
        findings: List of classified finding dicts
        manifest: Dependency manifest from load_dependency_manifest()
        check_date: ISO date string (defaults to today)

    Returns:
        Markdown report string
    """
    if check_date is None:
        check_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Group findings by priority
    by_priority: dict[str, list[dict]] = {"P0": [], "P1": [], "P2": [], "P3": []}
    for f in findings:
        priority = f.get("priority", "P3")
        by_priority.setdefault(priority, []).append(f)

    has_critical = bool(by_priority["P0"])
    has_high = bool(by_priority["P1"])

    # Executive summary
    total = len(findings)
    p0_count = len(by_priority["P0"])
    p1_count = len(by_priority["P1"])
    p2_count = len(by_priority["P2"])
    p3_count = len(by_priority["P3"])

    if has_critical:
        summary = f"CRITICAL: {p0_count} breaking change(s) detected requiring immediate action."
    elif has_high:
        summary = f"{p1_count} high-priority finding(s) requiring near-term attention."
    elif total > 0:
        summary = f"{total} finding(s) detected, none critical. Review at next planning session."
    else:
        summary = "No significant changes detected. Claude Code platform is stable for AVT."

    lines = [
        "# Claude Code Feature Intelligence Report",
        "",
        f"**Generated**: {check_date}",
        f"**Claude Code Minimum Version**: {manifest.get('claude_code_minimum', 'unknown')}",
        f"**Dependencies Tracked**: {len(manifest.get('dependencies', []))}",
        "",
        "## Executive Summary",
        "",
        summary,
        f"Findings: {p0_count} P0, {p1_count} P1, {p2_count} P2, {p3_count} P3.",
        "",
        "---",
        "",
    ]

    # P0 section
    lines.append("## P0: Critical (Immediate Action Required)")
    lines.append("")
    if by_priority["P0"]:
        for f in by_priority["P0"]:
            lines.extend(_format_finding(f))
    else:
        lines.append("None identified.")
    lines.extend(["", "---", ""])

    # P1 section
    lines.append("## P1: High Priority (Near-term Action)")
    lines.append("")
    if by_priority["P1"]:
        for f in by_priority["P1"]:
            lines.extend(_format_finding(f))
    else:
        lines.append("None identified.")
    lines.extend(["", "---", ""])

    # P2 section
    lines.append("## P2: Strategic (Evaluate for Adoption)")
    lines.append("")
    if by_priority["P2"]:
        for f in by_priority["P2"]:
            lines.extend(_format_finding(f))
    else:
        lines.append("None identified.")
    lines.extend(["", "---", ""])

    # P3 as table
    lines.append("## P3: Track (Monitor Only)")
    lines.append("")
    if by_priority["P3"]:
        lines.append("| Finding | Category | Source | Notes |")
        lines.append("|---------|----------|--------|-------|")
        for f in by_priority["P3"]:
            title = f.get("title", "Unknown")
            cat = f.get("category", "")
            source = f.get("source", "")
            notes = f.get("details", "")[:80]
            lines.append(f"| {title} | {cat} | {source} | {notes} |")
    else:
        lines.append("None identified.")
    lines.extend(["", "---", ""])

    # Action items summary
    lines.append("## Action Items Summary")
    lines.append("")
    lines.append("### Immediate (This Week)")
    if by_priority["P0"] or by_priority["P1"]:
        for f in by_priority["P0"] + by_priority["P1"]:
            action = f.get("recommended_action", "Review and address")
            lines.append(f"- [ ] {f.get('title', 'Unknown')}: {action}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("### Strategic (This Quarter)")
    if by_priority["P2"]:
        for f in by_priority["P2"]:
            action = f.get("recommended_action", "Evaluate for adoption")
            lines.append(f"- [ ] {f.get('title', 'Unknown')}: {action}")
    else:
        lines.append("- None")
    lines.append("")

    return "\n".join(lines)


def _format_finding(finding: dict) -> list[str]:
    """Format a single P0/P1/P2 finding as markdown."""
    lines = [
        f"### {finding.get('title', 'Unknown Finding')}",
        f"- **Category**: {finding.get('category', 'Unknown')}",
        f"- **Affected Component**: {finding.get('affected_component', 'Unknown')}",
        f"- **Confidence**: {finding.get('confidence', 'Unknown')}",
        f"- **Source**: {finding.get('source', 'Unknown')}",
        f"- **Details**: {finding.get('details', 'No details')}",
        f"- **Impact on AVT**: {finding.get('impact', 'Unknown')}",
    ]

    files_to_modify = finding.get("files_to_modify", [])
    if files_to_modify:
        lines.append("- **Files to Modify**:")
        for file_entry in files_to_modify:
            lines.append(f"  - `{file_entry}`")

    lines.append(f"- **Recommended Action**: {finding.get('recommended_action', 'Review')}")
    lines.append("")
    return lines


def update_last_run(project_dir: str | None = None) -> None:
    """Write current epoch timestamp to .avt/compatibility-monitor/.last-run-ts."""
    root = Path(project_dir or _PROJECT_DIR)
    compat_dir = root / ".avt" / "compatibility-monitor"
    compat_dir.mkdir(parents=True, exist_ok=True)
    ts_path = compat_dir / ".last-run-ts"
    ts_path.write_text(str(time.time()))


def should_schedule_followup(findings: list[dict]) -> tuple[bool, int, str]:
    """Determine if an adaptive follow-up check should be scheduled.

    Args:
        findings: List of classified finding dicts

    Returns:
        Tuple of (should_follow_up, hours_delay, reason)
    """
    for f in findings:
        confidence = f.get("confidence", "")
        category = f.get("category", "")
        details = f.get("details", "").lower()

        # Pending announcement or release candidate
        pending_signals = [
            "release candidate", "upcoming release", "pending announcement",
            "beta", "preview", "coming soon", "expected to", "planned for",
            "will be released", "pre-release",
        ]

        if any(signal in details for signal in pending_signals):
            if category == "Conflict":
                return (True, 4, f"Pending change may affect AVT: {f.get('title', 'unknown')}")
            return (True, 6, f"Upcoming change worth monitoring: {f.get('title', 'unknown')}")

        # Unconfirmed breaking change
        if f.get("is_breaking") and confidence == "Likely":
            return (True, 4, f"Unconfirmed breaking change needs verification: {f.get('title', 'unknown')}")

    return (False, 0, "")


def write_report(
    report_content: str,
    findings: list[dict],
    project_dir: str | None = None,
    check_date: str | None = None,
) -> list[str]:
    """Write report to appropriate locations based on finding severity.

    Returns list of paths where report was written.
    """
    root = Path(project_dir or _PROJECT_DIR)
    if check_date is None:
        check_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    written_paths = []

    # Always write to ephemeral location
    compat_dir = root / ".avt" / "compatibility-reports"
    compat_dir.mkdir(parents=True, exist_ok=True)
    ephemeral_path = compat_dir / f"cr-{check_date}-cc-compat.md"
    ephemeral_path.write_text(report_content)
    written_paths.append(str(ephemeral_path))

    # Promote to docs/reports/ if P0 or P1 findings exist
    has_critical = any(
        f.get("priority") in ("P0", "P1") for f in findings
    )
    if has_critical:
        reports_dir = root / "docs" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        promoted_path = reports_dir / f"claude-code-intel-{check_date}.md"
        promoted_path.write_text(report_content)
        written_paths.append(str(promoted_path))

    return written_paths
