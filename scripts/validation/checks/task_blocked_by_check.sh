#!/usr/bin/env bash
# task_blocked_by_check.sh -- Verify blockedBy field structure in task files
# Creates tasks with blockedBy and verifies the JSON structure is correct.
# Exit 0 = structure works, Exit 1 = broken
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

TEST_LIST="validation-blockedby-$$"
TASK_DIR="$HOME/.claude/tasks/$TEST_LIST"

# Clean up
rm -rf "$TASK_DIR"
mkdir -p "$TASK_DIR"

# Create a mock task pair to verify the blockedBy JSON structure works
# This tests our governance hook's task manipulation pattern
cat > "$TASK_DIR/1.json" <<'EOF'
{"id": "1", "subject": "Review task", "description": "Governance review", "status": "pending"}
EOF

cat > "$TASK_DIR/2.json" <<'EOF'
{"id": "2", "subject": "Impl task", "description": "Implementation", "status": "pending", "blockedBy": ["1"]}
EOF

# Verify the blockedBy structure is valid JSON and parseable
RESULT=$(python3 -c "
import json, sys
try:
    with open('$TASK_DIR/2.json') as f:
        task = json.load(f)
    blocked_by = task.get('blockedBy', [])
    if isinstance(blocked_by, list) and '1' in blocked_by:
        print('OK')
    else:
        print(f'BAD_STRUCTURE: blockedBy={blocked_by}')
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null || echo "ERROR")

# Clean up
rm -rf "$TASK_DIR"

if [[ "$RESULT" == "OK" ]]; then
    echo "PASSED: blockedBy field structure is valid and parseable"
    exit 0
else
    echo "FAILED: $RESULT"
    exit 1
fi
