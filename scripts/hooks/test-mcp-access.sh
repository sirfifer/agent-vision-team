#!/usr/bin/env bash
# ============================================================================
# MCP Accessibility Verification
#
# Verifies that user-scope MCP servers (~/.claude/mcp.json) are correctly
# configured and accessible. Catches the common failure where MCP servers
# are registered but not actually launchable.
#
# Usage:
#   ./scripts/hooks/test-mcp-access.sh           # Static + launch checks only
#   ./scripts/hooks/test-mcp-access.sh --live     # Also test from Claude session
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MCP_CONFIG="$HOME/.claude/mcp.json"

# Prevent "nested session" error when running from inside Claude Code (2.1.42+)
unset CLAUDECODE 2>/dev/null || true

# ── Parse args ────────────────────────────────────────────────────────────────
LIVE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --live)  LIVE=true; shift ;;
        *)       echo "Unknown arg: $1"; exit 1 ;;
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

echo "============================================================"
echo "  MCP Accessibility Verification"
echo "============================================================"
echo "  Config:  ${MCP_CONFIG}"
echo "  Live:    ${LIVE}"
echo ""

# ══════════════════════════════════════════════════════════════════
# PHASE 1: Static Config Validation
# ══════════════════════════════════════════════════════════════════
echo "-- Phase 1: Static Config Validation --"

# 1a: Config file exists
CONFIG_EXISTS="false"
[[ -f "$MCP_CONFIG" ]] && CONFIG_EXISTS="true"
check "Config file exists at ~/.claude/mcp.json" "true" "$CONFIG_EXISTS"

if [[ "$CONFIG_EXISTS" == "false" ]]; then
    echo ""
    echo "  FATAL: MCP config not found. Cannot continue."
    echo "  Create ~/.claude/mcp.json with user-scope MCP server definitions."
    echo ""
    echo "  Result: FAILED"
    exit 1
fi

# 1b: Valid JSON
JSON_VALID="false"
python3 -c "import json; json.load(open('$MCP_CONFIG'))" 2>/dev/null && JSON_VALID="true"
check "Config is valid JSON" "true" "$JSON_VALID"

# 1c: All three servers defined
for server in collab-kg collab-quality collab-governance; do
    HAS_SERVER=$(python3 -c "
import json
cfg = json.load(open('$MCP_CONFIG'))
print('true' if '$server' in cfg.get('mcpServers', {}) else 'false')
" 2>/dev/null || echo "false")
    check "Config defines $server" "true" "$HAS_SERVER"
done

# 1d: CWD paths exist and contain pyproject.toml
for server in collab-kg collab-quality collab-governance; do
    CWD=$(python3 -c "
import json
cfg = json.load(open('$MCP_CONFIG'))
print(cfg.get('mcpServers', {}).get('$server', {}).get('cwd', ''))
" 2>/dev/null || echo "")

    if [[ -n "$CWD" ]]; then
        CWD_EXISTS="false"
        [[ -d "$CWD" ]] && CWD_EXISTS="true"
        check "CWD for $server exists" "true" "$CWD_EXISTS"

        PYPROJECT_EXISTS="false"
        [[ -f "$CWD/pyproject.toml" ]] && PYPROJECT_EXISTS="true"
        check "CWD for $server has pyproject.toml" "true" "$PYPROJECT_EXISTS"
    else
        check "CWD for $server is defined" "non-empty" "empty"
    fi
done

# 1e: No stale project-scope MCP definitions
HAS_PROJECT_MCP=$(python3 -c "
import json
cfg = json.load(open('$PROJECT_DIR/.claude/settings.json'))
print('true' if 'mcpServers' in cfg else 'false')
" 2>/dev/null || echo "unknown")
check "No project-scope MCP in .claude/settings.json" "false" "$HAS_PROJECT_MCP"

echo ""

# ══════════════════════════════════════════════════════════════════
# PHASE 2: Server Launch Verification
# ══════════════════════════════════════════════════════════════════
echo "-- Phase 2: Server Launch Verification --"

module_for_server() {
    case "$1" in
        collab-kg)         echo "collab_kg.server" ;;
        collab-quality)    echo "collab_quality.server" ;;
        collab-governance) echo "collab_governance.server" ;;
    esac
}

for server_name in collab-kg collab-quality collab-governance; do
    CWD=$(python3 -c "
import json
cfg = json.load(open('$MCP_CONFIG'))
print(cfg.get('mcpServers', {}).get('$server_name', {}).get('cwd', ''))
" 2>/dev/null || echo "")

    MODULE="$(module_for_server "$server_name")"

    if [[ -n "$CWD" && -d "$CWD" ]]; then
        IMPORT_OK="false"
        cd "$CWD"
        uv run python -c "import ${MODULE}; print('importable')" 2>/dev/null && IMPORT_OK="true"
        cd "$PROJECT_DIR"
        check "$server_name module importable" "true" "$IMPORT_OK"
    else
        check "$server_name module importable" "true" "cwd_missing"
    fi
done

echo ""

# ══════════════════════════════════════════════════════════════════
# PHASE 3: Live Session MCP Access (only with --live)
# ══════════════════════════════════════════════════════════════════
if [[ "$LIVE" == "true" ]]; then
    echo "-- Phase 3: Live Session MCP Access --"

    # Check if claude CLI is available
    if ! command -v claude &>/dev/null; then
        echo "  SKIP: claude CLI not found in PATH"
        echo ""
    else
        LIVE_WORKSPACE=$(mktemp -d /tmp/avt-mcp-live-XXXXXX)
        LIVE_OUTPUT="${LIVE_WORKSPACE}/claude-output.txt"

        PROMPT="You have access to three MCP servers. Call ONE tool from each:
1. From collab-kg: call search_nodes with query \"test-connectivity-check\"
2. From collab-governance: call get_governance_status
3. From collab-quality: call validate

For each, report whether the call succeeded or failed. Write a brief summary."

        echo "  Running claude -p with MCP tool calls..."
        claude -p "$PROMPT" \
            --model haiku \
            --output-format text \
            --dangerously-skip-permissions \
            2>&1 > "$LIVE_OUTPUT" || true

        if [[ -f "$LIVE_OUTPUT" ]]; then
            LIVE_CONTENT=$(cat "$LIVE_OUTPUT")

            # Check for evidence of MCP accessibility
            # Negative indicators: hallucinated results, "not available", "error"
            for server in "collab-kg" "collab-quality" "collab-governance"; do
                ACCESSIBLE="accessible"
                if echo "$LIVE_CONTENT" | grep -qi "not available\|connection refused\|MCP.*error.*${server}\|no.*tool.*${server}" 2>/dev/null; then
                    ACCESSIBLE="not_accessible"
                fi
                # Also check for positive indicators
                if echo "$LIVE_CONTENT" | grep -qi "hallucin\|made.up\|simulated\|cannot.*access.*mcp" 2>/dev/null; then
                    ACCESSIBLE="hallucinated"
                fi
                check "$server accessible from Claude session" "accessible" "$ACCESSIBLE"
            done

            echo ""
            echo "  --- Claude output (first 20 lines) ---"
            head -20 "$LIVE_OUTPUT"
        else
            echo "  Claude output file not created."
            FAIL=$((FAIL + 3))
        fi

        rm -rf "$LIVE_WORKSPACE"
    fi
    echo ""
else
    echo "-- Phase 3: Live Session MCP Access (skipped, use --live) --"
    echo ""
fi

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

exit $FINAL_EXIT
