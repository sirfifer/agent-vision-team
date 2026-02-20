#!/usr/bin/env python3
from __future__ import annotations

"""Background: update session context with milestones and discoveries.

Reads the session transcript during governance review processing to identify
completed goals and new discoveries. Updates the session context file.

Spawned by:
- _holistic-settle-check.py (after holistic review)
- _run-governance-review.sh (after individual review)

Usage:
    python3 _update-session-context.py <session_id> <transcript_path> <source>

    source: "holistic_review" | "individual_review" | "refresh"

Environment:
    CLAUDE_PROJECT_DIR: Project root directory
    GOVERNANCE_MOCK_REVIEW: If set, skip AI call and make no changes
"""

import fcntl
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
AVT_DIR = Path(PROJECT_DIR) / ".avt"
LOG_PATH = AVT_DIR / "hook-context-reinforcement.log"

# Minimum seconds between updates (avoid rapid-fire from concurrent reviews)
UPDATE_THROTTLE_SECONDS = 60
# Maximum total discoveries per session
MAX_DISCOVERIES = 10


def _log(msg: str) -> None:
    """Append a timestamped log line."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] [update-ctx] {msg}\n")
    except Exception:
        pass


def _extract_recent_transcript(transcript_path: str) -> str:
    """Extract recent assistant messages from transcript JSONL."""
    if not transcript_path or not Path(transcript_path).exists():
        return "(transcript not available)"
    try:
        with open(transcript_path) as f:
            lines = f.readlines()
        recent = lines[-50:] if len(lines) > 50 else lines
        excerpts = []
        for line in recent:
            try:
                entry = json.loads(line)
                if entry.get("role") == "assistant":
                    content = entry.get("content", "")
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                excerpts.append(block["text"][:500])
                    elif isinstance(content, str):
                        excerpts.append(content[:500])
            except json.JSONDecodeError:
                continue
        return "\n---\n".join(excerpts[-5:])
    except Exception:
        return "(could not read transcript)"


def _build_update_prompt(existing: dict, recent_transcript: str) -> str:
    """Build the prompt for haiku to identify completed goals and new discoveries."""
    distillation = existing.get("distillation", {})
    key_points = distillation.get("key_points", [])
    discoveries = existing.get("discoveries", [])

    kp_lines = []
    for kp in key_points:
        status = kp.get("status", "active")
        kp_lines.append(f"- [{status}] {kp['id']}: {kp['text']}")

    disc_lines = [f"- {d['text']}" for d in discoveries[-5:]]

    return f"""Given session goals and recent activity, identify what has changed. Return ONLY a JSON object.

## Current Session Goals
{chr(10).join(kp_lines) if kp_lines else "(none)"}

## Current Discoveries
{chr(10).join(disc_lines) if disc_lines else "(none)"}

## Recent Activity (from transcript)
{recent_transcript[:4000]}

## Instructions
Return ONLY a JSON object:
{{
  "completed_goals": ["kp-1"],
  "new_discoveries": [
    {{"text": "concise description of milestone or finding"}}
  ],
  "thrash_indicators": []
}}

Rules:
- Only mark a goal completed if the transcript clearly shows it was accomplished
- A discovery is a significant finding, milestone, or contextual piece that helps the agent stay on track
- Only include genuinely NEW discoveries not already in the existing list
- thrash_indicators: only include if there is clear evidence of repeated failures,
  circular reasoning, or confusion. If unsure, leave empty.
- NEVER include negative or discouraging content. If you do not have something constructive to say, say nothing.
- Maximum 3 new discoveries per update"""


def _run_claude(prompt: str, timeout: int = 30) -> str:
    """Run claude --print --model haiku with temp file I/O."""
    input_fd, input_path = tempfile.mkstemp(prefix="avt-update-ctx-", suffix="-input.md")
    output_fd, output_path = tempfile.mkstemp(prefix="avt-update-ctx-", suffix="-output.md")

    try:
        with os.fdopen(input_fd, "w") as f:
            f.write(prompt)
        os.close(output_fd)

        with open(input_path) as fin, open(output_path, "w") as fout:
            result = subprocess.run(
                ["claude", "--print", "--model", "haiku"],
                stdin=fin,
                stdout=fout,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )

        if result.returncode != 0:
            _log(f"claude --print failed: rc={result.returncode}")
            return ""

        with open(output_path) as f:
            return f.read()
    except subprocess.TimeoutExpired:
        _log("claude --print timed out")
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


def _parse_json_response(raw: str) -> dict | None:
    """Extract JSON from claude response."""
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


def _is_duplicate_discovery(text: str, existing_discoveries: list[dict]) -> bool:
    """Check if a discovery is a duplicate (case-insensitive substring match)."""
    lower = text.lower().strip()
    for d in existing_discoveries:
        existing_lower = d.get("text", "").lower().strip()
        # Check both directions for substring containment
        if lower in existing_lower or existing_lower in lower:
            return True
    return False


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: _update-session-context.py <session_id> <transcript_path> <source>")
        return 1

    session_id = sys.argv[1]
    transcript_path = sys.argv[2]
    source = sys.argv[3]

    session_ctx_path = AVT_DIR / f".session-context-{session_id}.json"

    # Exit early if no session context file (distillation hasn't run yet)
    if not session_ctx_path.exists():
        _log(f"No session context for {session_id[:8]}; skipping update")
        return 0

    # Mock mode: skip
    if os.environ.get("GOVERNANCE_MOCK_REVIEW"):
        _log(f"Mock mode: skipping context update for {session_id[:8]}")
        return 0

    # Read existing session context with file locking
    try:
        fd = os.open(str(session_ctx_path), os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            with os.fdopen(fd, "r") as f:
                existing = json.load(f)
        except Exception:
            os.close(fd)
            raise
    except (json.JSONDecodeError, OSError) as e:
        _log(f"Cannot read session context: {e}")
        return 0

    # Throttle: skip if updated recently
    updated_at = existing.get("updated_at", "")
    if updated_at:
        try:
            last_update = datetime.fromisoformat(updated_at)
            elapsed = (datetime.now(timezone.utc) - last_update).total_seconds()
            if elapsed < UPDATE_THROTTLE_SECONDS:
                _log(f"Throttled: last update {elapsed:.0f}s ago (< {UPDATE_THROTTLE_SECONDS}s)")
                return 0
        except (ValueError, TypeError):
            pass

    _log(f"Updating session context for {session_id[:8]} (source={source})")

    # Extract recent transcript
    recent_transcript = _extract_recent_transcript(transcript_path)

    # Build and run AI prompt
    prompt = _build_update_prompt(existing, recent_transcript)
    raw = _run_claude(prompt)
    parsed = _parse_json_response(raw)

    if not parsed:
        _log("Update parse failed; keeping existing context")
        return 0

    # Apply updates
    now = datetime.now(timezone.utc).isoformat()
    distillation = existing.get("distillation", {})
    key_points = distillation.get("key_points", [])
    discoveries = existing.get("discoveries", [])

    changes_made = False

    # Mark completed goals
    completed_ids = set(parsed.get("completed_goals", []))
    for kp in key_points:
        if kp["id"] in completed_ids and kp.get("status") != "completed":
            kp["status"] = "completed"
            kp["completed_at"] = now
            _log(f"Marked goal completed: {kp['id']}")
            changes_made = True

    # Add new discoveries (deduplicate, cap)
    for new_disc in parsed.get("new_discoveries", [])[:3]:
        text = new_disc.get("text", "").strip()
        if not text:
            continue
        if len(discoveries) >= MAX_DISCOVERIES:
            _log(f"Discovery cap reached ({MAX_DISCOVERIES}); skipping")
            break
        if _is_duplicate_discovery(text, discoveries):
            _log(f"Duplicate discovery skipped: {text[:60]}")
            continue
        disc_id = f"disc-{len(discoveries) + 1}"
        discoveries.append(
            {
                "id": disc_id,
                "text": text,
                "discovered_at": now,
                "source": source,
            }
        )
        _log(f"Added discovery: {text[:80]}")
        changes_made = True

    # Update thrash indicators (constructive only)
    thrash = parsed.get("thrash_indicators", [])
    if thrash:
        existing["thrash_indicators"] = [t for t in thrash[:3] if isinstance(t, str) and t.strip()]
        changes_made = True

    if not changes_made:
        _log("No changes detected; keeping existing context")
        return 0

    # Write updated context atomically with file locking
    existing["updated_at"] = now
    existing["discoveries"] = discoveries
    distillation["key_points"] = key_points
    existing["distillation"] = distillation

    tmp_path = session_ctx_path.with_suffix(".json.tmp")
    try:
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.write(fd, json.dumps(existing, indent=2).encode())
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        tmp_path.rename(session_ctx_path)
        _log(f"Session context updated for {session_id[:8]}")
    except Exception as e:
        _log(f"Error writing updated session context: {e}")
        try:
            tmp_path.unlink()
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        _log(f"ERROR: {e}")
        sys.exit(0)  # Never fail loudly; background process
