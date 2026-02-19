"""Project configuration loader for Quality server."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG_PATH = Path(".avt/project-config.json")

# Default values matching extension/src/models/ProjectConfig.ts
DEFAULT_SETTINGS = {
    "mockTests": False,
    "mockTestsForCostlyOps": True,
    "coverageThreshold": 80,
    "autoGovernance": True,
    "qualityGates": {
        "build": True,
        "lint": True,
        "tests": True,
        "coverage": True,
        "findings": True,
    },
    "kgAutoCuration": True,
}

DEFAULT_QUALITY_CONFIG = {
    "testCommands": {},
    "lintCommands": {},
    "buildCommands": {},
    "formatCommands": {},
}


def load_project_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load project configuration from .avt/project-config.json.

    Returns default configuration if file doesn't exist or is invalid.
    """
    path = config_path or DEFAULT_CONFIG_PATH

    if not path.exists():
        return _get_default_config()

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Merge with defaults to ensure all keys exist
            return _merge_with_defaults(config)
    except (json.JSONDecodeError, IOError):
        return _get_default_config()


def _get_default_config() -> Dict[str, Any]:
    """Return default project configuration."""
    return {
        "version": 1,
        "setupComplete": False,
        "languages": [],
        "settings": DEFAULT_SETTINGS.copy(),
        "quality": DEFAULT_QUALITY_CONFIG.copy(),
        "permissions": [],
        "ingestion": {
            "lastVisionIngest": None,
            "lastArchitectureIngest": None,
            "visionDocCount": 0,
            "architectureDocCount": 0,
        },
    }


def _merge_with_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge loaded config with defaults to ensure all keys exist."""
    defaults = _get_default_config()

    # Ensure settings has all required keys
    if "settings" in config:
        config["settings"] = {**DEFAULT_SETTINGS, **config["settings"]}
        # Ensure qualityGates has all required keys
        if "qualityGates" in config["settings"]:
            config["settings"]["qualityGates"] = {
                **DEFAULT_SETTINGS["qualityGates"],
                **config["settings"]["qualityGates"],
            }
    else:
        config["settings"] = DEFAULT_SETTINGS.copy()

    # Ensure quality has all required keys
    if "quality" in config:
        config["quality"] = {**DEFAULT_QUALITY_CONFIG, **config["quality"]}
    else:
        config["quality"] = DEFAULT_QUALITY_CONFIG.copy()

    # Ensure other top-level keys exist
    for key in defaults:
        if key not in config:
            config[key] = defaults[key]

    return config


def get_coverage_threshold(config_path: Optional[Path] = None) -> float:
    """Get the coverage threshold from project config."""
    config = load_project_config(config_path)
    return float(config.get("settings", {}).get("coverageThreshold", 80))


def get_enabled_gates(config_path: Optional[Path] = None) -> Dict[str, bool]:
    """Get which quality gates are enabled."""
    config = load_project_config(config_path)
    return config.get("settings", {}).get("qualityGates", DEFAULT_SETTINGS["qualityGates"])


def is_mock_tests_enabled(config_path: Optional[Path] = None) -> bool:
    """Check if mock tests are enabled (not recommended)."""
    config = load_project_config(config_path)
    return config.get("settings", {}).get("mockTests", False)


def is_mock_costly_ops_enabled(config_path: Optional[Path] = None) -> bool:
    """Check if mock tests for costly operations are enabled (recommended)."""
    config = load_project_config(config_path)
    return config.get("settings", {}).get("mockTestsForCostlyOps", True)


def get_test_command(language: str, config_path: Optional[Path] = None) -> Optional[str]:
    """Get the test command for a specific language."""
    config = load_project_config(config_path)
    return config.get("quality", {}).get("testCommands", {}).get(language)


def get_lint_command(language: str, config_path: Optional[Path] = None) -> Optional[str]:
    """Get the lint command for a specific language."""
    config = load_project_config(config_path)
    return config.get("quality", {}).get("lintCommands", {}).get(language)


def get_build_command(language: str, config_path: Optional[Path] = None) -> Optional[str]:
    """Get the build command for a specific language."""
    config = load_project_config(config_path)
    return config.get("quality", {}).get("buildCommands", {}).get(language)


def get_format_command(language: str, config_path: Optional[Path] = None) -> Optional[str]:
    """Get the format command for a specific language."""
    config = load_project_config(config_path)
    return config.get("quality", {}).get("formatCommands", {}).get(language)
