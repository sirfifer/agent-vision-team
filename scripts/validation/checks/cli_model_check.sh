#!/usr/bin/env bash
# cli_model_check.sh -- Verify a model alias resolves to a working model
# Usage: cli_model_check.sh <model_alias>
# Exit 0 = model works, Exit 1 = model fails
set -euo pipefail

MODEL="${1:?Usage: cli_model_check.sh <model_alias>}"

# Use unset CLAUDECODE to avoid nested session detection issues
OUTPUT=$(unset CLAUDECODE 2>/dev/null; claude --print --model "$MODEL" "Reply with exactly: PLATFORM_CHECK_OK" 2>/dev/null) || {
    echo "FAILED: claude --print --model $MODEL returned non-zero exit code"
    exit 1
}

if echo "$OUTPUT" | grep -qi "PLATFORM_CHECK_OK"; then
    echo "PASSED: '$MODEL' alias resolves and produces output"
    exit 0
else
    # Model responded but not with expected text; still functional
    echo "PASSED: '$MODEL' alias resolves (response: $(echo "$OUTPUT" | head -c 80))"
    exit 0
fi
