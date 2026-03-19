#!/usr/bin/env bash
# mcp_import_check.sh -- Verify all MCP server modules can be imported
# Exit 0 = all importable, Exit 1 = import failure
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

SERVERS=("knowledge-graph:collab_kg" "quality:collab_quality" "governance:collab_governance")
FAILED=()

for entry in "${SERVERS[@]}"; do
    dir="${entry%%:*}"
    module="${entry##*:}"
    server_dir="$PROJECT_DIR/mcp-servers/$dir"

    if [[ ! -d "$server_dir" ]]; then
        FAILED+=("$dir (directory not found)")
        continue
    fi

    if ! uv run --directory "$server_dir" python -c "import $module" 2>/dev/null; then
        FAILED+=("$dir ($module import failed)")
    fi
done

if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo "FAILED: Import failures: ${FAILED[*]}"
    exit 1
fi

echo "PASSED: All 3 MCP server modules importable"
exit 0
