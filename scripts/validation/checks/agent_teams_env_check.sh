#!/usr/bin/env bash
# agent_teams_env_check.sh -- Check if CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is still needed
# Tests Agent Teams availability by checking CLI help/docs for the feature.
# Exit 0 = Agent Teams available, Exit 1 = not available
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

# Check if the env var is set in settings.json
HAS_ENV_VAR=$(python3 -c "
import json
data = json.load(open('$SETTINGS_FILE'))
env = data.get('env', {})
val = env.get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS', '')
print(val)
" 2>/dev/null || echo "")

# Check Claude Code version (Agent Teams official as of 2.1.x with Opus 4.6)
VERSION=$(claude --version 2>/dev/null | head -1 | sed 's/[^0-9.]//g' || echo "unknown")

# Check if TeamCreate tool is available (indicates Agent Teams support)
# We test by asking Claude if it has the TeamCreate tool
OUTPUT=$(unset CLAUDECODE 2>/dev/null; claude --print "Do you have access to a TeamCreate tool? Reply with exactly YES or NO." 2>/dev/null) || true

HAS_TEAMS="unknown"
if echo "$OUTPUT" | grep -qi "YES"; then
    HAS_TEAMS="yes"
elif echo "$OUTPUT" | grep -qi "NO"; then
    HAS_TEAMS="no"
fi

if [[ "$HAS_TEAMS" == "yes" ]]; then
    if [[ -n "$HAS_ENV_VAR" ]]; then
        echo "PASSED: Agent Teams available (env var set: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=$HAS_ENV_VAR; may be unnecessary now)"
    else
        echo "PASSED: Agent Teams available without experimental env var"
    fi
    exit 0
elif [[ "$HAS_TEAMS" == "no" ]]; then
    if [[ -z "$HAS_ENV_VAR" ]]; then
        echo "FAILED: Agent Teams not available and experimental env var not set"
    else
        echo "FAILED: Agent Teams not available despite env var being set"
    fi
    exit 1
else
    echo "INCONCLUSIVE: Could not determine Agent Teams availability (version: $VERSION)"
    exit 1
fi
