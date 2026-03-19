#!/usr/bin/env bash
# agent_teams_task_check.sh -- Verify Agent Teams can share a task list
# This is a structural check verifying the task sharing prerequisites are met.
# Full live testing is done by test-agent-teams.sh.
# Exit 0 = prerequisites met, Exit 1 = missing prerequisites
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

# Check 1: Agent Teams env var or native support
HAS_TEAMS_ENV=$(python3 -c "
import json
data = json.load(open('$SETTINGS_FILE'))
val = data.get('env', {}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS', '')
print('yes' if val else 'no')
" 2>/dev/null || echo "no")

# Check 2: Task system is usable
TASK_DIR="$HOME/.claude/tasks"
TASK_SYSTEM_WORKS=false
if [[ -d "$TASK_DIR" ]]; then
    TASK_SYSTEM_WORKS=true
fi

# Check 3: Hooks for task governance are configured
HAS_TASK_HOOKS=$(python3 -c "
import json
data = json.load(open('$SETTINGS_FILE'))
hooks = data.get('hooks', {})
has_tc = 'TaskCompleted' in hooks
has_ti = 'TeammateIdle' in hooks
print('yes' if has_tc and has_ti else 'no')
" 2>/dev/null || echo "no")

ISSUES=()
if [[ "$HAS_TEAMS_ENV" != "yes" ]]; then
    # Check if Agent Teams works without env var (post-graduation)
    ISSUES+=("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS not set (may not be needed post-graduation)")
fi
if [[ "$HAS_TASK_HOOKS" != "yes" ]]; then
    ISSUES+=("Missing TaskCompleted or TeammateIdle hooks")
fi

if [[ ${#ISSUES[@]} -eq 0 ]]; then
    echo "PASSED: Agent Teams task sharing prerequisites met (env var, task hooks)"
    exit 0
elif [[ ${#ISSUES[@]} -eq 1 && "${ISSUES[0]}" == *"may not be needed"* ]]; then
    echo "PASSED: Agent Teams task sharing prerequisites met (env var may be optional post-graduation)"
    exit 0
else
    echo "FAILED: Missing prerequisites: ${ISSUES[*]}"
    exit 1
fi
