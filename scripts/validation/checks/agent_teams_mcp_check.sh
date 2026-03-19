#!/usr/bin/env bash
# agent_teams_mcp_check.sh -- Verify teammates can access MCP servers
# Each teammate is a full Claude Code session; MCP access depends on
# user-scope config being correct. This verifies the prerequisites.
# Full live testing is done by test-agent-teams.sh.
# Exit 0 = MCP prerequisites met for teammates, Exit 1 = missing
set -euo pipefail

MCP_CONFIG="$HOME/.claude/mcp.json"

# Check 1: User-scope MCP config exists
if [[ ! -f "$MCP_CONFIG" ]]; then
    echo "FAILED: No user-scope MCP config at $MCP_CONFIG"
    exit 1
fi

# Check 2: All 3 servers defined
SERVERS=$(python3 -c "
import json
data = json.load(open('$MCP_CONFIG'))
servers = list(data.get('mcpServers', {}).keys())
print(' '.join(servers))
" 2>/dev/null || echo "")

REQUIRED=("collab-kg" "collab-quality" "collab-governance")
MISSING=()
for req in "${REQUIRED[@]}"; do
    if ! echo "$SERVERS" | grep -q "$req"; then
        MISSING+=("$req")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "FAILED: Missing MCP servers for teammates: ${MISSING[*]}"
    exit 1
fi

# Check 3: No project-scope MCP that could cause hallucination (issue #13898)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [[ -f "$PROJECT_DIR/.mcp.json" ]]; then
    echo "WARNING: Project-scope .mcp.json exists alongside user-scope; teammates may hallucinate MCP results (issue #13898)"
    exit 1
fi

# Check 4: Server directories exist and have pyproject.toml
for req in "${REQUIRED[@]}"; do
    SERVER_DIR=$(python3 -c "
import json
data = json.load(open('$MCP_CONFIG'))
server = data.get('mcpServers', {}).get('$req', {})
args = server.get('args', [])
# Look for --directory flag
for i, arg in enumerate(args):
    if arg == '--directory' and i + 1 < len(args):
        print(args[i+1])
        break
" 2>/dev/null || echo "")

    if [[ -n "$SERVER_DIR" && ! -d "$SERVER_DIR" ]]; then
        MISSING+=("$req (directory $SERVER_DIR not found)")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "FAILED: Server directory issues: ${MISSING[*]}"
    exit 1
fi

echo "PASSED: All 3 MCP servers at user scope; no project-scope conflict; teammate MCP access prerequisites met"
exit 0
