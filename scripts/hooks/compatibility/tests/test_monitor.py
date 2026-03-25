"""Tests for compatibility monitor core module."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with minimal structure."""
    avt_dir = tmp_path / ".avt"
    avt_dir.mkdir()
    (tmp_path / ".avt" / "compatibility-reports").mkdir()
    (tmp_path / ".avt" / "compatibility-monitor").mkdir()
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_deps_yaml(tmp_project):
    """Write a minimal platform-deps.yaml."""
    deps_dir = tmp_project / "scripts" / "validation"
    deps_dir.mkdir(parents=True)
    deps_path = deps_dir / "platform-deps.yaml"
    deps_path.write_text("""\
version: "1.0"
claude_code_minimum: "2.1.33"

dependencies:
  hook_post_tool_use_fires:
    category: hooks
    description: "PostToolUse hooks fire on TaskCreate"
    critical: true
    used_by:
      - scripts/hooks/governance-task-intercept.py
  mcp_user_scope_config:
    category: mcp
    description: "~/.claude/mcp.json defines all 3 required servers"
    critical: true
    used_by:
      - CLAUDE.md
""")
    return tmp_project


@pytest.fixture
def sample_findings():
    """Return a list of sample findings covering all priorities."""
    return [
        {
            "title": "SSE transport deprecated in MCP spec",
            "category": "Conflict",
            "affected_component": "MCP Servers",
            "confidence": "Confirmed",
            "is_breaking": True,
            "is_deprecation": False,
            "is_opportunity": False,
            "source": "https://github.com/modelcontextprotocol/specification/issues/123",
            "details": "SSE transport officially deprecated in MCP 2.0 spec",
            "impact": "All 3 MCP servers use SSE transport",
            "files_to_modify": ["mcp-servers/knowledge-graph/server.py"],
            "recommended_action": "Migrate to streamable HTTP transport",
        },
        {
            "title": "Hook system adding PreMessage type",
            "category": "Opportunity",
            "affected_component": "Hooks",
            "confidence": "Confirmed",
            "is_breaking": False,
            "is_deprecation": False,
            "is_opportunity": True,
            "source": "https://docs.anthropic.com/claude-code/hooks",
            "details": "New PreMessage hook type available",
            "impact": "Could strengthen context reinforcement",
            "recommended_action": "Evaluate adoption for context reinforcement",
        },
        {
            "title": "claude --print flag may change",
            "category": "Conflict",
            "affected_component": "CLI",
            "confidence": "Rumor",
            "is_breaking": True,
            "is_deprecation": False,
            "is_opportunity": False,
            "source": "https://reddit.com/r/ClaudeAI/...",
            "details": "Community reports suggest --print flag rename",
            "impact": "Governance reviewer uses claude --print",
            "recommended_action": "Monitor for confirmation",
        },
        {
            "title": "New Haiku model alias behavior",
            "category": "General Intelligence",
            "affected_component": "Model Resolution",
            "confidence": "Rumor",
            "is_breaking": False,
            "is_deprecation": False,
            "is_opportunity": False,
            "source": "https://news.ycombinator.com/...",
            "details": "Discussion about new model aliasing behavior",
            "impact": "Minimal",
            "recommended_action": "Monitor",
        },
    ]


# ---------------------------------------------------------------------------
# classify_finding tests
# ---------------------------------------------------------------------------

class TestClassifyFinding:
    def test_confirmed_breaking_is_p0(self):
        from compatibility.monitor import classify_finding

        result = classify_finding({
            "category": "Conflict",
            "confidence": "Confirmed",
            "is_breaking": True,
        })
        assert result == "P0"

    def test_likely_breaking_is_p1(self):
        from compatibility.monitor import classify_finding

        result = classify_finding({
            "category": "Conflict",
            "confidence": "Likely",
            "is_breaking": True,
        })
        assert result == "P1"

    def test_confirmed_deprecation_is_p1(self):
        from compatibility.monitor import classify_finding

        result = classify_finding({
            "category": "Conflict",
            "confidence": "Confirmed",
            "is_deprecation": True,
        })
        assert result == "P1"

    def test_likely_deprecation_is_p1(self):
        from compatibility.monitor import classify_finding

        result = classify_finding({
            "category": "Conflict",
            "confidence": "Likely",
            "is_deprecation": True,
        })
        assert result == "P1"

    def test_confirmed_opportunity_is_p2(self):
        from compatibility.monitor import classify_finding

        result = classify_finding({
            "category": "Opportunity",
            "confidence": "Confirmed",
            "is_opportunity": True,
        })
        assert result == "P2"

    def test_rumor_conflict_is_p2(self):
        from compatibility.monitor import classify_finding

        result = classify_finding({
            "category": "Conflict",
            "confidence": "Rumor",
            "is_breaking": False,
        })
        assert result == "P2"

    def test_generic_finding_is_p3(self):
        from compatibility.monitor import classify_finding

        result = classify_finding({
            "category": "General Intelligence",
            "confidence": "Rumor",
        })
        assert result == "P3"

    def test_empty_finding_is_p3(self):
        from compatibility.monitor import classify_finding

        result = classify_finding({})
        assert result == "P3"


# ---------------------------------------------------------------------------
# is_known_finding tests
# ---------------------------------------------------------------------------

class TestIsKnownFinding:
    def test_known_title_matches(self):
        from compatibility.monitor import is_known_finding

        finding = {"title": "SSE transport deprecated"}
        baseline = ["2026-03-20: SSE transport deprecated in MCP spec"]
        assert is_known_finding(finding, baseline) is True

    def test_known_source_matches(self):
        from compatibility.monitor import is_known_finding

        finding = {"title": "Something new", "source": "https://github.com/issue/123"}
        baseline = ["Found at https://github.com/issue/123"]
        assert is_known_finding(finding, baseline) is True

    def test_unknown_finding_not_matched(self):
        from compatibility.monitor import is_known_finding

        finding = {"title": "Brand new feature"}
        baseline = ["Old finding about hooks", "Another old finding"]
        assert is_known_finding(finding, baseline) is False

    def test_empty_title_not_matched(self):
        from compatibility.monitor import is_known_finding

        finding = {"title": ""}
        baseline = ["Some observation"]
        assert is_known_finding(finding, baseline) is False

    def test_empty_baseline_not_matched(self):
        from compatibility.monitor import is_known_finding

        finding = {"title": "Something"}
        assert is_known_finding(finding, []) is False

    def test_case_insensitive_match(self):
        from compatibility.monitor import is_known_finding

        finding = {"title": "MCP Transport Change"}
        baseline = ["mcp transport change detected"]
        assert is_known_finding(finding, baseline) is True


# ---------------------------------------------------------------------------
# generate_report tests
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_report_has_header(self, sample_findings):
        from compatibility.monitor import generate_report

        report = generate_report(sample_findings, {"claude_code_minimum": "2.1.33", "dependencies": []})
        assert "# Claude Code Feature Intelligence Report" in report

    def test_report_has_all_priority_sections(self, sample_findings):
        from compatibility.monitor import generate_report

        # Add priority to findings
        for f in sample_findings:
            from compatibility.monitor import classify_finding
            f["priority"] = classify_finding(f)

        report = generate_report(sample_findings, {"claude_code_minimum": "2.1.33", "dependencies": []})
        assert "## P0: Critical" in report
        assert "## P1: High Priority" in report
        assert "## P2: Strategic" in report
        assert "## P3: Track" in report

    def test_report_has_executive_summary(self, sample_findings):
        from compatibility.monitor import generate_report, classify_finding

        for f in sample_findings:
            f["priority"] = classify_finding(f)

        report = generate_report(sample_findings, {"claude_code_minimum": "2.1.33", "dependencies": []})
        assert "## Executive Summary" in report
        assert "CRITICAL" in report  # Has P0 finding

    def test_empty_findings_report(self):
        from compatibility.monitor import generate_report

        report = generate_report([], {"claude_code_minimum": "2.1.33", "dependencies": []})
        assert "No significant changes detected" in report
        assert "None identified" in report

    def test_report_includes_check_date(self):
        from compatibility.monitor import generate_report

        report = generate_report([], {"claude_code_minimum": "2.1.33", "dependencies": []}, check_date="2026-03-23")
        assert "2026-03-23" in report

    def test_report_includes_action_items(self, sample_findings):
        from compatibility.monitor import generate_report, classify_finding

        for f in sample_findings:
            f["priority"] = classify_finding(f)

        report = generate_report(sample_findings, {"claude_code_minimum": "2.1.33", "dependencies": []})
        assert "## Action Items Summary" in report
        assert "Immediate (This Week)" in report


# ---------------------------------------------------------------------------
# update_last_run tests
# ---------------------------------------------------------------------------

class TestUpdateLastRun:
    def test_creates_timestamp_file(self, tmp_project):
        from compatibility.monitor import update_last_run

        update_last_run(str(tmp_project))
        ts_path = tmp_project / ".avt" / "compatibility-monitor" / ".last-run-ts"
        assert ts_path.exists()
        ts = float(ts_path.read_text().strip())
        assert abs(ts - time.time()) < 5  # within 5 seconds

    def test_overwrites_existing_timestamp(self, tmp_project):
        from compatibility.monitor import update_last_run

        ts_path = tmp_project / ".avt" / "compatibility-monitor" / ".last-run-ts"
        ts_path.write_text("1000.0")

        update_last_run(str(tmp_project))
        ts = float(ts_path.read_text().strip())
        assert ts > 1000.0

    def test_creates_directory_if_missing(self, tmp_path):
        from compatibility.monitor import update_last_run

        update_last_run(str(tmp_path))
        ts_path = tmp_path / ".avt" / "compatibility-monitor" / ".last-run-ts"
        assert ts_path.exists()


# ---------------------------------------------------------------------------
# should_schedule_followup tests
# ---------------------------------------------------------------------------

class TestShouldScheduleFollowup:
    def test_no_followup_for_normal_findings(self):
        from compatibility.monitor import should_schedule_followup

        findings = [{"title": "Some change", "details": "A confirmed breaking change", "confidence": "Confirmed"}]
        should, hours, reason = should_schedule_followup(findings)
        assert should is False

    def test_followup_for_pending_announcement(self):
        from compatibility.monitor import should_schedule_followup

        findings = [{
            "title": "New release",
            "category": "Conflict",
            "details": "Release candidate spotted, expected to land today",
            "confidence": "Likely",
        }]
        should, hours, reason = should_schedule_followup(findings)
        assert should is True
        assert hours == 4
        assert "New release" in reason

    def test_followup_for_upcoming_release(self):
        from compatibility.monitor import should_schedule_followup

        findings = [{
            "title": "MCP 2.0",
            "category": "Opportunity",
            "details": "MCP 2.0 coming soon with new features",
            "confidence": "Likely",
        }]
        should, hours, reason = should_schedule_followup(findings)
        assert should is True
        assert hours == 6

    def test_followup_for_unconfirmed_breaking(self):
        from compatibility.monitor import should_schedule_followup

        findings = [{
            "title": "Hook change",
            "details": "Reports of hook behavior change",
            "confidence": "Likely",
            "is_breaking": True,
        }]
        should, hours, reason = should_schedule_followup(findings)
        assert should is True
        assert hours == 4

    def test_no_followup_for_empty_findings(self):
        from compatibility.monitor import should_schedule_followup

        should, hours, reason = should_schedule_followup([])
        assert should is False


# ---------------------------------------------------------------------------
# write_report tests
# ---------------------------------------------------------------------------

class TestWriteReport:
    def test_writes_to_ephemeral_location(self, tmp_project):
        from compatibility.monitor import write_report

        paths = write_report("# Test Report", [], str(tmp_project), check_date="2026-03-23")
        assert len(paths) == 1
        assert "compatibility-reports" in paths[0]
        assert Path(paths[0]).exists()
        assert Path(paths[0]).read_text() == "# Test Report"

    def test_promotes_on_p0_finding(self, tmp_project):
        from compatibility.monitor import write_report

        findings = [{"priority": "P0", "title": "Critical"}]
        paths = write_report("# Critical Report", findings, str(tmp_project), check_date="2026-03-23")
        assert len(paths) == 2
        assert any("docs/reports" in p for p in paths)
        promoted = [p for p in paths if "docs/reports" in p][0]
        assert Path(promoted).read_text() == "# Critical Report"

    def test_promotes_on_p1_finding(self, tmp_project):
        from compatibility.monitor import write_report

        findings = [{"priority": "P1", "title": "High"}]
        paths = write_report("# High Report", findings, str(tmp_project), check_date="2026-03-23")
        assert len(paths) == 2

    def test_no_promotion_for_p2_only(self, tmp_project):
        from compatibility.monitor import write_report

        findings = [{"priority": "P2", "title": "Strategic"}]
        paths = write_report("# Strategic Report", findings, str(tmp_project), check_date="2026-03-23")
        assert len(paths) == 1
        assert "compatibility-reports" in paths[0]

    def test_naming_convention(self, tmp_project):
        from compatibility.monitor import write_report

        paths = write_report("# Test", [], str(tmp_project), check_date="2026-03-23")
        assert "cr-2026-03-23-cc-compat.md" in paths[0]


# ---------------------------------------------------------------------------
# load_dependency_manifest tests
# ---------------------------------------------------------------------------

class TestLoadDependencyManifest:
    def test_loads_from_yaml(self, sample_deps_yaml):
        from compatibility.monitor import load_dependency_manifest

        manifest = load_dependency_manifest(str(sample_deps_yaml))
        assert manifest["version"] == "1.0"
        assert manifest["claude_code_minimum"] == "2.1.33"
        assert len(manifest["dependencies"]) == 2

    def test_deps_have_names(self, sample_deps_yaml):
        from compatibility.monitor import load_dependency_manifest

        manifest = load_dependency_manifest(str(sample_deps_yaml))
        names = [d["name"] for d in manifest["dependencies"]]
        assert "hook_post_tool_use_fires" in names
        assert "mcp_user_scope_config" in names

    def test_missing_file_returns_empty(self, tmp_path):
        from compatibility.monitor import load_dependency_manifest

        manifest = load_dependency_manifest(str(tmp_path))
        assert manifest["version"] == "unknown"
        assert manifest["dependencies"] == []

    def test_deps_have_category(self, sample_deps_yaml):
        from compatibility.monitor import load_dependency_manifest

        manifest = load_dependency_manifest(str(sample_deps_yaml))
        categories = {d["category"] for d in manifest["dependencies"]}
        assert "hooks" in categories
        assert "mcp" in categories
