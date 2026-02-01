#!/bin/bash
#
# Start both MCP servers for Collaborative Intelligence System
#
# Usage: ./start-servers.sh
#

echo "Starting Collaborative Intelligence MCP Servers..."
echo ""

# Start Knowledge Graph server in background
echo "Starting Knowledge Graph server on port 3101..."
cd mcp-servers/knowledge-graph
uv run python -m collab_kg.server > ../../kg-server.log 2>&1 &
KG_PID=$!
cd ../..

# Wait a moment for server to start
sleep 2

# Start Quality server in background
echo "Starting Quality server on port 3102..."
cd mcp-servers/quality
uv run python -m collab_quality.server > ../../quality-server.log 2>&1 &
QUALITY_PID=$!
cd ../..

# Wait a moment for server to start
sleep 2

# Check if servers are running
echo ""
echo "Checking server health..."

if curl -s http://localhost:3101/health > /dev/null 2>&1; then
  echo "✓ Knowledge Graph server is running (PID: $KG_PID)"
else
  echo "✗ Knowledge Graph server failed to start"
  echo "  Check kg-server.log for errors"
fi

if curl -s http://localhost:3102/health > /dev/null 2>&1; then
  echo "✓ Quality server is running (PID: $QUALITY_PID)"
else
  echo "✗ Quality server failed to start"
  echo "  Check quality-server.log for errors"
fi

echo ""
echo "Server PIDs:"
echo "  Knowledge Graph: $KG_PID"
echo "  Quality: $QUALITY_PID"
echo ""
echo "To stop servers:"
echo "  kill $KG_PID $QUALITY_PID"
echo ""
echo "Logs:"
echo "  Knowledge Graph: kg-server.log"
echo "  Quality: quality-server.log"
echo ""
echo "Servers are running in background. Close this terminal to keep them running."
