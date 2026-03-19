#!/usr/bin/env bash
# hook_exit_code_check.sh -- Verify PreToolUse hooks can block via exit code 2
# This is a structural check: verifies the hook scripts exist, are executable,
# and return exit code 2 when appropriate conditions exist.
# Exit 0 = blocking mechanism works, Exit 1 = broken
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Test holistic-review-gate.sh with a mock flag file
GATE_SCRIPT="$PROJECT_DIR/scripts/hooks/holistic-review-gate.sh"

if [[ ! -x "$GATE_SCRIPT" ]]; then
    echo "FAILED: holistic-review-gate.sh not found or not executable"
    exit 1
fi

# Create a temporary flag file to trigger blocking
TEST_FLAG_DIR="$PROJECT_DIR/.avt"
mkdir -p "$TEST_FLAG_DIR"
TEST_FLAG="$TEST_FLAG_DIR/.holistic-review-pending-validation-test"
echo '{"status": "pending", "session_id": "validation-test"}' > "$TEST_FLAG"

# Pipe mock hook input to the gate script
EXIT_CODE=0
echo '{"tool_name": "Write", "tool_input": {"file_path": "/tmp/test.txt"}}' | "$GATE_SCRIPT" 2>/dev/null || EXIT_CODE=$?

# Clean up the test flag
rm -f "$TEST_FLAG"

if [[ $EXIT_CODE -eq 2 ]]; then
    echo "PASSED: holistic-review-gate.sh returns exit code 2 to block tool execution"
    exit 0
elif [[ $EXIT_CODE -eq 0 ]]; then
    echo "FAILED: Gate script returned 0 (allow) despite pending flag file"
    exit 1
else
    echo "FAILED: Gate script returned unexpected exit code $EXIT_CODE"
    exit 1
fi
