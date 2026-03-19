#!/usr/bin/env bash
# agent_defs_teammate_check.sh -- Check if .claude/agents/ can be used as teammates
# Tests bug #24316: agent definitions as Agent Teams teammates.
# Exit 0 = feature works, Exit 1 = still broken (workaround needed)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
AGENTS_DIR="$PROJECT_DIR/.claude/agents"

# First verify agent definitions exist
if [[ ! -d "$AGENTS_DIR" ]]; then
    echo "FAILED: .claude/agents/ directory not found"
    exit 1
fi

AGENT_COUNT=$(ls "$AGENTS_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
if [[ "$AGENT_COUNT" -eq 0 ]]; then
    echo "FAILED: No agent definitions found in .claude/agents/"
    exit 1
fi

# Check GitHub issue status if gh CLI available
if command -v gh &>/dev/null; then
    ISSUE_STATE=$(gh issue view 24316 -R anthropics/claude-code --json state -q '.state' 2>/dev/null || echo "unknown")
    if [[ "$ISSUE_STATE" == "CLOSED" ]]; then
        echo "PASSED: Issue #24316 is CLOSED; agent defs may now work as teammates ($AGENT_COUNT definitions found)"
        exit 0
    elif [[ "$ISSUE_STATE" == "OPEN" ]]; then
        echo "FAILED: Issue #24316 still OPEN; agent defs cannot be used as teammates (workaround: embed prompts in spawn). $AGENT_COUNT definitions found."
        exit 1
    fi
fi

# Fallback: try to check via claude
echo "INFO: Cannot determine issue #24316 status (gh CLI not available or rate limited). $AGENT_COUNT agent definitions present."
exit 1
