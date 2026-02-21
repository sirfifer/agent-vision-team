"""Tests for prompt builders and directive loading."""

from __future__ import annotations

import json


class TestDirectiveLoading:
    def test_load_default_directives(self):
        from audit.prompts import load_directives

        directives = load_directives()
        assert len(directives) > 0
        for d in directives:
            assert "id" in d
            assert "description" in d
            assert "watches" in d
            assert "haiku_question" in d

    def test_load_from_custom_path(self, tmp_path):
        from audit.prompts import load_directives

        custom = tmp_path / "custom.json"
        custom.write_text(json.dumps({"directives": [{"id": "custom", "watches": ["*"], "haiku_question": "test?"}]}))
        directives = load_directives(custom)
        assert len(directives) == 1
        assert directives[0]["id"] == "custom"

    def test_load_missing_file(self, tmp_path):
        from audit.prompts import load_directives

        directives = load_directives(tmp_path / "nonexistent.json")
        assert directives == []


class TestDirectiveMatching:
    def test_wildcard_matches_all(self):
        from audit.prompts import match_directives

        directives = [{"id": "catch-all", "watches": ["*"]}]
        anomalies = [{"type": "anything.here"}]
        matched = match_directives(anomalies, directives)
        assert len(matched) == 1

    def test_prefix_glob_match(self):
        from audit.prompts import match_directives

        directives = [{"id": "gov", "watches": ["governance.*"]}]
        anomalies = [{"type": "governance.task_pair_created"}]
        matched = match_directives(anomalies, directives)
        assert len(matched) == 1

    def test_underscore_glob_match(self):
        from audit.prompts import match_directives

        directives = [{"id": "ctx", "watches": ["context.reinforcement_*"]}]
        anomalies = [{"type": "context.reinforcement_skipped"}]
        matched = match_directives(anomalies, directives)
        assert len(matched) == 1

    def test_no_match(self):
        from audit.prompts import match_directives

        directives = [{"id": "gov", "watches": ["governance.*"]}]
        anomalies = [{"type": "quality.gate_failed"}]
        matched = match_directives(anomalies, directives)
        assert len(matched) == 0

    def test_exact_match(self):
        from audit.prompts import match_directives

        directives = [{"id": "exact", "watches": ["agent.idle_blocked"]}]
        anomalies = [{"type": "agent.idle_blocked"}]
        matched = match_directives(anomalies, directives)
        assert len(matched) == 1

    def test_multiple_anomaly_types(self):
        from audit.prompts import match_directives

        directives = [
            {"id": "gov", "watches": ["governance.*"]},
            {"id": "ctx", "watches": ["context.*"]},
        ]
        anomalies = [
            {"type": "governance.blocked"},
            {"type": "context.reinforcement_injected"},
        ]
        matched = match_directives(anomalies, directives)
        assert len(matched) == 2


class TestPromptBuilders:
    def test_haiku_prompt_structure(self):
        from audit.prompts import build_haiku_prompt

        prompt = build_haiku_prompt(
            anomalies=[{"type": "test", "severity": "warning", "description": "desc"}],
            directives=[{"id": "d1", "haiku_question": "Is this ok?"}],
            recent_stats={"test.event": 5},
            recent_recommendations=[],
        )
        assert "triage" in prompt.lower()
        assert "JSON" in prompt
        assert "known_pattern" in prompt
        assert "Is this ok?" in prompt

    def test_sonnet_prompt_includes_haiku_result(self):
        from audit.prompts import build_sonnet_prompt

        prompt = build_sonnet_prompt(
            haiku_triage={"verdict": "emerging_pattern", "analysis": "test"},
            anomalies=[],
            directives=[],
            event_window=[],
            current_settings={},
            existing_recommendations=[],
        )
        assert "emerging_pattern" in prompt
        assert "escalate_to_opus" in prompt

    def test_opus_prompt_includes_sonnet_context(self):
        from audit.prompts import build_opus_prompt

        prompt = build_opus_prompt(
            sonnet_analysis={"analysis": "deep", "opus_context": "check systemic"},
            anomalies=[],
            directives=[],
            event_window=[],
            current_settings={},
            existing_recommendations=[],
            session_summaries=[],
        )
        assert "check systemic" in prompt
        assert "root_causes" in prompt
        assert "setting_range_changes" in prompt
