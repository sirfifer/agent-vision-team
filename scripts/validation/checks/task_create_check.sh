#!/usr/bin/env bash
# task_create_check.sh -- Verify TaskCreate produces task files
# Uses the existing task system infrastructure.
# Exit 0 = task creation works, Exit 1 = broken
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Use a unique test task list to avoid polluting real data
TEST_LIST="validation-test-$$"
TASK_DIR="$HOME/.claude/tasks/$TEST_LIST"

# Clean up from any previous run
rm -rf "$TASK_DIR"

# Try creating a task via claude --print
OUTPUT=$(unset CLAUDECODE 2>/dev/null; \
    CLAUDE_CODE_ENABLE_TASKS=true \
    CLAUDE_CODE_TASK_LIST_ID="$TEST_LIST" \
    claude --print "Create a task with subject 'Platform validation test task'. Do not do anything else." 2>/dev/null) || true

# Check if task files were created
if [[ -d "$TASK_DIR" ]] && ls "$TASK_DIR"/*.json 1>/dev/null 2>&1; then
    TASK_COUNT=$(ls "$TASK_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
    echo "PASSED: TaskCreate produced $TASK_COUNT task file(s) in $TASK_DIR"

    # Clean up
    rm -rf "$TASK_DIR"
    exit 0
else
    echo "FAILED: No task files created in $TASK_DIR"
    rm -rf "$TASK_DIR"
    exit 1
fi
