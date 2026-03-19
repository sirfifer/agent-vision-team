#!/usr/bin/env bash
# mcp_config_check.sh -- Verify MCP servers are defined at user scope
# Exit 0 = all servers found, Exit 1 = missing servers
set -euo pipefail

MCP_CONFIG="$HOME/.claude/mcp.json"
REQUIRED_SERVERS=("collab-kg" "collab-quality" "collab-governance")

if [[ ! -f "$MCP_CONFIG" ]]; then
    echo "FAILED: $MCP_CONFIG does not exist"
    exit 1
fi

# Validate JSON
if ! python3 -c "import json; json.load(open('$MCP_CONFIG'))" 2>/dev/null; then
    echo "FAILED: $MCP_CONFIG is not valid JSON"
    exit 1
fi

MISSING=()
for server in "${REQUIRED_SERVERS[@]}"; do
    if ! python3 -c "
import json, sys
data = json.load(open('$MCP_CONFIG'))
servers = data.get('mcpServers', {})
if '$server' not in servers:
    sys.exit(1)
" 2>/dev/null; then
        MISSING+=("$server")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "FAILED: Missing MCP servers in $MCP_CONFIG: ${MISSING[*]}"
    exit 1
fi

echo "PASSED: All 3 MCP servers defined at user scope (${REQUIRED_SERVERS[*]})"
exit 0
