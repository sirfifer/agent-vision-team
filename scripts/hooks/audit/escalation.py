"""Tiered LLM escalation chain: Haiku -> Sonnet -> Opus.

Each tier runs as a function called from `_audit-escalate.py`.
Each tier decides independently whether to escalate to the next.
Uses `claude --print` with temp file I/O (gold standard pattern).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
_AUDIT_DIR = Path(_PROJECT_DIR) / ".avt" / "audit"
_LOG_PATH = _AUDIT_DIR / "audit.log"


def _log(msg: str) -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG_PATH, "a") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] [escalation] {msg}\n")
    except Exception:
        pass


def _run_claude(prompt: str, model: str = "haiku", timeout: int = 60) -> str:
    """Run claude --print --model <model> with temp file I/O.

    Returns raw output string, or empty string on failure.
    """
    input_fd, input_path = tempfile.mkstemp(prefix="avt-escalate-", suffix="-input.md")
    output_fd, output_path = tempfile.mkstemp(prefix="avt-escalate-", suffix="-output.md")

    try:
        with os.fdopen(input_fd, "w") as f:
            f.write(prompt)
        os.close(output_fd)

        env = os.environ.copy()
        # Prevent nested session detection
        env.pop("CLAUDECODE", None)

        with open(input_path) as fin, open(output_path, "w") as fout:
            result = subprocess.run(
                ["claude", "--print", "--model", model],
                stdin=fin,
                stdout=fout,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                env=env,
            )

        if result.returncode != 0:
            _log(f"claude --print --model {model} failed: rc={result.returncode}")
            return ""

        with open(output_path) as f:
            return f.read()
    except subprocess.TimeoutExpired:
        _log(f"claude --print --model {model} timed out ({timeout}s)")
        return ""
    except FileNotFoundError:
        _log("claude CLI not found")
        return ""
    finally:
        for p in (input_path, output_path):
            try:
                os.unlink(p)
            except OSError:
                pass


def _parse_json(raw: str) -> "dict | None":
    """Extract JSON from LLM response."""
    raw = raw.strip()
    if not raw:
        return None

    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    import re

    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


def _save_tier_output(filename: str, data: dict) -> None:
    """Save tier output to .avt/audit/<filename>."""
    try:
        _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        path = _AUDIT_DIR / filename
        path.write_text(json.dumps(data, indent=2))
    except OSError as e:
        _log(f"Failed to save {filename}: {e}")


def run_tier1_haiku(
    anomalies: list[dict],
    directives: list[dict],
    recent_stats: dict,
    recent_recommendations: list[dict],
    model: str = "haiku",
) -> "dict | None":
    """Tier 1: Haiku triage. Quick pattern recognition.

    Returns parsed triage result, or None on failure.
    """
    from .prompts import build_haiku_prompt, match_directives

    matched = match_directives(anomalies, directives)
    prompt = build_haiku_prompt(anomalies, matched, recent_stats, recent_recommendations)

    _log(f"Tier 1 (Haiku): triaging {len(anomalies)} anomalies, {len(matched)} directives")
    start = time.time()
    raw = _run_claude(prompt, model=model, timeout=30)
    elapsed = time.time() - start
    _log(f"Tier 1 completed in {elapsed:.1f}s")

    parsed = _parse_json(raw)
    if parsed:
        parsed["tier"] = "haiku"
        parsed["elapsed_seconds"] = round(elapsed, 1)
        _save_tier_output("triage.json", parsed)
    else:
        _log("Tier 1: failed to parse response")

    return parsed


def run_tier2_sonnet(
    haiku_triage: dict,
    anomalies: list[dict],
    directives: list[dict],
    event_window: list[dict],
    current_settings: dict,
    existing_recommendations: list[dict],
    model: str = "sonnet",
) -> "dict | None":
    """Tier 2: Sonnet analysis. Substantive analysis with correlations.

    Returns parsed analysis result, or None on failure.
    """
    from .prompts import build_sonnet_prompt

    prompt = build_sonnet_prompt(
        haiku_triage,
        anomalies,
        directives,
        event_window,
        current_settings,
        existing_recommendations,
    )

    _log(f"Tier 2 (Sonnet): analyzing {len(anomalies)} anomalies")
    start = time.time()
    raw = _run_claude(prompt, model=model, timeout=120)
    elapsed = time.time() - start
    _log(f"Tier 2 completed in {elapsed:.1f}s")

    parsed = _parse_json(raw)
    if parsed:
        parsed["tier"] = "sonnet"
        parsed["elapsed_seconds"] = round(elapsed, 1)
        _save_tier_output("analysis.json", parsed)
    else:
        _log("Tier 2: failed to parse response")

    return parsed


def run_tier3_opus(
    sonnet_analysis: dict,
    anomalies: list[dict],
    directives: list[dict],
    event_window: list[dict],
    current_settings: dict,
    existing_recommendations: list[dict],
    session_summaries: list[dict],
    model: str = "opus",
) -> "dict | None":
    """Tier 3: Opus deep dive. Strategic analysis for significant milestones.

    Returns parsed deep analysis result, or None on failure.
    """
    from .prompts import build_opus_prompt

    prompt = build_opus_prompt(
        sonnet_analysis,
        anomalies,
        directives,
        event_window,
        current_settings,
        existing_recommendations,
        session_summaries,
    )

    _log(f"Tier 3 (Opus): deep dive on {len(anomalies)} anomalies")
    start = time.time()
    raw = _run_claude(prompt, model=model, timeout=180)
    elapsed = time.time() - start
    _log(f"Tier 3 completed in {elapsed:.1f}s")

    parsed = _parse_json(raw)
    if parsed:
        parsed["tier"] = "opus"
        parsed["elapsed_seconds"] = round(elapsed, 1)
        _save_tier_output("deep-analysis.json", parsed)
    else:
        _log("Tier 3: failed to parse response")

    return parsed
