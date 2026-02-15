#!/usr/bin/env bash
# TeammateIdle hook: prevent teammate from going idle if governance
# obligations remain (pending reviews, quality gates not run).
#
# This hook fires when a teammate is about to go idle. It checks
# the governance DB for pending reviews in the teammate's session.
#
# Exit codes:
#   0 = allow idle (no pending obligations)
#   2 = keep working (additionalContext provides feedback)

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
DB_PATH="${PROJECT_DIR}/.avt/governance.db"

# Read hook input from stdin
INPUT=$(cat)

# If no governance DB, allow idle (no governance system active)
if [ ! -f "$DB_PATH" ]; then
    exit 0
fi

# Check for pending reviews (any review in "pending" status)
PENDING=$(sqlite3 "$DB_PATH" \
    "SELECT COUNT(*) FROM task_reviews WHERE status = 'pending';" 2>/dev/null || echo "0")

if [ "$PENDING" -gt 0 ]; then
    python3 -c "
import json, sys
json.dump({
    'additionalContext': f'You have {sys.argv[1]} pending governance review(s). Complete or acknowledge them before going idle. Use get_pending_reviews() to see what needs attention.'
}, sys.stdout)
" "$PENDING"
    exit 2
fi

# Check for governed tasks still in pending_review status
PENDING_TASKS=$(sqlite3 "$DB_PATH" \
    "SELECT COUNT(*) FROM governed_tasks WHERE current_status = 'pending_review';" 2>/dev/null || echo "0")

if [ "$PENDING_TASKS" -gt 0 ]; then
    python3 -c "
import json, sys
json.dump({
    'additionalContext': f'{sys.argv[1]} task(s) are still awaiting governance review. Wait for reviews to complete before going idle.'
}, sys.stdout)
" "$PENDING_TASKS"
    exit 2
fi

exit 0
