#!/usr/bin/env bash
# ============================================================================
# E2E test runner for the Collaborative Intelligence System.
#
# Creates a temporary workspace, sets up the mock environment, runs the
# Python orchestrator, and cleans up on exit.
#
# Usage:
#   ./e2e/run-e2e.sh              # standard run (workspace cleaned up)
#   ./e2e/run-e2e.sh --keep       # preserve workspace after run
#   ./e2e/run-e2e.sh --verbose    # enable debug logging
#   ./e2e/run-e2e.sh --seed 42    # reproducible project generation
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
KEEP=false

# Scan arguments for --keep (consumed here; other args forwarded to Python).
FORWARD_ARGS=()
for arg in "$@"; do
    case $arg in
        --keep)
            KEEP=true
            FORWARD_ARGS+=("$arg")
            ;;
        *)
            FORWARD_ARGS+=("$arg")
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Create a unique temp workspace
# ---------------------------------------------------------------------------
WORKSPACE=$(mktemp -d /tmp/avt-e2e-XXXXXX)
echo "============================================"
echo "  AVT E2E Test Suite"
echo "============================================"
echo "  Workspace: $WORKSPACE"
echo "  Project:   $PROJECT_DIR"
echo ""

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
# Mock governance reviews so scenarios don't need a live claude binary.
export GOVERNANCE_MOCK_REVIEW=true

# ---------------------------------------------------------------------------
# Cleanup trap
# ---------------------------------------------------------------------------
cleanup() {
    local exit_code=$?
    if [ "$KEEP" = "false" ]; then
        rm -rf "$WORKSPACE"
        echo "  Cleaned up workspace: $WORKSPACE"
    else
        echo "  Workspace preserved: $WORKSPACE"
    fi
    exit $exit_code
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Run the Python orchestrator
# ---------------------------------------------------------------------------
# Run from the e2e/ directory so uv picks up e2e/pyproject.toml (which has
# pydantic as a dependency used by the MCP server libraries).
cd "$SCRIPT_DIR"
uv run python "$SCRIPT_DIR/run-e2e.py" --workspace "$WORKSPACE" "${FORWARD_ARGS[@]}"
