#!/usr/bin/env bash
# ============================================================================
# E2E Tests: Run the full end-to-end test suite
#
# Wraps the existing e2e/run-e2e.sh with consistent output formatting.
# ============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "============================================"
echo "  E2E Tests"
echo "============================================"
echo ""

if [ ! -f "$PROJECT_ROOT/e2e/run-e2e.sh" ]; then
  echo "ERROR: e2e/run-e2e.sh not found"
  exit 1
fi

"$PROJECT_ROOT/e2e/run-e2e.sh" "$@"

echo ""
echo "PASSED: E2E tests complete."
