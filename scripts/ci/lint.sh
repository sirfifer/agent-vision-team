#!/usr/bin/env bash
# ============================================================================
# Lint: Run all linters and formatters (check mode by default)
#
# Usage:
#   ./scripts/ci/lint.sh          # check only (CI mode)
#   ./scripts/ci/lint.sh --fix    # auto-fix violations
# ============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FIX=false
FAILED=false

for arg in "$@"; do
  case $arg in
    --fix) FIX=true ;;
  esac
done

echo "============================================"
echo "  Lint$([ "$FIX" = true ] && echo " (fix mode)" || echo " (check mode)")"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# ESLint — TypeScript extension
# ---------------------------------------------------------------------------
echo "--- ESLint: extension/src ---"
cd "$PROJECT_ROOT/extension"
if [ "$FIX" = true ]; then
  npx eslint src --ext ts --fix || FAILED=true
else
  npx eslint src --ext ts || FAILED=true
fi
echo ""

# ---------------------------------------------------------------------------
# Prettier — TypeScript / JSON
# ---------------------------------------------------------------------------
echo "--- Prettier: extension ---"
cd "$PROJECT_ROOT"
if [ "$FIX" = true ]; then
  npx prettier --write "extension/src/**/*.ts" "extension/webview-dashboard/src/**/*.{ts,tsx}" || FAILED=true
else
  npx prettier --check "extension/src/**/*.ts" "extension/webview-dashboard/src/**/*.{ts,tsx}" || FAILED=true
fi
echo ""

# ---------------------------------------------------------------------------
# Ruff — Python lint
# ---------------------------------------------------------------------------
PYTHON_DIRS=(
  "mcp-servers/knowledge-graph"
  "mcp-servers/quality"
  "mcp-servers/governance"
  "e2e"
  "server"
  "scripts"
)

echo "--- Ruff check: Python ---"
for dir in "${PYTHON_DIRS[@]}"; do
  full_path="$PROJECT_ROOT/$dir"
  if [ -d "$full_path" ]; then
    if [ "$FIX" = true ]; then
      ruff check --fix "$full_path" || FAILED=true
    else
      ruff check "$full_path" || FAILED=true
    fi
  fi
done
echo ""

# ---------------------------------------------------------------------------
# Ruff — Python format
# ---------------------------------------------------------------------------
echo "--- Ruff format: Python ---"
for dir in "${PYTHON_DIRS[@]}"; do
  full_path="$PROJECT_ROOT/$dir"
  if [ -d "$full_path" ]; then
    if [ "$FIX" = true ]; then
      ruff format "$full_path" || FAILED=true
    else
      ruff format --check "$full_path" || FAILED=true
    fi
  fi
done
echo ""

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
if [ "$FAILED" = true ]; then
  echo "FAILED: Lint violations found."
  echo "  Run './scripts/ci/lint.sh --fix' to auto-fix."
  exit 1
else
  echo "PASSED: All lint checks clean."
fi
