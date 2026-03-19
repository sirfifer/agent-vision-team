#!/usr/bin/env bash
# mcp_tool_search_check.sh -- Verify MCP Tool Search is enabled
# Exit 0 = enabled, Exit 1 = not enabled
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "FAILED: settings.json not found"
    exit 1
fi

TOOL_SEARCH=$(python3 -c "
import json
data = json.load(open('$SETTINGS_FILE'))
env = data.get('env', {})
val = env.get('ENABLE_TOOL_SEARCH', '')
print(val)
" 2>/dev/null || echo "")

if [[ -n "$TOOL_SEARCH" ]]; then
    echo "PASSED: MCP Tool Search enabled (ENABLE_TOOL_SEARCH=$TOOL_SEARCH)"
    exit 0
else
    echo "FAILED: ENABLE_TOOL_SEARCH not set in settings.json env block"
    exit 1
fi
