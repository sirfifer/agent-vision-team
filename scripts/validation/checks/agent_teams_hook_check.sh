#!/usr/bin/env bash
# agent_teams_hook_check.sh -- Verify teammates inherit hooks from settings.json
# Teammates are full Claude Code sessions that load the project's settings.json,
# including hooks. This verifies all required hooks are configured.
# Exit 0 = all hooks present, Exit 1 = missing hooks
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "FAILED: settings.json not found"
    exit 1
fi

# All hook types that teammates need to inherit
REQUIRED_HOOKS=("PostToolUse" "PreToolUse" "TeammateIdle" "TaskCompleted" "SessionStart")
MISSING=()
DETAILS=()

for hook_type in "${REQUIRED_HOOKS[@]}"; do
    RESULT=$(python3 -c "
import json
data = json.load(open('$SETTINGS_FILE'))
hooks = data.get('hooks', {})
if '$hook_type' not in hooks:
    print('missing')
elif len(hooks['$hook_type']) == 0:
    print('empty')
else:
    cmds = sum(len(e.get('hooks', [])) for e in hooks['$hook_type'])
    print(f'ok:{cmds}')
" 2>/dev/null || echo "error")

    if [[ "$RESULT" == "missing" || "$RESULT" == "empty" || "$RESULT" == "error" ]]; then
        MISSING+=("$hook_type")
    else
        CMD_COUNT="${RESULT#ok:}"
        DETAILS+=("$hook_type($CMD_COUNT cmds)")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "FAILED: Missing hooks for teammate inheritance: ${MISSING[*]}"
    exit 1
fi

echo "PASSED: All ${#REQUIRED_HOOKS[@]} hook types configured: ${DETAILS[*]}"
exit 0
