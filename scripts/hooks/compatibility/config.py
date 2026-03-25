"""Compatibility monitor configuration loader.

Reads settings from .avt/project-config.json under settings.compatibilityMonitor,
following the same cascade pattern as audit configuration settings.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

# Defaults: compatibility monitor is opt-in, starts disabled
DEFAULTS = {
    "enabled": False,
    "check_interval_hours": 24,
    "model_hint": "sonnet",
    "adaptive_followups": True,
    "notification_threshold": "P1",
}


def load_compat_config() -> dict:
    """Load compatibility monitor configuration with defaults.

    The enabled state can also be set via the AVT_COMPAT_MONITOR_ENABLED
    environment variable, which takes precedence over config file settings.
    """
    effective = _deep_copy(DEFAULTS)

    project_path = Path(_PROJECT_DIR) / ".avt" / "project-config.json"
    if project_path.exists():
        try:
            cfg = json.loads(project_path.read_text())
            compat_cfg = cfg.get("settings", {}).get("compatibilityMonitor", {})
            _deep_merge(effective, compat_cfg)
        except (json.JSONDecodeError, OSError):
            pass

    # Environment variable override for enabled state
    env_enabled = os.environ.get("AVT_COMPAT_MONITOR_ENABLED")
    if env_enabled is not None:
        effective["enabled"] = env_enabled.lower() in ("1", "true", "yes")

    return effective


def _deep_copy(d: dict) -> dict:
    """Simple deep copy for JSON-compatible dicts."""
    return json.loads(json.dumps(d))


def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base, recursing into nested dicts."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        elif value is not None:
            base[key] = value
