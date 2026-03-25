"""Tests for compatibility monitor configuration loader."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with .avt/project-config.json."""
    avt_dir = tmp_path / ".avt"
    avt_dir.mkdir()
    return tmp_path


@pytest.fixture
def _patch_project_dir(tmp_project):
    """Patch _PROJECT_DIR to point to tmp_project."""
    with mock.patch("compatibility.config._PROJECT_DIR", str(tmp_project)):
        yield tmp_project


def _write_config(project_dir: Path, compat_cfg: dict) -> None:
    """Write a project-config.json with the given compatibilityMonitor settings."""
    config = {"settings": {"compatibilityMonitor": compat_cfg}}
    config_path = project_dir / ".avt" / "project-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config))


class TestDefaults:
    def test_returns_defaults_when_no_config(self, _patch_project_dir):
        from compatibility.config import load_compat_config

        cfg = load_compat_config()
        assert cfg["enabled"] is False
        assert cfg["check_interval_hours"] == 24
        assert cfg["model_hint"] == "sonnet"
        assert cfg["adaptive_followups"] is True
        assert cfg["notification_threshold"] == "P1"

    def test_returns_defaults_when_empty_config(self, _patch_project_dir):
        _write_config(_patch_project_dir, {})
        from compatibility.config import load_compat_config

        cfg = load_compat_config()
        assert cfg["enabled"] is False
        assert cfg["check_interval_hours"] == 24


class TestProjectConfigOverride:
    def test_enabled_override(self, _patch_project_dir):
        _write_config(_patch_project_dir, {"enabled": True})
        from compatibility.config import load_compat_config

        cfg = load_compat_config()
        assert cfg["enabled"] is True

    def test_interval_override(self, _patch_project_dir):
        _write_config(_patch_project_dir, {"check_interval_hours": 12})
        from compatibility.config import load_compat_config

        cfg = load_compat_config()
        assert cfg["check_interval_hours"] == 12

    def test_partial_override_preserves_defaults(self, _patch_project_dir):
        _write_config(_patch_project_dir, {"enabled": True, "model_hint": "opus"})
        from compatibility.config import load_compat_config

        cfg = load_compat_config()
        assert cfg["enabled"] is True
        assert cfg["model_hint"] == "opus"
        assert cfg["check_interval_hours"] == 24  # default preserved
        assert cfg["adaptive_followups"] is True  # default preserved

    def test_notification_threshold_override(self, _patch_project_dir):
        _write_config(_patch_project_dir, {"notification_threshold": "P0"})
        from compatibility.config import load_compat_config

        cfg = load_compat_config()
        assert cfg["notification_threshold"] == "P0"


class TestEnvVarOverride:
    def test_env_var_enables(self, _patch_project_dir):
        from compatibility.config import load_compat_config

        with mock.patch.dict(os.environ, {"AVT_COMPAT_MONITOR_ENABLED": "true"}):
            cfg = load_compat_config()
        assert cfg["enabled"] is True

    def test_env_var_disables(self, _patch_project_dir):
        _write_config(_patch_project_dir, {"enabled": True})
        from compatibility.config import load_compat_config

        with mock.patch.dict(os.environ, {"AVT_COMPAT_MONITOR_ENABLED": "false"}):
            cfg = load_compat_config()
        assert cfg["enabled"] is False

    def test_env_var_accepts_1(self, _patch_project_dir):
        from compatibility.config import load_compat_config

        with mock.patch.dict(os.environ, {"AVT_COMPAT_MONITOR_ENABLED": "1"}):
            cfg = load_compat_config()
        assert cfg["enabled"] is True

    def test_env_var_takes_precedence_over_config(self, _patch_project_dir):
        _write_config(_patch_project_dir, {"enabled": False})
        from compatibility.config import load_compat_config

        with mock.patch.dict(os.environ, {"AVT_COMPAT_MONITOR_ENABLED": "yes"}):
            cfg = load_compat_config()
        assert cfg["enabled"] is True


class TestMalformedConfig:
    def test_invalid_json_returns_defaults(self, _patch_project_dir):
        config_path = _patch_project_dir / ".avt" / "project-config.json"
        config_path.write_text("not valid json {{{")
        from compatibility.config import load_compat_config

        cfg = load_compat_config()
        assert cfg["enabled"] is False
        assert cfg["check_interval_hours"] == 24

    def test_missing_settings_key_returns_defaults(self, _patch_project_dir):
        config_path = _patch_project_dir / ".avt" / "project-config.json"
        config_path.write_text(json.dumps({"version": 1}))
        from compatibility.config import load_compat_config

        cfg = load_compat_config()
        assert cfg["enabled"] is False
