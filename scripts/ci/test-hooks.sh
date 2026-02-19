#!/usr/bin/env bash
# ============================================================================
# Hook Tests: Run hook unit tests
#
# Wraps the existing scripts/hooks/test-hook-unit.sh.
# ============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "============================================"
echo "  Hook Unit Tests"
echo "============================================"
echo ""

if [ ! -f "$PROJECT_ROOT/scripts/hooks/test-hook-unit.sh" ]; then
  echo "ERROR: scripts/hooks/test-hook-unit.sh not found"
  exit 1
fi

"$PROJECT_ROOT/scripts/hooks/test-hook-unit.sh" "$@"

echo ""
echo "PASSED: Hook unit tests complete."
