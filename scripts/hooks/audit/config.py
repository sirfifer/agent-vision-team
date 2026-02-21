"""Audit configuration loader.

Reads settings from .avt/project-config.json under settings.audit,
following the same cascade pattern as context reinforcement settings.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

# Defaults: audit is opt-in, starts disabled
DEFAULTS = {
    "enabled": False,
    "level": "STANDARD",
    "settle_seconds": 5,
    "ring_buffer_size": 100,
    "anomaly_flush": True,
    "llm_analysis_enabled": True,
    "models": {
        "triage": "haiku",
        "analysis": "sonnet",
        "deep_dive": "opus",
    },
    "thresholds": {
        "governance_block_rate": 0.5,
        "reinforcement_skip_rate": 0.7,
        "event_rate_spike_multiplier": 3.0,
        "idle_block_count": 3,
    },
    "retention": {
        "events": "30d",
        "recommendations": "90d",
        "statistics": "365d",
    },
}


def load_audit_config() -> dict:
    """Load audit configuration with defaults, overridden by project config."""
    effective = _deep_copy(DEFAULTS)

    project_path = Path(_PROJECT_DIR) / ".avt" / "project-config.json"
    if project_path.exists():
        try:
            cfg = json.loads(project_path.read_text())
            audit_cfg = cfg.get("settings", {}).get("audit", {})
            _deep_merge(effective, audit_cfg)
        except (json.JSONDecodeError, OSError):
            pass

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
