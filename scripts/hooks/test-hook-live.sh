#!/usr/bin/env bash
# ============================================================================
# Live integration test for the governance hook pipeline.
#
# Launches a REAL Claude Code session that does real work (builds a Python
# library). The PostToolUse hook on TaskCreate should fire automatically,
# creating governance pairs for every task Claude creates.
#
# Usage:
#   ./scripts/hooks/test-hook-live.sh                 # Level 1 (mock review)
#   ./scripts/hooks/test-hook-live.sh --level 2       # Full governance review
#   ./scripts/hooks/test-hook-live.sh --level 3       # Full + subagents
#   ./scripts/hooks/test-hook-live.sh --keep           # Preserve workspace
#   ./scripts/hooks/test-hook-live.sh --model opus     # Use a specific model
#
# Levels:
#   1  Mock review (GOVERNANCE_MOCK_REVIEW=true). Tests interception only.
#   2  Real governance review with real criteria. Tests approve + block paths.
#   3  Real review + subagent delegation. Tests hook inheritance.
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── Defaults ────────────────────────────────────────────────────────────────
LEVEL=1
KEEP=false
MODEL="sonnet"  # sonnet is more likely to use task decomposition than haiku

# ── Parse args ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --level)  LEVEL="$2"; shift 2 ;;
        --keep)   KEEP=true; shift ;;
        --model)  MODEL="$2"; shift 2 ;;
        *)        echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ── Workspace setup ─────────────────────────────────────────────────────────
TIMESTAMP=$(date +%s)
LIST_ID="hook-live-test-${TIMESTAMP}"
WORKSPACE=$(mktemp -d /tmp/avt-hook-live-XXXXXX)
TASK_DIR="${HOME}/.claude/tasks/${LIST_ID}"
LOG_FILE="${PROJECT_DIR}/.avt/hook-governance.log"
HOLISTIC_LOG_FILE="${PROJECT_DIR}/.avt/hook-holistic.log"
DB_FILE="${PROJECT_DIR}/.avt/governance.db"
FLAG_FILE="${PROJECT_DIR}/.avt/.holistic-review-pending"
CLAUDE_OUTPUT="${WORKSPACE}/claude-output.txt"

mkdir -p "$WORKSPACE"

echo "============================================================"
echo "  Hook Pipeline Live Integration Test"
echo "============================================================"
echo "  Level:     ${LEVEL}"
echo "  Model:     ${MODEL}"
echo "  List ID:   ${LIST_ID}"
echo "  Workspace: ${WORKSPACE}"
echo "  Task dir:  ${TASK_DIR}"
echo "  Tasks:     CLAUDE_CODE_ENABLE_TASKS=true"
echo ""

# ── Snapshot state before test ──────────────────────────────────────────────
LOG_LINES_BEFORE=0
if [[ -f "$LOG_FILE" ]]; then
    LOG_LINES_BEFORE=$(wc -l < "$LOG_FILE" | tr -d ' ')
fi

DB_GOVERNED_BEFORE=0
DB_REVIEWS_BEFORE=0
DB_HOLISTIC_BEFORE=0
if [[ -f "$DB_FILE" ]]; then
    DB_GOVERNED_BEFORE=$(sqlite3 "$DB_FILE" "SELECT count(*) FROM governed_tasks;" 2>/dev/null || echo 0)
    DB_REVIEWS_BEFORE=$(sqlite3 "$DB_FILE" "SELECT count(*) FROM task_reviews;" 2>/dev/null || echo 0)
    DB_HOLISTIC_BEFORE=$(sqlite3 "$DB_FILE" "SELECT count(*) FROM holistic_reviews;" 2>/dev/null || echo 0)
fi

HOLISTIC_LOG_BEFORE=0
if [[ -f "$HOLISTIC_LOG_FILE" ]]; then
    HOLISTIC_LOG_BEFORE=$(wc -l < "$HOLISTIC_LOG_FILE" | tr -d ' ')
fi

# ── Select prompt ───────────────────────────────────────────────────────────
PROMPT_FILE="${SCRIPT_DIR}/test-prompts/level-${LEVEL}-prompt.md"
if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "ERROR: Prompt file not found: $PROMPT_FILE"
    exit 1
fi

PROMPT=$(cat "$PROMPT_FILE")

# ── Environment ─────────────────────────────────────────────────────────────
export CLAUDE_CODE_TASK_LIST_ID="$LIST_ID"
export CLAUDE_CODE_ENABLE_TASKS="true"
export CLAUDE_PROJECT_DIR="$PROJECT_DIR"

if [[ "$LEVEL" -eq 1 ]]; then
    export GOVERNANCE_MOCK_REVIEW=true
    echo "  Mock review: ENABLED (auto-approve)"
else
    unset GOVERNANCE_MOCK_REVIEW 2>/dev/null || true
    echo "  Mock review: DISABLED (real governance review)"
fi
echo ""

# ── Ensure .avt directory exists ────────────────────────────────────────────
mkdir -p "${PROJECT_DIR}/.avt"

# Clean up any stale holistic review flag from previous runs
rm -f "$FLAG_FILE" 2>/dev/null || true

# ── Run Claude ──────────────────────────────────────────────────────────────
echo "--- Running Claude Code session ---"
echo "  Prompt file: $PROMPT_FILE"
echo "  First line:  $(head -1 "$PROMPT_FILE")"
echo ""
echo "  This may take several minutes..."
echo ""

# Run Claude FROM THE PROJECT DIRECTORY so hooks from .claude/settings.json load.
# The prompt instructs Claude to write files in the workspace directory.
# --dangerously-skip-permissions: avoids interactive permission prompts
FULL_PROMPT="All files you create should go in the directory: ${WORKSPACE}

${PROMPT}"

claude -p "$FULL_PROMPT" \
    --model "$MODEL" \
    --output-format text \
    --dangerously-skip-permissions \
    2>&1 | tee "$CLAUDE_OUTPUT"

CLAUDE_EXIT=$?

echo ""
echo "--- Claude exited with code: $CLAUDE_EXIT ---"
echo ""

# ── Verification ────────────────────────────────────────────────────────────
echo "============================================================"
echo "  VERIFICATION"
echo "============================================================"
echo ""

PASS=0
FAIL=0
CLAUDE_TASK_FILES=0
REVIEW_FILES=0
INTERCEPTION_RATE="N/A"
NEW_GOVERNED=0
NEW_REVIEWS=0

check() {
    local label="$1"
    local expected="$2"
    local actual="$3"

    if [[ "$actual" == "$expected" ]]; then
        echo "  PASS  $label (expected=$expected, got=$actual)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  $label (expected=$expected, got=$actual)"
        FAIL=$((FAIL + 1))
    fi
}

check_gte() {
    local label="$1"
    local min="$2"
    local actual="$3"

    if [[ "$actual" -ge "$min" ]]; then
        echo "  PASS  $label (expected>=$min, got=$actual)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  $label (expected>=$min, got=$actual)"
        FAIL=$((FAIL + 1))
    fi
}

# --- 1. Task directory ---
echo "-- Task Files --"
if [[ -d "$TASK_DIR" ]]; then
    echo "  Task directory exists: $TASK_DIR"

    TOTAL_TASK_FILES=$(find "$TASK_DIR" -name "*.json" -not -name ".*" | wc -l | tr -d ' ')
    echo "  Total task JSON files: $TOTAL_TASK_FILES"

    # review-* files are created by our hook
    REVIEW_FILES=$(find "$TASK_DIR" -name "review-*.json" | wc -l | tr -d ' ')
    echo "  Review files (hook-created): $REVIEW_FILES"

    # Everything else was created by Claude via TaskCreate
    CLAUDE_TASK_FILES=$((TOTAL_TASK_FILES - REVIEW_FILES))
    echo "  Claude-created files: $CLAUDE_TASK_FILES"

    if [[ "$CLAUDE_TASK_FILES" -gt 0 ]]; then
        if [[ "$REVIEW_FILES" -eq "$CLAUDE_TASK_FILES" ]]; then
            INTERCEPTION_RATE=100
        elif [[ "$REVIEW_FILES" -gt 0 ]]; then
            INTERCEPTION_RATE=$((REVIEW_FILES * 100 / CLAUDE_TASK_FILES))
        else
            INTERCEPTION_RATE=0
        fi
        echo "  Interception rate: ${INTERCEPTION_RATE}%"

        check_gte "Claude created tasks" "1" "$CLAUDE_TASK_FILES"
        check "Interception rate is 100%" "100" "$INTERCEPTION_RATE"

        # Check that each review file has non-empty blocks (proves pairing).
        # Note: We check review files instead of implementation task blockedBy
        # because async mock reviews may clear blockedBy before verification.
        LINKED_COUNT=0
        for f in "$TASK_DIR"/review-*.json; do
            [[ -f "$f" ]] || continue
            HAS_BLOCKS=$(python3 -c "
import json
with open('$f') as fh:
    d = json.load(fh)
    blocks = d.get('blocks', [])
    # Ensure blocks has at least one non-empty entry
    valid = [b for b in blocks if b]
    print(len(valid))
" 2>/dev/null || echo "0")
            if [[ "$HAS_BLOCKS" -ge 1 ]]; then
                LINKED_COUNT=$((LINKED_COUNT + 1))
            fi
        done
        echo "  Review files with valid blocks: $LINKED_COUNT / $REVIEW_FILES"
        check "All review files linked to implementation tasks" "$REVIEW_FILES" "$LINKED_COUNT"
    else
        echo ""
        echo "  WARNING: No task files created by Claude."
        echo "  Possible causes:"
        echo "    - TaskCreate may not be available in --print mode"
        echo "    - The model may have done the work without decomposing into tasks"
        echo "    - The task list ID may not have been recognized"
        echo ""

        # Check environment
        echo "  Environment check:"
        echo "    CLAUDE_CODE_ENABLE_TASKS=${CLAUDE_CODE_ENABLE_TASKS:-unset}"
        echo "    CLAUDE_CODE_TASK_LIST_ID=${CLAUDE_CODE_TASK_LIST_ID:-unset}"

        # Check if any tasks ended up in a different directory
        echo "  Checking other task directories..."
        if [[ -d "${HOME}/.claude/tasks" ]]; then
            for d in "${HOME}/.claude/tasks"/*/; do
                [[ -d "$d" ]] || continue
                COUNT=$(find "$d" -name "*.json" -not -name ".*" 2>/dev/null | wc -l | tr -d ' ')
                if [[ "$COUNT" -gt 0 ]]; then
                    echo "    $(basename "$d"): $COUNT files"
                fi
            done
        fi
        FAIL=$((FAIL + 1))
    fi

    # List all task files for inspection
    echo ""
    echo "  --- Task file listing ---"
    for f in "$TASK_DIR"/*.json; do
        [[ -f "$f" ]] || continue
        [[ "$(basename "$f")" == .* ]] && continue
        INFO=$(python3 -c "
import json
with open('$f') as fh:
    d = json.load(fh)
    subj = d.get('subject', '???')[:60]
    st = d.get('status', '?')
    bb = len(d.get('blockedBy', []))
    bl = len(d.get('blocks', []))
    print(f'{st} blockedBy={bb} blocks={bl} | {subj}')
" 2>/dev/null || echo "???")
        echo "    $(basename "$f"): $INFO"
    done
    echo ""
else
    echo "  Task directory does NOT exist: $TASK_DIR"
    echo "  Claude did not use TaskCreate (or used a different list ID)."
    echo ""

    # Scan for any task directories
    if [[ -d "${HOME}/.claude/tasks" ]]; then
        echo "  Existing task directories:"
        ls -la "${HOME}/.claude/tasks/" 2>/dev/null || echo "    (none)"
    else
        echo "  No ~/.claude/tasks/ directory exists at all."
    fi
    echo ""
    FAIL=$((FAIL + 1))
fi

# --- 2. Hook log ---
echo "-- Hook Log --"
if [[ -f "$LOG_FILE" ]]; then
    LOG_LINES_AFTER=$(wc -l < "$LOG_FILE" | tr -d ' ')
    NEW_LOG_LINES=$((LOG_LINES_AFTER - LOG_LINES_BEFORE))
    echo "  New log entries since test start: $NEW_LOG_LINES"

    if [[ "$NEW_LOG_LINES" -gt 0 ]]; then
        INTERCEPT_LOG_COUNT=$(tail -n "$NEW_LOG_LINES" "$LOG_FILE" | grep -c "Intercepting task:" 2>/dev/null || echo 0)
        SKIP_LOG_COUNT=$(tail -n "$NEW_LOG_LINES" "$LOG_FILE" | grep -c "Skipping review task:" 2>/dev/null || echo 0)
        PAIR_LOG_COUNT=$(tail -n "$NEW_LOG_LINES" "$LOG_FILE" | grep -c "Governance pair created:" 2>/dev/null || echo 0)
        POSTTOOL_COUNT=$(tail -n "$NEW_LOG_LINES" "$LOG_FILE" | grep -c "PostToolUse fired" 2>/dev/null || echo 0)

        echo "  PostToolUse fired: $POSTTOOL_COUNT"
        echo "  Interceptions logged: $INTERCEPT_LOG_COUNT"
        echo "  Review tasks skipped: $SKIP_LOG_COUNT"
        echo "  Governance pairs created: $PAIR_LOG_COUNT"

        if [[ "$CLAUDE_TASK_FILES" -gt 0 ]]; then
            check_gte "Hook logged interceptions >= tasks" "$CLAUDE_TASK_FILES" "$INTERCEPT_LOG_COUNT"
        fi

        echo ""
        echo "  --- Recent hook log ---"
        tail -n "$NEW_LOG_LINES" "$LOG_FILE" | head -40
    else
        echo "  No new log entries. Hook did not fire."
    fi
    echo ""
else
    echo "  Hook log not found: $LOG_FILE"
    echo "  (This is expected on first run; the hook creates it)"
    echo ""
fi

# --- 3. Governance DB ---
echo "-- Governance Database --"
if [[ -f "$DB_FILE" ]]; then
    DB_GOVERNED_AFTER=$(sqlite3 "$DB_FILE" "SELECT count(*) FROM governed_tasks;" 2>/dev/null || echo 0)
    DB_REVIEWS_AFTER=$(sqlite3 "$DB_FILE" "SELECT count(*) FROM task_reviews;" 2>/dev/null || echo 0)

    NEW_GOVERNED=$((DB_GOVERNED_AFTER - DB_GOVERNED_BEFORE))
    NEW_REVIEWS=$((DB_REVIEWS_AFTER - DB_REVIEWS_BEFORE))

    echo "  New governed task records: $NEW_GOVERNED"
    echo "  New review records: $NEW_REVIEWS"

    if [[ "$CLAUDE_TASK_FILES" -gt 0 ]]; then
        check "DB governed tasks = Claude tasks" "$CLAUDE_TASK_FILES" "$NEW_GOVERNED"
        check "DB reviews = Claude tasks" "$CLAUDE_TASK_FILES" "$NEW_REVIEWS"
    fi

    if [[ "$NEW_GOVERNED" -gt 0 ]]; then
        echo ""
        echo "  --- Recent governed tasks ---"
        sqlite3 -header -column "$DB_FILE" \
            "SELECT implementation_task_id, substr(subject,1,50) as subject, current_status
             FROM governed_tasks
             ORDER BY rowid DESC LIMIT 15;" 2>/dev/null || echo "  (query failed)"
    fi
    echo ""
else
    echo "  Governance DB not found: $DB_FILE"
    echo ""
fi

# --- 4. Work output ---
echo "-- Work Output --"
if [[ "$LEVEL" -eq 1 ]]; then
    # Level 1: Python texttools library
    PY_MODULE_COUNT=$(find "$WORKSPACE" -path "*/texttools/*.py" 2>/dev/null | wc -l | tr -d ' ')
    PY_TEST_COUNT=$(find "$WORKSPACE" -path "*/tests/test_*.py" 2>/dev/null | wc -l | tr -d ' ')
    TOTAL_PY=$(find "$WORKSPACE" -name "*.py" 2>/dev/null | wc -l | tr -d ' ')

    echo "  Total Python files: $TOTAL_PY"
    echo "  Module files (texttools/*.py): $PY_MODULE_COUNT"
    echo "  Test files (tests/test_*.py): $PY_TEST_COUNT"

    check_gte "At least 1 work output file created" "1" "$TOTAL_PY"

    if [[ "$PY_MODULE_COUNT" -gt 0 ]]; then
        echo ""
        echo "  --- Module files ---"
        find "$WORKSPACE" -path "*/texttools/*.py" -exec basename {} \; 2>/dev/null | sort
    fi
    if [[ "$PY_TEST_COUNT" -gt 0 ]]; then
        echo ""
        echo "  --- Test files ---"
        find "$WORKSPACE" -path "*/tests/test_*.py" -exec basename {} \; 2>/dev/null | sort
    fi
else
    # Level 2/3: Poem anthology
    POEM_COUNT=$(find "$WORKSPACE" -path "*/poems/*.txt" 2>/dev/null | wc -l | tr -d ' ')
    TOTAL_FILES=$(find "$WORKSPACE" -type f -not -name ".*" 2>/dev/null | wc -l | tr -d ' ')

    echo "  Total files created: $TOTAL_FILES"
    echo "  Poem files (poems/*.txt): $POEM_COUNT"

    check_gte "At least 1 work output file created" "1" "$TOTAL_FILES"

    if [[ "$POEM_COUNT" -gt 0 ]]; then
        echo ""
        echo "  --- Poem files ---"
        find "$WORKSPACE" -path "*/poems/*.txt" -exec basename {} \; 2>/dev/null | sort
    fi
fi
echo ""

# --- 5. Level 2+: Review verdicts ---
if [[ "$LEVEL" -ge 2 ]]; then
    echo "-- Governance Review Verdicts (Level 2+) --"
    if [[ -f "$DB_FILE" ]]; then
        APPROVED=$(sqlite3 "$DB_FILE" \
            "SELECT count(*) FROM task_reviews WHERE status='approved';" 2>/dev/null || echo 0)
        BLOCKED=$(sqlite3 "$DB_FILE" \
            "SELECT count(*) FROM task_reviews WHERE status='blocked';" 2>/dev/null || echo 0)
        PENDING=$(sqlite3 "$DB_FILE" \
            "SELECT count(*) FROM task_reviews WHERE status='pending';" 2>/dev/null || echo 0)

        echo "  Approved: $APPROVED"
        echo "  Blocked: $BLOCKED"
        echo "  Pending: $PENDING"

        check_gte "At least 1 approved review" "1" "$APPROVED"
    fi
    echo ""
fi

# --- 6. Level 3: Subagent evidence ---
if [[ "$LEVEL" -ge 3 ]]; then
    echo "-- Subagent Evidence (Level 3) --"
    if grep -qi "subagent\|Task tool\|spawning\|delegat" "$CLAUDE_OUTPUT" 2>/dev/null; then
        echo "  Subagent delegation detected in Claude output"
    else
        echo "  No subagent delegation detected in Claude output"
    fi
    echo ""
fi

# --- 7. Holistic Review Pipeline ---
echo "-- Holistic Review Pipeline --"

# Determine if session_id was available (holistic path activated)
HOLISTIC_ACTIVATED="false"
NEW_HOLISTIC_LINES=0

if [[ -f "$DB_FILE" && "$CLAUDE_TASK_FILES" -gt 0 ]]; then
    # Check if any governed tasks from this test run have session_id populated
    WITH_SESSION=$(sqlite3 "$DB_FILE" \
        "SELECT count(*) FROM governed_tasks
         WHERE session_id != '' AND session_id IS NOT NULL
         AND implementation_task_id LIKE '${LIST_ID}/%';" 2>/dev/null || echo 0)

    if [[ "$WITH_SESSION" -gt 0 ]]; then
        HOLISTIC_ACTIVATED="true"
        echo "  Session tracking: ACTIVE ($WITH_SESSION tasks with session_id)"
    else
        echo "  Session tracking: INACTIVE (no session_id from Claude Code)"
    fi
fi

if [[ "$HOLISTIC_ACTIVATED" == "true" ]]; then
    # 7a. Session ID in governed tasks
    check_gte "Tasks have session_id populated" "1" "$WITH_SESSION"

    # 7b. Holistic review log (settle checker activity)
    if [[ -f "$HOLISTIC_LOG_FILE" ]]; then
        HOLISTIC_LOG_AFTER=$(wc -l < "$HOLISTIC_LOG_FILE" | tr -d ' ')
        NEW_HOLISTIC_LINES=$((HOLISTIC_LOG_AFTER - HOLISTIC_LOG_BEFORE))
        echo "  New holistic log entries: $NEW_HOLISTIC_LINES"

        if [[ "$NEW_HOLISTIC_LINES" -gt 0 ]]; then
            SETTLE_STARTED=$(tail -n "$NEW_HOLISTIC_LINES" "$HOLISTIC_LOG_FILE" | grep -c "Settle checker started" 2>/dev/null || echo 0)
            SETTLE_DEFERRED=$(tail -n "$NEW_HOLISTIC_LINES" "$HOLISTIC_LOG_FILE" | grep -c "deferring" 2>/dev/null || echo 0)
            SETTLE_LATEST=$(tail -n "$NEW_HOLISTIC_LINES" "$HOLISTIC_LOG_FILE" | grep -c "I'm the latest" 2>/dev/null || echo 0)
            REVIEW_COMPLETED=$(tail -n "$NEW_HOLISTIC_LINES" "$HOLISTIC_LOG_FILE" | grep -c "Holistic review complete\|Mock holistic" 2>/dev/null || echo 0)
            FLAG_REMOVED=$(tail -n "$NEW_HOLISTIC_LINES" "$HOLISTIC_LOG_FILE" | grep -c "Flag.*removed\|Flag file removed" 2>/dev/null || echo 0)

            echo "  Settle checkers started: $SETTLE_STARTED"
            echo "  Settle checkers deferred (newer tasks existed): $SETTLE_DEFERRED"
            echo "  Latest checker triggered review: $SETTLE_LATEST"
            echo "  Holistic review completed: $REVIEW_COMPLETED"
            echo "  Flag file removed by settle checker: $FLAG_REMOVED"

            check_gte "Settle checkers spawned" "1" "$SETTLE_STARTED"
            check_gte "Holistic review completed" "1" "$REVIEW_COMPLETED"

            # If holistic review completed, verify individual reviews were queued
            INDIVIDUAL_QUEUED=$(tail -n "$NEW_HOLISTIC_LINES" "$HOLISTIC_LOG_FILE" | grep -c "Individual review queued\|Individual reviews queued" 2>/dev/null || echo 0)
            echo "  Individual reviews queued after holistic: $INDIVIDUAL_QUEUED"

            echo ""
            echo "  --- Recent holistic log ---"
            tail -n "$NEW_HOLISTIC_LINES" "$HOLISTIC_LOG_FILE" | head -30
        else
            echo "  No new holistic log entries. Settle checker may not have run."
        fi
    else
        echo "  Holistic log not found: $HOLISTIC_LOG_FILE"
        echo "  (settle checker creates this file)"
    fi

    echo ""

    # 7c. Flag file lifecycle
    # After approved holistic review (mock or real), flag should be removed.
    # After blocked review, flag should exist with status=blocked.
    # Determine expected state from holistic review DB verdict
    EXPECTED_FLAG_STATE="removed"  # default expectation
    if [[ -f "$DB_FILE" ]]; then
        HR_VERDICT=$(sqlite3 "$DB_FILE" \
            "SELECT verdict FROM holistic_reviews ORDER BY rowid DESC LIMIT 1;" 2>/dev/null || echo "")
        if [[ "$HR_VERDICT" == "blocked" || "$HR_VERDICT" == "needs_human_review" ]]; then
            EXPECTED_FLAG_STATE="present"
        fi
    fi

    if [[ -f "$FLAG_FILE" ]]; then
        FLAG_STATUS=$(python3 -c "
import json, sys
try:
    data = json.load(open('$FLAG_FILE'))
    print(data.get('status', 'unknown'))
except:
    print('unknown')
" 2>/dev/null || echo "unknown")
        echo "  Flag file: EXISTS (status=$FLAG_STATUS)"
        if [[ "$FLAG_STATUS" == "blocked" ]]; then
            echo "  WARN: Holistic review blocked. Tasks collectively violated standards."
            FLAG_GUIDANCE=$(python3 -c "
import json
data = json.load(open('$FLAG_FILE'))
print(data.get('guidance', '(no guidance)'))
" 2>/dev/null || echo "(could not read)")
            echo "  Guidance: $FLAG_GUIDANCE"
        fi
        # If we expected removal (approved), this is a failure
        if [[ "$EXPECTED_FLAG_STATE" == "removed" ]]; then
            check "Flag file removed after approved holistic review" "removed" "still_present"
        else
            check "Flag file present after $HR_VERDICT holistic review" "present" "present"
        fi
    else
        echo "  Flag file: cleaned up (holistic review approved)"
        if [[ "$EXPECTED_FLAG_STATE" == "removed" ]]; then
            check "Flag file removed after approved holistic review" "removed" "removed"
        else
            check "Flag file present after $HR_VERDICT holistic review" "present" "removed"
        fi
    fi

    # 7d. Holistic review DB record
    if [[ -f "$DB_FILE" ]]; then
        DB_HOLISTIC_AFTER=$(sqlite3 "$DB_FILE" "SELECT count(*) FROM holistic_reviews;" 2>/dev/null || echo 0)
        NEW_HOLISTIC=$((DB_HOLISTIC_AFTER - DB_HOLISTIC_BEFORE))
        echo "  Holistic review DB records (new): $NEW_HOLISTIC"

        if [[ "$NEW_HOLISTIC" -gt 0 ]]; then
            HOLISTIC_VERDICT=$(sqlite3 "$DB_FILE" \
                "SELECT verdict FROM holistic_reviews ORDER BY rowid DESC LIMIT 1;" 2>/dev/null || echo "unknown")
            HOLISTIC_TASK_COUNT=$(sqlite3 "$DB_FILE" \
                "SELECT task_ids FROM holistic_reviews ORDER BY rowid DESC LIMIT 1;" 2>/dev/null || echo "[]")
            HOLISTIC_SESSION=$(sqlite3 "$DB_FILE" \
                "SELECT session_id FROM holistic_reviews ORDER BY rowid DESC LIMIT 1;" 2>/dev/null || echo "unknown")

            echo "  Latest holistic review verdict: $HOLISTIC_VERDICT"
            echo "  Session: $HOLISTIC_SESSION"
            echo "  Tasks reviewed: $HOLISTIC_TASK_COUNT"

            check_gte "Holistic review DB record created" "1" "$NEW_HOLISTIC"
        else
            echo "  No holistic review records found."
            echo "  (This might mean < 2 tasks were created, skipping holistic review)"
            # Only fail this check if we have enough tasks for holistic review
            if [[ "$CLAUDE_TASK_FILES" -ge 2 ]]; then
                check_gte "Holistic review DB record created" "1" "$NEW_HOLISTIC"
            fi
        fi
    fi

    echo ""

    # 7e. Gate feedback in Claude output (informational)
    GATE_BLOCKS=$(grep -c "HOLISTIC GOVERNANCE REVIEW" "$CLAUDE_OUTPUT" 2>/dev/null || echo 0)
    GATE_IN_PROGRESS=$(grep -c "HOLISTIC GOVERNANCE REVIEW IN PROGRESS" "$CLAUDE_OUTPUT" 2>/dev/null || echo 0)
    GATE_BLOCKED=$(grep -c "HOLISTIC GOVERNANCE REVIEW BLOCKED" "$CLAUDE_OUTPUT" 2>/dev/null || echo 0)
    echo "  Gate block messages in Claude output: $GATE_BLOCKS"
    echo "    - In progress (waiting): $GATE_IN_PROGRESS"
    echo "    - Blocked (violation): $GATE_BLOCKED"
    # Informational only, not a hard assertion

else
    echo ""
    echo "  Holistic review path NOT activated."
    echo "  Possible causes:"
    echo "    - Claude Code does not provide session_id in PostToolUse hook input"
    echo "    - No tasks were created"
    echo "  Holistic review checks skipped. Individual review path was used instead."
fi
echo ""

# ── Summary ─────────────────────────────────────────────────────────────────
echo "============================================================"
echo "  SUMMARY"
echo "============================================================"
TOTAL=$((PASS + FAIL))
echo ""
echo "  Claude exit code:           $CLAUDE_EXIT"
echo "  Tasks created by Claude:    $CLAUDE_TASK_FILES"
echo "  Tasks intercepted by hook:  $REVIEW_FILES"
echo "  Interception rate:          ${INTERCEPTION_RATE}%"
echo "  DB governed task records:   $NEW_GOVERNED"
echo "  DB review records:          $NEW_REVIEWS"
echo "  Holistic review activated:  $HOLISTIC_ACTIVATED"
echo "  Holistic log entries:       $NEW_HOLISTIC_LINES"
if [[ "$LEVEL" -eq 1 ]]; then
    echo "  Python module files:        ${PY_MODULE_COUNT:-0}"
    echo "  Python test files:          ${PY_TEST_COUNT:-0}"
else
    echo "  Poem files:                 ${POEM_COUNT:-0}"
fi
echo ""
echo "  Checks: $PASS passed, $FAIL failed (of $TOTAL)"
echo ""

if [[ "$FAIL" -eq 0 && "$PASS" -gt 0 ]]; then
    echo "  Result: ALL PASSED"
    FINAL_EXIT=0
elif [[ "$CLAUDE_TASK_FILES" -eq 0 ]]; then
    echo "  Result: INCONCLUSIVE"
    echo "  Claude did not use TaskCreate. The hook could not be tested."
    echo ""
    echo "  Diagnostics:"
    echo "    CLAUDE_CODE_ENABLE_TASKS=${CLAUDE_CODE_ENABLE_TASKS:-unset}"
    echo "    CLAUDE_CODE_TASK_LIST_ID=${CLAUDE_CODE_TASK_LIST_ID:-unset}"
    echo ""
    echo "  Suggestions:"
    echo "    - Verify CLAUDE_CODE_ENABLE_TASKS=true is set"
    echo "    - Try with --model opus (more capable model)"
    echo "    - Try an interactive session: claude (then paste the prompt)"
    echo "    - Check claude --version is >= 2.1.16"
    FINAL_EXIT=2
else
    echo "  Result: FAILED ($FAIL failures)"
    FINAL_EXIT=1
fi

echo "============================================================"
echo ""

# ── Claude raw output (truncated) ──────────────────────────────────────────
echo "--- Claude output (last 30 lines) ---"
tail -30 "$CLAUDE_OUTPUT"
echo ""

# ── Cleanup ─────────────────────────────────────────────────────────────────
if [[ "$KEEP" == "true" ]]; then
    echo "Workspace preserved: $WORKSPACE"
    echo "Task directory: $TASK_DIR"
    echo "To clean up: rm -rf $WORKSPACE $TASK_DIR"
else
    rm -rf "$WORKSPACE"
    echo "Workspace cleaned: $WORKSPACE"
    echo "Task directory preserved: $TASK_DIR"
    echo "To clean up: rm -rf $TASK_DIR"
fi

exit $FINAL_EXIT
