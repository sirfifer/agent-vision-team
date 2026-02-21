#!/usr/bin/env bash
# ============================================================================
# Setup: Install all dependencies for the project
# ============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "============================================"
echo "  Setup: Installing Dependencies"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# Node.js dependencies
# ---------------------------------------------------------------------------
echo "--- Node.js: root ---"
cd "$PROJECT_ROOT"
npm ci

echo ""
echo "--- Node.js: extension ---"
cd "$PROJECT_ROOT/extension"
npm ci

echo ""
echo "--- Node.js: webview-dashboard ---"
cd "$PROJECT_ROOT/extension/webview-dashboard"
npm ci

# ---------------------------------------------------------------------------
# Python dependencies (using uv)
# ---------------------------------------------------------------------------
PYTHON_DIRS=(
  "mcp-servers/knowledge-graph"
  "mcp-servers/quality"
  "mcp-servers/governance"
  "e2e"
  "server"
)

for dir in "${PYTHON_DIRS[@]}"; do
  full_path="$PROJECT_ROOT/$dir"
  if [ -f "$full_path/pyproject.toml" ]; then
    echo ""
    echo "--- Python: $dir ---"
    cd "$full_path"
    uv sync --extra dev
  fi
done

echo ""
echo "============================================"
echo "  Setup complete"
echo "============================================"
