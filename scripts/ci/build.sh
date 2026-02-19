#!/usr/bin/env bash
# ============================================================================
# Build: Build all project artifacts
# ============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "============================================"
echo "  Build"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# Webview dashboard (must build before extension, since extension embeds it)
# ---------------------------------------------------------------------------
echo "--- Building webview dashboard ---"
cd "$PROJECT_ROOT/extension/webview-dashboard"
npm run build
echo ""

# ---------------------------------------------------------------------------
# Extension backend
# ---------------------------------------------------------------------------
echo "--- Building extension ---"
cd "$PROJECT_ROOT/extension"
node esbuild.config.js
echo ""

# ---------------------------------------------------------------------------
# Verify outputs
# ---------------------------------------------------------------------------
FAILED=false

if [ -f "$PROJECT_ROOT/extension/out/extension.js" ]; then
  SIZE=$(ls -lh "$PROJECT_ROOT/extension/out/extension.js" | awk '{print $5}')
  echo "  extension/out/extension.js ($SIZE)"
else
  echo "  MISSING: extension/out/extension.js"
  FAILED=true
fi

if [ -d "$PROJECT_ROOT/extension/webview-dashboard/dist" ]; then
  COUNT=$(find "$PROJECT_ROOT/extension/webview-dashboard/dist" -type f | wc -l | tr -d ' ')
  echo "  extension/webview-dashboard/dist/ ($COUNT files)"
else
  echo "  MISSING: extension/webview-dashboard/dist/"
  FAILED=true
fi

echo ""
if [ "$FAILED" = true ]; then
  echo "FAILED: Build outputs missing."
  exit 1
else
  echo "PASSED: Build successful."
fi
