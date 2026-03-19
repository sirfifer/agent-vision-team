#!/usr/bin/env bash
# auto_memory_check.sh -- Verify auto-memory MEMORY.md exists and is loadable
# Exit 0 = auto-memory configured, Exit 1 = not found
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Auto-memory path follows the pattern: ~/.claude/projects/<project-path-hash>/memory/MEMORY.md
# The exact path encoding varies, so we search for it
MEMORY_DIR="$HOME/.claude/projects"

if [[ ! -d "$MEMORY_DIR" ]]; then
    echo "FAILED: Auto-memory directory not found at $MEMORY_DIR"
    exit 1
fi

# Find MEMORY.md files related to this project
FOUND=$(find "$MEMORY_DIR" -name "MEMORY.md" -path "*/memory/*" 2>/dev/null | head -5)

if [[ -z "$FOUND" ]]; then
    echo "FAILED: No MEMORY.md files found in auto-memory directory"
    exit 1
fi

# Check if any of them reference our project
PROJECT_MEMORY=""
while IFS= read -r memfile; do
    if grep -qi "agent.vision.team\|avt\|agent-vision" "$memfile" 2>/dev/null; then
        PROJECT_MEMORY="$memfile"
        break
    fi
done <<< "$FOUND"

if [[ -n "$PROJECT_MEMORY" ]]; then
    LINES=$(wc -l < "$PROJECT_MEMORY" | tr -d ' ')
    echo "PASSED: Project auto-memory found at $PROJECT_MEMORY ($LINES lines)"
    if [[ "$LINES" -gt 200 ]]; then
        echo "WARNING: MEMORY.md has $LINES lines; only first 200 are loaded into prompts"
    fi
    exit 0
else
    echo "INFO: MEMORY.md files found but none reference this project"
    exit 0
fi
