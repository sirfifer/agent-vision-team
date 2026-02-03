#!/bin/bash
#
# Stop MCP Servers
# Clean shutdown of Knowledge Graph and Quality servers
#

echo "Stopping MCP servers..."

# Kill processes by name
pkill -f "collab_kg.server" && echo "  ✓ Knowledge Graph server stopped" || echo "  - Knowledge Graph server not running"
pkill -f "collab_quality.server" && echo "  ✓ Quality server stopped" || echo "  - Quality server not running"

echo ""
echo "Servers stopped."
