#!/usr/bin/env bash
# ============================================================================
# Test: Run unit tests
#
# Usage:
#   ./scripts/ci/test.sh                              # run all unit tests
#   ./scripts/ci/test.sh --component knowledge-graph   # run one MCP server
#   ./scripts/ci/test.sh --component quality
#   ./scripts/ci/test.sh --component governance
#   ./scripts/ci/test.sh --component extension         # run TS extension tests
#   ./scripts/ci/test.sh --component hooks             # run hook unit tests
# ============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPONENT=""
FAILED=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --component) COMPONENT="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo "============================================"
echo "  Tests$([ -n "$COMPONENT" ] && echo " ($COMPONENT)" || echo " (all)")"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# Python MCP server tests
# ---------------------------------------------------------------------------
run_python_tests() {
  local name="$1"
  local dir="$PROJECT_ROOT/mcp-servers/$name"

  if [ ! -d "$dir/tests" ]; then
    echo "  Skipping $name (no tests/ directory)"
    return 0
  fi

  echo "--- pytest: $name ---"
  cd "$dir"
  uv run pytest tests/ -v || FAILED=true
  echo ""
}

# ---------------------------------------------------------------------------
# TypeScript extension tests
# ---------------------------------------------------------------------------
run_extension_tests() {
  echo "--- extension tests ---"
  cd "$PROJECT_ROOT/extension"
  npm test || FAILED=true
  echo ""
}

# ---------------------------------------------------------------------------
# Hook unit tests
# ---------------------------------------------------------------------------
run_hook_tests() {
  echo "--- hook unit tests ---"
  "$PROJECT_ROOT/scripts/hooks/test-hook-unit.sh" || FAILED=true
  echo ""
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
if [ -n "$COMPONENT" ]; then
  case "$COMPONENT" in
    knowledge-graph|quality|governance)
      run_python_tests "$COMPONENT"
      ;;
    extension)
      run_extension_tests
      ;;
    hooks)
      run_hook_tests
      ;;
    *)
      echo "Unknown component: $COMPONENT"
      echo "Valid: knowledge-graph, quality, governance, extension, hooks"
      exit 1
      ;;
  esac
else
  # Run all
  run_python_tests "knowledge-graph"
  run_python_tests "quality"
  run_python_tests "governance"
  run_extension_tests
  run_hook_tests
fi

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
if [ "$FAILED" = true ]; then
  echo "FAILED: Some tests failed."
  exit 1
else
  echo "PASSED: All tests passed."
fi
