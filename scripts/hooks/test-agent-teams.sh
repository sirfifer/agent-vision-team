#!/usr/bin/env bash
# ============================================================================
# Agent Teams Integration Smoke Test
#
# Verifies that Agent Teams teammates can access MCP tools and that hooks
# fire for teammate actions. Fully automated via claude -p. $0 cost (Max).
#
# Usage:
#   ./scripts/hooks/test-agent-teams.sh                    # All phases
#   ./scripts/hooks/test-agent-teams.sh --keep             # Preserve workspace
#   ./scripts/hooks/test-agent-teams.sh --model sonnet     # Specific model
#   ./scripts/hooks/test-agent-teams.sh --phase 1          # Run only Phase 1
#
# Phases:
#   1  Teammate MCP Access: verify teammates can call MCP tools
#   2  Hook Firing: verify PostToolUse fires for teammate TaskCreate
#   3  TeammateIdle Hook Evidence (informational)
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Prevent "nested session" error when running from inside Claude Code (2.1.42+)
unset CLAUDECODE 2>/dev/null || true

# ── Defaults ──────────────────────────────────────────────────────────────────
KEEP=false
MODEL="sonnet"
PHASE=0  # 0 = run all phases

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --keep)    KEEP=true; shift ;;
        --model)   MODEL="$2"; shift 2 ;;
        --phase)   PHASE="$2"; shift 2 ;;
        *)         echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ── Workspace ─────────────────────────────────────────────────────────────────
TIMESTAMP=$(date +%s)
LIST_ID="teams-test-${TIMESTAMP}"
WORKSPACE=$(mktemp -d /tmp/avt-teams-test-XXXXXX)
TASK_DIR="${HOME}/.claude/tasks/${LIST_ID}"
LOG_FILE="${PROJECT_DIR}/.avt/hook-governance.log"
HOLISTIC_LOG_FILE="${PROJECT_DIR}/.avt/hook-holistic.log"
DB_FILE="${PROJECT_DIR}/.avt/governance.db"

mkdir -p "$WORKSPACE"

echo "============================================================"
echo "  Agent Teams Integration Smoke Test"
echo "============================================================"
echo "  Model:     ${MODEL}"
echo "  List ID:   ${LIST_ID}"
echo "  Workspace: ${WORKSPACE}"
echo "  Phase:     ${PHASE:-all}"
echo ""

# ── Helpers ───────────────────────────────────────────────────────────────────
PASS=0
FAIL=0

check() {
    local label="$1"
    local expected="$2"
    local actual="$3"

    if [[ "$actual" == "$expected" ]]; then
        echo "  PASS  $label"
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

check_contains() {
    local label="$1"
    local needle="$2"
    local haystack="$3"

    if echo "$haystack" | grep -qi "$needle" 2>/dev/null; then
        echo "  PASS  $label"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  $label (expected to contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

# ── Snapshot state ────────────────────────────────────────────────────────────
LOG_LINES_BEFORE=0
[[ -f "$LOG_FILE" ]] && LOG_LINES_BEFORE=$(wc -l < "$LOG_FILE" | tr -d ' ')

DB_GOVERNED_BEFORE=0
[[ -f "$DB_FILE" ]] && DB_GOVERNED_BEFORE=$(sqlite3 "$DB_FILE" "SELECT count(*) FROM governed_tasks;" 2>/dev/null || echo 0)

# ── Environment ───────────────────────────────────────────────────────────────
export CLAUDE_CODE_TASK_LIST_ID="$LIST_ID"
export CLAUDE_CODE_ENABLE_TASKS="true"
export CLAUDE_PROJECT_DIR="$PROJECT_DIR"
export GOVERNANCE_MOCK_REVIEW=true

mkdir -p "${PROJECT_DIR}/.avt"

# Clean up stale flags
rm -f "${PROJECT_DIR}/.avt/.holistic-review-pending-"* 2>/dev/null || true

# ══════════════════════════════════════════════════════════════════
# PHASE 1: Teammate MCP Access
# ══════════════════════════════════════════════════════════════════
if [[ "$PHASE" -eq 0 || "$PHASE" -eq 1 ]]; then
    echo "-- Phase 1: Teammate MCP Access --"
    echo ""

    PROMPT_FILE="${SCRIPT_DIR}/test-prompts/teams-mcp-prompt.md"
    if [[ ! -f "$PROMPT_FILE" ]]; then
        echo "  ERROR: Prompt file not found: $PROMPT_FILE"
        FAIL=$((FAIL + 1))
    else
        PROMPT=$(cat "$PROMPT_FILE")
        FULL_PROMPT="All files you create should go in the directory: ${WORKSPACE}

${PROMPT}"

        PHASE1_OUTPUT="${WORKSPACE}/phase1-output.txt"

        echo "  Running Claude with MCP connectivity test..."
        claude -p "$FULL_PROMPT" \
            --model "$MODEL" \
            --output-format text \
            --dangerously-skip-permissions \
            2>&1 | tee "$PHASE1_OUTPUT"

        echo ""
        echo "  -- Phase 1 Verification --"

        # Check results file
        RESULTS_FILE="${WORKSPACE}/mcp-test-results.txt"
        RESULTS_EXISTS="false"
        [[ -f "$RESULTS_FILE" ]] && RESULTS_EXISTS="true"
        check "MCP results file created" "true" "$RESULTS_EXISTS"

        if [[ -f "$RESULTS_FILE" ]]; then
            RESULTS_CONTENT=$(cat "$RESULTS_FILE")

            # Check for evidence of KG access
            KG_EVIDENCE=$(echo "$RESULTS_CONTENT" | grep -ci "KG.*SUCCESS\|search_nodes\|knowledge.*graph\|entities" 2>/dev/null || echo 0)
            check_gte "Evidence of KG MCP access" "1" "$KG_EVIDENCE"

            # Check for evidence of Governance access
            GOV_EVIDENCE=$(echo "$RESULTS_CONTENT" | grep -ci "GOVERNANCE.*SUCCESS\|governance.*status\|pending\|governed" 2>/dev/null || echo 0)
            check_gte "Evidence of Governance MCP access" "1" "$GOV_EVIDENCE"

            # Check for evidence of Quality access
            QUAL_EVIDENCE=$(echo "$RESULTS_CONTENT" | grep -ci "QUALITY.*SUCCESS\|validate\|quality\|gates" 2>/dev/null || echo 0)
            check_gte "Evidence of Quality MCP access" "1" "$QUAL_EVIDENCE"

            echo ""
            echo "  --- MCP Results ---"
            cat "$RESULTS_FILE"
        fi
    fi

    echo ""
fi

# ══════════════════════════════════════════════════════════════════
# PHASE 2: Hook Firing for Teammate TaskCreate
# ══════════════════════════════════════════════════════════════════
if [[ "$PHASE" -eq 0 || "$PHASE" -eq 2 ]]; then
    echo "-- Phase 2: Hook Firing for Teammate TaskCreate --"
    echo ""

    # Re-snapshot log
    LOG_LINES_BEFORE_P2=0
    [[ -f "$LOG_FILE" ]] && LOG_LINES_BEFORE_P2=$(wc -l < "$LOG_FILE" | tr -d ' ')

    PROMPT_FILE="${SCRIPT_DIR}/test-prompts/teams-hooks-prompt.md"
    if [[ ! -f "$PROMPT_FILE" ]]; then
        echo "  ERROR: Prompt file not found: $PROMPT_FILE"
        FAIL=$((FAIL + 1))
    else
        PROMPT=$(cat "$PROMPT_FILE")
        FULL_PROMPT="All files you create should go in the directory: ${WORKSPACE}

${PROMPT}"

        PHASE2_OUTPUT="${WORKSPACE}/phase2-output.txt"

        echo "  Running Claude with TaskCreate hook test..."
        claude -p "$FULL_PROMPT" \
            --model "$MODEL" \
            --output-format text \
            --dangerously-skip-permissions \
            2>&1 | tee "$PHASE2_OUTPUT"

        echo ""
        echo "  -- Phase 2 Verification --"

        # Check hook log for teammate task interceptions
        LOG_LINES_AFTER_P2=0
        [[ -f "$LOG_FILE" ]] && LOG_LINES_AFTER_P2=$(wc -l < "$LOG_FILE" | tr -d ' ')
        NEW_LOG_LINES=$((LOG_LINES_AFTER_P2 - LOG_LINES_BEFORE_P2))

        if [[ "$NEW_LOG_LINES" -gt 0 ]]; then
            TEAMMATE_INTERCEPTS=$(tail -n "$NEW_LOG_LINES" "$LOG_FILE" | grep -c "Intercepting task:.*Teammate task" 2>/dev/null || echo 0)
            check_gte "PostToolUse fired for teammate TaskCreate" "2" "$TEAMMATE_INTERCEPTS"

            PAIR_CREATED=$(tail -n "$NEW_LOG_LINES" "$LOG_FILE" | grep -c "Governance pair created:" 2>/dev/null || echo 0)
            check_gte "Governance pairs created for teammate tasks" "2" "$PAIR_CREATED"
        else
            echo "  No new hook log entries. Hook may not have fired."
            FAIL=$((FAIL + 2))
        fi

        # Check governance DB
        if [[ -f "$DB_FILE" ]]; then
            TEAMMATE_GOVERNED=$(sqlite3 "$DB_FILE" \
                "SELECT COUNT(*) FROM governed_tasks WHERE subject LIKE '%Teammate task%';" 2>/dev/null || echo 0)
            check_gte "Teammate tasks have governance DB records" "2" "$TEAMMATE_GOVERNED"
        fi

        # Check task files
        if [[ -d "$TASK_DIR" ]]; then
            TEAMMATE_REVIEWS=$(find "$TASK_DIR" -name "review-*.json" 2>/dev/null | xargs grep -l "Teammate task" 2>/dev/null | wc -l | tr -d ' ')
            check_gte "Review tasks created for teammate tasks" "2" "$TEAMMATE_REVIEWS"
        fi

        # Check for session-scoped flag file creation in log
        if [[ "$NEW_LOG_LINES" -gt 0 ]]; then
            SESSION_FLAGS=$(tail -n "$NEW_LOG_LINES" "$LOG_FILE" | grep -c "Flag file created.*session=" 2>/dev/null || echo 0)
            check_gte "Session-scoped flag files created" "1" "$SESSION_FLAGS"
        fi

        # Check marker file
        MARKER="${WORKSPACE}/teammate-tasks-done.txt"
        MARKER_EXISTS="false"
        [[ -f "$MARKER" ]] && MARKER_EXISTS="true"
        check "Marker file created (tasks done)" "true" "$MARKER_EXISTS"
    fi

    echo ""

    # -- Phase 3: TeammateIdle Hook Evidence (informational) --
    echo "-- Phase 3: TeammateIdle Hook Evidence (informational) --"
    if [[ -f "${WORKSPACE}/phase2-output.txt" ]]; then
        IDLE_REDIRECT=$(grep -ci "pending governance review\|before going idle\|TeammateIdle" "${WORKSPACE}/phase2-output.txt" 2>/dev/null || echo 0)
        if [[ "$IDLE_REDIRECT" -gt 0 ]]; then
            echo "  INFO: TeammateIdle hook redirect evidence found ($IDLE_REDIRECT occurrences)"
        else
            echo "  INFO: No TeammateIdle redirect evidence (timing-dependent, not a failure)"
        fi
    fi
    echo ""
fi

# ══════════════════════════════════════════════════════════════════
# PHASE 4: Structural Hook Verification
# ══════════════════════════════════════════════════════════════════
echo "-- Phase 4: Structural Hook Verification --"
echo "  (Verifies hooks are configured correctly for teammate scenarios)"

# TaskCompleted hook is configured
TC_HOOK=$(python3 -c "
import json
cfg = json.load(open('${PROJECT_DIR}/.claude/settings.json'))
hooks = cfg.get('hooks', {}).get('TaskCompleted', [])
print('configured' if hooks else 'missing')
" 2>/dev/null || echo "error")
check "TaskCompleted hook configured in settings.json" "configured" "$TC_HOOK"

# TeammateIdle hook is configured
TI_HOOK=$(python3 -c "
import json
cfg = json.load(open('${PROJECT_DIR}/.claude/settings.json'))
hooks = cfg.get('hooks', {}).get('TeammateIdle', [])
print('configured' if hooks else 'missing')
" 2>/dev/null || echo "error")
check "TeammateIdle hook configured in settings.json" "configured" "$TI_HOOK"

# Hook scripts exist and are executable
for hook_script in teammate-idle-gate.sh task-completed-gate.sh; do
    HOOK_PATH="${PROJECT_DIR}/scripts/hooks/${hook_script}"
    HOOK_EXEC="false"
    [[ -x "$HOOK_PATH" ]] && HOOK_EXEC="true"
    check "${hook_script} exists and is executable" "true" "$HOOK_EXEC"
done

# Session-scoped flag files are used (check gate script for glob pattern)
GATE_USES_GLOB=$(grep -c "holistic-review-pending-" "${PROJECT_DIR}/scripts/hooks/holistic-review-gate.sh" 2>/dev/null || echo 0)
check_gte "holistic-review-gate.sh uses session-scoped flag pattern" "1" "$GATE_USES_GLOB"

echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "============================================================"
echo "  SUMMARY"
echo "============================================================"
TOTAL=$((PASS + FAIL))
echo ""
echo "  Checks: $PASS passed, $FAIL failed (of $TOTAL)"
echo ""

if [[ "$FAIL" -eq 0 && "$PASS" -gt 0 ]]; then
    echo "  Result: ALL PASSED"
    FINAL_EXIT=0
elif [[ "$TOTAL" -eq 0 ]]; then
    echo "  Result: NO CHECKS RUN"
    FINAL_EXIT=2
else
    echo "  Result: FAILED ($FAIL failures)"
    FINAL_EXIT=1
fi

echo "============================================================"
echo ""

# ── Cleanup ───────────────────────────────────────────────────────────────────
if [[ "$KEEP" == "true" ]]; then
    echo "Workspace preserved: $WORKSPACE"
    echo "Task directory: $TASK_DIR"
    echo "To clean up: rm -rf $WORKSPACE $TASK_DIR"
else
    rm -rf "$WORKSPACE"
    echo "Workspace cleaned: $WORKSPACE"
    [[ -d "$TASK_DIR" ]] && echo "Task directory preserved: $TASK_DIR"
fi

exit $FINAL_EXIT
