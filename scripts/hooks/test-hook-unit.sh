#!/usr/bin/env bash
# ============================================================================
# Hook Unit Tests: exercises each hook script in isolation.
#
# Creates simulated environments (governance.db, flag files), pipes JSON
# via stdin, and verifies exit codes + stdout JSON output.
#
# No Claude Code session required. Fast (~2s), deterministic, $0.
#
# Usage:
#   ./scripts/hooks/test-hook-unit.sh
#   ./scripts/hooks/test-hook-unit.sh --verbose
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
GOVERNANCE_DIR="${PROJECT_DIR}/mcp-servers/governance"
WORKSPACE=$(mktemp -d /tmp/avt-hook-unit-XXXXXX)

# ── Parse args ────────────────────────────────────────────────────────────────
VERBOSE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)  VERBOSE=true; shift ;;
        *)             echo "Unknown arg: $1"; exit 1 ;;
    esac
done

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

check_contains() {
    local label="$1"
    local needle="$2"
    local haystack="$3"

    if echo "$haystack" | grep -qi "$needle" 2>/dev/null; then
        echo "  PASS  $label"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  $label (expected to contain '$needle')"
        [[ "$VERBOSE" == "true" ]] && echo "         actual: $haystack"
        FAIL=$((FAIL + 1))
    fi
}

# Create a minimal governance DB with the required schema
create_db() {
    local db_path="$1"
    mkdir -p "$(dirname "$db_path")"
    sqlite3 "$db_path" << 'SQL'
CREATE TABLE IF NOT EXISTS governed_tasks (
    id TEXT PRIMARY KEY,
    implementation_task_id TEXT UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    description TEXT,
    context TEXT,
    current_status TEXT NOT NULL DEFAULT 'pending_review',
    created_at TEXT NOT NULL,
    released_at TEXT,
    session_id TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS task_reviews (
    id TEXT PRIMARY KEY,
    review_task_id TEXT NOT NULL,
    implementation_task_id TEXT NOT NULL,
    review_type TEXT NOT NULL DEFAULT 'governance',
    status TEXT NOT NULL DEFAULT 'pending',
    context TEXT,
    verdict TEXT,
    guidance TEXT,
    findings TEXT,
    standards_verified TEXT,
    reviewer TEXT NOT NULL DEFAULT 'governance-reviewer',
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS holistic_reviews (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    task_ids TEXT NOT NULL,
    task_subjects TEXT NOT NULL,
    collective_intent TEXT,
    verdict TEXT,
    findings TEXT,
    guidance TEXT,
    standards_verified TEXT,
    reviewer TEXT NOT NULL DEFAULT 'governance-reviewer',
    created_at TEXT NOT NULL,
    strengths_summary TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    agent TEXT,
    category TEXT,
    summary TEXT,
    intent TEXT,
    expected_outcome TEXT,
    vision_references TEXT,
    alternatives TEXT,
    components_affected TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    decision_id TEXT,
    plan_id TEXT,
    verdict TEXT NOT NULL,
    findings TEXT,
    guidance TEXT,
    standards_verified TEXT,
    reviewer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    strengths_summary TEXT DEFAULT ''
);
SQL
}

echo "============================================================"
echo "  Hook Unit Tests"
echo "============================================================"
echo "  Workspace: ${WORKSPACE}"
echo ""

# ══════════════════════════════════════════════════════════════════
# GROUP 1: teammate-idle-gate.sh
# ══════════════════════════════════════════════════════════════════
echo "-- Group 1: teammate-idle-gate.sh --"

IDLE_HOOK="${PROJECT_DIR}/scripts/hooks/teammate-idle-gate.sh"

# Test 1a: No governance DB -- allow idle (exit 0)
WORK_1A="${WORKSPACE}/1a"
mkdir -p "${WORK_1A}/.avt"
EXIT_CODE=0
OUTPUT=$(echo '{}' | CLAUDE_PROJECT_DIR="${WORK_1A}" bash "$IDLE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "1a: No DB -> exit 0 (allow idle)" "0" "$EXIT_CODE"

# Test 1b: Empty governance DB -- allow idle (exit 0)
WORK_1B="${WORKSPACE}/1b"
create_db "${WORK_1B}/.avt/governance.db"
EXIT_CODE=0
OUTPUT=$(echo '{}' | CLAUDE_PROJECT_DIR="${WORK_1B}" bash "$IDLE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "1b: Empty DB -> exit 0 (allow idle)" "0" "$EXIT_CODE"

# Test 1c: Pending reviews exist -- keep working (exit 2)
WORK_1C="${WORKSPACE}/1c"
create_db "${WORK_1C}/.avt/governance.db"
sqlite3 "${WORK_1C}/.avt/governance.db" << 'SQL'
INSERT INTO task_reviews VALUES ('r1','review-abc','impl-1','governance','pending','ctx','','','[]','[]','reviewer','2025-01-01T00:00:00Z',NULL);
SQL
EXIT_CODE=0
OUTPUT=$(echo '{}' | CLAUDE_PROJECT_DIR="${WORK_1C}" bash "$IDLE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "1c: Pending reviews -> exit 2 (keep working)" "2" "$EXIT_CODE"
check_contains "1c: Output mentions pending review" "pending governance review" "$OUTPUT"

# Test 1d: Pending governed tasks exist -- keep working (exit 2)
WORK_1D="${WORKSPACE}/1d"
create_db "${WORK_1D}/.avt/governance.db"
sqlite3 "${WORK_1D}/.avt/governance.db" << 'SQL'
INSERT INTO governed_tasks VALUES ('g1','impl-1','Auth service','desc','ctx','pending_review','2025-01-01T00:00:00Z',NULL,'');
SQL
EXIT_CODE=0
OUTPUT=$(echo '{}' | CLAUDE_PROJECT_DIR="${WORK_1D}" bash "$IDLE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "1d: Pending governed tasks -> exit 2 (keep working)" "2" "$EXIT_CODE"
check_contains "1d: Output mentions awaiting review" "awaiting governance review" "$OUTPUT"

# Test 1e: All approved -- allow idle (exit 0)
WORK_1E="${WORKSPACE}/1e"
create_db "${WORK_1E}/.avt/governance.db"
sqlite3 "${WORK_1E}/.avt/governance.db" << 'SQL'
INSERT INTO task_reviews VALUES ('r1','review-abc','impl-1','governance','approved','ctx','approved','OK','[]','[]','reviewer','2025-01-01T00:00:00Z','2025-01-01T00:01:00Z');
INSERT INTO governed_tasks VALUES ('g1','impl-1','Auth service','desc','ctx','approved','2025-01-01T00:00:00Z','2025-01-01T00:01:00Z','');
SQL
EXIT_CODE=0
OUTPUT=$(echo '{}' | CLAUDE_PROJECT_DIR="${WORK_1E}" bash "$IDLE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "1e: All approved -> exit 0 (allow idle)" "0" "$EXIT_CODE"

echo ""

# ══════════════════════════════════════════════════════════════════
# GROUP 2: task-completed-gate.sh
# ══════════════════════════════════════════════════════════════════
echo "-- Group 2: task-completed-gate.sh --"

COMPLETED_HOOK="${PROJECT_DIR}/scripts/hooks/task-completed-gate.sh"

# Test 2a: No governance DB -- allow completion (exit 0)
WORK_2A="${WORKSPACE}/2a"
mkdir -p "${WORK_2A}/.avt"
EXIT_CODE=0
OUTPUT=$(echo '{"tool_input": {"subject": "Some task", "id": "5"}}' | CLAUDE_PROJECT_DIR="${WORK_2A}" bash "$COMPLETED_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "2a: No DB -> exit 0 (allow completion)" "0" "$EXIT_CODE"

# Test 2b: Review task subject -- always allow (exit 0)
WORK_2B="${WORKSPACE}/2b"
create_db "${WORK_2B}/.avt/governance.db"
sqlite3 "${WORK_2B}/.avt/governance.db" << 'SQL'
INSERT INTO governed_tasks VALUES ('g1','default/review-abc','[GOVERNANCE] Review: Auth','desc','ctx','pending_review','2025-01-01T00:00:00Z',NULL,'');
SQL
EXIT_CODE=0
OUTPUT=$(echo '{"tool_input": {"subject": "[GOVERNANCE] Review: Auth", "id": "review-abc"}}' | CLAUDE_PROJECT_DIR="${WORK_2B}" CLAUDE_CODE_TASK_LIST_ID="default" bash "$COMPLETED_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "2b: Review task -> exit 0 (skip check)" "0" "$EXIT_CODE"

# Test 2c: No task ID in input -- allow (fail open, exit 0)
WORK_2C="${WORKSPACE}/2c"
create_db "${WORK_2C}/.avt/governance.db"
EXIT_CODE=0
OUTPUT=$(echo '{"tool_input": {"subject": "Unnamed task"}}' | CLAUDE_PROJECT_DIR="${WORK_2C}" bash "$COMPLETED_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "2c: No task ID -> exit 0 (fail open)" "0" "$EXIT_CODE"

# Test 2d: Task approved in DB -- allow completion (exit 0)
WORK_2D="${WORKSPACE}/2d"
create_db "${WORK_2D}/.avt/governance.db"
sqlite3 "${WORK_2D}/.avt/governance.db" << 'SQL'
INSERT INTO governed_tasks VALUES ('g1','default/5','Auth service','desc','ctx','approved','2025-01-01T00:00:00Z','2025-01-01T00:01:00Z','');
SQL
EXIT_CODE=0
OUTPUT=$(echo '{"tool_input": {"subject": "Auth service", "id": "5"}}' | CLAUDE_PROJECT_DIR="${WORK_2D}" CLAUDE_CODE_TASK_LIST_ID="default" bash "$COMPLETED_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "2d: Approved task -> exit 0 (allow completion)" "0" "$EXIT_CODE"

# Test 2e: Task pending_review in DB -- block (exit 2)
WORK_2E="${WORKSPACE}/2e"
create_db "${WORK_2E}/.avt/governance.db"
sqlite3 "${WORK_2E}/.avt/governance.db" << 'SQL'
INSERT INTO governed_tasks VALUES ('g1','default/5','Auth service','desc','ctx','pending_review','2025-01-01T00:00:00Z',NULL,'');
SQL
EXIT_CODE=0
OUTPUT=$(echo '{"tool_input": {"subject": "Auth service", "id": "5"}}' | CLAUDE_PROJECT_DIR="${WORK_2E}" CLAUDE_CODE_TASK_LIST_ID="default" bash "$COMPLETED_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "2e: Pending review -> exit 2 (block completion)" "2" "$EXIT_CODE"
check_contains "2e: Output mentions still pending" "still pending" "$OUTPUT"

# Test 2f: Task blocked in DB -- block (exit 2)
WORK_2F="${WORKSPACE}/2f"
create_db "${WORK_2F}/.avt/governance.db"
sqlite3 "${WORK_2F}/.avt/governance.db" << 'SQL'
INSERT INTO governed_tasks VALUES ('g1','default/5','Auth service','desc','ctx','blocked','2025-01-01T00:00:00Z',NULL,'');
SQL
EXIT_CODE=0
OUTPUT=$(echo '{"tool_input": {"subject": "Auth service", "id": "5"}}' | CLAUDE_PROJECT_DIR="${WORK_2F}" CLAUDE_CODE_TASK_LIST_ID="default" bash "$COMPLETED_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "2f: Blocked task -> exit 2 (block completion)" "2" "$EXIT_CODE"
check_contains "2f: Output mentions BLOCKED" "blocked" "$OUTPUT"

# Test 2g: Task not in DB (ungoverned) -- allow (exit 0)
WORK_2G="${WORKSPACE}/2g"
create_db "${WORK_2G}/.avt/governance.db"
EXIT_CODE=0
OUTPUT=$(echo '{"tool_input": {"subject": "New task", "id": "99"}}' | CLAUDE_PROJECT_DIR="${WORK_2G}" CLAUDE_CODE_TASK_LIST_ID="default" bash "$COMPLETED_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "2g: Ungoverned task -> exit 0 (allow completion)" "0" "$EXIT_CODE"

# Test 2h: Custom list ID namespacing
WORK_2H="${WORKSPACE}/2h"
create_db "${WORK_2H}/.avt/governance.db"
sqlite3 "${WORK_2H}/.avt/governance.db" << 'SQL'
INSERT INTO governed_tasks VALUES ('g1','my-project/7','Feature X','desc','ctx','pending_review','2025-01-01T00:00:00Z',NULL,'');
SQL
EXIT_CODE=0
OUTPUT=$(echo '{"tool_input": {"subject": "Feature X", "id": "7"}}' | CLAUDE_PROJECT_DIR="${WORK_2H}" CLAUDE_CODE_TASK_LIST_ID="my-project" bash "$COMPLETED_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "2h: Custom list ID namespacing -> exit 2 (found)" "2" "$EXIT_CODE"

echo ""

# ══════════════════════════════════════════════════════════════════
# GROUP 3: holistic-review-gate.sh
# ══════════════════════════════════════════════════════════════════
echo "-- Group 3: holistic-review-gate.sh --"

GATE_HOOK="${PROJECT_DIR}/scripts/hooks/holistic-review-gate.sh"

# Test 3a: No flag files -- allow (exit 0, fast path)
WORK_3A="${WORKSPACE}/3a"
mkdir -p "${WORK_3A}/.avt"
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_3A}" bash "$GATE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "3a: No flags -> exit 0 (fast path)" "0" "$EXIT_CODE"

# Test 3b: Single pending flag file -- block (exit 2)
WORK_3B="${WORKSPACE}/3b"
mkdir -p "${WORK_3B}/.avt"
NOW_ISO=$(python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())")
echo "{\"status\": \"pending\", \"created_at\": \"${NOW_ISO}\"}" > "${WORK_3B}/.avt/.holistic-review-pending-session123"
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_3B}" bash "$GATE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "3b: Pending flag -> exit 2 (block)" "2" "$EXIT_CODE"
check_contains "3b: Output mentions in progress" "HOLISTIC GOVERNANCE REVIEW IN PROGRESS" "$OUTPUT"

# Test 3c: Single blocked flag file -- block (exit 2) with guidance
WORK_3C="${WORKSPACE}/3c"
mkdir -p "${WORK_3C}/.avt"
echo "{\"status\": \"blocked\", \"guidance\": \"Fix auth pattern\", \"strengths_summary\": \"Good module structure\", \"created_at\": \"${NOW_ISO}\"}" > "${WORK_3C}/.avt/.holistic-review-pending-session456"
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_3C}" bash "$GATE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "3c: Blocked flag -> exit 2 (block)" "2" "$EXIT_CODE"
check_contains "3c: Output mentions what needs change" "WHAT NEEDS CHANGE" "$OUTPUT"

# Test 3d: Multiple flag files, mixed statuses -- most restrictive wins
WORK_3D="${WORKSPACE}/3d"
mkdir -p "${WORK_3D}/.avt"
echo "{\"status\": \"pending\", \"created_at\": \"${NOW_ISO}\"}" > "${WORK_3D}/.avt/.holistic-review-pending-sessionA"
echo "{\"status\": \"blocked\", \"guidance\": \"blocked guidance\", \"created_at\": \"${NOW_ISO}\"}" > "${WORK_3D}/.avt/.holistic-review-pending-sessionB"
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_3D}" bash "$GATE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "3d: Mixed flags -> exit 2 (blocked wins)" "2" "$EXIT_CODE"
# Blocked has priority 3 vs pending priority 1, so output should mention blocked guidance
check_contains "3d: Blocked status takes priority" "WHAT NEEDS CHANGE" "$OUTPUT"

# Test 3e: Stale flag file (>5 min old) -- auto-removed, allow (exit 0)
WORK_3E="${WORKSPACE}/3e"
mkdir -p "${WORK_3E}/.avt"
STALE_ISO=$(python3 -c "from datetime import datetime, timezone, timedelta; print((datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat())")
echo "{\"status\": \"pending\", \"created_at\": \"${STALE_ISO}\"}" > "${WORK_3E}/.avt/.holistic-review-pending-stale-session"
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_3E}" bash "$GATE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "3e: Stale flag (>5min) -> exit 0 (auto-removed)" "0" "$EXIT_CODE"
# Verify the stale file was actually removed
STALE_EXISTS="false"
[[ -f "${WORK_3E}/.avt/.holistic-review-pending-stale-session" ]] && STALE_EXISTS="true"
check "3e: Stale flag file was deleted" "false" "$STALE_EXISTS"

# Test 3f: needs_human_review status -- block (exit 2)
WORK_3F="${WORKSPACE}/3f"
mkdir -p "${WORK_3F}/.avt"
echo "{\"status\": \"needs_human_review\", \"created_at\": \"${NOW_ISO}\"}" > "${WORK_3F}/.avt/.holistic-review-pending-session789"
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_3F}" bash "$GATE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "3f: needs_human_review -> exit 2 (block)" "2" "$EXIT_CODE"
check_contains "3f: Output mentions human review" "human review" "$OUTPUT"

# Test 3g: Malformed JSON + valid pending flag -- valid flag triggers block
WORK_3G="${WORKSPACE}/3g"
mkdir -p "${WORK_3G}/.avt"
echo "{broken" > "${WORK_3G}/.avt/.holistic-review-pending-broken"
echo "{\"status\": \"pending\", \"created_at\": \"${NOW_ISO}\"}" > "${WORK_3G}/.avt/.holistic-review-pending-valid"
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_3G}" bash "$GATE_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "3g: Malformed + valid -> exit 2 (valid flag blocks)" "2" "$EXIT_CODE"

echo ""

# ══════════════════════════════════════════════════════════════════
# GROUP 4: verify-governance-review.sh
# ══════════════════════════════════════════════════════════════════
echo "-- Group 4: verify-governance-review.sh --"

VERIFY_HOOK="${PROJECT_DIR}/scripts/hooks/verify-governance-review.sh"

# Test 4a: No governance DB -- allow (exit 0)
WORK_4A="${WORKSPACE}/4a"
mkdir -p "${WORK_4A}/.avt"
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_4A}" bash "$VERIFY_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "4a: No DB -> exit 0 (allow)" "0" "$EXIT_CODE"

# Test 4b: Plan reviews exist -- allow (exit 0)
WORK_4B="${WORKSPACE}/4b"
create_db "${WORK_4B}/.avt/governance.db"
sqlite3 "${WORK_4B}/.avt/governance.db" << 'SQL'
INSERT INTO reviews VALUES ('rv1',NULL,'plan-001','approved','[]','Looks good','["vision"]','reviewer','2025-01-01T00:00:00Z','');
SQL
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_4B}" bash "$VERIFY_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "4b: Plan reviews exist -> exit 0 (allow)" "0" "$EXIT_CODE"

# Test 4c: No plan reviews -- block (exit 2)
WORK_4C="${WORKSPACE}/4c"
create_db "${WORK_4C}/.avt/governance.db"
# Insert a review WITHOUT plan_id (decision review, not plan review)
sqlite3 "${WORK_4C}/.avt/governance.db" << 'SQL'
INSERT INTO reviews VALUES ('rv1','dec-001',NULL,'approved','[]','OK','["vision"]','reviewer','2025-01-01T00:00:00Z','');
SQL
EXIT_CODE=0
OUTPUT=$(CLAUDE_PROJECT_DIR="${WORK_4C}" bash "$VERIFY_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "4c: No plan reviews -> exit 2 (block)" "2" "$EXIT_CODE"
check_contains "4c: Output mentions governance review required" "GOVERNANCE REVIEW REQUIRED" "$OUTPUT"

echo ""

# ══════════════════════════════════════════════════════════════════
# GROUP 5: governance-task-intercept.py parsing
# ══════════════════════════════════════════════════════════════════
echo "-- Group 5: governance-task-intercept.py parsing --"

# Test the Python functions directly via subprocess
# Must use uv run because governance-task-intercept.py imports from collab_governance (pydantic)
INTERCEPT_TESTS=$(cd "${GOVERNANCE_DIR}" && uv run python << PYEOF
import sys
import json

# Add governance directory to path for imports
sys.path.insert(0, '${GOVERNANCE_DIR}')

# Import the hook module using importlib (filename has dashes)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "governance_task_intercept",
    "${PROJECT_DIR}/scripts/hooks/governance-task-intercept.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

results = []

# Test 5a: _is_review_task detects all REVIEW_PREFIXES
prefixes_detected = all([
    mod._is_review_task("[GOVERNANCE] Review: Something"),
    mod._is_review_task("[REVIEW] Check: Something"),
    mod._is_review_task("[SECURITY] Audit: Something"),
    mod._is_review_task("[ARCHITECTURE] Design: Something"),
    mod._is_review_task("Any subject", "review-abc123"),
])
results.append(("5a: Detects all review prefixes + review- ID", prefixes_detected))

# Test 5b: _is_review_task returns False for normal subjects
normal_not_detected = all([
    not mod._is_review_task("Implement AuthService"),
    not mod._is_review_task("Add caching", "impl-xyz789"),
    not mod._is_review_task("Build feature #5"),
])
results.append(("5b: Normal tasks not detected as review", normal_not_detected))

# Test 5c: _extract_task_info handles various shapes
# Dict tool_result with id
info1 = mod._extract_task_info({
    "tool_input": {"prompt": "Build auth"},
    "tool_result": {"id": "task-1", "subject": "Auth task"}
})
shape_c1 = info1 is not None and info1["task_id"] == "task-1" and info1["subject"] == "Auth task"

# String tool_result (JSON)
info2 = mod._extract_task_info({
    "tool_input": {"prompt": "Build cache"},
    "tool_result": '{"id": "task-2", "subject": "Cache task"}'
})
shape_c2 = info2 is not None and info2["task_id"] == "task-2"

# Empty tool_result (common case)
info3 = mod._extract_task_info({
    "tool_input": {"prompt": "Build feature", "subject": "Feature X"},
    "tool_result": ""
})
shape_c3 = info3 is not None and info3["subject"] == "Feature X"

results.append(("5c: Handles various tool_result shapes", shape_c1 and shape_c2 and shape_c3))

# Test 5d: _extract_task_info returns None for empty input
info_empty = mod._extract_task_info({})
info_no_data = mod._extract_task_info({"tool_input": {}, "tool_result": {}})
results.append(("5d: Returns None for empty input", info_empty is None and info_no_data is None))

# Output results as JSON
print(json.dumps([{"label": r[0], "passed": r[1]} for r in results]))
PYEOF
) 2>/dev/null

if [[ $? -eq 0 && -n "$INTERCEPT_TESTS" ]]; then
    echo "$INTERCEPT_TESTS" | python3 -c "
import json, sys
results = json.load(sys.stdin)
for r in results:
    status = 'PASS' if r['passed'] else 'FAIL'
    print(f'  {status}  {r[\"label\"]}')
" 2>/dev/null
    # Count passes/failures
    PY_PASS=$(echo "$INTERCEPT_TESTS" | python3 -c "import json,sys; print(sum(1 for r in json.load(sys.stdin) if r['passed']))" 2>/dev/null || echo 0)
    PY_FAIL=$(echo "$INTERCEPT_TESTS" | python3 -c "import json,sys; print(sum(1 for r in json.load(sys.stdin) if not r['passed']))" 2>/dev/null || echo 0)
    PASS=$((PASS + PY_PASS))
    FAIL=$((FAIL + PY_FAIL))
else
    echo "  FAIL  Group 5: Python import failed"
    FAIL=$((FAIL + 4))
fi

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
else
    echo "  Result: FAILED ($FAIL failures)"
    FINAL_EXIT=1
fi

echo "============================================================"
echo ""

# ── Cleanup ───────────────────────────────────────────────────────────────────
rm -rf "$WORKSPACE"
echo "Workspace cleaned: $WORKSPACE"

exit $FINAL_EXIT
