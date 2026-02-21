#!/usr/bin/env bash
# Safety net hook: verify that submit_plan_for_review was called
# before allowing ExitPlanMode.
#
# This is a PreToolUse hook on ExitPlanMode. It checks the governance
# SQLite DB for a plan review record. If none exists, it exits 2
# to block the tool call and injects feedback via JSON stdout.
#
# Exit codes:
#   0 = allow (review found or DB not available)
#   2 = block (no review found)

set -euo pipefail

DB_PATH="${CLAUDE_PROJECT_DIR:-.}/.avt/governance.db"

# If governance DB doesn't exist, allow (server may not be running yet)
if [ ! -f "$DB_PATH" ]; then
  exit 0
fi

# Check if any plan reviews exist in the reviews table
PLAN_REVIEWS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM reviews WHERE plan_id IS NOT NULL;" 2>/dev/null || echo "0")

if [ "$PLAN_REVIEWS" -gt 0 ]; then
  # Audit: emit plan exit allowed (fire-and-forget)
  python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PROJECT_DIR:-.}/scripts/hooks')
from audit.emitter import emit_audit_event
emit_audit_event('governance.plan_exit_attempted', {
    'plan_reviews_found': int(sys.argv[1]), 'allowed': True,
}, source='hook:verify-governance-review')
" "$PLAN_REVIEWS" 2>/dev/null &
  # At least one plan review exists — allow
  exit 0
else
  # Audit: emit plan exit blocked (fire-and-forget)
  python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PROJECT_DIR:-.}/scripts/hooks')
from audit.emitter import emit_audit_event
emit_audit_event('governance.plan_exit_attempted', {
    'plan_reviews_found': 0, 'allowed': False,
}, source='hook:verify-governance-review')
" 2>/dev/null &
  # No plan review found — block with feedback
  cat <<'FEEDBACK'
{
  "additionalContext": "GOVERNANCE REVIEW REQUIRED: You must call submit_plan_for_review() on the collab-governance MCP server before presenting your plan. No plan review was found in the governance database. Please submit your plan for governance review first."
}
FEEDBACK
  exit 2
fi
