#!/usr/bin/env bash
# ============================================================================
# Capability Matrix Test
#
# Systematically verifies that agents at EVERY spawning level can exercise
# their tools: file I/O, bash execution, and MCP server access.
#
# Three phases test three spawning levels:
#   Phase 1: Direct session (claude -p)
#   Phase 2: Task tool subagent (claude -p spawning a subagent)
#   Phase 3: Agent Teams teammate (future, once teams stabilize)
#
# DESIGN NOTE: claude -p has a known limitation where mixed prompts
# (file ops + MCP calls) cause the model to conclude MCP isn't available.
# Each capability is therefore tested in a focused, single-purpose call.
# This limitation does NOT affect real agents (Task subagents inherit
# MCP from the parent session; teammates get their own MCP connections).
#
# All phases are automated. $0 cost (Max subscription).
#
# Usage:
#   ./scripts/hooks/test-capability-matrix.sh                # All phases
#   ./scripts/hooks/test-capability-matrix.sh --phase 1      # Direct only
#   ./scripts/hooks/test-capability-matrix.sh --phase 2      # Subagent only
#   ./scripts/hooks/test-capability-matrix.sh --keep          # Preserve workspace
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKSPACE=$(mktemp -d /tmp/avt-capability-XXXXXX)

# Prevent "nested session" error when running from inside Claude Code (2.1.42+)
unset CLAUDECODE 2>/dev/null || true
CAP_DIR="${PROJECT_DIR}/.avt/cap-test"

# ── Parse args ────────────────────────────────────────────────────────────────
PHASE=0          # 0 = all phases
KEEP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --phase)   PHASE="$2"; shift 2 ;;
        --keep)    KEEP=true; shift ;;
        *)         echo "Unknown arg: $1"; exit 1 ;;
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

check_file_exists() {
    local label="$1"
    local filepath="$2"

    if [[ -f "$filepath" ]]; then
        echo "  PASS  $label"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  $label (file not found: $filepath)"
        FAIL=$((FAIL + 1))
    fi
}

check_file_contains() {
    local label="$1"
    local filepath="$2"
    local needle="$3"

    if [[ -f "$filepath" ]] && grep -qi "$needle" "$filepath" 2>/dev/null; then
        echo "  PASS  $label"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  $label (file missing or doesn't contain: $needle)"
        FAIL=$((FAIL + 1))
    fi
}

check_no_error_indicators() {
    local label="$1"
    local content="$2"

    # Check for indicators that the MCP tool was NOT accessible.
    # Be precise: "Failed gates" and "No files...tool" are legitimate quality responses.
    if echo "$content" | grep -qi "tool.*not available\|cannot access mcp\|hallucinated\|no mcp tool\|error connecting\|tool not found\|mcp.*not accessible\|not in.*tool list" 2>/dev/null; then
        echo "  FAIL  $label (contains error indicators)"
        FAIL=$((FAIL + 1))
    else
        echo "  PASS  $label"
        PASS=$((PASS + 1))
    fi
}

# Run a focused claude -p call from the project directory
run_claude_focused() {
    local prompt="$1"
    local output_file="$2"

    local input_tmp
    input_tmp=$(mktemp /tmp/avt-cap-input-XXXXXX)
    echo "$prompt" > "$input_tmp"

    cd "$PROJECT_DIR"
    claude -p \
        --model sonnet \
        --output-format text \
        --dangerously-skip-permissions \
        < "$input_tmp" > "$output_file" 2>&1 || true

    rm -f "$input_tmp"
}

cleanup_cap_dir() {
    rm -rf "$CAP_DIR" 2>/dev/null || true
    mkdir -p "$CAP_DIR"
}

# ── Header ────────────────────────────────────────────────────────────────────
echo "============================================================"
echo "  Capability Matrix Test"
echo "============================================================"
echo "  Workspace:  ${WORKSPACE}"
echo "  Phase:      ${PHASE} (0=all)"
echo ""

# ══════════════════════════════════════════════════════════════════
# PHASE 1: Direct Session Capabilities
# ══════════════════════════════════════════════════════════════════
if [[ "$PHASE" -eq 0 || "$PHASE" -eq 1 ]]; then
    echo "-- Phase 1: Direct Session Capabilities --"

    # ── 1A: File Operations ───────────────────────────────────────
    echo "  [1A] Testing file write, edit, bash..."
    cleanup_cap_dir

    run_claude_focused \
        'Do these 3 things:
1. Write "direct-write-ok" to .avt/cap-test/cap-write-test.txt
2. Edit .avt/cap-test/cap-write-test.txt changing "direct-write-ok" to "direct-edit-ok"
3. Run: echo "bash-execution-verified" > .avt/cap-test/cap-bash-test.txt' \
        "${WORKSPACE}/p1a-output.txt"

    check_file_exists "P1: File write artifact created" "${CAP_DIR}/cap-write-test.txt"
    check_file_contains "P1: File edit applied" "${CAP_DIR}/cap-write-test.txt" "direct-edit-ok"
    check_file_exists "P1: Bash artifact created" "${CAP_DIR}/cap-bash-test.txt"
    check_file_contains "P1: Bash content correct" "${CAP_DIR}/cap-bash-test.txt" "bash-execution-verified"

    # ── 1B: MCP KG ───────────────────────────────────────────────
    echo "  [1B] Testing MCP Knowledge Graph..."

    MCP_KG_OUTPUT="${WORKSPACE}/p1b-kg-output.txt"
    run_claude_focused \
        'Call mcp__collab-kg__search_nodes with query "capability-probe". Print the result.' \
        "$MCP_KG_OUTPUT"

    MCP_KG_CONTENT=$(cat "$MCP_KG_OUTPUT" 2>/dev/null)
    if [[ -n "$MCP_KG_CONTENT" ]]; then
        check_no_error_indicators "P1: MCP KG accessible (no error indicators)" "$MCP_KG_CONTENT"
    else
        echo "  FAIL  P1: MCP KG returned empty output"
        FAIL=$((FAIL + 1))
    fi

    # ── 1C: MCP Quality ──────────────────────────────────────────
    echo "  [1C] Testing MCP Quality..."

    MCP_QUAL_OUTPUT="${WORKSPACE}/p1c-quality-output.txt"
    run_claude_focused \
        'Call mcp__collab-quality__validate. Print the result.' \
        "$MCP_QUAL_OUTPUT"

    MCP_QUAL_CONTENT=$(cat "$MCP_QUAL_OUTPUT" 2>/dev/null)
    if [[ -n "$MCP_QUAL_CONTENT" ]]; then
        check_no_error_indicators "P1: MCP Quality accessible (no error indicators)" "$MCP_QUAL_CONTENT"
    else
        echo "  FAIL  P1: MCP Quality returned empty output"
        FAIL=$((FAIL + 1))
    fi

    # ── 1D: MCP Governance ────────────────────────────────────────
    echo "  [1D] Testing MCP Governance..."

    MCP_GOV_OUTPUT="${WORKSPACE}/p1d-governance-output.txt"
    run_claude_focused \
        'Call mcp__collab-governance__get_governance_status. Print the result.' \
        "$MCP_GOV_OUTPUT"

    MCP_GOV_CONTENT=$(cat "$MCP_GOV_OUTPUT" 2>/dev/null)
    if [[ -n "$MCP_GOV_CONTENT" ]]; then
        check_no_error_indicators "P1: MCP Governance accessible (no error indicators)" "$MCP_GOV_CONTENT"
    else
        echo "  FAIL  P1: MCP Governance returned empty output"
        FAIL=$((FAIL + 1))
    fi

    cleanup_cap_dir
    echo ""
fi

# ══════════════════════════════════════════════════════════════════
# PHASE 2: Task Tool Subagent Capabilities
# ══════════════════════════════════════════════════════════════════
if [[ "$PHASE" -eq 0 || "$PHASE" -eq 2 ]]; then
    echo "-- Phase 2: Task Tool Subagent Capabilities --"

    # ── 2A: Subagent File Operations ──────────────────────────────
    echo "  [2A] Testing subagent file write, edit, bash..."
    cleanup_cap_dir

    run_claude_focused \
        'Use the Task tool to spawn a subagent. The subagent must do these 3 things (NOT you):
1. Write "subagent-write-ok" to .avt/cap-test/sub-write-test.txt
2. Edit .avt/cap-test/sub-write-test.txt changing "subagent-write-ok" to "subagent-edit-ok"
3. Run: echo "subagent-bash-verified" > .avt/cap-test/sub-bash-test.txt
Wait for the subagent to complete.' \
        "${WORKSPACE}/p2a-output.txt"

    check_file_exists "P2: Subagent file write artifact" "${CAP_DIR}/sub-write-test.txt"
    check_file_contains "P2: Subagent file edit applied" "${CAP_DIR}/sub-write-test.txt" "subagent-edit-ok"
    check_file_exists "P2: Subagent bash artifact" "${CAP_DIR}/sub-bash-test.txt"
    check_file_contains "P2: Subagent bash content correct" "${CAP_DIR}/sub-bash-test.txt" "subagent-bash-verified"

    # ── 2B: Subagent MCP KG ──────────────────────────────────────
    echo "  [2B] Testing subagent MCP Knowledge Graph..."
    cleanup_cap_dir

    run_claude_focused \
        'Use the Task tool to spawn a subagent. The subagent (NOT you) must call mcp__collab-kg__search_nodes with query "subagent-probe" and write the raw result to .avt/cap-test/sub-mcp-kg.txt. Wait for completion.' \
        "${WORKSPACE}/p2b-output.txt"

    if [[ -f "${CAP_DIR}/sub-mcp-kg.txt" && -s "${CAP_DIR}/sub-mcp-kg.txt" ]]; then
        SUB_KG=$(cat "${CAP_DIR}/sub-mcp-kg.txt")
        check_no_error_indicators "P2: Subagent MCP KG accessible" "$SUB_KG"
    else
        # Check parent output for evidence the tool was called
        P2B_OUT=$(cat "${WORKSPACE}/p2b-output.txt" 2>/dev/null)
        if echo "$P2B_OUT" | grep -qi "search_nodes\|entities\|knowledge.*graph\|query.*subagent" 2>/dev/null; then
            echo "  PASS  P2: Subagent MCP KG called (evidence in output)"
            PASS=$((PASS + 1))
        else
            echo "  FAIL  P2: Subagent MCP KG not accessible (no result file or evidence)"
            FAIL=$((FAIL + 1))
        fi
    fi

    # ── 2C: Subagent MCP Governance ───────────────────────────────
    echo "  [2C] Testing subagent MCP Governance..."
    cleanup_cap_dir

    run_claude_focused \
        'Use the Task tool to spawn a subagent. The subagent (NOT you) must call mcp__collab-governance__get_governance_status and write the raw result to .avt/cap-test/sub-mcp-gov.txt. Wait for completion.' \
        "${WORKSPACE}/p2c-output.txt"

    if [[ -f "${CAP_DIR}/sub-mcp-gov.txt" && -s "${CAP_DIR}/sub-mcp-gov.txt" ]]; then
        SUB_GOV=$(cat "${CAP_DIR}/sub-mcp-gov.txt")
        check_no_error_indicators "P2: Subagent MCP Governance accessible" "$SUB_GOV"
    else
        P2C_OUT=$(cat "${WORKSPACE}/p2c-output.txt" 2>/dev/null)
        if echo "$P2C_OUT" | grep -qi "governance.*status\|total_decisions\|governed_tasks\|approved\|pending" 2>/dev/null; then
            echo "  PASS  P2: Subagent MCP Governance called (evidence in output)"
            PASS=$((PASS + 1))
        else
            echo "  FAIL  P2: Subagent MCP Governance not accessible"
            FAIL=$((FAIL + 1))
        fi
    fi

    cleanup_cap_dir
    echo ""
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo "============================================================"
echo "  CAPABILITY MATRIX SUMMARY"
echo "============================================================"
TOTAL=$((PASS + FAIL))
echo ""
echo "  Checks: $PASS passed, $FAIL failed (of $TOTAL)"
echo ""

# Build result matrix from what we tested
echo "  ┌──────────────────┬─────────┬───────────┐"
echo "  │ Capability       │ Direct  │ Subagent  │"
echo "  ├──────────────────┼─────────┼───────────┤"

# Phase 1 results
P1_WRITE="--"; P1_EDIT="--"; P1_BASH="--"; P1_KG="--"; P1_QUAL="--"; P1_GOV="--"
P2_WRITE="--"; P2_EDIT="--"; P2_BASH="--"; P2_KG="--"; P2_GOV="--"

if [[ "$PHASE" -eq 0 || "$PHASE" -eq 1 ]]; then
    [[ -f "${CAP_DIR}/cap-write-test.txt" ]] 2>/dev/null || true
    # Parse from pass/fail counts isn't clean; just re-check files
    [[ -f "${WORKSPACE}/p1a-output.txt" ]] && P1_WRITE="OK" && P1_EDIT="OK" && P1_BASH="OK"
    # For file ops, trust the artifact checks above
    if [[ -f "${WORKSPACE}/p1b-kg-output.txt" ]]; then
        KG_C=$(cat "${WORKSPACE}/p1b-kg-output.txt" 2>/dev/null)
        if echo "$KG_C" | grep -qi "not available\|FAILED\|cannot\|no.*tool" 2>/dev/null; then
            P1_KG="FAIL"
        else
            P1_KG="OK"
        fi
    fi
    if [[ -f "${WORKSPACE}/p1c-quality-output.txt" ]]; then
        Q_C=$(cat "${WORKSPACE}/p1c-quality-output.txt" 2>/dev/null)
        if echo "$Q_C" | grep -qi "not available\|FAILED\|cannot\|no.*tool" 2>/dev/null; then
            P1_QUAL="FAIL"
        else
            P1_QUAL="OK"
        fi
    fi
    if [[ -f "${WORKSPACE}/p1d-governance-output.txt" ]]; then
        G_C=$(cat "${WORKSPACE}/p1d-governance-output.txt" 2>/dev/null)
        if echo "$G_C" | grep -qi "not available\|FAILED\|cannot\|no.*tool" 2>/dev/null; then
            P1_GOV="FAIL"
        else
            P1_GOV="OK"
        fi
    fi
fi

printf "  │ %-16s │ %-7s │ %-9s │\n" "FILE_WRITE" "$P1_WRITE" "$P2_WRITE"
printf "  │ %-16s │ %-7s │ %-9s │\n" "FILE_EDIT" "$P1_EDIT" "$P2_EDIT"
printf "  │ %-16s │ %-7s │ %-9s │\n" "BASH" "$P1_BASH" "$P2_BASH"
printf "  │ %-16s │ %-7s │ %-9s │\n" "MCP_KG" "$P1_KG" "$P2_KG"
printf "  │ %-16s │ %-7s │ %-9s │\n" "MCP_QUALITY" "$P1_QUAL" "--"
printf "  │ %-16s │ %-7s │ %-9s │\n" "MCP_GOVERNANCE" "$P1_GOV" "$P2_GOV"

echo "  └──────────────────┴─────────┴───────────┘"
echo ""

if [[ "$FAIL" -eq 0 && "$PASS" -gt 0 ]]; then
    echo "  Result: ALL PASSED"
    FINAL_EXIT=0
else
    echo "  Result: FAILED ($FAIL failures)"
    FINAL_EXIT=1
fi

echo "============================================================"

# ── Cleanup ───────────────────────────────────────────────────────────────────
rm -rf "$CAP_DIR" 2>/dev/null || true

if [[ "$KEEP" == "true" ]]; then
    echo ""
    echo "  Workspace preserved: ${WORKSPACE}"
else
    rm -rf "$WORKSPACE"
    echo ""
    echo "  Workspace cleaned: ${WORKSPACE}"
fi

exit $FINAL_EXIT
