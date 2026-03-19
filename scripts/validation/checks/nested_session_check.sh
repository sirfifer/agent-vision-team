#!/usr/bin/env bash
# nested_session_check.sh -- Verify claude --print works with CLAUDECODE unset
# This tests the workaround for nested session detection (2.1.42+)
# Exit 0 = works, Exit 1 = fails
set -euo pipefail

# Simulate the nested session scenario: set CLAUDECODE then unset it
export CLAUDECODE="simulated"

OUTPUT=$(unset CLAUDECODE 2>/dev/null; claude --print "Reply with exactly: NESTED_CHECK_OK" 2>/dev/null) || {
    echo "FAILED: claude --print failed after unsetting CLAUDECODE"
    exit 1
}

if [[ -n "$OUTPUT" ]]; then
    echo "PASSED: claude --print works after unsetting CLAUDECODE"
    exit 0
else
    echo "FAILED: Empty output from claude --print after unsetting CLAUDECODE"
    exit 1
fi
