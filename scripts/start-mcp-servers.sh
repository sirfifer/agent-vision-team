#!/bin/bash
#
# Start MCP Servers for Dogfooding Tests
# This script starts both the Knowledge Graph and Quality MCP servers
# with proper health checks and PID tracking.
#

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Starting MCP Servers for Dogfood Testing ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Start Knowledge Graph server
echo "Starting Knowledge Graph server on port 3101..."
cd "$PROJECT_ROOT/mcp-servers/knowledge-graph"
uv run python -m collab_kg.server > /tmp/kg-server.log 2>&1 &
KG_PID=$!
echo "  PID: $KG_PID"
echo "  Log: /tmp/kg-server.log"

# Wait for KG server to initialize
sleep 3

# Start Quality server
echo ""
echo "Starting Quality server on port 3102..."
cd "$PROJECT_ROOT/mcp-servers/quality"
uv run python -m collab_quality.server > /tmp/quality-server.log 2>&1 &
QUALITY_PID=$!
echo "  PID: $QUALITY_PID"
echo "  Log: /tmp/quality-server.log"

# Wait for Quality server to initialize
sleep 3

# Health checks
echo ""
echo "Verifying server health..."

if curl -s http://localhost:3101/health > /dev/null 2>&1; then
    echo "  ✓ Knowledge Graph server: HEALTHY (port 3101)"
else
    echo "  ✗ Knowledge Graph server: DOWN"
    echo "    Check /tmp/kg-server.log for errors"
    exit 1
fi

if curl -s http://localhost:3102/health > /dev/null 2>&1; then
    echo "  ✓ Quality server: HEALTHY (port 3102)"
else
    echo "  ✗ Quality server: DOWN"
    echo "    Check /tmp/quality-server.log for errors"
    exit 1
fi

echo ""
echo "=== MCP Servers Started Successfully ==="
echo ""
echo "Server PIDs:"
echo "  Knowledge Graph: $KG_PID"
echo "  Quality: $QUALITY_PID"
echo ""
echo "To stop servers, run:"
echo "  ./scripts/stop-mcp-servers.sh"
echo "  or: kill $KG_PID $QUALITY_PID"
echo ""
echo "Logs:"
echo "  tail -f /tmp/kg-server.log"
echo "  tail -f /tmp/quality-server.log"
