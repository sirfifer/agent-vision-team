#!/usr/bin/env python3
"""PreToolUse hook: context reinforcement to prevent drift.

Tracks tool call count per session. After a configurable threshold,
injects relevant context via additionalContext. Three-layer injection:

1. Session Context (primary): Distilled starting prompt + evolved discoveries
   from .avt/.session-context-{session_id}.json
2. Static Router (secondary): Vision/architecture/rules from context-router.json,
   matched via Jaccard similarity against tool_input keywords
3. Post-Compaction: handled by post-compaction-reinject.sh (separate hook)

Hook protocol:
- Reads JSON from stdin (tool_name, tool_input, session_id, transcript_path)
- Writes JSON to stdout (additionalContext) when injecting
- Exit 0 = allow (always allows; this hook advises, never blocks)

Registered as: PreToolUse on Write|Edit|Bash|Task
Runs after: holistic-review-gate.sh (which may block with exit 2)

Performance:
- Fast path (~1ms): counter under threshold -> exit 0
- Slow path (~50ms): session context read or keyword matching + injection
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
AVT_DIR = Path(PROJECT_DIR) / ".avt"
LOG_PATH = AVT_DIR / "hook-context-reinforcement.log"

# Installation defaults (lowest priority in cascade)
INSTALLATION_DEFAULTS = {
    "enabled": True,
    "toolCallThreshold": 8,
    "maxTokensPerInjection": 400,
    "debounceSeconds": 30,
    "maxInjectionsPerSession": 10,
    "jaccardThreshold": 0.15,
    "postCompactionReinject": True,
    "routerAutoRegenerate": True,
    "sessionContextEnabled": True,
    "sessionContextDebounceSeconds": 60,
    "maxDiscoveriesPerSession": 10,
    "refreshInterval": 5,
    "distillationModel": "haiku",
}

# Stopwords for keyword extraction (matches generate-context-router.py)
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "must",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "not",
        "no",
        "nor",
        "so",
        "if",
        "then",
        "than",
        "when",
        "where",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "own",
        "same",
        "too",
        "very",
        "just",
        "about",
        "above",
        "after",
        "again",
        "also",
        "any",
        "as",
        "because",
        "before",
        "between",
        "during",
        "into",
        "over",
        "through",
        "under",
        "until",
        "up",
        "while",
        "use",
        "used",
        "using",
    }
)


def log(msg: str) -> None:
    """Append a timestamped log line."""
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")
    except OSError:
        pass


def load_settings() -> dict:
    """Load effective settings via cascade: installation -> global -> project."""
    effective = dict(INSTALLATION_DEFAULTS)

    # Global config (~/.avt/global-config.json)
    global_path = Path.home() / ".avt" / "global-config.json"
    if global_path.exists():
        try:
            global_cfg = json.loads(global_path.read_text())
            cr = global_cfg.get("contextReinforcement", {})
            for k, v in cr.items():
                if v is not None and k in effective:
                    effective[k] = v
        except (json.JSONDecodeError, OSError):
            pass

    # Project config (.avt/project-config.json)
    project_path = AVT_DIR / "project-config.json"
    if project_path.exists():
        try:
            project_cfg = json.loads(project_path.read_text())
            cr = project_cfg.get("settings", {}).get("contextReinforcement", {})
            for k, v in cr.items():
                if v is not None and k in effective:
                    effective[k] = v
        except (json.JSONDecodeError, OSError):
            pass

    return effective


def increment_counter(counter_path: Path) -> int:
    """Atomically increment session call counter. Returns new value."""
    count = 0
    if counter_path.exists():
        try:
            count = int(counter_path.read_text().strip())
        except (ValueError, OSError):
            count = 0
    count += 1
    try:
        counter_path.write_text(str(count))
    except OSError:
        pass
    return count


def tokenize(text: str) -> set[str]:
    """Extract keywords from text."""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]*", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def load_router() -> list[dict]:
    """Load context router routes."""
    router_path = AVT_DIR / "context-router.json"
    if not router_path.exists():
        return []
    try:
        data = json.loads(router_path.read_text())
        return data.get("routes", [])
    except (json.JSONDecodeError, OSError):
        return []


def load_injection_history(history_path: Path) -> list[dict]:
    """Load injection history for dedup/debounce/cap checks."""
    if not history_path.exists():
        return []
    try:
        return json.loads(history_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_injection_history(history_path: Path, history: list[dict]) -> None:
    """Save injection history."""
    try:
        history_path.write_text(json.dumps(history))
    except OSError:
        pass


def find_best_match(
    routes: list[dict],
    input_keywords: set[str],
    threshold: float,
) -> tuple[dict | None, float]:
    """Find the best-matching route above the Jaccard threshold."""
    best_route = None
    best_score = 0.0

    for route in routes:
        route_keywords = set(route.get("keywords", []))
        score = jaccard(input_keywords, route_keywords)
        if score >= threshold and score > best_score:
            best_score = score
            best_route = route

    return best_route, best_score


def extract_tool_input_text(tool_input: dict | str) -> str:
    """Extract searchable text from tool_input."""
    if isinstance(tool_input, str):
        return tool_input

    parts = []
    for key in ("file_path", "content", "old_string", "new_string", "command", "prompt", "description", "pattern"):
        val = tool_input.get(key, "")
        if isinstance(val, str):
            parts.append(val)
    return " ".join(parts)


def load_session_context(session_ctx_path: Path) -> dict | None:
    """Load the session context file if it exists and is valid."""
    if not session_ctx_path.exists():
        return None
    try:
        data = json.loads(session_ctx_path.read_text())
        if data.get("distillation", {}).get("status") in ("ready", "fallback"):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def build_session_injection(context: dict) -> str | None:
    """Build the injection string from session context.

    Returns formatted string or None if nothing meaningful to inject.
    Constructive only: excludes completed goals, thrash guidance only if constructive.
    """
    distillation = context.get("distillation", {})
    key_points = distillation.get("key_points", [])
    constraints = distillation.get("constraints", [])
    key_decisions = distillation.get("key_decisions", [])
    discoveries = context.get("discoveries", [])
    thrash = context.get("thrash_indicators", [])

    # Filter to active goals only
    active_goals = [kp for kp in key_points if kp.get("status") != "completed"]

    # If all goals are completed, skip injection (work is done)
    if not active_goals and not discoveries:
        return None

    parts = ["SESSION CONTEXT:"]

    if active_goals:
        parts.append("Goals remaining:")
        for kp in active_goals:
            parts.append(f"- {kp['text']}")

    if discoveries:
        # Show most recent 5 discoveries
        recent = discoveries[-5:]
        parts.append("Key findings:")
        for disc in recent:
            parts.append(f"- {disc['text']}")

    if constraints:
        parts.append("Constraints: " + "; ".join(constraints))

    if key_decisions:
        parts.append("Key decisions: " + "; ".join(key_decisions))

    # Thrash guidance only if present and constructive
    if thrash:
        # Only include if it offers a constructive path forward
        guidance_parts = [t for t in thrash if isinstance(t, str) and t.strip()]
        if guidance_parts:
            parts.append("Guidance: " + "; ".join(guidance_parts[:2]))

    return "\n".join(parts)


def is_session_debounced(history: list[dict], settings: dict) -> bool:
    """Check if session context was recently injected (debounce)."""
    debounce = settings.get("sessionContextDebounceSeconds", 60)
    now = time.time()
    for entry in history:
        if entry.get("route_id") == "session-context":
            elapsed = now - entry.get("timestamp", 0)
            if elapsed < debounce:
                return True
    return False


def spawn_distillation(session_id: str, transcript_path: str, refresh: bool = False) -> None:
    """Spawn background distillation process (detached)."""
    distill_script = Path(__file__).parent / "_distill-session-context.py"
    if not distill_script.exists():
        log(f"[{session_id[:8]}] Distillation script not found")
        return

    cmd = ["python3", str(distill_script), session_id, transcript_path]
    if refresh:
        cmd.append("--refresh")

    try:
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = PROJECT_DIR
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        log(f"[{session_id[:8]}] Spawned distillation (refresh={refresh})")
    except Exception as e:
        log(f"[{session_id[:8]}] Failed to spawn distillation: {e}")


def update_session_injection_count(session_ctx_path: Path) -> int:
    """Increment and return the injection count in the session context file."""
    try:
        data = json.loads(session_ctx_path.read_text())
        count = data.get("injection_count", 0) + 1
        data["injection_count"] = count
        data["last_injected_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        session_ctx_path.write_text(json.dumps(data, indent=2))
        return count
    except (json.JSONDecodeError, OSError):
        return 0


def main() -> int:
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return 0  # Cannot parse input; allow silently

    session_id = hook_input.get("session_id", "unknown")
    tool_input = hook_input.get("tool_input", {})
    transcript_path = hook_input.get("transcript_path", "")

    # Ensure .avt directory exists
    AVT_DIR.mkdir(parents=True, exist_ok=True)

    # Load settings
    settings = load_settings()

    # Check if enabled
    if not settings.get("enabled", True):
        return 0

    # Increment call counter
    counter_path = AVT_DIR / f".session-calls-{session_id}"
    call_count = increment_counter(counter_path)

    # Fast path: under threshold
    threshold = settings.get("toolCallThreshold", 8)
    if call_count < threshold:
        return 0

    # Load injection history (shared by session context and static routes)
    history_path = AVT_DIR / f".injection-history-{session_id}"
    history = load_injection_history(history_path)
    now = time.time()

    # Cap: skip if max injections reached (applies to all injection types)
    max_injections = settings.get("maxInjectionsPerSession", 10)
    if len(history) >= max_injections:
        log(f"[{session_id[:8]}] Cap reached ({len(history)}/{max_injections})")
        return 0

    # ── Layer 1: Session Context (primary) ────────────────────────────────
    if settings.get("sessionContextEnabled", True):
        session_ctx_path = AVT_DIR / f".session-context-{session_id}.json"
        session_ctx = load_session_context(session_ctx_path)

        if session_ctx:
            if not is_session_debounced(history, settings):
                injection = build_session_injection(session_ctx)
                if injection:
                    log(
                        f"[{session_id[:8]}] Injecting session context "
                        f"(call #{call_count}, injection #{len(history) + 1}/{max_injections})"
                    )
                    # Update history
                    history = [e for e in history if e.get("route_id") != "session-context"]
                    history.append({"route_id": "session-context", "timestamp": now})
                    save_injection_history(history_path, history)

                    # Track injection count and trigger refresh if needed
                    count = update_session_injection_count(session_ctx_path)
                    refresh_interval = settings.get("refreshInterval", 5)
                    if count > 0 and count % refresh_interval == 0 and transcript_path:
                        spawn_distillation(session_id, transcript_path, refresh=True)

                    json.dump({"additionalContext": injection}, sys.stdout)
                    return 0
        elif transcript_path:
            # Session context doesn't exist yet; spawn background distillation
            spawn_distillation(session_id, transcript_path)
            log(f"[{session_id[:8]}] No session context; spawned distillation, falling through to static router")

    # ── Layer 2: Static Router (secondary) ────────────────────────────────
    routes = load_router()
    if not routes:
        log(f"[{session_id[:8]}] No router or empty routes; skipping")
        return 0

    # Extract keywords from tool input
    input_text = extract_tool_input_text(tool_input)
    input_keywords = tokenize(input_text)
    if not input_keywords:
        return 0

    # Find best match
    jaccard_threshold = settings.get("jaccardThreshold", 0.15)
    best_route, best_score = find_best_match(routes, input_keywords, jaccard_threshold)

    if not best_route:
        return 0

    route_id = best_route["id"]

    # Debounce: skip if same route injected within debounceSeconds
    debounce_seconds = settings.get("debounceSeconds", 30)
    for entry in history:
        if entry.get("route_id") == route_id:
            elapsed = now - entry.get("timestamp", 0)
            if elapsed < debounce_seconds:
                log(f"[{session_id[:8]}] Debounced {route_id} ({elapsed:.0f}s < {debounce_seconds}s)")
                return 0

    # Inject
    context = best_route.get("context", "")
    log(
        f"[{session_id[:8]}] Injecting {route_id} "
        f"(call #{call_count}, score={best_score:.2f}, "
        f"injection #{len(history) + 1}/{max_injections})"
    )

    # Update history (remove old entry for this route if exists, then append new)
    history = [e for e in history if e.get("route_id") != route_id]
    history.append({"route_id": route_id, "timestamp": now})
    save_injection_history(history_path, history)

    # Output additionalContext
    json.dump({"additionalContext": context}, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(0)  # Never block on errors
