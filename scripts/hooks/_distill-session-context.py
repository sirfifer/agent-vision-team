#!/usr/bin/env python3
from __future__ import annotations

"""Background: distill the original user prompt into session context.

Reads the session transcript to find the first user message,
then calls haiku to distill it into key points, constraints, and
key decisions. Writes the result to .avt/.session-context-{session_id}.json.

Spawned by context-reinforcement.py as a detached background process.

Usage:
    python3 _distill-session-context.py <session_id> <transcript_path> [--refresh]

Environment:
    CLAUDE_PROJECT_DIR: Project root directory
    GOVERNANCE_MOCK_REVIEW: If set, skip AI call and produce synthetic distillation
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

# Short prompts below this threshold are stored directly without AI distillation
SHORT_PROMPT_THRESHOLD = 500


def _log(msg: str) -> None:
    """Append a timestamped log line."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] [distill] {msg}\n")
    except Exception:
        pass


def _extract_original_prompt(transcript_path: str) -> str:
    """Extract the first user message from the transcript JSONL."""
    if not transcript_path or not Path(transcript_path).exists():
        return ""
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # First user message contains the original prompt
                if entry.get("type") == "user":
                    msg = entry.get("message", {})
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        parts = []
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                parts.append(block["text"])
                            elif isinstance(block, str):
                                parts.append(block)
                        return "\n".join(parts)
    except Exception as e:
        _log(f"Error reading transcript: {e}")
    return ""


def _extract_recent_transcript(transcript_path: str) -> str:
    """Extract recent assistant messages from transcript (for refresh mode)."""
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


def _build_distillation_prompt(original_prompt: str) -> str:
    """Build the prompt for haiku to distill the original user prompt."""
    return f"""Extract key information from this AI coding session prompt. Return ONLY a JSON object with no other text.

## Original Prompt
{original_prompt[:8000]}

## Instructions
Return ONLY a JSON object:
{{
  "key_points": [
    {{"id": "kp-1", "text": "concise goal or task description"}}
  ],
  "constraints": ["explicit constraint from the prompt"],
  "key_decisions": ["decision or preference stated in the prompt"]
}}

Rules:
- Each key_point should be a discrete, actionable goal
- Constraints are things the user explicitly said to do or avoid
- Key decisions are preferences or choices stated in the prompt
- Be concise: each item should be one sentence
- Maximum 8 key_points, 5 constraints, 5 key_decisions
- If the prompt is simple with one goal, that is fine: return one key_point"""


def _build_refresh_prompt(existing_context: dict, recent_transcript: str) -> str:
    """Build the prompt for haiku to refresh/update the session context."""
    distillation = existing_context.get("distillation", {})
    key_points = distillation.get("key_points", [])
    discoveries = existing_context.get("discoveries", [])

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
- thrash_indicators: only include if there is clear evidence of repeated failures, circular reasoning, or confusion
- NEVER include negative or discouraging content
- Maximum 3 new discoveries per update"""


def _run_claude(prompt: str, timeout: int = 30) -> str:
    """Run claude --print --model haiku with temp file I/O."""
    input_fd, input_path = tempfile.mkstemp(prefix="avt-distill-", suffix="-input.md")
    output_fd, output_path = tempfile.mkstemp(prefix="avt-distill-", suffix="-output.md")

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
            _log(f"claude --print failed: rc={result.returncode} stderr={result.stderr[:200]}")
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

    # Try direct parse
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    # Try markdown JSON block
    import re

    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { to last }
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


def _build_mock_distillation(original_prompt: str) -> dict:
    """Build a synthetic distillation for mock/test mode."""
    truncated = original_prompt[:200]
    if len(original_prompt) > 200:
        truncated += "..."
    return {
        "key_points": [{"id": "kp-1", "text": truncated}],
        "constraints": [],
        "key_decisions": [],
    }


def _build_short_prompt_distillation(original_prompt: str) -> dict:
    """Build distillation directly from a short prompt (no AI call needed)."""
    return {
        "key_points": [{"id": "kp-1", "text": original_prompt.strip()}],
        "constraints": [],
        "key_decisions": [],
    }


def _write_session_context(
    session_ctx_path: Path,
    session_id: str,
    distillation: dict,
    status: str = "ready",
    existing: dict | None = None,
) -> None:
    """Write session context file atomically with file locking."""
    now = datetime.now(timezone.utc).isoformat()

    # Ensure key_points have status field
    for kp in distillation.get("key_points", []):
        if "status" not in kp:
            kp["status"] = "active"

    context = existing or {
        "version": 1,
        "session_id": session_id,
        "created_at": now,
        "discoveries": [],
        "thrash_indicators": [],
        "injection_count": 0,
        "last_injected_at": None,
    }

    context["updated_at"] = now
    context["distillation"] = {
        "status": status,
        **distillation,
    }

    # Atomic write with file locking
    tmp_path = session_ctx_path.with_suffix(".json.tmp")
    session_ctx_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.write(fd, json.dumps(context, indent=2).encode())
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        tmp_path.rename(session_ctx_path)
    except Exception as e:
        _log(f"Error writing session context: {e}")
        try:
            tmp_path.unlink()
        except OSError:
            pass


def _do_initial_distillation(session_id: str, transcript_path: str) -> None:
    """Run initial distillation of the original user prompt."""
    session_ctx_path = AVT_DIR / f".session-context-{session_id}.json"

    # Skip if already exists
    if session_ctx_path.exists():
        _log(f"Session context already exists for {session_id}; skipping initial distillation")
        return

    original_prompt = _extract_original_prompt(transcript_path)
    if not original_prompt:
        _log("No original prompt found in transcript; writing fallback")
        _write_session_context(
            session_ctx_path,
            session_id,
            {"key_points": [], "constraints": [], "key_decisions": []},
            status="fallback",
        )
        return

    _log(f"Distilling prompt ({len(original_prompt)} chars) for session {session_id[:8]}")

    # Mock mode
    if os.environ.get("GOVERNANCE_MOCK_REVIEW"):
        _log("Mock mode: writing synthetic distillation")
        distillation = _build_mock_distillation(original_prompt)
        _write_session_context(session_ctx_path, session_id, distillation)
        return

    # Short prompt: store directly
    if len(original_prompt) < SHORT_PROMPT_THRESHOLD:
        _log("Short prompt: storing directly without AI call")
        distillation = _build_short_prompt_distillation(original_prompt)
        _write_session_context(session_ctx_path, session_id, distillation)
        return

    # AI distillation via haiku
    prompt = _build_distillation_prompt(original_prompt)
    raw = _run_claude(prompt)
    parsed = _parse_json_response(raw)

    if parsed and "key_points" in parsed:
        _log(f"Distillation succeeded: {len(parsed['key_points'])} key points")
        _write_session_context(session_ctx_path, session_id, parsed)
    else:
        _log("Distillation parse failed; writing fallback")
        distillation = _build_mock_distillation(original_prompt)
        _write_session_context(session_ctx_path, session_id, distillation, status="fallback")


def _do_refresh(session_id: str, transcript_path: str) -> None:
    """Refresh the session context with current transcript state."""
    session_ctx_path = AVT_DIR / f".session-context-{session_id}.json"

    if not session_ctx_path.exists():
        _log("No session context for refresh; running initial distillation instead")
        _do_initial_distillation(session_id, transcript_path)
        return

    try:
        existing = json.loads(session_ctx_path.read_text())
    except (json.JSONDecodeError, OSError):
        _log("Cannot read existing session context for refresh")
        return

    # Mock mode: skip
    if os.environ.get("GOVERNANCE_MOCK_REVIEW"):
        _log("Mock mode: skipping refresh")
        return

    recent_transcript = _extract_recent_transcript(transcript_path)
    prompt = _build_refresh_prompt(existing, recent_transcript)
    raw = _run_claude(prompt)
    parsed = _parse_json_response(raw)

    if not parsed:
        _log("Refresh parse failed; keeping existing context")
        return

    # Apply updates
    distillation = existing.get("distillation", {})
    key_points = distillation.get("key_points", [])
    discoveries = existing.get("discoveries", [])
    now = datetime.now(timezone.utc).isoformat()

    # Mark completed goals
    completed_ids = set(parsed.get("completed_goals", []))
    for kp in key_points:
        if kp["id"] in completed_ids and kp.get("status") != "completed":
            kp["status"] = "completed"
            kp["completed_at"] = now
            _log(f"Marked goal completed: {kp['id']}")

    # Add new discoveries (deduplicate, cap at 10)
    existing_texts = {d["text"].lower() for d in discoveries}
    for new_disc in parsed.get("new_discoveries", [])[:3]:
        text = new_disc.get("text", "").strip()
        if text and text.lower() not in existing_texts and len(discoveries) < 10:
            disc_id = f"disc-{len(discoveries) + 1}"
            discoveries.append(
                {
                    "id": disc_id,
                    "text": text,
                    "discovered_at": now,
                    "source": "refresh",
                }
            )
            existing_texts.add(text.lower())
            _log(f"Added discovery: {text[:80]}")

    # Update thrash indicators (constructive only)
    thrash = parsed.get("thrash_indicators", [])
    if thrash:
        existing["thrash_indicators"] = thrash[:3]

    existing["discoveries"] = discoveries
    distillation["key_points"] = key_points
    existing["distillation"] = distillation

    _write_session_context(session_ctx_path, session_id, distillation, existing=existing)
    _log(f"Refresh complete for session {session_id[:8]}")


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: _distill-session-context.py <session_id> <transcript_path> [--refresh]")
        return 1

    session_id = sys.argv[1]
    transcript_path = sys.argv[2]
    refresh = "--refresh" in sys.argv

    if refresh:
        _do_refresh(session_id, transcript_path)
    else:
        _do_initial_distillation(session_id, transcript_path)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        _log(f"ERROR: {e}")
        sys.exit(0)  # Never fail loudly; background process
