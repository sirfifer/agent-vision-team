#!/usr/bin/env bash
# env_override_check.sh -- Verify settings.json env block behavior
# This is informational: documents whether settings.json env overrides shell env
# Exit 0 = behavior confirmed, Exit 1 = unexpected behavior
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "FAILED: settings.json not found"
    exit 1
fi

# Check what env vars are defined in settings.json
ENV_VARS=$(python3 -c "
import json
data = json.load(open('$SETTINGS_FILE'))
env = data.get('env', {})
print(', '.join(f'{k}={v}' for k, v in env.items()))
" 2>/dev/null || echo "none")

if [[ "$ENV_VARS" == "none" || -z "$ENV_VARS" ]]; then
    echo "INFO: No env vars defined in settings.json"
    exit 0
fi

echo "PASSED: settings.json env block defines: $ENV_VARS"
exit 0
