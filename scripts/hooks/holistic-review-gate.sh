#!/usr/bin/env bash
# PreToolUse gate: blocks Write/Edit/Bash/Task while holistic review is pending.
#
# Fast path (~1ms): flag file doesn't exist -> exit 0 (allow)
# Slow path: flag file exists -> read it, determine status, exit 2 (block)
#
# The flag file is created by governance-task-intercept.py (PostToolUse hook)
# and removed by _holistic-settle-check.py after holistic review completes.
#
# Exit codes:
#   0 = allow the tool call
#   2 = block the tool call (additionalContext shown to agent)

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
FLAG_FILE="${PROJECT_DIR}/.avt/.holistic-review-pending"
STALE_TIMEOUT=300  # 5 minutes: auto-expire stale flags

# Fast path: no flag = no pending review
if [ ! -f "$FLAG_FILE" ]; then
    exit 0
fi

# Check for stale flag (older than STALE_TIMEOUT seconds)
if command -v python3 &>/dev/null; then
    IS_STALE=$(python3 -c "
import json, sys, time
from datetime import datetime, timezone
try:
    data = json.load(open('$FLAG_FILE'))
    created = data.get('created_at', '')
    if created:
        ts = datetime.fromisoformat(created).timestamp()
        if time.time() - ts > $STALE_TIMEOUT:
            print('stale')
            sys.exit(0)
    print('fresh')
except Exception:
    print('fresh')
" 2>/dev/null || echo "fresh")

    if [ "$IS_STALE" = "stale" ]; then
        # Remove stale flag and allow
        rm -f "$FLAG_FILE" 2>/dev/null || true
        exit 0
    fi
fi

# Flag exists and is fresh: read status
STATUS=$(python3 -c "
import json, sys
try:
    data = json.load(open('$FLAG_FILE'))
    print(data.get('status', 'pending'))
except Exception:
    print('pending')
" 2>/dev/null || echo "pending")

case "$STATUS" in
    pending)
        REASON="HOLISTIC GOVERNANCE REVIEW IN PROGRESS: Your tasks are being reviewed collectively before any work can begin. This typically takes 30-120 seconds. Please wait."
        ;;
    blocked)
        GUIDANCE=$(python3 -c "
import json, sys
try:
    data = json.load(open('$FLAG_FILE'))
    parts = []
    ss = data.get('strengths_summary', '')
    if ss:
        parts.append('WHAT IS SOUND: ' + ss)
    g = data.get('guidance', 'Review blocked.')
    parts.append('WHAT NEEDS CHANGE: ' + g)
    print(' '.join(parts).replace('\"', '\\\\\\''))
except Exception:
    print('Review blocked.')
" 2>/dev/null || echo "Review blocked.")
        REASON="HOLISTIC GOVERNANCE REVIEW: Your tasks were reviewed as a group and some aspects need revision. ${GUIDANCE} Review the guidance carefully: preserve what is sound and revise only the problematic tasks."
        ;;
    needs_human_review)
        REASON="HOLISTIC REVIEW: Needs human review. Tasks are held pending human approval. Contact the project lead."
        ;;
    *)
        REASON="HOLISTIC REVIEW: Unknown status. Tasks are held pending review."
        ;;
esac

# Output feedback as JSON and block
# Use python to ensure valid JSON output
python3 -c "
import json, sys
reason = sys.argv[1]
json.dump({'additionalContext': reason}, sys.stdout)
" "$REASON"
exit 2
