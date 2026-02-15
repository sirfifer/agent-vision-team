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
FLAG_DIR="${PROJECT_DIR}/.avt"
FLAG_PATTERN=".holistic-review-pending-*"
STALE_TIMEOUT=300  # 5 minutes: auto-expire stale flags

# Fast path: no flag files = no pending review
# Session-scoped flag files (.holistic-review-pending-{session_id}) allow
# multiple concurrent Agent Teams teammates to have independent reviews.
if ! ls "${FLAG_DIR}"/${FLAG_PATTERN} 1>/dev/null 2>&1; then
    exit 0
fi

# Find the most restrictive flag file (check all, remove stale ones)
# Priority: blocked > needs_human_review > pending > (none)
FLAG_FILE=""
STATUS=""

if command -v python3 &>/dev/null; then
    RESULT=$(python3 -c "
import json, glob, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

flag_dir = '${FLAG_DIR}'
pattern = '${FLAG_PATTERN}'
stale_timeout = ${STALE_TIMEOUT}

# Priority map: higher = more restrictive
priority = {'blocked': 3, 'needs_human_review': 2, 'pending': 1}
best_file = ''
best_status = ''
best_priority = 0

for flag_path in glob.glob(os.path.join(flag_dir, pattern)):
    try:
        with open(flag_path) as f:
            data = json.load(f)

        # Check for stale flag
        created = data.get('created_at', '')
        if created:
            ts = datetime.fromisoformat(created).timestamp()
            if time.time() - ts > stale_timeout:
                os.unlink(flag_path)
                continue

        status = data.get('status', 'pending')
        p = priority.get(status, 1)
        if p > best_priority:
            best_priority = p
            best_status = status
            best_file = flag_path
    except Exception:
        continue

print(f'{best_file}|{best_status}')
" 2>/dev/null || echo "|")

    FLAG_FILE=$(echo "$RESULT" | cut -d'|' -f1)
    STATUS=$(echo "$RESULT" | cut -d'|' -f2)
fi

# All flags were stale and removed
if [ -z "$FLAG_FILE" ] || [ -z "$STATUS" ]; then
    exit 0
fi

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
