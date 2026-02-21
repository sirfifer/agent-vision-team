"""Tests for audit event emitter."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture
def audit_dir(tmp_path):
    """Create a temporary audit directory and patch the emitter to use it."""
    audit_path = tmp_path / "audit"
    audit_path.mkdir()
    with (
        mock.patch("audit.emitter._AUDIT_DIR", audit_path),
        mock.patch("audit.emitter._EVENTS_PATH", audit_path / "events.jsonl"),
        mock.patch("audit.emitter._SETTLE_TS_PATH", audit_path / ".last-event-ts"),
    ):
        yield audit_path


class TestEmitAuditEvent:
    def test_basic_emission(self, audit_dir):
        from audit.emitter import emit_audit_event

        emit_audit_event("test.event", {"key": "value"}, source="test")
        events_path = audit_dir / "events.jsonl"
        assert events_path.exists()

        lines = events_path.read_text().strip().split("\n")
        assert len(lines) == 1

        event = json.loads(lines[0])
        assert event["type"] == "test.event"
        assert event["data"]["key"] == "value"
        assert event["source"] == "test"
        assert event["id"].startswith("evt-")
        assert "ts" in event
        assert "ts_iso" in event

    def test_multiple_emissions(self, audit_dir):
        from audit.emitter import emit_audit_event

        for i in range(5):
            emit_audit_event(f"test.event.{i}", {"index": i})

        events_path = audit_dir / "events.jsonl"
        lines = events_path.read_text().strip().split("\n")
        assert len(lines) == 5

    def test_session_id_from_arg(self, audit_dir):
        from audit.emitter import emit_audit_event

        emit_audit_event("test.event", {}, session_id="sess-123")
        event = json.loads((audit_dir / "events.jsonl").read_text().strip())
        assert event["session_id"] == "sess-123"

    def test_session_id_from_env(self, audit_dir):
        from audit.emitter import emit_audit_event

        with mock.patch.dict(os.environ, {"CLAUDE_SESSION_ID": "env-sess"}):
            emit_audit_event("test.event", {})

        event = json.loads((audit_dir / "events.jsonl").read_text().strip())
        assert event["session_id"] == "env-sess"

    def test_settle_timestamp_updated(self, audit_dir):
        from audit.emitter import emit_audit_event

        emit_audit_event("test.event", {})
        settle_path = audit_dir / ".last-event-ts"
        assert settle_path.exists()
        ts = float(settle_path.read_text())
        assert ts > 0

    def test_tap_guarantee_no_exception(self, audit_dir):
        """Emitter must never raise, even if directory is not writable."""
        from audit.emitter import emit_audit_event

        with (
            mock.patch("audit.emitter._AUDIT_DIR", Path("/nonexistent/path")),
            mock.patch("audit.emitter._EVENTS_PATH", Path("/nonexistent/path/events.jsonl")),
        ):
            # Should not raise
            emit_audit_event("test.event", {"should": "not crash"})

    def test_json_serializable_data(self, audit_dir):
        from audit.emitter import emit_audit_event

        emit_audit_event(
            "test.event",
            {
                "string": "hello",
                "number": 42,
                "float": 3.14,
                "bool": True,
                "null": None,
                "list": [1, 2, 3],
                "nested": {"a": "b"},
            },
        )
        event = json.loads((audit_dir / "events.jsonl").read_text().strip())
        assert event["data"]["nested"]["a"] == "b"

    def test_agent_field(self, audit_dir):
        from audit.emitter import emit_audit_event

        emit_audit_event("test.event", {}, agent="worker-001")
        event = json.loads((audit_dir / "events.jsonl").read_text().strip())
        assert event["agent"] == "worker-001"
