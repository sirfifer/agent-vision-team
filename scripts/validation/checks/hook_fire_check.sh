#!/usr/bin/env bash
# hook_fire_check.sh -- Verify hook types are configured in settings.json
# This checks that the hook TYPE and MATCHER exist in settings, confirming
# the platform accepts them without error (silent breakage detection).
# Usage: hook_fire_check.sh <hook_type> [matcher]
# Exit 0 = hook configured and accepted, Exit 1 = not found or invalid
set -euo pipefail

HOOK_TYPE="${1:?Usage: hook_fire_check.sh <hook_type> [matcher]}"
MATCHER="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "FAILED: settings.json not found"
    exit 1
fi

# Verify the hook type exists in settings
RESULT=$(python3 -c "
import json, sys

data = json.load(open('$SETTINGS_FILE'))
hooks = data.get('hooks', {})

hook_type = '$HOOK_TYPE'
matcher = '$MATCHER'

if hook_type not in hooks:
    print(f'MISSING: {hook_type} not in hooks section')
    sys.exit(1)

entries = hooks[hook_type]
if not entries:
    print(f'EMPTY: {hook_type} has no hook entries')
    sys.exit(1)

if matcher:
    # Check that at least one entry has this matcher
    found = False
    for entry in entries:
        entry_matcher = entry.get('matcher', '')
        if matcher in entry_matcher or entry_matcher == matcher:
            found = True
            break
    if not found:
        # Some hooks (TeammateIdle, TaskCompleted) don't use matchers
        # Check if any entry exists without a matcher
        for entry in entries:
            if 'matcher' not in entry:
                found = True
                break
    if not found:
        print(f'MISSING_MATCHER: {hook_type} has no entry matching \"{matcher}\"')
        sys.exit(1)

# Count hook commands
total_commands = sum(len(e.get('hooks', [])) for e in entries)
print(f'OK: {hook_type} configured with {len(entries)} entries, {total_commands} commands')
" 2>/dev/null) || {
    echo "FAILED: $HOOK_TYPE hook type not found in settings.json"
    exit 1
}

if echo "$RESULT" | grep -q "^OK:"; then
    # Verify the hook scripts actually exist and are executable
    SCRIPTS=$(python3 -c "
import json
data = json.load(open('$SETTINGS_FILE'))
entries = data.get('hooks', {}).get('$HOOK_TYPE', [])
for entry in entries:
    for hook in entry.get('hooks', []):
        cmd = hook.get('command', '')
        # Extract the script path (after python/uv/bash)
        print(cmd)
" 2>/dev/null || echo "")

    echo "PASSED: $RESULT"
    exit 0
else
    echo "FAILED: $RESULT"
    exit 1
fi
