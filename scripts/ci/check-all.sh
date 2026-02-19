#!/usr/bin/env bash
# ============================================================================
# Check All: Run the full quality pipeline (fail-fast)
#
# This is the "did I break anything?" command.
# Runs: lint → typecheck → build → test → coverage
#
# Usage:
#   ./scripts/ci/check-all.sh         # full pipeline
# ============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT_DIR="$PROJECT_ROOT/scripts/ci"

echo "============================================"
echo "  Full Quality Pipeline"
echo "============================================"
echo ""
echo "  Steps: lint → typecheck → build → test → coverage"
echo ""

STEP=0
TOTAL=5

run_step() {
  local name="$1"
  local script="$2"
  shift 2
  STEP=$((STEP + 1))
  echo ""
  echo "[$STEP/$TOTAL] $name"
  echo "--------------------------------------------"
  "$SCRIPT_DIR/$script" "$@"
  echo ""
}

run_step "Lint"      lint.sh
run_step "Typecheck" typecheck.sh
run_step "Build"     build.sh
run_step "Test"      test.sh
run_step "Coverage"  coverage.sh

echo "============================================"
echo "  ALL CHECKS PASSED"
echo "============================================"
