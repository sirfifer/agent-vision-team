#!/bin/bash
set -e

# ── Configuration ─────────────────────────────────────────────────────────

PROJECT_DIR="${PROJECT_DIR:-/project}"
export CLAUDE_PROJECT_DIR="$PROJECT_DIR"
export CLAUDE_CODE_ENABLE_TASKS="true"
export CLAUDE_CODE_TASK_LIST_ID="${CLAUDE_CODE_TASK_LIST_ID:-avt-container}"

echo "=== AVT Gateway Container ==="
echo "Project directory: $PROJECT_DIR"

# ── Clone repo if needed ──────────────────────────────────────────────────

if [ -n "$GIT_REPO_URL" ] && [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "Cloning $GIT_REPO_URL..."
    git clone "${GIT_REPO_URL}" "$PROJECT_DIR"
    if [ -n "$GIT_BRANCH" ]; then
        cd "$PROJECT_DIR" && git checkout "$GIT_BRANCH"
    fi
fi

# ── Generate self-signed TLS cert if needed ───────────────────────────────

TLS_CERT="${TLS_CERT_PATH:-/etc/ssl/certs/avt.crt}"
TLS_KEY="${TLS_KEY_PATH:-/etc/ssl/private/avt.key}"

if [ ! -f "$TLS_CERT" ]; then
    echo "Generating self-signed TLS certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$TLS_KEY" \
        -out "$TLS_CERT" \
        -subj "/CN=avt-gateway" \
        2>/dev/null || echo "Warning: could not generate TLS cert (openssl may not be installed)"
fi

# ── Start MCP servers ────────────────────────────────────────────────────

echo "Starting MCP servers..."

cd "$PROJECT_DIR"

# Knowledge Graph (port 3101)
uv run --directory mcp-servers/knowledge-graph python -m collab_kg.server &
KG_PID=$!

# Quality (port 3102)
uv run --directory mcp-servers/quality python -m collab_quality.server &
QUALITY_PID=$!

# Governance (port 3103)
uv run --directory mcp-servers/governance python -m collab_governance.server &
GOVERNANCE_PID=$!

# Wait for servers to be ready
echo "Waiting for MCP servers..."
for port in 3101 3102 3103; do
    for i in $(seq 1 30); do
        if curl -s "http://localhost:$port/sse" >/dev/null 2>&1; then
            echo "  Port $port ready"
            break
        fi
        sleep 1
    done
done

# ── Start Gateway ─────────────────────────────────────────────────────────

echo "Starting AVT Gateway..."
cd /workspace/server
PROJECT_DIR="$PROJECT_DIR" uv run uvicorn avt_gateway.app:app --host 0.0.0.0 --port 8080 &
GATEWAY_PID=$!

sleep 2
echo "Gateway started on port 8080"

# ── Start Nginx (foreground, keeps container alive) ───────────────────────

echo "Starting Nginx..."
echo "=== AVT Gateway ready ==="
echo "Access the dashboard at https://localhost"

nginx -g "daemon off;"
