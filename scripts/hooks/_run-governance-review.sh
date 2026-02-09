#!/usr/bin/env bash
# Background governance review runner.
#
# Spawned by governance-task-intercept.py as a detached background process.
# Runs claude --print with governance-reviewer context, then calls the
# governance MCP server to complete the review.
#
# Usage: _run-governance-review.sh <review_task_id> <impl_task_id> <subject>
#
# This script uses temp file I/O (the gold-standard CLI pattern) to avoid
# argument length limits and pipe buffering issues.

set -euo pipefail

REVIEW_TASK_ID="${1:?Missing review_task_id}"
IMPL_TASK_ID="${2:?Missing impl_task_id}"
SUBJECT="${3:-unknown}"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
LOG_FILE="${PROJECT_DIR}/.avt/hook-governance.log"

log() {
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[$ts] [async-review] $*" >> "$LOG_FILE" 2>/dev/null || true
}

log "Starting async review: review=$REVIEW_TASK_ID impl=$IMPL_TASK_ID subject=$SUBJECT"

# If GOVERNANCE_MOCK_REVIEW is set (E2E tests), auto-approve immediately
if [ -n "${GOVERNANCE_MOCK_REVIEW:-}" ]; then
    log "Mock mode: auto-approving review $REVIEW_TASK_ID"
    # Use the governance server's Python to complete the review
    cd "$PROJECT_DIR/mcp-servers/governance"
    uv run python -c "
import sys
sys.path.insert(0, '.')
from collab_governance.task_integration import release_task
from collab_governance.store import GovernanceStore
from collab_governance.models import TaskReviewStatus, Verdict
from pathlib import Path
from datetime import datetime, timezone

db_path = Path('${PROJECT_DIR}/.avt/governance.db')
store = GovernanceStore(db_path=db_path)

# Update review record
review = store.get_task_review_by_review_task_id('$REVIEW_TASK_ID')
if review:
    review.status = TaskReviewStatus.APPROVED
    review.verdict = Verdict.APPROVED
    review.guidance = 'Mock review: auto-approved'
    review.completed_at = datetime.now(timezone.utc).isoformat()
    store.update_task_review(review)

# Release the task blocker
release_task('$REVIEW_TASK_ID', 'approved', 'Mock review: auto-approved')

# Update governed task status
store.update_governed_task_status('$IMPL_TASK_ID', 'approved', datetime.now(timezone.utc).isoformat())
store.close()
print('Review completed (mock)')
" 2>&1 | while IFS= read -r line; do log "$line"; done
    log "Mock review completed for $REVIEW_TASK_ID"
    exit 0
fi

# Query sibling tasks for context
LIST_ID="${CLAUDE_CODE_TASK_LIST_ID:-default}"
SIBLING_TASKS=$(cd "$PROJECT_DIR/mcp-servers/governance" && uv run python -c "
import sys, json
sys.path.insert(0, '.')
from collab_governance.store import GovernanceStore
from pathlib import Path

db_path = Path('${PROJECT_DIR}/.avt/governance.db')
if not db_path.exists():
    print('- (no governance DB found)')
    sys.exit(0)
store = GovernanceStore(db_path=db_path)
all_tasks = store.get_all_governed_tasks(limit=20)
# Construct the namespaced ID for comparison
my_id = '${LIST_ID}/${IMPL_TASK_ID}'
siblings = [t for t in all_tasks if t['implementation_task_id'] != my_id]
if siblings:
    for t in siblings[:5]:
        print(f'- {t[\"subject\"]} (status: {t[\"current_status\"]})')
else:
    print('- (no sibling tasks)')
store.close()
" 2>/dev/null || echo "- (could not query siblings)")

log "Sibling tasks: $SIBLING_TASKS"

# Build the review prompt
INPUT_FILE=$(mktemp "${TMPDIR:-/tmp}/avt-review-XXXXXX-input.md")
OUTPUT_FILE=$(mktemp "${TMPDIR:-/tmp}/avt-review-XXXXXX-output.md")

cleanup() {
    rm -f "$INPUT_FILE" "$OUTPUT_FILE" 2>/dev/null || true
}
trap cleanup EXIT

cat > "$INPUT_FILE" <<PROMPT
You are a governance reviewer. A new task has been created and needs governance review before execution.

## Task Under Review
- **Subject**: $SUBJECT
- **Task ID**: $IMPL_TASK_ID
- **Review Task ID**: $REVIEW_TASK_ID

## Sibling Tasks (created in the same session)
Consider whether this task makes sense in context of its siblings:
$SIBLING_TASKS

## Instructions

Apply PIN (Positive, Innovative, Negative) methodology:

1. **POSITIVE**: What's sound about this task? Is it well-scoped and clear?
2. **INNOVATIVE**: Does the task show good thinking about the project?
3. **NEGATIVE**: Evaluate alignment with vision standards and architecture patterns.
   - For simple, well-defined tasks, approve quickly and note what's good.
   - For tasks that touch critical systems, require more scrutiny.
   - If blocking, specify what's salvageable and what needs to change.

Respond with ONLY a JSON object (no markdown, no explanation outside the JSON):
{
  "verdict": "approved" | "blocked" | "needs_human_review",
  "strengths_summary": "what the task gets right",
  "findings": [
    {
      "tier": "vision" | "architecture" | "quality",
      "severity": "vision_conflict" | "architectural" | "logic",
      "description": "what was found",
      "suggestion": "how to fix it",
      "strengths": ["what is sound"],
      "salvage_guidance": "what to preserve"
    }
  ],
  "guidance": "acknowledge strengths, then direct changes",
  "standards_verified": ["list of standards checked"]
}
PROMPT

log "Running claude --print for review..."

# Run claude --print with temp file I/O
if claude --print < "$INPUT_FILE" > "$OUTPUT_FILE" 2>/dev/null; then
    REVIEW_OUTPUT=$(cat "$OUTPUT_FILE")
    log "claude --print completed. Output length: ${#REVIEW_OUTPUT}"
else
    log "claude --print failed. Marking as needs_human_review."
    REVIEW_OUTPUT='{"verdict":"needs_human_review","findings":[],"guidance":"Automated review failed. Manual review required.","standards_verified":[]}'
fi

# Parse verdict and complete the review via Python
cd "$PROJECT_DIR/mcp-servers/governance"
echo "$REVIEW_OUTPUT" | uv run python -c "
import json
import sys
sys.path.insert(0, '.')
from collab_governance.task_integration import release_task
from collab_governance.store import GovernanceStore
from collab_governance.models import TaskReviewStatus, Verdict, Finding
from pathlib import Path
from datetime import datetime, timezone

raw = sys.stdin.read().strip()
db_path = Path('${PROJECT_DIR}/.avt/governance.db')

# Parse the review output
try:
    # Try to extract JSON from the output
    data = None
    if raw.startswith('{'):
        data = json.loads(raw)
    else:
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))

    if not data:
        raise ValueError('No JSON found')

    verdict_str = data.get('verdict', 'needs_human_review')
    guidance = data.get('guidance', '')
    strengths_summary = data.get('strengths_summary', '')
    findings_raw = data.get('findings', [])
    standards = data.get('standards_verified', [])
    # Prepend strengths to guidance so agents see what's sound
    if strengths_summary and verdict_str != 'approved':
        guidance = f'STRENGTHS: {strengths_summary} | GUIDANCE: {guidance}'
except Exception as e:
    verdict_str = 'needs_human_review'
    guidance = f'Could not parse review output: {e}'
    findings_raw = []
    standards = []

# Map verdict string to enum
verdict_map = {
    'approved': Verdict.APPROVED,
    'blocked': Verdict.BLOCKED,
    'needs_human_review': Verdict.NEEDS_HUMAN_REVIEW,
}
verdict = verdict_map.get(verdict_str, Verdict.NEEDS_HUMAN_REVIEW)
status_map = {
    Verdict.APPROVED: TaskReviewStatus.APPROVED,
    Verdict.BLOCKED: TaskReviewStatus.BLOCKED,
    Verdict.NEEDS_HUMAN_REVIEW: TaskReviewStatus.NEEDS_HUMAN_REVIEW,
}

store = GovernanceStore(db_path=db_path)

# Update review record
review = store.get_task_review_by_review_task_id('$REVIEW_TASK_ID')
if review:
    review.status = status_map.get(verdict, TaskReviewStatus.NEEDS_HUMAN_REVIEW)
    review.verdict = verdict
    review.guidance = guidance
    review.findings = [Finding(**f) for f in findings_raw if isinstance(f, dict)]
    review.standards_verified = standards
    review.completed_at = datetime.now(timezone.utc).isoformat()
    store.update_task_review(review)
    print(f'Review record updated: {review.id} -> {verdict_str}')

# If approved, release the task
if verdict == Verdict.APPROVED:
    result = release_task('$REVIEW_TASK_ID', 'approved', guidance)
    if result:
        print(f'Task released: $IMPL_TASK_ID')
    store.update_governed_task_status(
        '$IMPL_TASK_ID', 'approved',
        datetime.now(timezone.utc).isoformat()
    )
elif verdict == Verdict.BLOCKED:
    release_task('$REVIEW_TASK_ID', 'blocked', guidance)
    store.update_governed_task_status('$IMPL_TASK_ID', 'blocked')
else:
    release_task('$REVIEW_TASK_ID', 'needs_human_review', guidance)

store.close()
print(f'Review completed: verdict={verdict_str}')
" 2>&1 | while IFS= read -r line; do log "$line"; done

log "Async review finished for $REVIEW_TASK_ID"
