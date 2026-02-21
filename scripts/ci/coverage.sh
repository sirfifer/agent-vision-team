#!/usr/bin/env bash
# ============================================================================
# Coverage: Run tests with coverage and enforce threshold
#
# Coverage threshold: 80% target (see TODO below for ratcheting plan)
# ============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# TODO: Ratchet to 80% as test coverage improves.
# Current baselines (2026-02-19): knowledge-graph=36%, quality=41%, governance=0%
THRESHOLD=30
FAILED=false
SKIP_EXTENSION=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-extension) SKIP_EXTENSION=true; shift ;;
    *) shift ;;
  esac
done

echo "============================================"
echo "  Coverage (threshold: ${THRESHOLD}%)"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# Results tracking
# ---------------------------------------------------------------------------
declare -a RESULTS=()

record_result() {
  local name="$1"
  local pct="$2"
  local status="$3"
  RESULTS+=("$name|$pct|$status")
}

# ---------------------------------------------------------------------------
# Python MCP server coverage
# ---------------------------------------------------------------------------
run_python_coverage() {
  local name="$1"
  local dir="$PROJECT_ROOT/mcp-servers/$name"

  # Discover actual package directory (collab_*) instead of guessing from name
  local pkg_name
  pkg_name=$(find "$dir" -maxdepth 1 -type d -name 'collab_*' -exec basename {} \; | head -1)
  if [ -z "$pkg_name" ]; then
    pkg_name="collab_${name//-/_}"
  fi

  if [ ! -d "$dir/tests" ]; then
    echo "  Skipping $name (no tests/ directory)"
    record_result "$name" "N/A" "SKIP"
    return 0
  fi

  # Skip if only __init__.py exists (no actual test files)
  local test_files
  test_files=$(find "$dir/tests" -name 'test_*.py' -o -name '*_test.py' | head -1)
  if [ -z "$test_files" ]; then
    echo "  Skipping $name (no test files)"
    record_result "$name" "N/A" "SKIP"
    return 0
  fi

  echo "--- coverage: $name ---"
  cd "$dir"

  local output rc=0
  output=$(uv run --extra dev pytest tests/ \
    --cov="$pkg_name" \
    --cov-report=term-missing \
    --cov-report=xml:"$PROJECT_ROOT/coverage/${name}-coverage.xml" \
    --cov-fail-under="$THRESHOLD" \
    -v 2>&1) || rc=$?

  echo "$output"

  if [ "$rc" -eq 5 ]; then
    echo "  (no tests collected — skipping coverage)"
    record_result "$name" "N/A" "SKIP"
  elif [ "$rc" -eq 0 ]; then
    local pct
    pct=$(echo "$output" | grep "^TOTAL" | awk '{print $NF}' | tr -d '%')
    record_result "$name" "${pct}%" "PASS"
  else
    local pct
    pct=$(echo "$output" | grep "^TOTAL" | awk '{print $NF}' | tr -d '%' || echo "?")
    record_result "$name" "${pct}%" "FAIL"
    FAILED=true
  fi
  echo ""
}

# ---------------------------------------------------------------------------
# TypeScript extension coverage
# ---------------------------------------------------------------------------
run_extension_coverage() {
  echo "--- coverage: extension ---"
  cd "$PROJECT_ROOT/extension"

  if npm run test:coverage 2>&1; then
    record_result "extension" ">=80%" "PASS"
  else
    record_result "extension" "<80%" "FAIL"
    FAILED=true
  fi
  echo ""
}

# ---------------------------------------------------------------------------
# Create coverage output directory
# ---------------------------------------------------------------------------
mkdir -p "$PROJECT_ROOT/coverage"

# ---------------------------------------------------------------------------
# Run all coverage
# ---------------------------------------------------------------------------
run_python_coverage "knowledge-graph"
run_python_coverage "quality"
run_python_coverage "governance"

if [ "$SKIP_EXTENSION" = false ]; then
  run_extension_coverage
else
  echo "--- coverage: extension (skipped) ---"
  record_result "extension" "N/A" "SKIP"
  echo ""
fi

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
echo "============================================"
echo "  Coverage Summary"
echo "============================================"
printf "  %-20s %-10s %-6s\n" "Component" "Coverage" "Status"
printf "  %-20s %-10s %-6s\n" "---" "---" "---"
for entry in "${RESULTS[@]}"; do
  IFS='|' read -r name pct status <<< "$entry"
  printf "  %-20s %-10s %-6s\n" "$name" "$pct" "$status"
done
echo ""

if [ "$FAILED" = true ]; then
  echo "FAILED: Coverage below ${THRESHOLD}% in one or more components."
  exit 1
else
  echo "PASSED: All components meet ${THRESHOLD}% coverage threshold."
fi
