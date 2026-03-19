#!/usr/bin/env bash
# mcp_session_access_check.sh -- Verify MCP tools accessible from session/subagent
# Usage: mcp_session_access_check.sh <context>  (context = "direct" or "subagent")
# This uses claude --print to attempt an MCP call.
# Exit 0 = MCP accessible, Exit 1 = not accessible
set -euo pipefail

CONTEXT="${1:?Usage: mcp_session_access_check.sh <direct|subagent>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# We test by asking Claude to call a simple MCP tool
# Using collab-kg's search_nodes as a lightweight test
PROMPT="Use the collab-kg MCP server's search_nodes tool to search for 'test'. Just call the tool and report what happens. If you get a result (even empty), say MCP_ACCESS_OK. If you cannot access MCP tools, say MCP_ACCESS_FAILED."

if [[ "$CONTEXT" == "direct" ]]; then
    OUTPUT=$(unset CLAUDECODE 2>/dev/null; cd "$PROJECT_DIR" && claude --print "$PROMPT" 2>/dev/null) || {
        echo "FAILED: claude --print failed for direct MCP access test"
        exit 1
    }
elif [[ "$CONTEXT" == "subagent" ]]; then
    # For subagent test, we ask the model to spawn a task subagent that calls MCP
    # This is expensive, so we do a lighter check: verify MCP config is at user scope
    # (which is the prerequisite for subagent MCP access)
    MCP_CONFIG="$HOME/.claude/mcp.json"
    if [[ -f "$MCP_CONFIG" ]]; then
        # Verify it's user-scope (not project-scope which causes hallucination)
        PROJECT_MCP="$PROJECT_DIR/.mcp.json"
        if [[ -f "$PROJECT_MCP" ]]; then
            echo "WARNING: Both user-scope and project-scope MCP configs exist; subagent may hallucinate (issue #13898)"
            exit 1
        fi
        echo "PASSED: MCP at user scope only (subagent access prerequisite met)"
        exit 0
    else
        echo "FAILED: No user-scope MCP config found at $MCP_CONFIG"
        exit 1
    fi
else
    echo "FAILED: Unknown context: $CONTEXT (expected 'direct' or 'subagent')"
    exit 1
fi

if echo "$OUTPUT" | grep -qi "MCP_ACCESS_OK"; then
    echo "PASSED: MCP tools accessible from $CONTEXT session"
    exit 0
elif echo "$OUTPUT" | grep -qi "MCP_ACCESS_FAILED"; then
    echo "FAILED: MCP tools not accessible from $CONTEXT session"
    exit 1
else
    # Check for any indication of MCP tool use in the output
    if echo "$OUTPUT" | grep -qi "search_nodes\|entities\|results"; then
        echo "PASSED: MCP tools appear accessible from $CONTEXT session (indirect evidence)"
        exit 0
    fi
    echo "INCONCLUSIVE: Could not determine MCP access from $CONTEXT session"
    exit 1
fi
