#!/usr/bin/env bash
# SessionStart hook (compact matcher): re-inject critical context after compaction.
#
# Fires after context compaction events. Reads the context router and
# injects all vision-tier routes plus current task focus.
#
# Target: ~10ms execution, ~200 tokens injected.
#
# Exit codes:
#   0 = success (additionalContext injected or nothing to inject)

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
ROUTER_PATH="${PROJECT_DIR}/.avt/context-router.json"
SESSION_STATE="${PROJECT_DIR}/.avt/session-state.md"
CONFIG_PATH="${PROJECT_DIR}/.avt/project-config.json"

# Check if router exists
if [ ! -f "$ROUTER_PATH" ]; then
    exit 0
fi

# Check if post-compaction reinject is enabled (default: true)
if [ -f "$CONFIG_PATH" ] && command -v python3 &>/dev/null; then
    ENABLED=$(python3 -c "
import json, sys
try:
    config = json.load(open('$CONFIG_PATH'))
    cr = config.get('settings', {}).get('contextReinforcement', {})
    print('true' if cr.get('postCompactionReinject', True) else 'false')
except Exception:
    print('true')
" 2>/dev/null || echo "true")

    if [ "$ENABLED" = "false" ]; then
        exit 0
    fi
fi

# Also check global config
GLOBAL_CONFIG="$HOME/.avt/global-config.json"
if [ -f "$GLOBAL_CONFIG" ] && command -v python3 &>/dev/null; then
    GLOBAL_ENABLED=$(python3 -c "
import json, sys
try:
    config = json.load(open('$GLOBAL_CONFIG'))
    cr = config.get('contextReinforcement', {})
    val = cr.get('postCompactionReinject', None)
    # Only print if explicitly set (project config takes precedence above)
    print('true' if val is None or val else 'false')
except Exception:
    print('true')
" 2>/dev/null || echo "true")

    # Global only matters if project config didn't set it
    if [ "$GLOBAL_ENABLED" = "false" ] && [ "${ENABLED:-true}" = "true" ]; then
        # Check if project config explicitly set it
        if [ -f "$CONFIG_PATH" ]; then
            PROJECT_SET=$(python3 -c "
import json
try:
    config = json.load(open('$CONFIG_PATH'))
    cr = config.get('settings', {}).get('contextReinforcement', {})
    print('true' if 'postCompactionReinject' in cr else 'false')
except Exception:
    print('false')
" 2>/dev/null || echo "false")
            if [ "$PROJECT_SET" = "false" ]; then
                exit 0
            fi
        else
            exit 0
        fi
    fi
fi

# Read session_id from stdin (hook input JSON)
HOOK_INPUT=$(cat)
SESSION_ID=""
if command -v python3 &>/dev/null && [ -n "$HOOK_INPUT" ]; then
    SESSION_ID=$(echo "$HOOK_INPUT" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
    print(data.get('session_id', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")
fi

# Build injection content using Python
if command -v python3 &>/dev/null; then
    RESULT=$(python3 -c "
import json, sys
from pathlib import Path

router_path = '$ROUTER_PATH'
session_state_path = '$SESSION_STATE'
session_id = '$SESSION_ID'
avt_dir = Path('$PROJECT_DIR') / '.avt'

parts = ['POST-COMPACTION CONTEXT REINJECT:']
has_content = False

# Layer 1: Session context (primary, most important for post-compaction)
if session_id:
    session_ctx_path = avt_dir / f'.session-context-{session_id}.json'
    if session_ctx_path.exists():
        try:
            ctx = json.loads(session_ctx_path.read_text())
            distillation = ctx.get('distillation', {})
            key_points = distillation.get('key_points', [])
            discoveries = ctx.get('discoveries', [])
            constraints = distillation.get('constraints', [])

            active_goals = [kp for kp in key_points if kp.get('status') != 'completed']
            if active_goals or discoveries:
                parts.append('')
                parts.append('--- SESSION CONTEXT ---')
                if active_goals:
                    parts.append('Goals remaining:')
                    for kp in active_goals:
                        parts.append(f\"- {kp['text']}\")
                if discoveries:
                    parts.append('Key findings:')
                    for d in discoveries[-5:]:
                        parts.append(f\"- {d['text']}\")
                if constraints:
                    parts.append('Constraints: ' + '; '.join(constraints))
                has_content = True
        except Exception:
            pass

# Layer 2: Vision standards from router
try:
    with open(router_path) as f:
        router = json.load(f)
except Exception:
    if has_content:
        json.dump({'additionalContext': chr(10).join(parts)}, sys.stdout)
    sys.exit(0)

routes = router.get('routes', [])
vision_routes = [r for r in routes if r.get('tier') == 'vision']

if vision_routes:
    parts.append('')
    parts.append('--- VISION STANDARDS ---')
    for route in vision_routes:
        parts.append(route.get('context', ''))
    has_content = True

if not has_content:
    sys.exit(0)

# Add current task focus if session-state.md exists
try:
    with open(session_state_path) as f:
        content = f.read().strip()
    if content:
        focus = content[:400]
        if len(content) > 400:
            focus += '...'
        parts.append('')
        parts.append('--- CURRENT TASK FOCUS ---')
        parts.append(focus)
except (FileNotFoundError, OSError):
    pass

full_context = chr(10).join(parts)
json.dump({'additionalContext': full_context}, sys.stdout)
" 2>/dev/null)

    if [ -n "$RESULT" ]; then
        echo "$RESULT"
    fi
fi

exit 0
