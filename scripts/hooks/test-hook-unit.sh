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

# ══════════════════════════════════════════════════════════════════
# GROUP 6: context-reinforcement.py session context features
# ══════════════════════════════════════════════════════════════════
echo "-- Group 6: context-reinforcement.py session context --"

CR_HOOK="${PROJECT_DIR}/scripts/hooks/context-reinforcement.py"

# Helper: create a session context file with active goals
create_session_context() {
    local dir="$1"
    local session_id="$2"
    local status="${3:-ready}"
    mkdir -p "${dir}/.avt"
    cat > "${dir}/.avt/.session-context-${session_id}.json" << SCEOF
{
  "version": 1,
  "session_id": "${session_id}",
  "created_at": "2026-02-20T10:00:00Z",
  "updated_at": "2026-02-20T10:00:00Z",
  "distillation": {
    "status": "${status}",
    "key_points": [
      {"id": "kp-1", "text": "Implement dark mode toggle", "status": "active"},
      {"id": "kp-2", "text": "Add state management", "status": "completed", "completed_at": "2026-02-20T10:05:00Z"}
    ],
    "constraints": ["Must pass all existing tests"],
    "key_decisions": ["Using CSS-in-JS approach"]
  },
  "discoveries": [
    {"id": "disc-1", "text": "ThemeContext already exists", "discovered_at": "2026-02-20T10:05:00Z", "source": "holistic_review"}
  ],
  "thrash_indicators": [],
  "injection_count": 0,
  "last_injected_at": null
}
SCEOF
}

# Helper: create a session context with all goals completed
create_completed_session_context() {
    local dir="$1"
    local session_id="$2"
    mkdir -p "${dir}/.avt"
    cat > "${dir}/.avt/.session-context-${session_id}.json" << SCEOF
{
  "version": 1,
  "session_id": "${session_id}",
  "created_at": "2026-02-20T10:00:00Z",
  "updated_at": "2026-02-20T10:00:00Z",
  "distillation": {
    "status": "ready",
    "key_points": [
      {"id": "kp-1", "text": "Implement dark mode toggle", "status": "completed"},
      {"id": "kp-2", "text": "Add state management", "status": "completed"}
    ],
    "constraints": [],
    "key_decisions": []
  },
  "discoveries": [],
  "thrash_indicators": [],
  "injection_count": 0,
  "last_injected_at": null
}
SCEOF
}

# Helper: create an injection history with a recent session-context entry
create_recent_injection_history() {
    local dir="$1"
    local session_id="$2"
    local ts
    ts=$(python3 -c "import time; print(time.time())")
    mkdir -p "${dir}/.avt"
    echo "[{\"route_id\": \"session-context\", \"timestamp\": ${ts}}]" > "${dir}/.avt/.injection-history-${session_id}"
}

# Test 6a: Session context file with active goals -> injects them
WORK_6A="${WORKSPACE}/6a"
create_session_context "${WORK_6A}" "sess-6a"
# Create counter above threshold
mkdir -p "${WORK_6A}/.avt"
echo "10" > "${WORK_6A}/.avt/.session-calls-sess-6a"
EXIT_CODE=0
OUTPUT=$(echo '{"session_id":"sess-6a","tool_input":{"command":"npm test"},"transcript_path":""}' | \
    CLAUDE_PROJECT_DIR="${WORK_6A}" python3 "$CR_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "6a: Session context with active goals -> exit 0" "0" "$EXIT_CODE"
check_contains "6a: Injects active goals" "Implement dark mode toggle" "$OUTPUT"
check_contains "6a: Shows SESSION CONTEXT header" "SESSION CONTEXT" "$OUTPUT"
# Verify completed goals are excluded
NOT_FOUND="true"
echo "$OUTPUT" | grep -q "Add state management" && NOT_FOUND="false"
check "6a: Completed goals excluded" "true" "$NOT_FOUND"

# Test 6b: All goals completed -> no session injection, returns empty
WORK_6B="${WORKSPACE}/6b"
create_completed_session_context "${WORK_6B}" "sess-6b"
echo "10" > "${WORK_6B}/.avt/.session-calls-sess-6b"
EXIT_CODE=0
OUTPUT=$(echo '{"session_id":"sess-6b","tool_input":{"command":"echo test"},"transcript_path":""}' | \
    CLAUDE_PROJECT_DIR="${WORK_6B}" python3 "$CR_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "6b: All goals completed -> exit 0" "0" "$EXIT_CODE"
# Output should be empty (no injection) since no static router either
check "6b: No injection (all completed, no router)" "" "$OUTPUT"

# Test 6c: Session context missing + transcript_path set -> spawns distillation (check no crash)
WORK_6C="${WORKSPACE}/6c"
mkdir -p "${WORK_6C}/.avt"
echo "10" > "${WORK_6C}/.avt/.session-calls-sess-6c"
# Create a fake transcript
echo '{"type":"user","message":{"content":"Build a dark mode feature"}}' > "${WORK_6C}/transcript.jsonl"
EXIT_CODE=0
OUTPUT=$(echo '{"session_id":"sess-6c","tool_input":{"command":"echo test"},"transcript_path":"'"${WORK_6C}"'/transcript.jsonl"}' | \
    CLAUDE_PROJECT_DIR="${WORK_6C}" python3 "$CR_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "6c: Missing session context -> exit 0 (no crash)" "0" "$EXIT_CODE"

# Test 6d: Session context debounce -> second call within 60s skips session injection
WORK_6D="${WORKSPACE}/6d"
create_session_context "${WORK_6D}" "sess-6d"
echo "10" > "${WORK_6D}/.avt/.session-calls-sess-6d"
create_recent_injection_history "${WORK_6D}" "sess-6d"
EXIT_CODE=0
OUTPUT=$(echo '{"session_id":"sess-6d","tool_input":{"command":"echo test"},"transcript_path":""}' | \
    CLAUDE_PROJECT_DIR="${WORK_6D}" python3 "$CR_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "6d: Debounced session context -> exit 0" "0" "$EXIT_CODE"
# Should NOT contain SESSION CONTEXT since debounced
NO_SESSION="true"
echo "$OUTPUT" | grep -q "SESSION CONTEXT" && NO_SESSION="false"
check "6d: Session context not injected (debounced)" "true" "$NO_SESSION"

# Test 6e: Malformed session context file -> falls through (no crash)
WORK_6E="${WORKSPACE}/6e"
mkdir -p "${WORK_6E}/.avt"
echo "10" > "${WORK_6E}/.avt/.session-calls-sess-6e"
echo "{broken json" > "${WORK_6E}/.avt/.session-context-sess-6e.json"
EXIT_CODE=0
OUTPUT=$(echo '{"session_id":"sess-6e","tool_input":{"command":"echo test"},"transcript_path":""}' | \
    CLAUDE_PROJECT_DIR="${WORK_6E}" python3 "$CR_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "6e: Malformed session context -> exit 0 (no crash)" "0" "$EXIT_CODE"

# Test 6f: sessionContextEnabled=false -> skips session context
WORK_6F="${WORKSPACE}/6f"
create_session_context "${WORK_6F}" "sess-6f"
echo "10" > "${WORK_6F}/.avt/.session-calls-sess-6f"
# Override with project config that disables session context
cat > "${WORK_6F}/.avt/project-config.json" << 'PCEOF'
{"settings":{"contextReinforcement":{"sessionContextEnabled":false}}}
PCEOF
EXIT_CODE=0
OUTPUT=$(echo '{"session_id":"sess-6f","tool_input":{"command":"echo test"},"transcript_path":""}' | \
    CLAUDE_PROJECT_DIR="${WORK_6F}" python3 "$CR_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "6f: Session context disabled -> exit 0" "0" "$EXIT_CODE"
# Should not contain SESSION CONTEXT
NO_SESSION_6F="true"
echo "$OUTPUT" | grep -q "SESSION CONTEXT" && NO_SESSION_6F="false"
check "6f: Session context not injected (disabled)" "true" "$NO_SESSION_6F"

# Test 6g: Session context with discoveries -> includes findings
WORK_6G="${WORKSPACE}/6g"
create_session_context "${WORK_6G}" "sess-6g"
echo "10" > "${WORK_6G}/.avt/.session-calls-sess-6g"
EXIT_CODE=0
OUTPUT=$(echo '{"session_id":"sess-6g","tool_input":{"command":"npm build"},"transcript_path":""}' | \
    CLAUDE_PROJECT_DIR="${WORK_6G}" python3 "$CR_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "6g: Session context with discoveries -> exit 0" "0" "$EXIT_CODE"
check_contains "6g: Includes discoveries" "ThemeContext already exists" "$OUTPUT"
check_contains "6g: Includes constraints" "Must pass all existing tests" "$OUTPUT"
check_contains "6g: Includes key decisions" "CSS-in-JS" "$OUTPUT"

# Test 6h: Under threshold -> no injection (fast path)
WORK_6H="${WORKSPACE}/6h"
create_session_context "${WORK_6H}" "sess-6h"
echo "3" > "${WORK_6H}/.avt/.session-calls-sess-6h"
EXIT_CODE=0
OUTPUT=$(echo '{"session_id":"sess-6h","tool_input":{"command":"echo test"},"transcript_path":""}' | \
    CLAUDE_PROJECT_DIR="${WORK_6H}" python3 "$CR_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "6h: Under threshold -> exit 0 (fast path)" "0" "$EXIT_CODE"
check "6h: No injection below threshold" "" "$OUTPUT"

echo ""

# ══════════════════════════════════════════════════════════════════
# GROUP 7: _distill-session-context.py
# ══════════════════════════════════════════════════════════════════
echo "-- Group 7: _distill-session-context.py --"

DISTILL_SCRIPT="${PROJECT_DIR}/scripts/hooks/_distill-session-context.py"

# Test 7a: Mock mode with short prompt -> writes session context
WORK_7A="${WORKSPACE}/7a"
mkdir -p "${WORK_7A}/.avt"
echo '{"type":"user","message":{"content":"Fix the login button"}}' > "${WORK_7A}/transcript.jsonl"
GOVERNANCE_MOCK_REVIEW=true CLAUDE_PROJECT_DIR="${WORK_7A}" python3 "$DISTILL_SCRIPT" "sess-7a" "${WORK_7A}/transcript.jsonl" 2>/dev/null
EXIT_CODE=$?
check "7a: Mock mode short prompt -> exit 0" "0" "$EXIT_CODE"
SC_EXISTS_7A="false"
[[ -f "${WORK_7A}/.avt/.session-context-sess-7a.json" ]] && SC_EXISTS_7A="true"
check "7a: Session context file created" "true" "$SC_EXISTS_7A"
if [[ "$SC_EXISTS_7A" == "true" ]]; then
    SC_CONTENT_7A=$(cat "${WORK_7A}/.avt/.session-context-sess-7a.json")
    check_contains "7a: Contains key_points" "key_points" "$SC_CONTENT_7A"
    check_contains "7a: Contains the prompt text" "Fix the login button" "$SC_CONTENT_7A"
    check_contains "7a: Status is ready" "\"status\": \"ready\"" "$SC_CONTENT_7A"
fi

# Test 7b: Mock mode with long prompt -> writes truncated
WORK_7B="${WORKSPACE}/7b"
mkdir -p "${WORK_7B}/.avt"
# Create a prompt > 500 chars
LONG_PROMPT=$(python3 -c "print('Implement a comprehensive authentication system with OAuth2, JWT tokens, session management, ' * 10)")
echo "{\"type\":\"user\",\"message\":{\"content\":\"${LONG_PROMPT}\"}}" > "${WORK_7B}/transcript.jsonl"
GOVERNANCE_MOCK_REVIEW=true CLAUDE_PROJECT_DIR="${WORK_7B}" python3 "$DISTILL_SCRIPT" "sess-7b" "${WORK_7B}/transcript.jsonl" 2>/dev/null
EXIT_CODE=$?
check "7b: Mock mode long prompt -> exit 0" "0" "$EXIT_CODE"
SC_EXISTS_7B="false"
[[ -f "${WORK_7B}/.avt/.session-context-sess-7b.json" ]] && SC_EXISTS_7B="true"
check "7b: Session context file created" "true" "$SC_EXISTS_7B"
if [[ "$SC_EXISTS_7B" == "true" ]]; then
    SC_CONTENT_7B=$(cat "${WORK_7B}/.avt/.session-context-sess-7b.json")
    check_contains "7b: Contains truncation marker" "..." "$SC_CONTENT_7B"
fi

# Test 7c: Existing session context -> skips (already distilled)
WORK_7C="${WORKSPACE}/7c"
create_session_context "${WORK_7C}" "sess-7c"
echo '{"type":"user","message":{"content":"This should not override"}}' > "${WORK_7C}/transcript.jsonl"
GOVERNANCE_MOCK_REVIEW=true CLAUDE_PROJECT_DIR="${WORK_7C}" python3 "$DISTILL_SCRIPT" "sess-7c" "${WORK_7C}/transcript.jsonl" 2>/dev/null
EXIT_CODE=$?
check "7c: Existing context -> exit 0 (skips)" "0" "$EXIT_CODE"
# Verify original content was preserved (not overwritten)
SC_CONTENT_7C=$(cat "${WORK_7C}/.avt/.session-context-sess-7c.json")
check_contains "7c: Original content preserved" "dark mode toggle" "$SC_CONTENT_7C"
NOT_OVERWRITTEN="true"
echo "$SC_CONTENT_7C" | grep -q "should not override" && NOT_OVERWRITTEN="false"
check "7c: Not overwritten" "true" "$NOT_OVERWRITTEN"

# Test 7d: Transcript not found -> writes fallback status
WORK_7D="${WORKSPACE}/7d"
mkdir -p "${WORK_7D}/.avt"
GOVERNANCE_MOCK_REVIEW=true CLAUDE_PROJECT_DIR="${WORK_7D}" python3 "$DISTILL_SCRIPT" "sess-7d" "/nonexistent/transcript.jsonl" 2>/dev/null
EXIT_CODE=$?
check "7d: Missing transcript -> exit 0" "0" "$EXIT_CODE"
SC_EXISTS_7D="false"
[[ -f "${WORK_7D}/.avt/.session-context-sess-7d.json" ]] && SC_EXISTS_7D="true"
check "7d: Session context file created (fallback)" "true" "$SC_EXISTS_7D"
if [[ "$SC_EXISTS_7D" == "true" ]]; then
    SC_CONTENT_7D=$(cat "${WORK_7D}/.avt/.session-context-sess-7d.json")
    check_contains "7d: Status is fallback" "fallback" "$SC_CONTENT_7D"
fi

# Test 7e: Short prompt (< 500 chars) stored directly without mock flag
WORK_7E="${WORKSPACE}/7e"
mkdir -p "${WORK_7E}/.avt"
echo '{"type":"user","message":{"content":"Add a logout button to the header"}}' > "${WORK_7E}/transcript.jsonl"
# No GOVERNANCE_MOCK_REVIEW -> but short prompt should skip AI call
CLAUDE_PROJECT_DIR="${WORK_7E}" python3 "$DISTILL_SCRIPT" "sess-7e" "${WORK_7E}/transcript.jsonl" 2>/dev/null
EXIT_CODE=$?
check "7e: Short prompt (no mock) -> exit 0" "0" "$EXIT_CODE"
SC_EXISTS_7E="false"
[[ -f "${WORK_7E}/.avt/.session-context-sess-7e.json" ]] && SC_EXISTS_7E="true"
check "7e: Session context file created" "true" "$SC_EXISTS_7E"
if [[ "$SC_EXISTS_7E" == "true" ]]; then
    SC_CONTENT_7E=$(cat "${WORK_7E}/.avt/.session-context-sess-7e.json")
    check_contains "7e: Contains prompt text directly" "Add a logout button" "$SC_CONTENT_7E"
    check_contains "7e: Status is ready" "\"status\": \"ready\"" "$SC_CONTENT_7E"
fi

# Test 7f: Multi-block content in transcript
WORK_7F="${WORKSPACE}/7f"
mkdir -p "${WORK_7F}/.avt"
echo '{"type":"user","message":{"content":[{"type":"text","text":"Build a dark mode"},{"type":"text","text":"with toggle switch"}]}}' > "${WORK_7F}/transcript.jsonl"
CLAUDE_PROJECT_DIR="${WORK_7F}" python3 "$DISTILL_SCRIPT" "sess-7f" "${WORK_7F}/transcript.jsonl" 2>/dev/null
EXIT_CODE=$?
check "7f: Multi-block content -> exit 0" "0" "$EXIT_CODE"
SC_EXISTS_7F="false"
[[ -f "${WORK_7F}/.avt/.session-context-sess-7f.json" ]] && SC_EXISTS_7F="true"
check "7f: Session context file created" "true" "$SC_EXISTS_7F"
if [[ "$SC_EXISTS_7F" == "true" ]]; then
    SC_CONTENT_7F=$(cat "${WORK_7F}/.avt/.session-context-sess-7f.json")
    check_contains "7f: First text block captured" "dark mode" "$SC_CONTENT_7F"
    check_contains "7f: Second text block captured" "toggle switch" "$SC_CONTENT_7F"
fi

# Test 7g: Refresh with mock mode -> no-op (preserves existing)
WORK_7G="${WORKSPACE}/7g"
create_session_context "${WORK_7G}" "sess-7g"
echo '{"type":"user","message":{"content":"original prompt"}}' > "${WORK_7G}/transcript.jsonl"
GOVERNANCE_MOCK_REVIEW=true CLAUDE_PROJECT_DIR="${WORK_7G}" python3 "$DISTILL_SCRIPT" "sess-7g" "${WORK_7G}/transcript.jsonl" --refresh 2>/dev/null
EXIT_CODE=$?
check "7g: Refresh mock mode -> exit 0" "0" "$EXIT_CODE"
# Verify original content preserved
SC_CONTENT_7G=$(cat "${WORK_7G}/.avt/.session-context-sess-7g.json")
check_contains "7g: Original content preserved on mock refresh" "dark mode toggle" "$SC_CONTENT_7G"

echo ""

# ══════════════════════════════════════════════════════════════════
# GROUP 8: _update-session-context.py
# ══════════════════════════════════════════════════════════════════
echo "-- Group 8: _update-session-context.py --"

UPDATE_SCRIPT="${PROJECT_DIR}/scripts/hooks/_update-session-context.py"

# Test 8a: Mock mode -> skips update
WORK_8A="${WORKSPACE}/8a"
create_session_context "${WORK_8A}" "sess-8a"
echo '{"type":"user","message":{"content":"test prompt"}}' > "${WORK_8A}/transcript.jsonl"
GOVERNANCE_MOCK_REVIEW=true CLAUDE_PROJECT_DIR="${WORK_8A}" python3 "$UPDATE_SCRIPT" "sess-8a" "${WORK_8A}/transcript.jsonl" "holistic_review" 2>/dev/null
EXIT_CODE=$?
check "8a: Mock mode -> exit 0" "0" "$EXIT_CODE"
# Verify file unchanged (updated_at should still be original)
SC_CONTENT_8A=$(cat "${WORK_8A}/.avt/.session-context-sess-8a.json")
check_contains "8a: Original updated_at preserved (mock)" "2026-02-20T10:00:00Z" "$SC_CONTENT_8A"

# Test 8b: No session context file -> exits early
WORK_8B="${WORKSPACE}/8b"
mkdir -p "${WORK_8B}/.avt"
CLAUDE_PROJECT_DIR="${WORK_8B}" python3 "$UPDATE_SCRIPT" "sess-8b" "/dev/null" "holistic_review" 2>/dev/null
EXIT_CODE=$?
check "8b: No session context -> exit 0 (early exit)" "0" "$EXIT_CODE"

# Test 8c: Throttle (updated < 60s ago) -> exits early
WORK_8C="${WORKSPACE}/8c"
mkdir -p "${WORK_8C}/.avt"
# Create session context with very recent updated_at
NOW_ISO_8C=$(python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())")
cat > "${WORK_8C}/.avt/.session-context-sess-8c.json" << SCEOF
{
  "version": 1,
  "session_id": "sess-8c",
  "created_at": "2026-02-20T10:00:00Z",
  "updated_at": "${NOW_ISO_8C}",
  "distillation": {
    "status": "ready",
    "key_points": [{"id": "kp-1", "text": "Some goal", "status": "active"}],
    "constraints": [],
    "key_decisions": []
  },
  "discoveries": [],
  "thrash_indicators": [],
  "injection_count": 0,
  "last_injected_at": null
}
SCEOF
CLAUDE_PROJECT_DIR="${WORK_8C}" python3 "$UPDATE_SCRIPT" "sess-8c" "/dev/null" "holistic_review" 2>/dev/null
EXIT_CODE=$?
check "8c: Throttled -> exit 0" "0" "$EXIT_CODE"

# Test 8d: Discovery deduplication (pure Python test)
DUP_TEST=$(python3 << PYEOF
import sys
sys.path.insert(0, '${PROJECT_DIR}/scripts/hooks')

# Import the module
import importlib.util
spec = importlib.util.spec_from_file_location(
    "update_session_context",
    "${PROJECT_DIR}/scripts/hooks/_update-session-context.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Test _is_duplicate_discovery
existing = [
    {"text": "ThemeContext already exists in src/context/"},
    {"text": "Config file uses JSON format"}
]

# Exact duplicate
assert mod._is_duplicate_discovery("ThemeContext already exists in src/context/", existing) == True
# Substring match (new is subset of existing)
assert mod._is_duplicate_discovery("ThemeContext already exists", existing) == True
# Substring match (existing is subset of new)
assert mod._is_duplicate_discovery("ThemeContext already exists in src/context/ and is unused", existing) == True
# Case insensitive
assert mod._is_duplicate_discovery("themecontext already exists in src/context/", existing) == True
# Not a duplicate
assert mod._is_duplicate_discovery("A completely new discovery about caching", existing) == False

print("ALL_PASSED")
PYEOF
) 2>/dev/null
check "8d: Discovery dedup logic" "ALL_PASSED" "$DUP_TEST"

# Test 8e: _parse_json_response handles various formats
PARSE_TEST=$(python3 << PYEOF
import sys
sys.path.insert(0, '${PROJECT_DIR}/scripts/hooks')

import importlib.util
spec = importlib.util.spec_from_file_location(
    "update_session_context",
    "${PROJECT_DIR}/scripts/hooks/_update-session-context.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Direct JSON
result = mod._parse_json_response('{"completed_goals": ["kp-1"]}')
assert result is not None and result["completed_goals"] == ["kp-1"]

# JSON in markdown code block
result2 = mod._parse_json_response('Here is the result:\n\`\`\`json\n{"completed_goals": ["kp-2"]}\n\`\`\`')
assert result2 is not None and result2["completed_goals"] == ["kp-2"]

# JSON embedded in text
result3 = mod._parse_json_response('Sure, here is: {"completed_goals": []} the answer.')
assert result3 is not None and result3["completed_goals"] == []

# Empty string
result4 = mod._parse_json_response('')
assert result4 is None

# No JSON at all
result5 = mod._parse_json_response('No JSON here')
assert result5 is None

print("ALL_PASSED")
PYEOF
) 2>/dev/null
check "8e: JSON parse handles formats" "ALL_PASSED" "$PARSE_TEST"

# Test 8f: Missing arguments -> exit 1
WORK_8F="${WORKSPACE}/8f"
mkdir -p "${WORK_8F}/.avt"
CLAUDE_PROJECT_DIR="${WORK_8F}" python3 "$UPDATE_SCRIPT" "sess-8f" 2>/dev/null
EXIT_CODE=$?
check "8f: Missing args -> exit 1" "1" "$EXIT_CODE"

echo ""

# ══════════════════════════════════════════════════════════════════
# GROUP 9: post-compaction-reinject.sh session context
# ══════════════════════════════════════════════════════════════════
echo "-- Group 9: post-compaction-reinject.sh session context --"

REINJECT_HOOK="${PROJECT_DIR}/scripts/hooks/post-compaction-reinject.sh"

# Test 9a: Session context included before vision routes
WORK_9A="${WORKSPACE}/9a"
create_session_context "${WORK_9A}" "sess-9a"
# Create a context router with vision routes
mkdir -p "${WORK_9A}/.avt"
cat > "${WORK_9A}/.avt/context-router.json" << 'RTEOF'
{
  "routes": [
    {"id": "r1", "tier": "vision", "context": "VISION: Use protocol-based DI"}
  ]
}
RTEOF
EXIT_CODE=0
OUTPUT=$(echo '{"session_id": "sess-9a"}' | CLAUDE_PROJECT_DIR="${WORK_9A}" bash "$REINJECT_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "9a: Session context + vision routes -> exit 0" "0" "$EXIT_CODE"
# Verify session context appears
check_contains "9a: Session context injected" "SESSION CONTEXT" "$OUTPUT"
check_contains "9a: Active goals shown" "Implement dark mode toggle" "$OUTPUT"
check_contains "9a: Discoveries shown" "ThemeContext already exists" "$OUTPUT"
# Verify vision routes also appear
check_contains "9a: Vision routes included" "VISION STANDARDS" "$OUTPUT"
check_contains "9a: Vision route content" "protocol-based DI" "$OUTPUT"

# Test 9b: Session context only (no router) -> still injects session context
WORK_9B="${WORKSPACE}/9b"
create_session_context "${WORK_9B}" "sess-9b"
# Create router file (required for hook to proceed)
cat > "${WORK_9B}/.avt/context-router.json" << 'RTEOF'
{"routes": []}
RTEOF
EXIT_CODE=0
OUTPUT=$(echo '{"session_id": "sess-9b"}' | CLAUDE_PROJECT_DIR="${WORK_9B}" bash "$REINJECT_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "9b: Session context only -> exit 0" "0" "$EXIT_CODE"
check_contains "9b: Session context without vision routes" "SESSION CONTEXT" "$OUTPUT"

# Test 9c: No session_id in input -> falls back to vision-only behavior
WORK_9C="${WORKSPACE}/9c"
mkdir -p "${WORK_9C}/.avt"
cat > "${WORK_9C}/.avt/context-router.json" << 'RTEOF'
{
  "routes": [
    {"id": "r1", "tier": "vision", "context": "VISION: No singletons"}
  ]
}
RTEOF
EXIT_CODE=0
OUTPUT=$(echo '{}' | CLAUDE_PROJECT_DIR="${WORK_9C}" bash "$REINJECT_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "9c: No session_id -> exit 0" "0" "$EXIT_CODE"
# Should still show vision routes
check_contains "9c: Vision routes shown without session context" "No singletons" "$OUTPUT"

# Test 9d: No router file -> exit 0 silently
WORK_9D="${WORKSPACE}/9d"
mkdir -p "${WORK_9D}/.avt"
EXIT_CODE=0
OUTPUT=$(echo '{"session_id": "sess-9d"}' | CLAUDE_PROJECT_DIR="${WORK_9D}" bash "$REINJECT_HOOK" 2>/dev/null) || EXIT_CODE=$?
check "9d: No router file -> exit 0" "0" "$EXIT_CODE"

echo ""

# ══════════════════════════════════════════════════════════════════
# GROUP 10: governance pipeline integration
# ══════════════════════════════════════════════════════════════════
echo "-- Group 10: governance pipeline integration --"

# Test 10a: context-reinforcement.py Python functions (direct import testing)
PIPELINE_TEST=$(cd "${GOVERNANCE_DIR}" && uv run python << PYEOF
import sys
import json
import os
import importlib.util

# Import context-reinforcement module
spec = importlib.util.spec_from_file_location(
    "context_reinforcement",
    "${PROJECT_DIR}/scripts/hooks/context-reinforcement.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

results = []

# Test build_session_injection with active goals
ctx_active = {
    "distillation": {
        "key_points": [
            {"id": "kp-1", "text": "Build auth", "status": "active"},
            {"id": "kp-2", "text": "Done task", "status": "completed"},
        ],
        "constraints": ["No new deps"],
        "key_decisions": ["Use JWT"],
    },
    "discoveries": [{"text": "Auth middleware exists"}],
    "thrash_indicators": [],
}
injection = mod.build_session_injection(ctx_active)
results.append(("10a-i: Active goals in injection", injection is not None and "Build auth" in injection))
results.append(("10a-ii: Completed excluded", injection is not None and "Done task" not in injection))
results.append(("10a-iii: Constraints included", injection is not None and "No new deps" in injection))
results.append(("10a-iv: Discoveries included", injection is not None and "Auth middleware" in injection))
results.append(("10a-v: Key decisions included", injection is not None and "Use JWT" in injection))

# Test build_session_injection with all completed
ctx_completed = {
    "distillation": {
        "key_points": [
            {"id": "kp-1", "text": "Done", "status": "completed"},
        ],
        "constraints": [],
        "key_decisions": [],
    },
    "discoveries": [],
    "thrash_indicators": [],
}
injection_nil = mod.build_session_injection(ctx_completed)
results.append(("10a-vi: All completed returns None", injection_nil is None))

# Test build_session_injection with thrash indicators
ctx_thrash = {
    "distillation": {
        "key_points": [{"id": "kp-1", "text": "Goal A", "status": "active"}],
        "constraints": [],
        "key_decisions": [],
    },
    "discoveries": [],
    "thrash_indicators": ["Try alternative approach to auth"],
}
injection_thrash = mod.build_session_injection(ctx_thrash)
results.append(("10a-vii: Thrash guidance included", injection_thrash is not None and "Try alternative" in injection_thrash))

# Test is_session_debounced
import time
history_recent = [{"route_id": "session-context", "timestamp": time.time()}]
settings = {"sessionContextDebounceSeconds": 60}
results.append(("10a-viii: Recent -> debounced", mod.is_session_debounced(history_recent, settings) == True))

history_old = [{"route_id": "session-context", "timestamp": time.time() - 120}]
results.append(("10a-ix: Old -> not debounced", mod.is_session_debounced(history_old, settings) == False))

history_empty = []
results.append(("10a-x: Empty -> not debounced", mod.is_session_debounced(history_empty, settings) == False))

# Test load_session_context
import tempfile
from pathlib import Path

tmpdir = tempfile.mkdtemp()
ctx_path = Path(tmpdir) / "test-ctx.json"

# Valid context
ctx_path.write_text(json.dumps({"distillation": {"status": "ready"}, "version": 1}))
loaded = mod.load_session_context(ctx_path)
results.append(("10a-xi: Valid context loaded", loaded is not None and loaded["version"] == 1))

# Context with wrong status
ctx_path.write_text(json.dumps({"distillation": {"status": "pending"}, "version": 1}))
loaded_bad = mod.load_session_context(ctx_path)
results.append(("10a-xii: Wrong status returns None", loaded_bad is None))

# Non-existent path
loaded_none = mod.load_session_context(Path(tmpdir) / "nonexistent.json")
results.append(("10a-xiii: Missing file returns None", loaded_none is None))

# Malformed JSON
ctx_path.write_text("{broken")
loaded_broken = mod.load_session_context(ctx_path)
results.append(("10a-xiv: Malformed JSON returns None", loaded_broken is None))

import shutil
shutil.rmtree(tmpdir, ignore_errors=True)

print(json.dumps([{"label": r[0], "passed": r[1]} for r in results]))
PYEOF
) 2>/dev/null

if [[ $? -eq 0 && -n "$PIPELINE_TEST" ]]; then
    echo "$PIPELINE_TEST" | python3 -c "
import json, sys
results = json.load(sys.stdin)
for r in results:
    status = 'PASS' if r['passed'] else 'FAIL'
    print(f'  {status}  {r[\"label\"]}')
" 2>/dev/null
    PY_PASS=$(echo "$PIPELINE_TEST" | python3 -c "import json,sys; print(sum(1 for r in json.load(sys.stdin) if r['passed']))" 2>/dev/null || echo 0)
    PY_FAIL=$(echo "$PIPELINE_TEST" | python3 -c "import json,sys; print(sum(1 for r in json.load(sys.stdin) if not r['passed']))" 2>/dev/null || echo 0)
    PASS=$((PASS + PY_PASS))
    FAIL=$((FAIL + PY_FAIL))
else
    echo "  FAIL  Group 10: Python import failed"
    FAIL=$((FAIL + 14))
fi

# Test 10b: _distill-session-context.py Python functions (direct import testing)
DISTILL_PY_TEST=$(python3 << PYEOF
import sys
import json
import importlib.util

spec = importlib.util.spec_from_file_location(
    "distill_session_context",
    "${PROJECT_DIR}/scripts/hooks/_distill-session-context.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

results = []

# Test _extract_original_prompt with string content
import tempfile, os
tmpdir = tempfile.mkdtemp()
t1 = os.path.join(tmpdir, "t1.jsonl")
with open(t1, "w") as f:
    f.write('{"type":"user","message":{"content":"Build a dark mode feature"}}\n')
    f.write('{"type":"assistant","message":{"content":"Sure!"}}\n')

prompt = mod._extract_original_prompt(t1)
results.append(("10b-i: Extract string prompt", prompt == "Build a dark mode feature"))

# Test with list content
t2 = os.path.join(tmpdir, "t2.jsonl")
with open(t2, "w") as f:
    f.write('{"type":"user","message":{"content":[{"type":"text","text":"Part 1"},{"type":"text","text":"Part 2"}]}}\n')

prompt2 = mod._extract_original_prompt(t2)
results.append(("10b-ii: Extract list prompt", "Part 1" in prompt2 and "Part 2" in prompt2))

# Test with nonexistent file
prompt3 = mod._extract_original_prompt("/nonexistent/file.jsonl")
results.append(("10b-iii: Nonexistent file returns empty", prompt3 == ""))

# Test with empty path
prompt4 = mod._extract_original_prompt("")
results.append(("10b-iv: Empty path returns empty", prompt4 == ""))

# Test _build_mock_distillation
mock = mod._build_mock_distillation("Short prompt")
results.append(("10b-v: Mock short prompt", "Short prompt" in mock["key_points"][0]["text"]))

long_text = "x" * 500
mock_long = mod._build_mock_distillation(long_text)
results.append(("10b-vi: Mock long prompt truncated", mock_long["key_points"][0]["text"].endswith("...")))

# Test _build_short_prompt_distillation
short = mod._build_short_prompt_distillation("Fix the button")
results.append(("10b-vii: Short prompt distill", short["key_points"][0]["text"] == "Fix the button"))

# Test _parse_json_response
parsed = mod._parse_json_response('{"key_points": []}')
results.append(("10b-viii: Parse direct JSON", parsed is not None and "key_points" in parsed))

parsed_none = mod._parse_json_response('')
results.append(("10b-ix: Parse empty returns None", parsed_none is None))

import shutil
shutil.rmtree(tmpdir, ignore_errors=True)

print(json.dumps([{"label": r[0], "passed": r[1]} for r in results]))
PYEOF
) 2>/dev/null

if [[ $? -eq 0 && -n "$DISTILL_PY_TEST" ]]; then
    echo "$DISTILL_PY_TEST" | python3 -c "
import json, sys
results = json.load(sys.stdin)
for r in results:
    status = 'PASS' if r['passed'] else 'FAIL'
    print(f'  {status}  {r[\"label\"]}')
" 2>/dev/null
    PY_PASS=$(echo "$DISTILL_PY_TEST" | python3 -c "import json,sys; print(sum(1 for r in json.load(sys.stdin) if r['passed']))" 2>/dev/null || echo 0)
    PY_FAIL=$(echo "$DISTILL_PY_TEST" | python3 -c "import json,sys; print(sum(1 for r in json.load(sys.stdin) if not r['passed']))" 2>/dev/null || echo 0)
    PASS=$((PASS + PY_PASS))
    FAIL=$((FAIL + PY_FAIL))
else
    echo "  FAIL  Group 10b: Python import failed"
    FAIL=$((FAIL + 9))
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
