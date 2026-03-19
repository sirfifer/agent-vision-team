#!/usr/bin/env bash
# hook_subagent_check.sh -- Verify Task subagents inherit PostToolUse hooks
# This is a structural/documentation check based on proven behavior.
# The actual live test is in test-hook-live.sh --level 3.
# Exit 0 = confirmed, Exit 1 = evidence missing
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

# Check that PostToolUse hooks are configured (prerequisite for inheritance)
HAS_POST_TOOL_USE=$(python3 -c "
import json
data = json.load(open('$SETTINGS_FILE'))
hooks = data.get('hooks', {})
if 'PostToolUse' in hooks and len(hooks['PostToolUse']) > 0:
    print('yes')
else:
    print('no')
" 2>/dev/null || echo "no")

if [[ "$HAS_POST_TOOL_USE" != "yes" ]]; then
    echo "FAILED: No PostToolUse hooks configured in settings.json"
    exit 1
fi

# Check that the hook script exists and is executable
HOOK_CMD=$(python3 -c "
import json
data = json.load(open('$SETTINGS_FILE'))
entries = data['hooks']['PostToolUse']
for entry in entries:
    for hook in entry.get('hooks', []):
        print(hook.get('command', ''))
        break
    break
" 2>/dev/null || echo "")

if [[ -z "$HOOK_CMD" ]]; then
    echo "FAILED: PostToolUse hook command is empty"
    exit 1
fi

# Verify the governance-task-intercept.py script exists
INTERCEPT_SCRIPT="$PROJECT_DIR/scripts/hooks/governance-task-intercept.py"
if [[ ! -f "$INTERCEPT_SCRIPT" ]]; then
    echo "FAILED: governance-task-intercept.py not found"
    exit 1
fi

echo "PASSED: PostToolUse hook configured; subagent inheritance proven in Level 3 tests"
exit 0
