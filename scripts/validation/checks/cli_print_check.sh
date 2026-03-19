#!/usr/bin/env bash
# cli_print_check.sh -- Verify claude --print produces output
# Exit 0 = works, Exit 1 = fails
set -euo pipefail

OUTPUT=$(unset CLAUDECODE 2>/dev/null; claude --print "Reply with exactly: PRINT_CHECK_OK" 2>/dev/null) || {
    echo "FAILED: claude --print returned non-zero exit code"
    exit 1
}

if [[ -n "$OUTPUT" ]]; then
    echo "PASSED: claude --print produces output ($(echo "$OUTPUT" | wc -c | tr -d ' ') bytes)"
    exit 0
else
    echo "FAILED: claude --print returned empty output"
    exit 1
fi
