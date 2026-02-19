#!/usr/bin/env bash
# ============================================================================
# Typecheck: Run TypeScript type checking (no emit)
# ============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FAILED=false

echo "============================================"
echo "  TypeScript Type Check"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# Extension backend
# ---------------------------------------------------------------------------
echo "--- tsc --noEmit: extension ---"
cd "$PROJECT_ROOT/extension"
npx tsc --noEmit || FAILED=true
echo ""

# ---------------------------------------------------------------------------
# Webview dashboard
# ---------------------------------------------------------------------------
echo "--- tsc --noEmit: webview-dashboard ---"
cd "$PROJECT_ROOT/extension/webview-dashboard"
npx tsc --noEmit || FAILED=true
echo ""

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
if [ "$FAILED" = true ]; then
  echo "FAILED: Type errors found."
  exit 1
else
  echo "PASSED: No type errors."
fi
