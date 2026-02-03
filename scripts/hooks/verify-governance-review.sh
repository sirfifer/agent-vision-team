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

DB_PATH="${CLAUDE_PROJECT_DIR:-.}/.claude/collab/governance.db"

# If governance DB doesn't exist, allow (server may not be running yet)
if [ ! -f "$DB_PATH" ]; then
  exit 0
fi

# Check if any plan reviews exist in the reviews table
PLAN_REVIEWS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM reviews WHERE plan_id IS NOT NULL;" 2>/dev/null || echo "0")

if [ "$PLAN_REVIEWS" -gt 0 ]; then
  # At least one plan review exists — allow
  exit 0
else
  # No plan review found — block with feedback
  cat <<'FEEDBACK'
{
  "additionalContext": "GOVERNANCE REVIEW REQUIRED: You must call submit_plan_for_review() on the collab-governance MCP server before presenting your plan. No plan review was found in the governance database. Please submit your plan for governance review first."
}
FEEDBACK
  exit 2
fi
