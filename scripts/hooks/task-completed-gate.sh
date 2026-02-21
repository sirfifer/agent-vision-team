#!/usr/bin/env bash
# TaskCompleted hook: prevent task completion if governance review
# is still pending or blocked.
#
# This hook fires when a task is being marked as completed. It verifies
# that governance requirements are met before allowing completion.
#
# Exit codes:
#   0 = allow completion
#   2 = block completion (additionalContext provides feedback)

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
DB_PATH="${PROJECT_DIR}/.avt/governance.db"

# Read hook input from stdin
INPUT=$(cat)

# Extract task subject from hook input
TASK_SUBJECT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    # TaskCompleted hook input may contain task info
    ti = data.get('tool_input', {})
    subject = ti.get('subject', '') or ti.get('title', '') or ''
    print(subject)
except Exception:
    print('')
" 2>/dev/null || echo "")

# Skip for review tasks (they complete as part of the review flow)
if echo "$TASK_SUBJECT" | grep -qi '^\[GOVERNANCE\]\|^\[REVIEW\]\|^\[SECURITY\]\|^\[ARCHITECTURE\]'; then
    exit 0
fi

# If no governance DB, allow completion (no governance system active)
if [ ! -f "$DB_PATH" ]; then
    exit 0
fi

# Extract task ID from hook input
TASK_ID=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {})
    task_id = ti.get('id', '') or ti.get('task_id', '') or ''
    print(task_id)
except Exception:
    print('')
" 2>/dev/null || echo "")

if [ -z "$TASK_ID" ]; then
    # Can't identify the task; allow completion (fail open)
    exit 0
fi

# Check if this task has a governed task record
LIST_ID="${CLAUDE_CODE_TASK_LIST_ID:-default}"
DB_TASK_ID="${LIST_ID}/${TASK_ID}"

STATUS=$(sqlite3 "$DB_PATH" \
    "SELECT current_status FROM governed_tasks WHERE implementation_task_id = '${DB_TASK_ID}' LIMIT 1;" 2>/dev/null || echo "")

# Audit helper: emit task completion event (fire-and-forget)
_audit_emit() {
    python3 -c "
import sys; sys.path.insert(0, '${PROJECT_DIR}/scripts/hooks')
from audit.emitter import emit_audit_event
emit_audit_event('task.completion_attempted', {
    'task_id': sys.argv[1], 'subject': sys.argv[2],
    'status': sys.argv[3], 'allowed': sys.argv[4] == 'true',
}, source='hook:task-completed-gate')
" "$1" "$2" "$3" "$4" 2>/dev/null &
}

case "$STATUS" in
    "approved"|"")
        # Approved or not governed: allow completion
        _audit_emit "$TASK_ID" "$TASK_SUBJECT" "${STATUS:-untracked}" "true"
        exit 0
        ;;
    "pending_review")
        _audit_emit "$TASK_ID" "$TASK_SUBJECT" "$STATUS" "false"
        python3 -c "
import json, sys
subject = sys.argv[1] or 'this task'
json.dump({
    'additionalContext': f\"Task '{subject}' cannot be completed: governance review is still pending. Wait for the review to complete. Use get_task_review_status() to check progress.\"
}, sys.stdout)
" "$TASK_SUBJECT"
        exit 2
        ;;
    "blocked")
        _audit_emit "$TASK_ID" "$TASK_SUBJECT" "$STATUS" "false"
        python3 -c "
import json, sys
subject = sys.argv[1] or 'this task'
json.dump({
    'additionalContext': f\"Task '{subject}' cannot be completed: governance review BLOCKED this task. Address the review findings before completing. Use get_task_review_status() to see the guidance.\"
}, sys.stdout)
" "$TASK_SUBJECT"
        exit 2
        ;;
    *)
        _audit_emit "$TASK_ID" "$TASK_SUBJECT" "$STATUS" "false"
        python3 -c "
import json, sys
subject = sys.argv[1] or 'this task'
status = sys.argv[2]
json.dump({
    'additionalContext': f\"Task '{subject}' has governance status '{status}'. Check get_task_review_status() before completing.\"
}, sys.stdout)
" "$TASK_SUBJECT" "$STATUS"
        exit 2
        ;;
esac
